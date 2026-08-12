# Migrating to 2026.8.0

-----

Version 2026.8.0 replaces the CFFI binding with immutable native CPython types. Legacy operations that remain safe on immutable objects retain their behavior, while mutating call patterns fail with migration guidance.

## API replacements

| Before | Now |
| --- | --- |
| `PublicKeyXOnly` | `XOnlyPublicKey` |
| `private_key.public_key_xonly` | `private_key.xonly_public_key` |
| `sign(message, hasher=None)` | `sign_digest(digest)` |
| `verify(signature, message, hasher=None)` | `verify_digest(signature, digest)` |
| `custom_nonce` | `extra_entropy` containing exactly 32 bytes |
| `key.add(scalar, update=True)` | `key = key.add(scalar)` |
| `key.multiply(scalar, update=True)` | `key = key.multiply(scalar)` |
| `key.combine(keys, update=True)` | `key = key.combine(keys)` |
| `xonly_key.tweak_add(scalar)` | `xonly_key = xonly_key.add_tweak(scalar)` |
| `PublicKey.from_signature_and_message(...)` | `PublicKey.recover(...)` |
| CFFI signature conversion objects | Byte-oriented functions in `coincurve.ecdsa` |

`PrivateKey(secret)` now requires exactly 32 bytes. Use `PrivateKey.from_int()` or `PrivateKey.from_hex()` for shorter scalar forms.

`PublicKey.combine(keys)` remains an instance operation and includes the receiver in the sum. `PublicKey.combine_keys(keys)` combines a complete sequence without an implicit receiver.

`PrivateKey.sign_schnorr(message, aux_randomness=b"")` and `XOnlyPublicKey.verify(signature, message)` continue to operate on raw messages, including the legacy requirement that signing input is exactly 32 bytes. Use `sign_schnorr_message()` and `verify_message()` when SHA-256 hashing is wanted, or the explicit digest methods when the input is already a 32-byte digest. For scalar signing, omitted or empty auxiliary randomness is generated, while explicit `None` disables auxiliary randomness.

Parsed x-only keys report `parity=None` unless the parity is supplied as `XOnlyPublicKey(data, parity=...)`. Keys derived from a secret, converted from a full public key, or returned by `add_tweak()` have known parity.

## Removed APIs

`Context`, `GLOBAL_CONTEXT`, context arguments, public flag constants, arbitrary nonce callbacks, CFFI objects, pointer-oriented ECDSA helpers, mutable tweaks, legacy scalar and secret helpers in `coincurve.utils`, and PyPy support have been removed.

## Performance-oriented usage

Prefer digest methods when the caller already has a 32-byte digest. They avoid a Python hasher call and make the cost of the binding visible.

Use same-key instance batches when one key handles many inputs, `coincurve.batch` for pairwise Python objects, and `coincurve.batch.packed` for fixed-width data pipelines that can avoid per-item Python objects.

## Versioning

Coincurve now uses `YYYY.MM.PATCH` calendar versions. August 2026 releases begin with `2026.8.0` and continue as `2026.8.1`, while the first September release is `2026.9.0`. Prereleases use PEP 440 forms such as `2026.8.0rc1`, release tags use forms such as `v2026.8.0`, and the version identifies release time rather than API compatibility. Breaking changes may occur in any new calendar release and will be called out explicitly in the history.
