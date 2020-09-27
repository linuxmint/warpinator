%define name warpinator
%define version 1.0.8
%define release 3

Summary: Send and Receive Files across the Network
Name: %{name}
Version: %{version}
Release: %{release}
License: GPL
Group: Utilities
Source: %{name}-%{version}.tar.gz
URL: https://github.com/linuxmint/warpinator
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
# not relocatable because the data file packages depend upon the location
# of the data files in this package

Requires: python3-grpcio python3-cryptography python3-netifaces python3-pynacl python3-zeroconf python3-google-api-core python3-packaging python3-xapp python3-xapps-overrides python3-setproctitle
BuildRequires: gcc make autoconf automake ninja-build meson python3-grpcio polkit-devel gettext libappstream-glib gtk-update-icon-cache

%description
Warpinator allows you to easily connect multiple computers
on a local area network and share files quickly and securely.

%global debug_package %{nil}

%prep
%setup -q

%build
meson builddir --prefix=%{buildroot}/usr
ninja -C builddir

%install
ninja -C builddir install
mv %{buildroot}/usr/etc %{buildroot}/etc
mkdir -p %{buildroot}/%{_docdir}/warpinator/
echo "0" > %{buildroot}/%{_docdir}/warpinator/AUTHORS
echo "0" > %{buildroot}/%{_docdir}/warpinator/INSTALL.Unix
cp README.md %{buildroot}/%{_docdir}/warpinator/README
echo "0" > %{buildroot}/%{_docdir}/warpinator/MML.html
echo "0" > %{buildroot}/%{_docdir}/warpinator/Lua.html
find %{buildroot} -type f -exec sed -i -e 's,%{buildroot},,g' {} \;
find %{buildroot} -iname *.py -exec sed -i -e 's,%{buildroot},,g' {} \;
find %{buildroot} -iname warpinator -exec sed -i -e 's,%{buildroot},,g' {} \;

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%doc AUTHORS COPYING INSTALL.Unix README docs/MML.html docs/Lua.html
%{_bindir}/warpinator
%{_datadir}/icons/hicolor/*/apps/*Warpinator*
%{_datadir}/icons/hicolor/icon-theme.cache
%{_datadir}/glib-2.0/schemas/gschemas.compiled
%{_datadir}/glib-2.0/schemas/org.x.Warpinator.gschema.xml
%{_datadir}/applications/warpinator.desktop
%{_datadir}/locale/*/LC_MESSAGES/warpinator.mo
%{_datadir}/metainfo/warpinator.appdata.xml
%{_datadir}/polkit-1/actions/org.x.warpinator.policy
%{_datadir}/warpinator/*
%{_libexecdir}/warpinator/*.py
%{_libexecdir}/warpinator/firewall/ufw-modify
%{_sysconfdir}/xdg/autostart/warpinator-autostart.desktop


%changelog
* Mon Sep 07 2020 Elagost <me@elagost.com>
- Created spec file
