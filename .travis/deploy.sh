#!/bin/bash

set -e -x

echo "deploy"

# remove left over files from previous steps
rm -rf build dist
mkdir dist

python setup.py sdist

if [[ "$TRAVIS_OS_NAME" == "linux" && ${BUILD_LINUX_WHEELS} -eq 1 ]]; then
    docker run --rm -e BUILD_GMP_CPU="amd64" -v $(pwd):/io quay.io/pypa/manylinux1_x86_64 /io/.travis/build-linux-wheels.sh
    linux32 docker run --rm -e BUILD_GMP_CPU="i686" -v $(pwd):/io quay.io/pypa/manylinux1_i686 /io/.travis/build-linux-wheels.sh
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

    if [[ "$TRAVIS_PYTHON_VERSION" == "pypy3" ]]; then
        python -m pip install wheel
        python setup.py bdist_wheel
        python3 -m pip install wheel pyelftools typing
        python3 -m pip install -e git://github.com/pypa/auditwheel.git@fb6f76d4262dbb76a6ea068000e71fdfe6fd06ee#egg=auditwheel
        wget -q https://nixos.org/releases/patchelf/patchelf-0.9/patchelf-0.9.tar.bz2 && tar -xjpf patchelf-*.tar.bz2 && cd patchelf* && ./configure > /dev/null && sudo make install > /dev/null && cd ..
        auditwheel repair dist/coincurve*.whl
        rm dist/coincurve*.whl
        mv wheelhouse/coincurve*.whl dist
    fi
fi

ls -l dist

python -m pip install twine

# Ignore non-existing files in globs
shopt -s nullglob

twine upload --skip-existing dist/coincurve*.{whl,gz} -u "${PYPI_USERNAME}"

set +e +x
