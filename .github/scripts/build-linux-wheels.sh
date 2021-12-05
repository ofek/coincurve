#!/bin/sh

# Find out if we're emulating 32-bit
[ "$(getconf LONG_BIT)" == "32" ] && ARCH=i686 || ARCH=amd64

# Install system packages required by our library
yum install -y pkgconfig libffi libffi-devel

# Use updated GMP
curl -O https://ftp.gnu.org/gnu/gmp/gmp-6.2.1.tar.bz2 && tar -xjpf gmp-*.tar.bz2 && cd gmp* && ./configure --build=${ARCH}-pc-linux-gnu > /dev/null && make > /dev/null && make check > /dev/null && make install > /dev/null && cd ..
