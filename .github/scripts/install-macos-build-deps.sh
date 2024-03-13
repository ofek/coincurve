#!/bin/bash
set -ex

# update brew
brew update

# Update openssl if necessary
brew outdated openssl || brew upgrade openssl

# Install packages needed to build lib-secp256k1
for pkg in pkg-config; do
    brew list $pkg > /dev/null || brew install $pkg
    brew outdated --quiet $pkg || brew upgrade $pkg
done
