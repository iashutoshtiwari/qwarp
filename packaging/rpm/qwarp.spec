Name:           qwarp
Version:        0.9.2
Release:        1%{?dist}
Summary:        A lightweight, Wayland-native Qt6 wrapper for Cloudflare WARP
License:        MIT
URL:            https://github.com/iashutoshtiwari/qwarp
Source0:        %{name}-%{version}-source.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-build
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  pyproject-rpm-macros
BuildRequires:  qt6-linguist
Requires:       python3
Requires:       python3-pyqt6
Requires:       cloudflare-warp

%description
QWarp is an unofficial, Linux-only PyQt6 GUI for the Cloudflare WARP client.
It is intended to remain lightweight, Wayland-native, usable on X11, and suitable
for both Python package and frozen PyInstaller builds.

%prep
%setup -q -n %{name}-%{version}

%build
bash scripts/build_locales.sh
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files qwarp

install -Dm644 qwarp.desktop %{buildroot}%{_datadir}/applications/qwarp.desktop
install -Dm644 src/qwarp/assets/app-icon.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/qwarp.svg

%files -n qwarp -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/qwarp
%{_datadir}/applications/qwarp.desktop
%{_datadir}/icons/hicolor/scalable/apps/qwarp.svg

%changelog
* Mon Aug 31 2026 Ashutosh Tiwari <contact@ashutoshtiwari.dev> - 0.9.2-1
- Improve installation and contributor documentation and remove unused files

* Sun Aug 30 2026 Ashutosh Tiwari <contact@ashutoshtiwari.dev> - 0.9.1-1
- Harden asynchronous state, settings, lifecycle, and release handling

* Sat Aug 29 2026 Ashutosh Tiwari <contact@ashutoshtiwari.dev> - 0.9.0-1
- Initial RPM release for 0.9.0
