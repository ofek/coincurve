#!/bin/bash

set -e -x

echo "deploy"

python setup.py install

# remove any left over files from previous steps
rm -rf build dist
mkdir dist

python setup.py sdist

if [[ "$TRAVIS_OS_NAME" == "linux" && ${BUILD_LINUX_WHEELS} -eq 1 ]]; then
    docker run --rm -e PLAT="manylinux2010_x86_64" -e BUILD_GMP_CPU="amd64" -v $(pwd):/io quay.io/pypa/manylinux2010_x86_64 /io/.travis/build-linux-wheels.sh
    docker run --rm -e PLAT="manylinux1_x86_64" -e BUILD_GMP_CPU="amd64" -v $(pwd):/io quay.io/pypa/manylinux1_x86_64 /io/.travis/build-linux-wheels.sh
    linux32 docker run --rm -e PLAT="manylinux1_i686" -e BUILD_GMP_CPU="i686" -v $(pwd):/io quay.io/pypa/manylinux1_i686 /io/.travis/build-linux-wheels.sh
    .travis/build_windows_wheels.sh
else
    if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
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
        [ -d dist/ ] || mkdir dist/
        mv fixed_wheels/coincurve*.whl dist/
        # Clean up build directories.
        rm -fr dist_wheels/ fixed_wheels/
    fi
fi

ls -l dist

python -m pip install twine

# Ignore non-existing files in globs
shopt -s nullglob

twine upload --skip-existing dist/coincurve*.{whl,gz} -u "${PYPI_USERNAME}"

set +e +x
