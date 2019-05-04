#!/bin/bash

set -e
set -x

# Install a system package required by our library
yum install -y pkg-config libffi libffi-devel

# Use updated GMP
curl -O https://ftp.gnu.org/gnu/gmp/gmp-6.1.2.tar.bz2 && tar -xjpf gmp-*.tar.bz2 && cd gmp* && ./configure --build=${BUILD_GMP_CPU}-pc-linux-gnu > /dev/null && make > /dev/null && make check > /dev/null && make install > /dev/null && cd ..

mkdir out

# PyPy
if [[ "$PLAT" == "manylinux2010_x86_64" ]]; then
    mkdir /opt/python/pypy3
    curl -LO https://bitbucket.org/squeaky/portable-pypy/downloads/pypy3.6-7.1.1-beta-linux_x86_64-portable.tar.bz2
    tar -xjpf -C /opt/python/pypy3 --strip-components=1 pypy3.6-7.1.1-beta-linux_x86_64-portable.tar.bz2
    curl -sSL https://raw.githubusercontent.com/pypa/get-pip/master/get-pip.py | /opt/python/pypy3/bin/pypy
fi

# Compile wheels
for PYBIN in /opt/python/*/bin; do
	if [[ ${PYBIN} =~ (cp27|cp35|cp36|cp37|cp38|pypy) ]]; then
	    ${PYBIN}/pip wheel /io/ -w wheelhouse/
    fi
done

# Adjust wheel tags
for whl in wheelhouse/coincurve*.whl; do
    auditwheel repair "$whl" --plat $PLAT -w out
done

cp out/*.whl /io/dist
