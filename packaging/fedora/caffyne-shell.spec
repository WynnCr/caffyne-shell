Name:           caffyne-shell
Version:        1.0.0
Release:        1%{?dist}
Summary:        A modern, GTK-based desktop shell built on top of Fabric

License:        GPL-3.0-only
URL:            https://github.com/caffyne-org/caffyne-shell
Source0:        %{name}-%{version}.tar.gz

BuildArch:      x86_64

BuildRequires:  python3-devel
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  wayland-devel
BuildRequires:  gtk3-devel

# Python dependencies
Requires:       python3-fabric
Requires:       fabric-cli
Requires:       python3-cffi
Requires:       python3-click
Requires:       python3-loguru
Requires:       python3-pam
Requires:       python3-pillow
Requires:       python3-psutil
Requires:       python3-pycairo
Requires:       python3-pycparser
Requires:       python3-gobject
Requires:       python3-rapidfuzz
Requires:       python3-setproctitle
Requires:       python3-six
Requires:       python3-thefuzz

# System packages
Requires:       gtk-layer-shell
Requires:       libdbusmenu-gtk3
Requires:       cinnamon-desktop
Requires:       gnome-bluetooth
Requires:       matugen
Requires:       playerctl
Requires:       brightnessctl
Requires:       wf-recorder
Requires:       upower
Requires:       NetworkManager
Requires:       bluez

# FHS workaround for python modules, I really hate non FHS stuff on nixos
%global __os_install_post %{nil}

%description
caffyne shell is a modern, GTK-based desktop shell built on top of Fabric, Python, and GTK.
It features a highly customizable drag-and-drop panel, fluid animations, and deeply integrated system applets designed specifically for modern Wayland compositors.

%prep
%autosetup -n %{name}-%{version}

%build
pushd snippets/blur/lib
make %{?_smp_mflags}
popd

pushd snippets/hacktk/lib
make %{?_smp_mflags}
popd

%install
mkdir -p %{buildroot}/usr/share/caffyne-shell
mkdir -p %{buildroot}/usr/bin

cp -r assets bar_widgets config greetd icons lightdm matugen services snippets sounds style svgs themes utils wallpapers windows bar.py lockscreen.py main.py plugin_loader.py user_options.py %{buildroot}/usr/share/caffyne-shell/

cp packaging/fedora/startcaffyneshell %{buildroot}/usr/bin/startcaffyneshell
chmod +x %{buildroot}/usr/bin/startcaffyneshell

chmod +x %{buildroot}/usr/share/caffyne-shell/snippets/blur/lib/libblur.so
chmod +x %{buildroot}/usr/share/caffyne-shell/snippets/hacktk/lib/libhacktk.so

%files
/usr/share/caffyne-shell/
/usr/bin/startcaffyneshell

%changelog
* Fri Jul 03 2026 Maintainer <amritanshukumar13012008@gmail.com> - 1.0.0-1
- First packaging for Fedora COPR.
