# coincurve

| | |
| --- | --- |
| CI/CD | [![CI - Build](https://github.com/ofek/coincurve/workflows/build/badge.svg)](https://github.com/ofek/coincurve/actions?query=workflow%3Abuild) [![CI - Coverage](https://img.shields.io/codecov/c/github/ofek/coincurve/master.svg?logo=codecov&logoColor=red)](https://codecov.io/github/ofek/coincurve) |
| Docs | [![CI - Docs](https://github.com/ofek/coincurve/workflows/docs/badge.svg)](https://github.com/ofek/coincurve/actions?query=workflow%3Adocs) |
| Package | [![PyPI - Version](https://img.shields.io/pypi/v/coincurve.svg?logo=pypi&label=PyPI&logoColor=gold)](https://pypi.org/project/coincurve/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/coincurve.svg?color=blue&label=Downloads&logo=pypi&logoColor=gold)](https://pypi.org/project/coincurve/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/coincurve.svg?logo=python&label=Python&logoColor=gold)](https://pypi.org/project/coincurve/) |
| Meta | [![Code style - black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) [![License - MIT/Apache-2.0](https://img.shields.io/badge/license-MIT%2FApache--2.0-9400d3.svg)](https://spdx.org/licenses/) [![GitHub Sponsors](https://img.shields.io/github/sponsors/ofek?logo=GitHub%20Sponsors&style=social)](https://github.com/sponsors/ofek) |

-----

This library provides well-tested Python bindings for [libsecp256k1](https://github.com/bitcoin-core/secp256k1), the heavily optimized C library
used by [Bitcoin Core](https://github.com/bitcoin/bitcoin) for operations on the elliptic curve [secp256k1](https://en.bitcoin.it/wiki/Secp256k1).

Feel free to read the [documentation](https://ofek.dev/coincurve/)!

## Quick Start

```
pip install coincurve
```
```py
from coincurve import keys, PrivateKey, verify_signature

priv = PrivateKey(secret=None)  # Generate a random private key
pub = priv.public_key.format()  # Derive a public key from the private key

print(f"private key: {priv.to_hex()}")
print(f"public key: {pub.hex()}\n")

signed_msg = keys.PrivateKey.sign(priv, message=b"Sign Me!")  # Signs a message using the private key

verify_msg = verify_signature(signature=signed_msg, message=b"Sign Me!", public_key=bytes(pub))  # Verifies if a signed message is valid
print(f"signature: {signed_msg.hex()}")
print(f"valid sig: {verify_msg}")
```
## Users

- [Ethereum](https://ethereum.org)
- [LBRY](https://lbry.com)
- [ZeroNet](https://zeronet.io)
- [libp2p](https://libp2p.io)

and [many more](https://ofek.dev/coincurve/users/)!

## License

`coincurve` is distributed under the terms of any of the following licenses:

- [MIT](https://spdx.org/licenses/MIT.html)
- [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html)
