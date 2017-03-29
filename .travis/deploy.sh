#!/bin/bash

set -e -x

echo "deploy"

# remove left over files from previous steps
rm -rf build dist
mkdir dist
ls
python setup.py sdist

# On linux we want to build `manylinux1` wheels. See:
if [[ "$TRAVIS_OS_NAME" == "linux" && ${BUILD_LINUX_WHEELS} -eq 1 ]]; then
	docker run --rm -e BUILD_LINUX_WHEELS -v $(pwd):/io ${WHEELBUILDER_IMAGE} /io/.travis/build-linux-wheels.sh
else
	# Only build wheels for the non experimental bundled version
	if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
		python -m pip install wheel
		python setup.py bdist_wheel
	fi
fi

ls -l dist

python -m pip install twine

# Ignore non-existing files in globs
shopt -s nullglob

twine upload --skip-existing dist/coincurve*.{whl,gz} -u "${PYPI_USERNAME}"

set +e +x
