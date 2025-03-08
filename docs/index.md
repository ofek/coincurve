# coincurve

| | |
| --- | --- |
| CI/CD | [![CI - Test](https://github.com/ofek/coincurve/actions/workflows/build.yml/badge.svg){ loading=lazy }](https://github.com/ofek/coincurve/actions/workflows/build.yml) [![CI - Coverage](https://img.shields.io/codecov/c/github/ofek/coincurve/master.svg?logo=codecov&logoColor=red){ loading=lazy }](https://codecov.io/github/ofek/coincurve) |
| Docs | [![CI - Docs](https://github.com/ofek/coincurve/actions/workflows/docs.yml/badge.svg){ loading=lazy }](https://github.com/ofek/coincurve/actions/workflows/docs.yml) |
| Package | [![PyPI - Version](https://img.shields.io/pypi/v/coincurve.svg?logo=pypi&label=PyPI&logoColor=gold){ loading=lazy }](https://pypi.org/project/coincurve/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/coincurve.svg?color=blue&label=Downloads&logo=pypi&logoColor=gold){ loading=lazy }](https://pypi.org/project/coincurve/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/coincurve.svg?logo=python&label=Python&logoColor=gold){ loading=lazy }](https://pypi.org/project/coincurve/) |
| Meta | [![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg){ loading=lazy }](https://github.com/ofek/dep-sync) [![linting - Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json){ loading=lazy }](https://github.com/astral-sh/ruff) [![types - Mypy](https://img.shields.io/badge/types-Mypy-blue.svg){ loading=lazy }](https://github.com/python/mypy) [![License - MIT OR Apache-2.0](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-9400d3.svg){ loading=lazy }](https://spdx.org/licenses/) [![GitHub Sponsors](https://img.shields.io/github/sponsors/ofek?logo=GitHub%20Sponsors&style=social){ loading=lazy }](https://github.com/sponsors/ofek) |

-----

This library provides well-tested Python bindings for [libsecp256k1][], the heavily optimized
C library used by [Bitcoin Core][] for operations on the elliptic curve [secp256k1][].

## Features

- Fastest available implementation (more than 10x faster than OpenSSL)
- Clean, easy to use API
- Frequent updates from the development version of [libsecp256k1][]
- Linux, macOS, and Windows all have binary packages for multiple architectures
- Deterministic signatures as specified by [RFC 6979][]
- Non-malleable signatures (lower-S form) by default
- Secure, non-malleable [ECDH][] implementation

## Users

- [Ethereum](https://ethereum.org)
- [LBRY](https://lbry.com)
- [libp2p](https://libp2p.io)

and [many more](users.md)!

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
