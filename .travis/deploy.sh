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
		python -m pip install wheel
		python setup.py bdist_wheel
	fi

	if [[ "$TRAVIS_PYTHON_VERSION" == "pypy3" ]]; then
		python -m pip install wheel
		python setup.py bdist_wheel
		python3 -m pip install wheel auditwheel pyelftools typing
		wget -q https://nixos.org/releases/patchelf/patchelf-0.9/patchelf-0.9.tar.bz2 && tar -xjpf patchelf-*.tar.bz2 && cd patchelf* && ./configure > /dev/null && make install > /dev/null && cd ..
		auditwheel repair dist/coincurve*.whl
		rm dist/coincurve*.whl
		mv coincurve*.whl dist
	fi
fi

ls -l dist

python -m pip install twine

# Ignore non-existing files in globs
shopt -s nullglob

twine upload --skip-existing dist/coincurve*.{whl,gz} -u "${PYPI_USERNAME}"

set +e +x
