#!/bin/bash

set -e
set -x

# On osx we need to bring our own Python.
# See: https://github.com/travis-ci/travis-ci/issues/2312
if [[ $TRAVIS_OS_NAME == "osx" ]]; then

	# We use the official python.org installers to make sure our wheels are
	# going to be as widely compatible as possible
	PYTHON_PKG_27="https://www.python.org/ftp/python/2.7.15/python-2.7.15-macosx10.6.pkg"
	PYTHON_PKG_36="https://www.python.org/ftp/python/3.6.5/python-3.6.5-macosx10.6.pkg"
	GET_PIP="https://bootstrap.pypa.io/get-pip.py"

	# update brew
	brew update || brew update

	# Update openssl if necessary
	brew outdated openssl || brew upgrade openssl

	# Install packages needed to build lib-secp256k1
	for pkg in automake libtool pkg-config libffi; do
		brew list $pkg > /dev/null || brew install $pkg
		brew outdated --quiet $pkg || brew upgrade $pkg
	done

	mkdir -p ~/.cache/python-dl

	if [[ "${TRAVIS_PYTHON_VERSION}" == "3.5" ]]; then
		PYVERSION="${TRAVIS_PYTHON_VERSION}.5"
		brew outdated pyenv || brew upgrade pyenv
		pyenv install ${PYVERSION}
		pyenv global ${PYVERSION}
	else
		builtin pushd ~/.cache/python-dl
		ls -l

		py_pkg=PYTHON_PKG_${TRAVIS_PYTHON_VERSION//./}
		py_pkg=${!py_pkg}

		installer_pkg=$(basename ${py_pkg})

		# The package might have been cached from a previous run
		if [[ ! -f ${installer_pkg} ]]; then
			curl -LO ${py_pkg}
		fi

		sudo installer -pkg ${installer_pkg} -target /
		builtin popd
	fi

	case "${TRAVIS_PYTHON_VERSION}" in
		2.7)
			python=/Library/Frameworks/Python.framework/Versions/${TRAVIS_PYTHON_VERSION}/bin/python
			virtualenv=virtualenv
			;;
		3.6)
			python=/Library/Frameworks/Python.framework/Versions/${TRAVIS_PYTHON_VERSION}/bin/python3
			virtualenv=venv
			;;
		3.5)
			python="$(pyenv root)/versions/${PYVERSION}/bin/python"
			virtualenv=venv
			;;
	esac

	if [[ "${TRAVIS_PYTHON_VERSION}" == "2.7" ]]; then
		builtin pushd ~
		curl -LO ${GET_PIP}
		${python} get-pip.py
		${python} -m pip install --user virtualenv
		builtin popd
	fi

	# https://bugs.python.org/issue28150
	if [[ "${NEED_SSL_FIX}" == "true" ]]; then
		"/Applications/Python ${TRAVIS_PYTHON_VERSION}/Install Certificates.command"
	fi

	mkdir ~/virtualenv
	${python} -m ${virtualenv} ~/virtualenv/python${TRAVIS_PYTHON_VERSION}
	source ~/virtualenv/python${TRAVIS_PYTHON_VERSION}/bin/activate
fi

# Install necessary packages
python -m pip install -U cffi pytest coverage

set +x +e
