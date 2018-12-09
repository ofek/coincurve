Coincurve
=========

.. image:: https://travis-ci.org/ofek/coincurve.svg?branch=master
    :target: https://travis-ci.org/ofek/coincurve
    :alt: Travis CI

.. image:: https://codecov.io/github/ofek/coincurve/coverage.svg?branch=master
    :target: https://codecov.io/github/ofek/coincurve?branch=master
    :alt: Codecov

.. image:: https://img.shields.io/pypi/status/coverage.svg
    :target: https://pypi.org/project/coincurve
    :alt: PyPI - Status

.. image:: https://img.shields.io/pypi/v/coincurve.svg
    :target: https://pypi.org/project/coincurve
    :alt: PyPI - Version

.. image:: https://pepy.tech/badge/coincurve
    :target: https://pepy.tech/project/coincurve
    :alt: PyPI - Downloads

.. image:: https://img.shields.io/badge/license-MIT%2FApache--2.0-9400d3.svg
    :target: https://choosealicense.com/licenses
    :alt: License: MIT/Apache-2.0

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black
    :alt: Code style: black

-----

This library provides well-tested Python CFFI bindings for
`libsecp256k1 <https://github.com/bitcoin-core/secp256k1>`_, the heavily
optimized C library used by `Bitcoin Core <https://github.com/bitcoin/bitcoin>`_
for operations on elliptic curve secp256k1.

Table of Contents
~~~~~~~~~~~~~~~~~

.. contents::
    :backlinks: top
    :local:

Features
--------

- Fastest available implementation (more than 10x faster than OpenSSL)
- Clean, easy to use API
- Frequent updates from `libsecp256k1 <https://github.com/bitcoin-core/secp256k1>`_ master
- Linux, macOS, and Windows all have binary packages for both 64 and 32-bit architectures
- Linux & macOS use GMP for faster computation
- Deterministic signatures via `RFC 6979 <https://tools.ietf.org/html/rfc6979>`_
- Non-malleable signatures (lower-S form) by default
- Secure, non-malleable `ECDH implementation <https://github.com/ofek/coincurve/issues/9#issuecomment-329235214>`_
- Implements a fix for `<https://bugs.python.org/issue28150>`_ to support Python 3.6+ on macOS

Users
-----

