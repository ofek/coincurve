#!/bin/bash

set -e
set -x

if [[ "$OS_NAME" =~ "macos-" ]]; then

    # update brew
    brew update

    # Update openssl if necessary
    brew outdated openssl || brew upgrade openssl

    # Install packages needed to build lib-secp256k1
    for pkg in automake libtool pkg-config; do
        brew list $pkg > /dev/null || brew install $pkg
        brew outdated --quiet $pkg || brew upgrade $pkg
    done
fi

set +x +e
