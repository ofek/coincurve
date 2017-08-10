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

Coincurve replaces `secp256k1-py <https://github.com/ludbb/secp256k1-py>`_.

New features include:

- Cleaner API
- Uses newest version of `libsecp256k1 <https://github.com/bitcoin-core/secp256k1>`_
- Support for Windows
- Linux, macOS, and Windows all have binary packages for both 64 and 32-bit architectures
- Linux & macOS use GMP for faster computation
- Endomorphism optimization is enabled
- A global context is used by default, drastically increasing performance
- Fixed ECDH
- A fix to remove CFFI warnings
- Implements a fix for `<https://bugs.python.org/issue28150>`_ to support Python 3.6+ on macOS

Table of Contents
~~~~~~~~~~~~~~~~~

.. contents::
    :backlinks: top
    :local:

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

* Returns: ``bytes``. 71 <= len(signature) <= 72

``sign_recoverable(message, hasher=sha256)``

* Parameters:

    - **message** (``bytes``) - The message to sign.
    - **hasher** - The hash function to use, can be ``None``. hasher(message) must return 32 bytes.

* Returns: ``bytes``

``ecdh(public_key)``

Computes a Diffie-Hellman secret in constant time.

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

Changelog
---------

Important changes are emphasized.

5.2.0
^^^^^

- Added support for supplying a custom nonce to ``PrivateKey.sign``.

5.1.0
^^^^^

- Added ``PublicKey.combine_keys`` class method.
- Improvements to documentation.

5.0.1
^^^^^

- Fixed an issue where ``validate_secret`` would occasionally erroneously error
  on user-provided secrets (secrets not generated by Coincurve itself) if there
  were not exactly 256 bits of entropy. See
  `#5 <https://github.com/ofek/coincurve/issues/5>`_

5.0.0
^^^^^

- **Breaking:** Coincurve is now dual-licensed under the terms of MIT and Apache v2.0.
- Performance improvements from libsecp256k1 master:
  `1 <https://github.com/bitcoin-core/secp256k1/commit/cf12fa13cb96797d6ce356a5023051f99f915fe6>`_
  `2 <https://github.com/bitcoin-core/secp256k1/commit/aa8499080e2a657113781921096b59a74d7bc0e7>`_
  `3 <https://github.com/bitcoin-core/secp256k1/commit/8b7680a826498a786eca5737e0e97ee4d2e63713>`_
  `4 <https://github.com/bitcoin-core/secp256k1/commit/465159c278cecc2cf8d934e78f640f345243eb72>`_
  `5 <https://github.com/bitcoin-core/secp256k1/commit/4cc8f52505b2922390a115c77eeb3b251bc9af88>`_
  `6 <https://github.com/bitcoin-core/secp256k1/commit/cbc20b8c34d44c2ef175420f3cdfe054f82e8e2c>`_
- Improvements to documentation.

4.5.1
^^^^^

- First public stable release
