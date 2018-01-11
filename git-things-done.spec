%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           git-things-done
Version:        0.4.9
Release:        16%{?dist}
Summary:        Personal organizer for the GNOME desktop

Group:          Applications/Productivity
License:        GPLv3+
URL:            https://github.com/Osndok/git-things-done/
BuildArch:      noarch
Source0:        https://github.com/Osndok/git-things-done/archive/v%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  python-devel
BuildRequires:  gettext
BuildRequires:  desktop-file-utils
BuildRequires:  pyxdg
Requires:       pygtk2 pygtk2-libglade python-configobj pyxdg pycairo gnome-python2-gnome
Requires:       python-liblarch >= 2.1.0
Requires:       python-liblarch_gtk
Requires:       dbus-python
Requires:       hicolor-icon-theme

# For RTM backend
Requires:       python-dateutil
# Bugzilla backend?
Requires:       notify-python

# One day, the two shall live in harmony!
# But for the moment, the two projects are not even separated enough to avoid conflicting files.
Conflicts:      gtg

%description
Getting Things GNOME! (GTG) is a personal organizer for the GNOME desktop
environment inspired by the Getting Things Done (GTD) methodology. GTG is
designed with flexibility, adaptability, and ease of use in mind so it can be
used as more than just GTD software.

"GIT Things Done" (GTD) is a fork of GTG with several goals to boost
productivity & improve the underlying datamodel. Particularly by using
an easily introspectible git-based storage backend (rather than a sqlite
backend), and not trying to move to gtk3.

%prep
%setup -q -n "git-things-done-%{version}"
sed -i -e "s|#!/usr/bin/env python||" GTG/gtg.py


%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT
rm -rf $RPM_BUILD_ROOT/%{python_sitelib}/GTG/plugins/geolocalized_tasks
rm -rf $RPM_BUILD_ROOT/%{python_sitelib}/GTG/plugins/geolocalized-tasks.gtg-plugin
desktop-file-validate $RPM_BUILD_ROOT/%{_datadir}/applications/%{name}.desktop

%find_lang gtd --with-gnome

mkdir ${RPM_BUILD_ROOT}%{_datadir}/gtd

%clean
rm -rf $RPM_BUILD_ROOT


%post
touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%posttrans
gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :


