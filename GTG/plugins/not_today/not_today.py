# -*- coding: utf-8 -*-
# Copyright (c) 2012 - Lionel Dricot <lionel@ploum.net>

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

import gtk
from GTG.tools.dates import Date
from GTG import _
from GTG.core.task import Task

class notToday:

    def __init__(self):
        self.plugin_api = None
        self.tb_button = None
        self.tb_button2 = None

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.req = self.plugin_api.get_requester()
        self._init_gtk()
        self.plugin_api.set_active_selection_changed_callback(self.selection_changed)

    def mark_not_today(self, button):
        start_date = Date.parse("tomorrow")
        for tid in self.plugin_api.get_selected():
            task = self.req.get_task(tid)
            task.set_start_date(start_date)

    def task_cb(self, widget, plugin_api, task):
        start_date = Date.parse("tomorrow")
        task.set_start_date(start_date)
        plugin_api.get_view_manager().close_task(task.get_id())

    def mark_next_week(self, button):
        start_date = Date.parse("+7d")
        for tid in self.plugin_api.get_selected():
            task = self.req.get_task(tid)
            task.set_start_date(start_date)

    def task_cb2(self, widget, plugin_api, task):
        start_date = Date.parse("+7d")
        task.set_start_date(start_date)
        plugin_api.get_view_manager().close_task(task.get_id())

    def selection_changed(self, selection):
        if selection.count_selected_rows() > 0:
            self.tb_button.set_sensitive(True)
            self.tb_button2.set_sensitive(True)
        else:
            self.tb_button.set_sensitive(False)
            self.tb_button2.set_sensitive(False)

## GTK FUNCTIONS ##############################################################
    def _init_gtk(self):
        """ Initialize all the GTK widgets """

        self.tb_button = gtk.ToolButton()
        self.tb_button.set_sensitive(False)
        self.tb_button.set_icon_name("document-revert")
        self.tb_button.set_is_important(True)
        do_it_tomorrow=_("Do it tomorrow");
        self.tb_button.set_label(do_it_tomorrow);
        self.tb_button.set_tooltip_text(do_it_tomorrow);
        self.tb_button.connect('clicked', self.mark_not_today)
        self.tb_button.show()
        self.plugin_api.add_toolbar_item(self.tb_button)

        self.tb_button2 = gtk.ToolButton()
        self.tb_button2.set_sensitive(False)
        self.tb_button2.set_icon_name("media-skip-forward")
        self.tb_button2.set_is_important(True)
        next_week=_("Defer Till Next Week");
        self.tb_button2.set_label(next_week);
        self.tb_button2.set_tooltip_text(do_it_tomorrow);
        self.tb_button2.connect('clicked', self.mark_next_week)
        self.tb_button2.show()
        self.plugin_api.add_toolbar_item(self.tb_button2)

    def onTaskOpened(self, plugin_api):
        # get the opened task
        task = plugin_api.get_ui().get_task()

        if task.get_status() == Task.STA_ACTIVE:
            # add buttons
            self.taskbutton = gtk.ToolButton()
            #self.decide_button_mode(self.taskbutton, task)
            self.taskbutton.connect('clicked', self.task_cb, plugin_api, task)
            self.taskbutton.set_tooltip_text(_("Do it tomorrow"));
            self.taskbutton.set_icon_name("document-revert")
            self.taskbutton.show()
            plugin_api.add_toolbar_item(self.taskbutton)

            self.taskbutton2 = gtk.ToolButton()
            #self.decide_button_mode(self.taskbutton2, task)
            self.taskbutton2.connect('clicked', self.task_cb2, plugin_api, task)
            self.taskbutton2.set_tooltip_text(_("Defer Till Next Week"));
            self.taskbutton2.set_icon_name("media-skip-forward")
            self.taskbutton2.show()
            plugin_api.add_toolbar_item(self.taskbutton2)

    def deactivate(self, plugin_api):
        """ Remove Toolbar Button """
        if plugin_api.is_browser():
            if self.tb_button:
                self.plugin_api.remove_toolbar_item(self.tb_button)
                self.tb_button = False
            if self.tb_button2:
                self.plugin_api.remove_toolbar_item(self.tb_button2)
                self.tb_button2 = False
        else:
            if self.taskbutton:
                self.plugin_api.remove_toolbar_item(self.taskbutton)
                self.taskbutton = False
            if self.taskbutton2:
                self.plugin_api.remove_toolbar_item(self.taskbutton2)
                self.taskbutton2 = False




