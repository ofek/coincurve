#!/bin/bash

set -e
set -x

mkdir dist
mv coincurve/_windows_libsecp256k1.py /tmp/_windows_libsecp256k1.py

if [[ "$OS_NAME" =~ "ubuntu-" ]]; then
    if [[ "$PYTHON_VERSION" =~ "pypy" ]]; then
        docker run --rm -e PYTHON_VERSION="$PYTHON_VERSION" -e PLAT="manylinux2010_x86_64" -e BUILD_GMP_CPU="amd64" -v $(pwd):/io pypywheels/manylinux2010-pypy_x86_64 /io/.github/scripts/build-linux-wheels.sh
    else
        docker run --rm -e PYTHON_VERSION="$PYTHON_VERSION" -e PLAT="manylinux2010_x86_64" -e BUILD_GMP_CPU="amd64" -v $(pwd):/io quay.io/pypa/manylinux2010_x86_64 /io/.github/scripts/build-linux-wheels.sh
        docker run --rm -e PYTHON_VERSION="$PYTHON_VERSION" -e PLAT="manylinux1_x86_64" -e BUILD_GMP_CPU="amd64" -v $(pwd):/io quay.io/pypa/manylinux1_x86_64 /io/.github/scripts/build-linux-wheels.sh
        linux32 docker run --rm -e PYTHON_VERSION="$PYTHON_VERSION" -e PLAT="manylinux1_i686" -e BUILD_GMP_CPU="i686" -v $(pwd):/io quay.io/pypa/manylinux1_i686 /io/.github/scripts/build-linux-wheels.sh

        if [[ "$PYTHON_VERSION" == "$PYTHON_VERSION_BUILD_EXTRA" ]]; then
            # Build the source distribution
            python setup.py sdist

            # Build the wheels for Windows
            mv /tmp/_windows_libsecp256k1.py coincurve/_windows_libsecp256k1.py
            .github/scripts/build-windows-wheels.sh
            mv coincurve/_windows_libsecp256k1.py /tmp/_windows_libsecp256k1.py
        fi
    fi
else
    # Make sure we can build and "fix" the wheel.
    python -m pip install delocate wheel
    # Create directories for the built and fixed wheels.
    mkdir dist_wheels/ fixed_wheels/
    # Build the wheel for the local OS.
    python -m pip wheel . --wheel-dir dist_wheels/
    # Make the wheel relocatable to another OS.
    delocate-wheel \
        --check-archs \
        --wheel-dir fixed_wheels/ \
        --verbose \
        dist_wheels/coincurve*.whl
    # Move the fixed wheel into dist/.
    mv fixed_wheels/coincurve*.whl dist/
    # Clean up build directories.
    rm -fr dist_wheels/ fixed_wheels/
fi

ls -l dist

set +x +e
