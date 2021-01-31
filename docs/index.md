# coincurve

[![CI - Build](https://github.com/ofek/coincurve/workflows/build/badge.svg)](https://github.com/ofek/coincurve/actions?query=workflow%3Abuild)
[![CI - Docs](https://github.com/ofek/coincurve/workflows/docs/badge.svg)](https://github.com/ofek/coincurve/actions?query=workflow%3Adocs)
[![CI - Coverage](https://img.shields.io/codecov/c/github/ofek/coincurve/master.svg?logo=codecov&logoColor=red)](https://codecov.io/github/ofek/coincurve)

[![PyPI - Version](https://img.shields.io/pypi/v/coincurve.svg?logo=pypi&label=PyPI&logoColor=gold)](https://pypi.org/project/coincurve/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/coincurve.svg?color=blue&label=Downloads&logo=pypi&logoColor=gold)](https://pypi.org/project/coincurve/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/coincurve.svg?logo=python&label=Python&logoColor=gold)](https://pypi.org/project/coincurve/)

[![License - MIT/Apache-2.0](https://img.shields.io/badge/license-MIT%2FApache--2.0-9400d3.svg)](https://spdx.org/licenses/)
[![Code style - black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

-----

This library provides well-tested Python bindings for [libsecp256k1][], the heavily optimized
C library used by [Bitcoin Core][] for operations on the elliptic curve [secp256k1][].

## Features

- Fastest available implementation (more than 10x faster than OpenSSL)
- Clean, easy to use API
- Frequent updates from the development version of [libsecp256k1][]
- Linux, macOS, and Windows all have binary packages for multiple architectures
- Linux & macOS use GMP for faster computation
- Deterministic signatures as specified by [RFC 6979][]
- Non-malleable signatures (lower-S form) by default
- Secure, non-malleable [ECDH][] implementation

## License

`coincurve` is distributed under the terms of any of the following licenses:

- [MIT](https://spdx.org/licenses/MIT.html)
- [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html)

## Navigation

Desktop readers can use keyboard shortcuts to navigate.

| Keys | Action |
| --- | --- |
| <ul><li><kbd>,</kbd> (comma)</li><li><kbd>p</kbd></li></ul> | Navigate to the "previous" page |
| <ul><li><kbd>.</kbd> (period)</li><li><kbd>n</kbd></li></ul> | Navigate to the "next" page |
| <ul><li><kbd>/</kbd></li><li><kbd>s</kbd></li></ul> | Display the search modal |
