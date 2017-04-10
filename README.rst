Coincurve
=========

.. image:: https://img.shields.io/pypi/v/coincurve.svg?style=flat-square
    :target: https://pypi.org/project/coincurve

.. image:: https://img.shields.io/travis/ofek/coincurve.svg?branch=master&style=flat-square
    :target: https://travis-ci.org/ofek/coincurve

.. image:: https://img.shields.io/pypi/pyversions/coincurve.svg?style=flat-square
    :target: https://pypi.org/project/coincurve

.. image:: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
    :target: https://en.wikipedia.org/wiki/MIT_License

-----

This library provides well-tested Python CFFI bindings for
`libsecp256k1 <https://github.com/bitcoin-core/secp256k1>`_, the heavily
optimized C library used by `Bitcoin Core <https://github.com/bitcoin/bitcoin>`_
for operations on elliptic curve secp256k1.

Coincurve replaces `secp256k1-py <https://github.com/ludbb/secp256k1-py>`_.

New features include:

- Support for Windows
- Linux, macOS, and Windows all have binary packages for both 64 and 32-bit architectures
- Linux & macOS use GMP for faster computation
- Endomorphism optimization is enabled
- A global context is used by default, drastically increasing performance
- A fix to remove CFFI warnings
- Each release uses newest version of `libsecp256k1 <https://github.com/bitcoin-core/secp256k1>`_
- Implements a fix for `<https://bugs.python.org/issue28150>`_ to support Python 3.6+ on macOS

**To retain backward compatibility with secp256k1-py, use coincurve version 2.1.1 specifically!**
Anything after that has a modified (cleaner :) API.

Installation
------------

Coincurve is distributed on PyPI and is available on Linux/macOS and Windows and
supports Python 2.7/3.5+ and PyPy2.7-v5.7.1/PyPy3.5-v5.7.1+.

.. code-block:: bash

    $ pip install coincurve

API
---

Coincurve provides a simple API.

coincurve.PrivateKey
^^^^^^^^^^^^^^^^^^^^

All instances have a ``public_key`` of type ``coincurve.PublicKey``

``PrivateKey(secret=None, context=GLOBAL_CONTEXT)``

* Parameters:

    - **secret** (``bytes``) - The secret to use.
    - **context** (``coincurve.Context``)

Methods
~~~~~~~

*classmethod* ``from_int(num, context=GLOBAL_CONTEXT)``

*classmethod* ``from_pem(pem, context=GLOBAL_CONTEXT)``

*classmethod* ``from_der(der, context=GLOBAL_CONTEXT)``

``sign(message, hasher=sha256)``

* Parameters:

    - **message** (``bytes``) - The message to sign.
    - **hasher** - The hash function to use. hasher(message) must return 32 bytes.

* Returns: ``bytes``. 71 <= len(signature) <= 72

``sign_recoverable(message, hasher=sha256)``

* Parameters:

    - **message** (``bytes``) - The message to sign.
    - **hasher** - The hash function to use. hasher(message) must return 32 bytes.

* Returns: ``bytes``

``ecdh(public_key, update=False)``

* Parameters:

    - **public_key** (``bytes``) - The other party's public key.
    - **update** - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PrivateKey``

``add(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to add.
    - **update** - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PrivateKey``

``multiply(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to multiply.
    - **update** - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PrivateKey``

``to_int()``

``to_pem()``

``to_der()``

coincurve.PublicKey
^^^^^^^^^^^^^^^^^^^

``PublicKey(data, context=GLOBAL_CONTEXT)``

* Parameters:

    - **data** (``bytes``) - The public key in compressed or uncompressed form.
    - **context** (``coincurve.Context``)

*classmethod* ``from_secret(secret, context=GLOBAL_CONTEXT)``

*classmethod* ``from_valid_secret(secret, context=GLOBAL_CONTEXT)``

*classmethod* ``from_point(x, y, context=GLOBAL_CONTEXT)``

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
    - **hasher** - The hash function to use. hasher(message) must return 32 bytes.

* Returns: The public key serialized to ``bytes``.

``add(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to add.
    - **update** - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PublicKey``

``multiply(scalar, update=False)``

* Parameters:

    - **scalar** (``bytes``) - The scalar to multiply.
    - **update** - If ``True``, will update and return ``self``.

* Returns: ``coincurve.PublicKey``










