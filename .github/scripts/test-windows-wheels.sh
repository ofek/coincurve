#!/bin/bash

set -e
set -x

PYTHON_VERSION=$1

docker container run --rm coincurve/minimal-windows \
    powershell -Command "pytest"
