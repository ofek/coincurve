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

- `<https://www.ethereum.org>`_
- `<https://lbry.io>`_
- `<https://ark.io>`_
- `<https://www.augur.net>`_
- `<https://www.nucypher.com>`_
- `<https://raiden.network>`_
- `<https://golem.network>`_
- `<https://omisego.network>`_

and `many more <https://github.com/ofek/coincurve/blob/master/DOWNSTREAM.rst>`_

Installation
------------

Coincurve is distributed on PyPI and is available on Linux/macOS and Windows and
supports Python 2.7/3.5+ and PyPy3.5-v5.8.1+.

.. code-block:: bash

    $ pip install coincurve

If you are on a system that doesn't have a precompiled binary wheel (e.g. FreeBSD)
then pip will fetch source to build yourself. You must have the necessary packages.

On Debian/Ubuntu the necessary system packages are:

- ``build-essential``
- ``automake``
- ``pkg-config``
- ``libtool``
- ``libffi-dev``
- ``python3-dev`` (or ``python-dev`` for Python 2)
- ``libgmp-dev`` (optional)

On macOS the necessary Homebrew packages are:

- ``automake``
- ``pkg-config``
- ``libtool``
- ``libffi``
- ``gmp`` (optional)

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

12.0.0
^^^^^^

- **New:** Binary wheels on Linux for PyPy3.6 v7.1.1-beta!
- **New:** Binary wheels on macOS for Python 3.8.0-alpha.3!
- **New:** Binary wheels on Linux are now also built with the new `manylinux2010 <https://www.python.org/dev/peps/pep-0571>`_ spec for 64-bit platforms!
- Improvements from libsecp256k1 master

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
