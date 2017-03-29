#!/bin/bash

if [[ "$TRAVIS_OS_NAME" == "linux" && ${BUILD_LINUX_WHEELS} -eq 1 ]]; then
    mkdir .hidden
    cp * .hidden -R
    mkdir .hidden/dist
    mv .hidden ../clean
    sudo apt-get install -y mingw-w64
    sudo apt-get -f install
fi
