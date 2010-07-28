# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
#
"""
FilteredTree provides a filtered view (subset) of tasks

FilteredTree
============
The problem we have is that, sometimes, we don't want to display all tasks.
We want tasks to be filtered (workview, tags, …)

The expected approach would be to put a gtk.TreeModelFilter above our
TaskTree. Unfortunately, this doesn't work because TreeModelFilter hides
all children of hidden nodes (not what we want!)

The solution we have found is to insert a fake tree between Tree and
TaskTree.  This fake tree is called FilteredTree and maps path and node
methods to a result corresponding to the filtered tree.

Note that the nodes are not aware that they are in a filtered tree.
Use the FilteredTree methods, not the node methods directly.
If you believe a function would be useful in a filtered tree, don't 
hesitate to make a proposal.

To be more efficient, a quick way to optimize the FilteredTree is to cache
all answers in a dictionary so we don't have to compute the answer 
all the time. This is not done yet.

B{Warning}: this is very fragile. Calls to any GTK registered view should be
perfecly in sync with changes in the underlying model.
We definitely should develop some unit tests for this class.

Structure of the source:

 1. Standard tree functions mapping (get_node, get_all_nodes, get_all_keys)
 2. Receiving signal functions ( task-added,task-modified,task-deleted)
 3. Treemodel helper functions. To make it easy to build a treemodel on top.
 4. Filtering : is_displayed() and refilter()
 5. Changing the filters (not for the main FilteredTree)
 6. Private helpers.

There's one main FilteredTree that you can get through the requester. This
main FilteredTree uses the filters applied throughout the requester. This
allows plugin writers to easily get the current displayed tree (main view).

You can create your own filters on top of this main FilteredTree, or you
can create your own personal FilteredTree custom view and apply your own
filters on top of it without interfering with the main view.  (This is
how the closed tasks pane is currently built.)

For custom views, the plugin writers are able to get their own
FilteredTree and apply on it the filters they want. (this is not finished
yet but in good shape).

An important point to stress is that information needs to be passed from
bottom to top, with no horizontal communication at all between views.

"""
import Queue

import gobject

from GTG.tools.liblarch.tree import RootNode
from GTG.tools.logger import Log


COUNT_CACHING_ENABLED = True


class VirtualRootNode(RootNode):
    """A virtual root node for a filtered tree.
    
    The VirtualRootNode has the same ID as the root node of the *tree* passed
    to the constructor. It can be used to keep a list of 
    
    """
    def __init__(self, tree):
        RootNode.__init__(self, tree.root._type)
        self._tree = tree
        self._true_root = tree.root

    def _get_id(self):
        return self._tree.root.id


