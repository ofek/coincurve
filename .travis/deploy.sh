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
		python3 -m pip install auditwheel
		python setup.py bdist_wheel
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
