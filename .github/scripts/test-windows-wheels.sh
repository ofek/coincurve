#!/bin/bash

set -e
set -x

PYTHON_VERSION=$1

docker container run --rm scikit-learn/minimal-windows \
    powershell -Command "pytest"
