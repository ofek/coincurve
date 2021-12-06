#!/bin/sh
set -ex

# Find out what we're emulating
ARCH="$(python -c 'import platform;print(platform.machine())')"

# Use updated GMP
curl -O https://ftp.gnu.org/gnu/gmp/gmp-6.2.1.tar.bz2 && tar -xjpf gmp-*.tar.bz2 && cd gmp* && ./configure --build=${ARCH}-pc-linux-gnu > /dev/null && make > /dev/null && make check > /dev/null && make install > /dev/null && cd ..
