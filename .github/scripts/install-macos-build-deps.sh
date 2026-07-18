#!/bin/bash
set -euxo pipefail

# CMake uses pkg-config to detect system libraries. Avoid updating the entire
# Homebrew installation in every CI job; the hosted runner image is immutable.
brew list pkg-config > /dev/null 2>&1 || brew install pkg-config
