#!/bin/bash
set -ex

build_dll() {
    ./autogen.sh
    echo "LDFLAGS = -no-undefined" >> Makefile.am
    ./configure --host=$1 --enable-module-recovery --enable-experimental --enable-module-ecdh --enable-benchmark=no --enable-tests=no --enable-openssl-tests=no --enable-exhaustive-tests=no --enable-static --disable-dependency-tracking --with-pic
    make
}

sudo apt-get install -y mingw-w64
sudo apt-get -f install

mkdir .hidden
cp * .hidden -R
mv .hidden/coincurve/_windows_libsecp256k1.py .hidden/coincurve/_libsecp256k1.py
mv .hidden ../clean

cd ..

curl -sLO "https://github.com/bitcoin-core/secp256k1/archive/$COINCURVE_UPSTREAM_REF.tar.gz"
tar -xzf "$COINCURVE_UPSTREAM_REF.tar.gz"
mv "secp256k1-$COINCURVE_UPSTREAM_REF" secp256k1

mv secp256k1 64bit
cp 64bit 32bit -R

cd 64bit
build_dll x86_64-w64-mingw32
mv .libs/libsecp256k1-0.dll ../clean/coincurve/libsecp256k1.dll
cd ../clean
python setup.py bdist_wheel --plat-name=win_amd64
rm coincurve/libsecp256k1.dll

cd ../32bit
build_dll i686-w64-mingw32
mv .libs/libsecp256k1-0.dll ../clean/coincurve/libsecp256k1.dll
cd ../clean
python setup.py bdist_wheel --plat-name=win32

mv dist/* ../coincurve/dist/
cd ../coincurve
