#!/bin/bash

if [[ "$TRAVIS_OS_NAME" == "linux" && ${BUILD_LINUX_WHEELS} -eq 1 ]]; then
    mkdir .hidden
    cp * .hidden -R
    mkdir .hidden/dist
    mv .hidden/coincurve/_windows_libsecp256k1.py .hidden/coincurve/_libsecp256k1.py
    mv .hidden ../clean
    sudo apt-get install -y mingw-w64
    sudo apt-get -f install
fi