class FilteredTree(gobject.GObject):
    """A tree data structure with filtering.
    
    A FilteredTree has an associated MainTree and FiltersBank. Some Filters
    from the FiltersBank are applied to every node in the MainTree. The nodes
    are either 'filtered' (do not appear in the FilteredTree) or 'displayed'
    (do appear in the FilteredTree)
    
    If a MainTree node with children is filtered, then the layout of the
    FilteredTree is different, as follows: any displayed children of the
    filtered node are made children of a "virtual root".
    
    An example. In the tree:
    
     A
     `B
     `C
      `D
       `E
      `F
     G
    
    ...suppose node C is filtered. Then D and F have no parent in the
    FilteredTree, so they become children of the "virtual root". The
    FilteredTree layout is:
    
    A
    `B
    D
    `E
    F
    G
    
    """
    #Those are the three signals you want to catch if displaying
    #a filteredtree. The argument of all signals is the tid of the task
    __gsignals__ = {'node-added-inview': (gobject.SIGNAL_RUN_FIRST, \
                                          gobject.TYPE_NONE, (str, )),
                    'node-deleted-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),
                    'node-modified-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),}

    def __init__(self, tree, filtersbank, refresh=True):
        """
        Construct a FilteredTree object on top of an existing task tree.
        @param req: The requestor object
        @param tree: The tree to filter from
        @param maintree: Whether this tree is the main tree.  The requester
        must be used to change filters against the main tree.
        """
        gobject.GObject.__init__(self)
        self.applied_filters = []
        self.tree = tree
        self.fbank = filtersbank
        self.update_count = 0
        self.add_count = 0
        self.remove_count = 0
        self.__nodes_count = 0
        self.flat = False
        # virtual root is the list of root nodes
        # initially, they are the root nodes of the original tree
        self.vroot = VirtualRootNode(self.tree)
        self.displayed_nodes = set()
        #This is for profiling
    #    self.using_cache = 0
        #useful for temp storage :
        self.__adding_lock = False
        # sets of nodes to process.
        # TODO: if order is important, change to Queue.Queue() or []
        self._to_modify = set()
        self._to_add = Queue.Queue()
        self._to_clean = Queue.Queue()
        self._cleaning = set()
        #an initial refilter is always needed if we don't apply a filter
        #for performance reason, we do it only if refresh = True
        self.__reset_cache()
        if refresh:
            self.refilter()
        # connect to signals
        self.tree.connect("node-added", self.__node_added)
        self.tree.connect("node-modified", self.__node_modified)
        self.tree.connect("node-deleted", self.__node_deleted)

    def __reset_cache(self):
        self.path_for_node_cache = {}
        self.counted_nodes = set()
        self.count_cache = {}

    #### Standard tree functions
    def get_node(self, id):
        """
        Retrieves the given node
        @param id: The tid of the task node
        @return: Node from the underlying tree
        """
        return self.tree.get_node(id)

    def get_root(self):
        """
        returns the root node
        """
        return self.tree.get_root()

    def get_all_nodes(self):
        """
        returns list of all displayed node keys
        """
        return list(self.displayed_nodes)

    def get_n_nodes(self, withfilters=[], include_transparent=True):
        """Return the number of displayed nodes in the tree.
        
        If the withfilters is set, returns the quantity of nodes
        that will be displayed if we apply those filters to the current
        tree. It means that the currently applied filters are also taken into
        account.
        
        If include_transparent=False, we only take into account the applied
        filters that doesn't have the transparent parameters.
        
        """
        toreturn = 0
        usecache = False
        if not include_transparent:
            #Currently, the cache only work for one filter
            if len(withfilters) == 1:
                usecache = True
            zelist = self.counted_nodes
        else:
            zelist = self.displayed_nodes
        if len(withfilters) > 0:
            key = "".join(withfilters)
            if usecache and self.count_cache.has_key(key):
                toreturn = self.count_cache[key]
#                self.using_cache += 1
#                print "we used cache %s" %(self.using_cache)
            else:
                for tid in zelist:
                    node = self.tree.get_node(tid)
                    result = True
                    for f in withfilters:
                        filt = self.fbank.get_filter(f)
                        if filt:
                            result = result and filt.is_displayed(node)
                    if result:
                        toreturn += 1
                if COUNT_CACHING_ENABLED and usecache:
                    self.count_cache[key] = toreturn
        else:
            toreturn = len(zelist)
        return toreturn

    ### GObject signal callbacks
    def __node_added(self, sender, node_id):
        # these checks are in a specific order. __filter_node() is much slower,
        # so try it second
        if node_id not in self.displayed_nodes and self.__filter_node(node_id):
            self.__add_node(node_id)

    def __node_modified(self, sender, node_id):
        """Callback for the node-modified signal."""
        if node_id not in self._to_modify:
            self._to_modify.add(node_id)
            self.__update_node(node_id)
            self._to_modify.remove(node_id)

    def __node_deleted(self, sender, node_id):
        self.__clean_node(node_id)

    ####TreeModel functions ##############################
    def print_tree(self):
        print "displayed : %s" % self.displayed_nodes
        self.__print_from_node(self.vroot)

    #The path received is only for tasks that are displayed
    #We have to find the good node.
    def get_node_for_path(self, path=()):
        """
        Returns node for the given path.
        """
        #We should convert the path to the base.path
        if len(path) == 0:
            return self.tree.root
        else:
            # this line will raise KeyError if path[0] is too high
            node_id = self.vroot.children[path[0]]
            return self.__node_for_path(node_id, list(path[1:]))

    def __node_for_path(self, node_id, path):
        if len(path) == 0 or self.flat:
            return node_id
        else:
            index = path.pop(0)
            child_id = self.node_children(node_id)[index]
            return self.__node_for_path(child_id, path)

    def get_paths_for_node(self, node_id):
        """
        Return a list of paths for a given node
        Return an empty list if no path for that Node.
        """
        toreturn = []
        if node_id:
            node = self.get_node(node_id)
            pars = self.node_parents(node_id)
        else:
            return [()]

        def find_path(node_id):
            paths = []
            for parent_id in self.node_parents(node_id):
                i = self.get_node(parent_id).children.index(node_id)
                for parent_path in find_path(parent_id):
                    paths.append(tuple(list(parent_path) + [i]))
            if not len(paths):
                paths.append((self.vroot.children.index(node_id),))
            return paths
        
        result = find_path(node_id)
        return result

    #pid is used only if nid has multiple parents.
    #if pid is none, a random parent is used.
    def next_node(self, node_id, parent_id=None):
        """
        Returns the next sibling node, or None if there are no other siblings
        """
        #We should take the next good node, not the next base node
        toreturn = None
        if node_id in self.vroot.children:
            i = self.vroot.children.index(node_id) + 1
            if len(self.vroot.children) > i:
                nextnode_id = self.vroot.children[i]
                if nextnode_id in self.displayed_nodes:
                    toreturn = nextnode_id
        else:
            parents_nodes = self.node_parents(node_id).copy()
            if len(parents_nodes):
                if parent_id and parent_id in parents_nodes:
                    parent_node = parent_id
                else:
                    parent_node = parents_nodes.pop()
                total = self.node_n_children(parent_node)
                c = 0
                next_id = -1
                while c < total and next_id < 0:
                    child_id = self.node_nth_child(parent_node, c)
                    c += 1
                    if child_id == node_id:
                        next_id = c
                if next_id >= 0 and next_id < total:
                    toreturn = self.node_nth_child(parent_node, next_id)
        #check to see if our result is correct
        if toreturn and toreturn not in self.displayed_nodes:
            toreturn = None
        return toreturn

    #Done
    def node_children(self, parent):
        """
        Returns the first child node of the given parent, or None
        if the parent has no children.
        @param parent: The parent node or None to retrieve the children
        of the virtual root.
        """
        #print "on_iter_children for parent %s" %parent.get_id()
        #here, we should return only good childrens
        child = self.node_nth_child(parent,0)
        return child

    #Done
    def node_has_child(self, node_id=None):
        """Return True if the given node has any displayed children."""
        return not self.flat and self.node_n_children(node_id) > 0

    def node_n_children(self, node_id):
        return len(self.node_children(node_id))

    def node_children(self, node_id):
        """Return a list of displayed children for the node with ID *node_id*.
        
        The children are listed in the same order as they are in the unfiltered
        tree.
        
        """
        if self.flat:
            return []
        else:
            node = self.tree.get_node(node_id)
            if node.id == self.vroot.id:
                return self.vroot.children
            else:
                return filter(lambda c: c in self.displayed_nodes,
                  node.children)

    def node_nth_child(self, node_id, n):
        """Return the *n*th displayed child of the node with ID *node_id*."""
        if self.flat:
            return None
        else:
            return self.node_children(node_id)[n]

    def node_parents(self, node_id):
        """Return a set of IDs of all displayed parents of the node with ID
        *node_id*."""
        return self.displayed_nodes.intersection(
          self.tree.get_node(node_id).parents)

    #### Filtering methods #########
    def is_displayed(self, node_id):
        """
        This is a public method that return True if the node is
        currently displayed in the tree
        """
        if node_id:
            toreturn = node_id in self.displayed_nodes
        else:
            toreturn = False
        return toreturn

    def __is_displayed(self, node_id):
        """
        This is a private method that return True if the node *should*
        be displayed in the tree, regardless of its current status.
        """
        if node_id == self.vroot.id:
            return False
        else:
            result = True
            counting_result = True
            cache_key = ""
            node = self.tree.get_node(node_id)
            for filter_name in self.applied_filters:
                f = self.fbank.get_filter(filter_name)
                cache_key += filter_name
                temp = f.filter(node)
                result = result and temp
                if not f.get_parameter('transparent'):
                    counting_result = counting_result and temp
            if counting_result and node_id not in self.counted_nodes:
                #This is an hard custom optimisation for task counting
                #Normally, we would here reset the cache of counted tasks
                #But this slow down a lot the startup.
                #So, we update manually the cache.
                for k in self.count_cache.keys():
                    f = self.fbank.get_filter(k)
                    if f.filter(node):
                        self.count_cache[k] += 1
                self.counted_nodes.add(node_id)
            elif not counting_result and node_id in self.counted_nodes:
                #Removing node is less critical so we just reset the cache.
                self.count_cache = {}
                self.counted_nodes.remove(node_id)
            return result

    __filter_node = __is_displayed

    def refilter(self):
        """Rebuild the FilteredTree from scratch.
        
        This method should be called only when the set of applied filters is
        changed (i.e. only filters_bank should call it).
        
        """
        self.update_count = 0
        self.add_count = 0
        self.remove_count = 0
        self.__reset_cache()
        # the FilteredTree is flat if *any* applied filter is flat
        self.flat = False
        for filter_name in self.applied_filters:
            if self.fbank.get_filter(filter_name).is_flat():
                self.flat = True
                break
        # first empty the current tree
        self.__clean_tree()
        self.displayed_nodes = set()
        if len(self.vroot.children) != 0:
            print "self.vroot.children = %s after __clean_from_node" % self.vroot.children
        # list nodes that will be ultimately displayed
        for node_id in self.tree.get_all_nodes():
            if self.__filter_node(node_id):
                self._to_add.put_nowait(node_id)
        # finally, add them
        self.__add_nodes()

    ####### Change filters #################
    def apply_filter(self, filter_name, parameters={}, reset=False,
      refresh=True):
        """
        Applies a new filter to the tree.  Can't be called on the main tree.
        @param filter_name: The name of an already registered filter to apply
        @param parameters: Optional parameters to pass to the filter
        @param reset : optional boolean. Should we remove other filters?
        """
        if reset:
            self.applied_filters = []
        try:
            f = self.fbank.get_filter(filter_name)
            if len(parameters):
                f.set_parameters(parameters)
            if filter_name not in self.applied_filters:
                self.applied_filters.append(filter_name)
                if refresh:
                    self.refilter()
                return True
            else:
                return False
        except KeyError, e:
            # the requested filter doesn't exist
            raise e

    def unapply_filter(self, filter_name, refresh=True):
        """
        Removes a filter from the tree.  Can't be called on the main tree.
        @param filter_name: The name of an already added filter to remove
        """
        if filter_name in self.applied_filters:
            self.applied_filters.remove(filter_name)
            if refresh:
                self.refilter()
            return True
        else:
            return False

    def reset_filters(self, refresh=True):
        """
        Clears all filters currently set on the tree.  Can't be called on 
        the main tree.
        """
        self.applied_filters = []
        if refresh:
            self.refilter()

    def reset_tag_filters(self, refilter=True):
        """
        Clears all filters currently set on the tree.  Can't be called on 
        the main tree.
        """
        # TODO: this is tag-specific, remove
        if "notag" in self.applied_filters:
            self.applied_filters.remove('notag')
        if "no_disabled_tag" in self.applied_filters:
            self.applied_filters.remove('no_disabled_tag')
        for f in self.applied_filters:
            if f.startswith('@'):
                self.applied_filters.remove(f)
        if refilter:
            self.refilter()

    ### Private methods
    def __is_root(self, node_id):
        """Return True if a node should be a virtual root node.
        
        If none of the parents of the node with ID *node_id* will be displayed
        with 
        
        """
        is_root = True
        if not self.flat:
            for parent_id in self.tree.get_node(node_id).parents:
                if self.__filter_node(parent_id):
                    is_root = False
                    break
        return is_root

    def __update_node(self, node_id):
        """Update a node."""
        if node_id in self._cleaning:
            # prevent recursion
            return
        displayed = node_id in self.displayed_nodes
        if self.__filter_node(node_id):
            #if the task was not displayed previously but now should
            #we add it.
            if not displayed:
                self.__add_node(node_id)
            else:
                self.update_count += 1
                self.emit("node-modified-inview", node_id)
                #I don't remember why we have to update the children.
#                if not self.flat:
#                    for child_id in self.get_node(node_id).children:
#                        self.__update_node(child_id)
                # node should be & is displayed. Maybe it is updated because
                # its relationship changed?
                if self.__is_root(node_id):
                    if node_id not in self.vroot.children:
                        # the node became a virtual root node
                        self.vroot.children.append(node_id)
                else:
                    if node_id in self.vroot.children:
                        # the node moved out of the virtual root
                        self.vroot.children.remove(node_id)
        else:
            #if the task was displayed previously but shouldn't be anymore
            #we remove it
            if displayed:
                self.__clean_node(node_id)
            else:
                self.emit("node-deleted-inview", node_id)

    def __add_node(self, node_id):
        self._to_add.put_nowait(node_id)
        self.__adding_loop()

    def __add_nodes(self):
        """Add the node with ID *node_id* to the displayed nodes."""
        if not self.__adding_lock and not self._to_add.empty():
            self.__adding_lock = True
            self.__adding_loop()

    def __adding_loop(self):
        """Process nodes to be added until none are left."""
        try:
            while True:
                node_id = self._to_add.get_nowait()
                is_root = self.__is_root(node_id)
                # if the parent node(s) will be displayed, wait 'til at least
                # one is displayed
                if not is_root and len(self.node_parents(node_id)) == 0:
                    if self._to_add.empty():
                        # node_id is going to get recycled endlessly. Give up.
                        print "giving up on %s" % node_id
                        pass
                    else:
                        # try again later
                        self._to_add.put_nowait(node_id)
                        continue
                if is_root and node_id not in self.vroot.children:
                    # the node is going to be under the virtual root
                    self.vroot.children.append(node_id)
                # actually add the node
                self.add_count += 1
                self.__nodes_count += 1
                self.displayed_nodes.add(node_id)
                # should be in displayed_nodes before updating the root
                self.emit("node-added-inview", node_id)
        except Queue.Empty:
            self.__adding_lock = False

    #This function print the actual tree. Useful for debugging
    def __print_from_node(self, node, prefix='`— '):
        if node.id != self.vroot.id:
            paths = str(self.get_paths_for_node(node.id))
            children = self.node_children(node.id)
        else:
            paths = self.vroot.children
            children = self.vroot.children
        print "%s%s    (%s) " % (prefix, node.id, paths)
        for child_id in children:
            child = self.tree.get_node(child_id)
            self.__print_from_node(child, '  %s' % prefix)

    def __clean_tree(self):
        """Undisplay all nodes."""
        # a callback function to fill a queue
        def recursive_clean(node_id):
            for child_id in reversed(self.node_children(node_id)):
                recursive_clean(child_id)
            if node_id not in self._cleaning:
                self._to_clean.put_nowait(node_id)
                self._cleaning.add(node_id)
        # we could just use self.displayed_nodes here, but we want to remove
        # leaf nodes first
        for child_id in reversed(self.vroot.children):
            recursive_clean(child_id)
        try:
            # one at a time, get a node out of the queue and clean it
            while True:
                node_id = self._to_clean.get_nowait()
                self.__clean_node(node_id)
                self._cleaning.remove(node_id)
        except Queue.Empty:
            # when the queue is empty, we're done
            return

    def __clean_node(self, node_id):
        """Undisplay a single node."""
        is_root = False
        if node_id in self.displayed_nodes:
            is_root = self.__is_root(node_id)
            self.remove_count += 1
            self.__nodes_count -= 1
            self.emit('node-deleted-inview', node_id)
            self.displayed_nodes.remove(node_id)
        if node_id in self.vroot.children:
            self.vroot.children.remove(node_id)
        if node_id in self.counted_nodes:
            self.counted_nodes.remove(node_id)
            self.count_cache = {}
        # TODO: test if this is necessary
        if not is_root:
            #we don't need to update parents if the node is root
            #this might happen with flat filter
            for parent_id in self.node_parents(node_id):
                if parent_id not in self._cleaning:
                    self.__update_node(parent_id)

