#!/bin/bash
set -ex

build_dll() {
    ./autogen.sh
    ./configure --host=$1 --enable-module-recovery --enable-experimental --enable-module-ecdh --enable-module-extrakeys --enable-module-schnorrsig --enable-benchmark=no --enable-tests=no --enable-exhaustive-tests=no --enable-static --disable-dependency-tracking --with-pic
    make
}

sudo apt-get install -y mingw-w64
sudo apt-get -f install

mkdir .hidden
cp * .hidden -R
mv .hidden/src/coincurve/_windows_libsecp256k1.py .hidden/src/coincurve/_libsecp256k1.py
mv .hidden ../clean

cd ..

curl -sLO "https://github.com/bitcoin-core/secp256k1/archive/$COINCURVE_UPSTREAM_REF.tar.gz"
tar -xzf "$COINCURVE_UPSTREAM_REF.tar.gz"
mv "secp256k1-$COINCURVE_UPSTREAM_REF" secp256k1

mv secp256k1 64bit
cp 64bit 32bit -R

cd 64bit
build_dll x86_64-w64-mingw32
# As the API changes, the -x.dll will change to -y.dll, so we use a wildcard
mv .libs/libsecp256k1-?.dll ../clean/src/coincurve/libsecp256k1.dll
cd ../clean
python -m build --wheel -C="--build-option=--plat-name win_amd64"
rm src/coincurve/libsecp256k1.dll
rm -rf build/temp.*

cd ../32bit
build_dll i686-w64-mingw32
# As the API changes, the -x.dll will change to -y.dll, so we use a wildcard
mv .libs/libsecp256k1-?.dll ../clean/src/coincurve/libsecp256k1.dll
cd ../clean
python -m build --wheel -C="--build-option--plat-name win32"

mv dist/* ../coincurve/dist
cd ../coincurve
