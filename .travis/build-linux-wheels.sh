#!/bin/bash

set -e
set -x

# Install a system package required by our library
yum install -y pkg-config libffi libffi-devel

# Use updated GMP
curl -O https://ftp.gnu.org/gnu/gmp/gmp-6.1.2.tar.bz2 && tar -xjpf gmp-*.tar.bz2 && cd gmp* && ./configure --build=${BUILD_GMP_CPU}-pc-linux-gnu > /dev/null && make > /dev/null && make check > /dev/null && make install > /dev/null && cd ..

mkdir out

if [[ "$TRAVIS_PYTHON_VERSION" == "pypy3" ]]; then
    curl -O https://bitbucket.org/squeaky/portable-pypy/downloads/pypy3.5-6.0.0-linux_x86_64-portable.tar.bz2
    tar -jxvf pypy3.5-6.0.0-linux_x86_64-portable.tar.bz2
    pypy3.5-6.0.0-linux_x86_64-portable/bin/python -m pip install wheel
    pypy3.5-6.0.0-linux_x86_64-portable/bin/python -m pip wheel /io/ -w wheelhouse/
    pypy3.5-6.0.0-linux_x86_64-portable/bin/python -m pip install wheel pyelftools typing
    pypy3.5-6.0.0-linux_x86_64-portable/bin/python -m pip install -e git://github.com/pypa/auditwheel.git@fb6f76d4262dbb76a6ea068000e71fdfe6fd06ee#egg=auditwheel
    curl -O https://nixos.org/releases/patchelf/patchelf-0.9/patchelf-0.9.tar.bz2 && tar -xjpf patchelf-*.tar.bz2 && cd patchelf* && ./configure > /dev/null && sudo make install > /dev/null && cd ..
    pypy3.5-6.0.0-linux_x86_64-portable/bin/python -m auditwheel repair wheelhouse/coincurve*.whl -w out
fi

# Compile wheels
for PYBIN in /opt/python/*/bin; do
	if [[ ${PYBIN} =~ (cp27|cp35|cp36|cp37) ]]; then
	    ${PYBIN}/pip wheel /io/ -w wheelhouse/
    fi
done

# Adjust wheel tags
for whl in wheelhouse/coincurve*.whl; do
    auditwheel repair $whl -w out
done

cp out/*.whl /io/dist
