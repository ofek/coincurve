#!/bin/bash

set -e -x

build_dll() {
    ./autogen.sh
    echo "LDFLAGS = -no-undefined" >> Makefile.am
    ./configure --host=$1 --enable-module-recovery --enable-experimental --enable-module-ecdh --disable-shared --enable-static --disable-dependency-tracking --with-pic --enable-benchmark=no
    make
}

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
