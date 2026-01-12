#!/bin/bash

pyv="3.13.7"
dist="/tmp/build"
build="$dist/build.tar.gz"

echo "install required python"
dnf -y install gcc openssl-devel bzip2-devel libffi-devel \
    zlib-devel wget make xz sudo git
dnf -y remove python3-pip
wget "https://www.python.org/ftp/python/$pyv/Python-$pyv.tar.xz"
tar -xf "Python-$pyv.tar.xz"
cd "Python-$pyv" && ./configure --enable-optimizations
make -j "$(nproc)" && make install
rm -f /usr/bin/python && ln -s /usr/local/bin/python3 /usr/bin/python
python -V
cd ..
echo "finished python"
python -m pip install "$build"
echo "install playwright"
dnf -y install nspr nss dbus-libs at-spi2-atk atk libX11 libXcomposite libXdamage \
    libXext libXfixes libXrandr mesa-libgbm libxcb \
    alsa-lib cups-libs xkeyboard-config cairo pango \
    libxkbcommon
playwright install chromium
rm -rf "$dist"
dnf -y remove git
echo "project installed"
