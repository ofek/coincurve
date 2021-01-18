#!/bin/bash

set -e
set -x

# Install system packages required by our library
yum install -y pkg-config libffi libffi-devel

# Use updated GMP
curl -O https://ftp.gnu.org/gnu/gmp/gmp-6.1.2.tar.bz2 && tar -xjpf gmp-*.tar.bz2 && cd gmp* && ./configure --build=${BUILD_GMP_CPU}-pc-linux-gnu > /dev/null && make > /dev/null && make check > /dev/null && make install > /dev/null && cd ..

mkdir out

python_version="$PYTHON_VERSION"

if [[ "$python_version" =~ "pypy" ]]; then
    python_version="pp36-pypy36_pp73|pp37-pypy37_pp73"
else
    python_version=${python_version/./}
    python_version="cp$python_version"
fi

echo "Looking for Python version pattern: $python_version"

# Compile wheels
for PYBIN in /opt/python/*/bin; do
	if [[ ${PYBIN} =~ $python_version ]]; then
	    ${PYBIN}/pip wheel /io/ -w wheelhouse/
    fi
done

# Adjust wheel tags
for whl in wheelhouse/coincurve*.whl; do
    auditwheel repair "$whl" --plat $PLAT -w out
done

cp out/*.whl /io/dist
