# Developer interface

-----

The key classes are immutable native CPython types. ECDSA message methods and explicitly named Schnorr message methods hash with SHA-256 by default, while digest methods accept exactly 32 bytes and avoid calling back into Python.

Private key representations never display secret material. Native secret and keypair storage is cleared when a private key is deallocated.

## Private keys

```python
from coincurve import PrivateKey

key = PrivateKey()
signature = key.sign(b"message")
digest_signature = key.sign_digest(bytes(32))

assert key.public_key.verify(signature, b"message")
assert key.public_key.verify_digest(digest_signature, bytes(32))
```

ECDSA signing is deterministic unless 32-byte `extra_entropy` is supplied. `sign_schnorr()` retains the legacy behavior of signing an exactly 32-byte message without hashing it, while `sign_schnorr_message()` hashes an arbitrary message and `sign_schnorr_digest()` makes the digest contract explicit. Scalar Schnorr signing generates 32 bytes of operating-system auxiliary randomness when `aux_randomness` is omitted or `b""`; pass `None` for no auxiliary randomness or `bytes(32)` for deterministic zero auxiliary data.

::: coincurve.PrivateKey
    options:
      members:
      - __init__
      - secret
      - public_key
      - xonly_public_key
      - sign
      - sign_digest
      - sign_recoverable
      - sign_recoverable_digest
      - sign_schnorr
      - sign_schnorr_message
      - sign_schnorr_digest
      - sign_many
      - sign_digests
      - sign_recoverable_many
      - sign_recoverable_digests
      - sign_schnorr_many
      - sign_schnorr_digests
      - ecdh
      - ecdh_many
      - add
      - multiply
      - to_int
      - to_hex
      - to_pem
      - to_der
      - from_int
      - from_hex
      - from_pem
      - from_der

## Public keys

::: coincurve.PublicKey
    options:
      members:
      - __init__
      - verify
      - verify_digest
      - verify_many
      - verify_digests
      - format
      - point
      - combine
      - combine_keys
      - add
      - multiply
      - recover
      - recover_digest
      - from_secret
      - from_point

::: coincurve.XOnlyPublicKey
    options:
      members:
      - __init__
      - parity
      - verify
      - verify_message
      - verify_digest
      - verify_many
      - verify_digests
      - format
      - add_tweak
      - from_secret
      - from_public_key

## One-shot verification

::: coincurve.verify_signature

::: coincurve.verify_signature_digest

One-shot verification parses the serialized public key and DER signature in a single native call. A malformed or incorrect signature returns `False`; an invalid public key or a digest with the wrong length raises `ValueError`.

## Byte-oriented ECDSA utilities

::: coincurve.ecdsa.der_to_compact

::: coincurve.ecdsa.compact_to_der

::: coincurve.ecdsa.normalize_signature

::: coincurve.ecdsa.recoverable_to_der

## Sequence batches

`coincurve.batch` provides strict pairwise operations. Inputs are materialized before native work begins, pairwise lengths must match without broadcasting, and results retain input order. Verification failures become `False`, recovery failures become `None`, and malformed inputs raise with the offending index.

```python
from hashlib import sha256

from coincurve import PrivateKey
from coincurve import batch

keys = [PrivateKey(), PrivateKey()]
digests = [sha256(b"a").digest(), sha256(b"b").digest()]
signatures = batch.sign_digests(keys, digests)
valid = batch.verify_digests([key.public_key for key in keys], signatures, digests)

assert valid == [True, True]
```

The module exports `sign`, `sign_digests`, `sign_recoverable`, `sign_recoverable_digests`, `sign_schnorr`, `sign_schnorr_digests`, `verify`, `verify_digests`, `verify_schnorr`, `verify_schnorr_digests`, `recover`, `recover_digests`, `ecdh`, `derive_public_keys`, and `derive_xonly_public_keys`.

## Packed batches

`coincurve.batch.packed` accepts contiguous fixed-width records without constructing Python key objects. Operations that can fail return `(output, status)`, failed output records are zero-filled, and verification returns only a status buffer.

| Value | Record width |
| --- | ---: |
| Secret or digest | 32 bytes |
| Compressed public key | 33 bytes |
| X-only public key | 32 bytes |
| Compact ECDSA or Schnorr signature | 64 bytes |
| Recoverable signature | 65 bytes |
| Status | 1 byte, `0` or `1` |

Packed inputs are retained for the full native call. Do not mutate non-secret input buffers concurrently with an operation.

The packed module exports `derive_public_keys`, `derive_xonly_public_keys`, `sign_ecdsa_digests`, `sign_recoverable_digests`, `sign_schnorr_digests`, `verify_ecdsa_digests`, `verify_schnorr_digests`, `recover_public_keys`, and `ecdh`. Every input length must be an exact multiple of its record width, and pairwise record counts must match without broadcasting.
