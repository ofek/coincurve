# Scripts

-----

This directory contains scripts that are used to develop the project.

## Native coverage

Run `hatch run native-coverage:run` to rebuild the extension with LLVM source-based coverage, execute the complete test suite, and write LCOV and HTML reports to `build/native-coverage`. Pass test paths or pytest arguments after the command to measure a subset, such as `hatch run native-coverage:run tests/test_keys.py`.

The command requires `clang`, `llvm-profdata`, and `llvm-cov` on `PATH`. On Windows it uses `clang-cl` and installs Ninja from the declared dependency group; the Visual C++ build tools used by normal source builds must also be available.
