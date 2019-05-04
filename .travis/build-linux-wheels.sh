#!/bin/bash

set -e
set -x

# Install a system package required by our library
yum install -y pkg-config libffi libffi-devel

# Use updated GMP
curl -O https://ftp.gnu.org/gnu/gmp/gmp-6.1.2.tar.bz2 && tar -xjpf gmp-*.tar.bz2 && cd gmp* && ./configure --build=${BUILD_GMP_CPU}-pc-linux-gnu > /dev/null && make > /dev/null && make check > /dev/null && make install > /dev/null && cd ..

mkdir out

if [[ "$PLAT" == "manylinux2010_x86_64" ]]; then
    yum update curl
    curl -O https://nixos.org/releases/patchelf/patchelf-0.10/patchelf-0.10.tar.bz2 && tar -xjpf patchelf-*.tar.bz2 && cd patchelf* && ./configure > /dev/null && make install > /dev/null && cd ..
    curl -LO https://bitbucket.org/squeaky/portable-pypy/downloads/pypy3.6-7.1.1-beta-linux_x86_64-portable.tar.bz2
    tar -xjpf pypy3.6-7.1.1-beta-linux_x86_64-portable.tar.bz2
    pypy3.6-7.1.1-beta-linux_x86_64-portable/bin/pypy3 -m pip install typing
    pypy3.6-7.1.1-beta-linux_x86_64-portable/bin/pypy3 -m pip install wheel
    pypy3.6-7.1.1-beta-linux_x86_64-portable/bin/pypy3 -m pip install pyelftools
    pypy3.6-7.1.1-beta-linux_x86_64-portable/bin/pypy3 -m pip install auditwheel
    pypy3.6-7.1.1-beta-linux_x86_64-portable/bin/pypy3 -m pip wheel /io/ -w wheelhouse/
    pypy3.6-7.1.1-beta-linux_x86_64-portable/bin/pypy3 -m auditwheel repair wheelhouse/coincurve*.whl -w out
fi

# Compile wheels
for PYBIN in /opt/python/*/bin; do
	if [[ ${PYBIN} =~ (cp27|cp35|cp36|cp37|cp38) ]]; then
	    ${PYBIN}/pip wheel /io/ -w wheelhouse/
    fi
done

# Adjust wheel tags
for whl in wheelhouse/coincurve*.whl; do
    auditwheel repair "$whl" --plat $PLAT -w out
done

cp out/*.whl /io/dist
