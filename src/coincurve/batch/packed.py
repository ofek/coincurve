from __future__ import annotations

from typing import TypeAlias

from coincurve._coincurve import (
    _packed_derive_public_keys,
    _packed_derive_xonly_public_keys,
    _packed_ecdh,
    _packed_recover_public_keys,
    _packed_sign_ecdsa_digests,
    _packed_sign_recoverable_digests,
    _packed_sign_schnorr_digests,
    _packed_verify_ecdsa_digests,
    _packed_verify_schnorr_digests,
)

ReadableBuffer: TypeAlias = bytes | bytearray | memoryview


def derive_public_keys(secrets: ReadableBuffer) -> tuple[bytes, bytes]:
    """Derive packed compressed public keys and statuses from 32-byte secret records."""
    return _packed_derive_public_keys(secrets)


def derive_xonly_public_keys(secrets: ReadableBuffer) -> tuple[bytes, bytes]:
    """Derive packed x-only public keys and statuses from 32-byte secret records."""
    return _packed_derive_xonly_public_keys(secrets)


def sign_ecdsa_digests(secrets: ReadableBuffer, digests: ReadableBuffer) -> tuple[bytes, bytes]:
    """Sign packed digest records and return compact ECDSA signatures with statuses."""
    return _packed_sign_ecdsa_digests(secrets, digests)


def sign_recoverable_digests(secrets: ReadableBuffer, digests: ReadableBuffer) -> tuple[bytes, bytes]:
    """Sign packed digest records and return recoverable signatures with statuses."""
    return _packed_sign_recoverable_digests(secrets, digests)


def sign_schnorr_digests(secrets: ReadableBuffer, digests: ReadableBuffer) -> tuple[bytes, bytes]:
    """Sign packed digest records and return Schnorr signatures with statuses."""
    return _packed_sign_schnorr_digests(secrets, digests)


def verify_ecdsa_digests(public_keys: ReadableBuffer, signatures: ReadableBuffer, digests: ReadableBuffer) -> bytes:
    """Verify packed compact ECDSA signatures and return one status byte per record."""
    return _packed_verify_ecdsa_digests(public_keys, signatures, digests)


def verify_schnorr_digests(public_keys: ReadableBuffer, signatures: ReadableBuffer, digests: ReadableBuffer) -> bytes:
    """Verify packed Schnorr signatures and return one status byte per record."""
    return _packed_verify_schnorr_digests(public_keys, signatures, digests)


def recover_public_keys(signatures: ReadableBuffer, digests: ReadableBuffer) -> tuple[bytes, bytes]:
    """Recover packed compressed public keys and statuses from recoverable signatures."""
    return _packed_recover_public_keys(signatures, digests)


def ecdh(secrets: ReadableBuffer, public_keys: ReadableBuffer) -> tuple[bytes, bytes]:
    """Derive packed ECDH shared secrets and statuses from pairwise records."""
    return _packed_ecdh(secrets, public_keys)


__all__ = [
    "derive_public_keys",
    "derive_xonly_public_keys",
    "ecdh",
    "recover_public_keys",
    "sign_ecdsa_digests",
    "sign_recoverable_digests",
    "sign_schnorr_digests",
    "verify_ecdsa_digests",
    "verify_schnorr_digests",
]