- `AnyLedger <https://github.com/AnyLedger/anyledger-backend/blob/cb9e277ef4ba775384a1eb80ff1577418f88684e/requirements.in#L5>`_
- `Ark Ecosystem <https://github.com/ArkEcosystem/python-crypto/blob/a7c739c070ce17f8aa64155b95b698e7465ab373/setup.py#L9>`_
- `AugurProject <https://github.com/AugurProject/augur/blob/95177dfaee7d978608543523f180609c582c1ff9/packages/augur-core/requirements.txt#L9>`_
- `bit <https://github.com/ofek/bit>`_
- `btcrecover <https://github.com/gurnec/btcrecover/commit/f113867fa22d2f5b22175cc2b5b3892351bc1109>`_
- `crankycoin <https://github.com/cranklin/crankycoin/blob/3d2b3482698227397a8daf30e0b80b2f2c030aec/requirements.txt#L8>`_
- `eciespy <https://github.com/kigawas/eciespy/blob/c8dd8134eec12c565f6fa870663d04f0da6df6d0/requirements.txt#L3>`_
- `Enigma <https://github.com/enigmampc/surface/blob/40ca2056bce32d0d479e4809ac8cd5ded102b3f0/etc/requirements.txt#L8>`_
- `ethereum/eth-keys <https://github.com/ethereum/eth-keys/commit/81755dfda714d77c1f8a092810ca31e570d84425>`_
- `ethereum/eth-tester <https://github.com/ethereum/eth-tester/blob/96e4e69de46acca387f2a946920e4c3e3f35605f/tox.ini#L17>`_
- `ethereum/py-evm <https://github.com/ethereum/py-evm/pull/31>`_
- `ethereum/pydevp2p <https://github.com/ethereum/pydevp2p/pull/80>`_
- `ethereum/pyethereum <https://github.com/ethereum/pyethereum/pull/777>`_
- `ethereum/vyper <https://github.com/ethereum/vyper/blob/9491bcde0f87fd04d19d0a40a6c901b1bc0a718b/Dockerfile#L15>`_
- `EtherollApp <https://github.com/AndreMiras/EtherollApp/commit/2966c0850156364e46412da2331cee146b490e57>`_
- `ForkDelta <https://github.com/forkdelta/backend-replacement/blob/45517f48579f3270dc47da2075d8e0efc2e9ecb8/requirements.txt#L46>`_
- `golemfactory/golem <https://github.com/golemfactory/golem/pull/1527>`_
- `golemfactory/golem-messages <https://github.com/golemfactory/golem-messages/blob/1f72b6a6757036218cdf471c0295b8895b963266/setup.py#L39>`_
- `HoneyBadgerBFT <https://github.com/initc3/HoneyBadgerBFT-Python/blob/048d6afb3c7184db670b96119aa99a6a5b0dafa6/setup.py#L31>`_
- `JoinMarket <https://github.com/JoinMarket-Org/joinmarket-clientserver/pull/223>`_
- `lbryio/lbry <https://github.com/lbryio/lbry/blob/d64916a06115920aaa9eaab67704a0b2d34aae20/CHANGELOG.md#security-1>`_
- `lbryio/torba <https://github.com/lbryio/torba/pull/13>`_
- `minichain <https://github.com/kigawas/minichain/blob/8c1fd9499954bcdbc7e0f77f6fa6d9af3328f64c/requirements.txt#L3>`_
- `Nekoyume <https://github.com/nekoyume/nekoyume/pull/67>`_
- `NuCypher <https://github.com/nucypher/nucypher/pull/592>`_
- `OmiseGO <https://github.com/omisego/fee-burner/blob/984f75362ca193680ecb4dc43c7d2e13f3be68bd/contracts/requirements.txt#L9>`_
- `PeerAssets <https://github.com/PeerAssets/pypeerassets/commit/113c9a234c94499c7e591b8a93928be0a77298fa>`_
- `Planetarium <https://github.com/planetarium/coincurve-stubs>`_
- `python-idex <https://github.com/sammchardy/python-idex/blob/3b698533e290a0fe884961ce69c4b2e699378b8d/requirements.txt#L2>`_
- `PyWallet <https://github.com/AndreMiras/PyWallet/commit/69f2f240b39f332123d347c72bc75f0b199813c1>`_
- `QuarkChain <https://github.com/QuarkChain/pyquarkchain/blob/4c002d4b535174704ce39f3954e4026f23d520bb/requirements.txt#L4>`_
- `raiden-network/microraiden <https://github.com/raiden-network/microraiden/blob/8d5f1d86818f01c8cafe9366da1cecdef0e8b0f4/requirements.txt#L5>`_
- `raiden-network/raiden <https://github.com/raiden-network/raiden/pull/534>`_
- `raiden-network/raiden-contracts <https://github.com/raiden-network/raiden-contracts/blob/f251c01015564a2b91401692234aa5ed1ea67ebc/requirements.txt#L3>`_
- `raiden-network/raiden-libs <https://github.com/raiden-network/raiden-libs/blob/e88586e6d40e2b49d19efbdffafdaa2a86f84c86/requirements.txt#L1>`_

Installation
------------

Coincurve is distributed on PyPI and is available on Linux/macOS and Windows and
supports Python 2.7/3.5+ and PyPy3.5-v5.8.1+.

.. code-block:: bash

    $ pip install coincurve

If you are on a system that doesn't have a precompiled binary wheel (e.g. FreeBSD)
then pip will fetch source to build yourself. You must have the necessary packages.

On Debian/Ubuntu for example the necessary packages are:

- build-essential
- automake
- pkg-config
- libtool
- libffi-dev
- libgmp-dev (optional)

API
---

Coincurve provides a simple API.

coincurve.verify_signature
^^^^^^^^^^^^^^^^^^^^^^^^^^

``verify_signature(signature, message, public_key, hasher=sha256, context=GLOBAL_CONTEXT)``

Verifies some message was signed by the owner of a public key.

* Parameters:

    - **signature** (``bytes``) - The signature to verify.
    - **message** (``bytes``) - The message that was supposedly signed.
    - **public_key** (``bytes``) - A public key in compressed or uncompressed form.
    - **hasher** - The hash function to use, can be ``None``. hasher(message) must return 32 bytes.
    - **context** (``coincurve.Context``)

* Returns: ``bool``

coincurve.PrivateKey
^^^^^^^^^^^^^^^^^^^^

All instances have a ``public_key`` of type ``coincurve.PublicKey``

``PrivateKey(secret=None, context=GLOBAL_CONTEXT)``

* Parameters:

    - **secret** (``bytes``) - The secret to use.
    - **context** (``coincurve.Context``)

**Methods:**

*classmethod* ``from_hex(hexed, context=GLOBAL_CONTEXT)``

*classmethod* ``from_int(num, context=GLOBAL_CONTEXT)``

*classmethod* ``from_pem(pem, context=GLOBAL_CONTEXT)``

*classmethod* ``from_der(der, context=GLOBAL_CONTEXT)``

``sign(message, hasher=sha256, custom_nonce=None)``

