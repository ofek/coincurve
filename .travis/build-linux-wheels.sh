#!/bin/bash

set -e
set -x

# Install a system package required by our library
yum install -y pkg-config libffi libffi-devel

# Use updated GMP
wget -q https://gmplib.org/download/gmp/gmp-6.1.2.tar.bz2 && tar -xjpf gmp-*.tar.bz2 && cd gmp* && ./configure > /dev/null && make > /dev/null && make check > /dev/null && make install > /dev/null && cd ..

# Compile wheels
for PYBIN in /opt/python/*/bin; do
    case "${PYBIN}" in
		cp27|cp35|cp36)
			${PYBIN}/pip wheel /io/ -w wheelhouse/
			;;
	esac
done

# Adjust wheel tags
mkdir out
for whl in wheelhouse/coincurve*.whl; do
    auditwheel repair $whl -w out
done

cp out/*.whl /io/dist
