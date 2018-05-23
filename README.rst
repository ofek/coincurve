Coincurve
=========

.. image:: https://img.shields.io/pypi/v/coincurve.svg?style=flat-square
    :target: https://pypi.org/project/coincurve

.. image:: https://img.shields.io/travis/ofek/coincurve/master.svg?style=flat-square
    :target: https://travis-ci.org/ofek/coincurve

.. image:: https://img.shields.io/pypi/pyversions/coincurve.svg?style=flat-square
    :target: https://pypi.org/project/coincurve

.. image:: https://img.shields.io/pypi/l/coincurve.svg?style=flat-square
    :target: https://choosealicense.com/licenses

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

- `ethereum/pyethereum <https://github.com/ethereum/pyethereum/pull/777>`_
- `ethereum/py-evm <https://github.com/ethereum/py-evm/pull/31>`_
- `ethereum/pydevp2p <https://github.com/ethereum/pydevp2p/pull/80>`_
- `ethereum/eth-keys <https://github.com/ethereum/eth-keys/commit/81755dfda714d77c1f8a092810ca31e570d84425>`_
- `raiden-network/raiden <https://github.com/raiden-network/raiden/pull/534>`_
- `raiden-network/microraiden <https://github.com/raiden-network/microraiden/blob/8d5f1d86818f01c8cafe9366da1cecdef0e8b0f4/requirements.txt#L5>`_
- `raiden-network/raiden-contracts <https://github.com/raiden-network/raiden-contracts/blob/f251c01015564a2b91401692234aa5ed1ea67ebc/requirements.txt#L3>`_
- `golemfactory/golem <https://github.com/golemfactory/golem/pull/1527>`_
- `golemfactory/golem-messages <https://github.com/golemfactory/golem-messages/blob/1f72b6a6757036218cdf471c0295b8895b963266/setup.py#L39>`_
- `PeerAssets/pypeerassets <https://github.com/PeerAssets/pypeerassets/commit/113c9a234c94499c7e591b8a93928be0a77298fa>`_
- `btcrecover <https://github.com/gurnec/btcrecover/commit/f113867fa22d2f5b22175cc2b5b3892351bc1109>`_
- `crankycoin <https://github.com/cranklin/crankycoin/blob/3d2b3482698227397a8daf30e0b80b2f2c030aec/requirements.txt#L8>`_

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
- libgmp-dev

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

7.1.0
^^^^^

- Pin version of libsecp256k1
- Improve docs

7.0.0
^^^^^

- Improvements from libsecp256k1 master
- Fix build script

6.0.0
^^^^^

- Resolved `#6 <https://github.com/ofek/coincurve/issues/6>`_. You can choose
  to use this or remain on 5.2.0. This will only be a temporary change. See
  `<https://github.com/ofek/coincurve/commit/3e93480b3e38c6b9beb0bc2de83bc3630fc74c46>`_

View `all history <https://github.com/ofek/coincurve/blob/master/HISTORY.rst>`_