* Parameters:

    - **message** (``bytes``) - The message to sign.
    - **hasher** - The hash function to use, can be ``None``. hasher(message) must return 32 bytes.
    - **custom_nonce** - A tuple of arity 2 in the form of ``(nonce_fn, nonce_data)``. Refer to:
      `secp256k1.h <https://github.com/bitcoin-core/secp256k1/blob/b8c26a39903de7bf1d789232e030319116b011ac/include/secp256k1.h#L449-L450>`_

* Returns: ``bytes``. 68 <= len(signature) <= 71

``sign_recoverable(message, hasher=sha256)``

* Parameters:

    - **message** (``bytes``) - The message to sign.
    - **hasher** - The hash function to use, can be ``None``. hasher(message) must return 32 bytes.

* Returns: ``bytes``

``ecdh(public_key)``

Computes a Diffie-Hellman secret in constant time. **Note:** This prevents malleability by returning
``sha256(x)`` instead of the ``x`` coordinate directly. See `<https://github.com/ofek/coincurve/issues/9>`_.

* Parameters:

    - **public_key** (``bytes``) - Another party's public key in compressed or uncompressed form.

* Returns: ``bytes``

``add(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to add.
    - **update** (``bool``) - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PrivateKey``

``multiply(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to multiply.
    - **update** (``bool``) - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PrivateKey``

``to_hex()``

``to_int()``

``to_pem()``

``to_der()``

coincurve.PublicKey
^^^^^^^^^^^^^^^^^^^

``PublicKey(data, context=GLOBAL_CONTEXT)``

* Parameters:

    - **data** (``bytes``) - The public key in compressed or uncompressed form.
    - **context** (``coincurve.Context``)

**Methods:**

*classmethod* ``from_secret(secret, context=GLOBAL_CONTEXT)``

*classmethod* ``from_valid_secret(secret, context=GLOBAL_CONTEXT)``

*classmethod* ``from_point(x, y, context=GLOBAL_CONTEXT)``

*classmethod* ``from_signature_and_message(serialized_sig, message, hasher=sha256, context=GLOBAL_CONTEXT)``

*classmethod* ``combine_keys(public_keys, context=GLOBAL_CONTEXT)``

* Parameters:

    - **public_keys** (``list``) - A ``list`` of ``coincurve.PublicKey`` to add.
    - **context** (``coincurve.Context``)

* Returns: ``coincurve.PublicKey``

``format(compressed=True)``

* Parameters:

    - **compressed** (``bool``)

* Returns: The public key serialized to ``bytes``.

``point()``

* Returns: (x, y)

``verify(signature, message, hasher=sha256)``

Verifies some message was signed by the owner of this public key.

* Parameters:

    - **signature** (``bytes``) - The signature to verify.
    - **message** (``bytes``) - The message that was supposedly signed.
    - **hasher** - The hash function to use, can be ``None``. hasher(message) must return 32 bytes.

* Returns: ``bool``

``add(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to add.
    - **update** (``bool``) - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PublicKey``

``multiply(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to multiply.
    - **update** (``bool``) - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PublicKey``

``combine(public_keys, update=False)``

* Parameters:

    - **public_keys** (``list``) - A ``list`` of ``coincurve.PublicKey`` to add.
    - **update** (``bool``) - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PublicKey``

License
-------

Coincurve is distributed under the terms of both

- `Apache License, Version 2.0 <https://choosealicense.com/licenses/apache-2.0>`_
- `MIT License <https://choosealicense.com/licenses/mit>`_

at your option.

Credits
-------

- Contributors of `libsecp256k1 <https://github.com/bitcoin-core/secp256k1>`_.
- Contributors of `secp256k1-py <https://github.com/ludbb/secp256k1-py>`_.
  While Coincurve is nearly a complete rewrite, much of the build system
  provided by `ulope <https://github.com/ulope>`_ remains.

History
-------

Important changes are emphasized.

11.0.0
^^^^^^

- Fix some linking scenarios by placing bundled libsecp256k1 dir first in path
- Allow override of system libsecp256k1 with environment variable
- Add benchmarks
- Use Codecov to track coverage
- Use black for code formatting

10.0.0
^^^^^^

- Support tox for testing
- Compatibility with latest libsecp256k1 ECDH API
- Make libgmp optional when building from source

9.0.0
^^^^^

- Fixed wheels for macOS
- **Breaking:** Drop support for 32-bit macOS

8.0.2
^^^^^

- No longer package tests

8.0.0
^^^^^

- **New:** Binary wheels for Python 3.7!
- **Changed:** Binary wheels on macOS for Python 3.5 now use Homebrew
  Python for compilation due to new security requirements
- Make build system support new GitHub & PyPI security requirements
- Improvements from libsecp256k1 master

View `all history <https://github.com/ofek/coincurve/blob/master/HISTORY.rst>`_
