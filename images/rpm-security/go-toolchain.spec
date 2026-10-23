Name:           aax-go-toolchain
Version:        1.27.3
Release:        1.el9.aax.1
Summary:        Pinned Go toolchain for isolated AAX source builds
License:        BSD-3-Clause
URL:            https://go.dev/
Provides:       golang = %{version}
Provides:       golang-bin = %{version}
Provides:       golang-src = %{version}
AutoReqProv:    no
%global debug_package %{nil}

%description
The complete pinned Go distribution used only in the AAX RPM build stage.

%prep

%build
GOROOT=/opt/aax-go /opt/aax-go/bin/go version | grep -F 'go version go%{version} '

%install
mkdir -p %{buildroot}/opt %{buildroot}/usr/bin
cp -a /opt/aax-go %{buildroot}/opt/
ln -s /opt/aax-go/bin/go %{buildroot}/usr/bin/go
ln -s /opt/aax-go/bin/gofmt %{buildroot}/usr/bin/gofmt

%files
/opt/aax-go
/usr/bin/go
/usr/bin/gofmt