%files -f gtd.lang
%defattr(-,root,root,-)
%doc AUTHORS CHANGELOG LICENSE README
%{_bindir}/gtd
%{_bindir}/gtd-cli
%{_bindir}/gtd-new-task
%{_datadir}/dbus-1/services/org.gnome.GTD.service
%{_datadir}/appdata/%{name}.appdata.xml
%{_datadir}/applications/%{name}.desktop
%{_datadir}/gtd
%{python_sitelib}/*
%{_mandir}/man1/*.1.gz
%{_datadir}/icons/hicolor/*/apps/gtd*
%{_datadir}/icons/hicolor/*/actions/gtd*
%{_datadir}/icons/hicolor/*/categories/gtd*
%{_datadir}/icons/hicolor/*/emblems/gtd*
%{_datadir}/icons/hicolor/svg/gtd*
%{_datadir}/icons/ubuntu-mono-dark/
%{_datadir}/icons/ubuntu-mono-light/


%changelog
* Wed Dec 20 2017 Robert Hailey <git AT osndok DOT com> - 0.3.1-15
- Appropriated Fedora's fine gtg.spec file for new gtg fork

* Tue Nov 21 2017 Ankur Sinha <ankursinha AT fedoraproject DOT org> - 0.3.1-14
- Rebuild for liblarch update

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.3.1-13
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.3.1-12
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-11
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 0.3.1-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Sun Jan 10 2016 Ankur Sinha <ankursinha AT fedoraproject DOT org> 0.3.1-9
- remove useless line with define macro

* Wed Dec 23 2015 Ankur Sinha <ankursinha AT fedoraproject DOT org> 0.3.1-8
- Add patch to remove pdftk dep. #1133565

* Tue Jul 28 2015 Ankur Sinha <ankursinha AT fedoraproject DOT org> 0.3.1-7
- Add notify Requires

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Mar 26 2015 Richard Hughes <rhughes@redhat.com> - 0.3.1-5
- Add an AppData file for the software center

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu Dec 26 2013 Ankur Sinha <ankursinha AT fedoraproject DOT org> 0.3.1-3
- Add optional dep for RTM backend. 

* Sun Dec 01 2013 Ankur Sinha <ankursinha AT fedoraproject DOT org> 0.3.1-2
- Update URL

* Wed Nov 27 2013 Ankur Sinha <ankursinha AT fedoraproject DOT org> 0.3.1-0
- Update to latest release

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Fri Nov  9 2012 Yanko Kaneti <yaneti@declera.com> 0.3-2
- Add missing requires on python-liblarch(_gtk)

* Fri Nov  9 2012 Yanko Kaneti <yaneti@declera.com> 0.3-1
- New upstream release - 0.3

* Wed Jul 18 2012 Yanko Kaneti <yaneti@declera.com> 0.2.4-8
- Add patch for crash bug 841179 (lp bug 744294)

* Thu Jun 14 2012 Yanko Kaneti <yaneti@declera.com> 0.2.4-7
- Remove the geolocalized_tasks plugin which uses pyclutter,
  which uses gtk3. Bug #817841

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.4-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.4-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Wed Jul 21 2010 David Malcolm <dmalcolm@redhat.com> - 0.2.4-3
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Thu Jun 10 2010 Yanko Kaneti <yaneti@declera.com> 0.2.4-2
- Avoid "RuntimeError: not holding the import lock" with recent pythons, from upstream
- Alternative X test, avoiding the xorg-x11-utils dependency
- Requires dbus-python

* Sun Apr 11 2010 Yanko Kaneti <yaneti@declera.com> 0.2.4-1
- New bugfix release from upstream

* Thu Mar 4 2010 Yanko Kaneti <yaneti@declera.com> 0.2.3-1
- "A bit of polishing." - from upstream

* Mon Mar 1 2010 Yanko Kaneti <yaneti@declera.com> 0.2.2-1
- New upstream release.
  http://gtg.fritalk.com/post/2010/03/01/Getting-Things-GNOME!-0.2.2-(Protector)-release-is-out!

* Fri Feb 19 2010 Yanko Kaneti <yaneti@declera.com> 0.2.1-3
- Fixup the last fixup. Again preventing crash on startup.

* Sun Feb 14 2010 Yanko Kaneti <yaneti@declera.com> 0.2.1-2
- Pull upstream fix for bug 565224. Prevents crash on startup

* Sun Jan 31 2010 Yanko Kaneti <yaneti@declera.com> 0.2.1-1
- Upstream bugfix release

* Sun Jan 31 2010 Yanko Kaneti <yaneti@declera.com> 0.2-3
- Pull an upstream fix for missing tomboy.ui - bug 560316

* Mon Dec 14 2009 Yanko Kaneti <yaneti@declera.com> 0.2-2
- 0.2 final.
  http://gtg.fritalk.com/post/2009/12/10/The-new-Getting-Things-GNOME!-0.2-Gorignak-has-landed!

* Thu Dec  3 2009 Yanko Kaneti <yaneti@declera.com> 0.1.9-1
- 0.2 beta.
  http://gtg.fritalk.com/post/2009/12/02/Getting-Things-GNOME!-0.1.9-is-out!
- Remove some no longer necessary patching
- BR: pyxdg

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.1.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Tue Jul 14 2009 Yanko Kaneti <yaneti@declera.com> 0.1.2-3
- Use %%{__python} instead of python

* Mon Jul 13 2009 Yanko Kaneti <yaneti@declera.com> 0.1.2-2
- Implement review feedback
  https://bugzilla.redhat.com/show_bug.cgi?id=510994#c1

* Mon Jul 13 2009 Yanko Kaneti <yaneti@declera.com> 0.1.2-1
- Initial packaging
