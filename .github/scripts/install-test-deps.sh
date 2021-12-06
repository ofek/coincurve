#!/bin/bash
set -ex

if [ "$RUNNER_OS" == "macOS" ]; then
    ./.github/scripts/install-macos-build-deps.sh
fi

python -m pip install --upgrade cffi
python -m pip install --upgrade tox codecov
