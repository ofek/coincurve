from __future__ import annotations

from typing import TYPE_CHECKING

from coincurve._coincurve import (
    _batch_derive_public_keys,
    _batch_derive_xonly_public_keys,
    _batch_ecdh,
    _batch_recover_digests,
    _batch_sign_digests,
    _batch_sign_recoverable_digests,
    _batch_sign_schnorr_digests,
    _batch_verify_digests,
    _batch_verify_schnorr_digests,
)
from coincurve.batch import packed
from coincurve.utils import MSG_HASH_SIZE, sha256

if TYPE_CHECKING:
    from collections.abc import Iterable

    from coincurve import PrivateKey, PublicKey, XOnlyPublicKey
    from coincurve.types import Hasher


def _hash_message(message: bytes, hasher: Hasher, index: int) -> bytes:
    try:
        digest = hasher(message)
    except Exception as error:
        if hasattr(error, "add_note"):
            error.add_note(f"The hasher failed for messages[{index}].")
        raise
    if type(digest) is bytes and len(digest) == MSG_HASH_SIZE:
        return digest
    try:
        view = memoryview(digest)
    except TypeError:
        message_text = f"The hasher result for messages[{index}] must be a readable buffer."
        raise TypeError(message_text) from None
    if view.ndim != 1 or not view.c_contiguous:
        message_text = f"The hasher result for messages[{index}] must be one-dimensional and C-contiguous."
        raise TypeError(message_text)
    if view.nbytes != MSG_HASH_SIZE:
        message_text = f"The hasher result for messages[{index}] must be exactly 32 bytes."
        raise ValueError(message_text)
    return bytes(view)


def _hash_messages(messages: Iterable[bytes], hasher: Hasher) -> tuple[bytes, ...]:
    return tuple(_hash_message(message, hasher, index) for index, message in enumerate(messages))


def sign(private_keys: Iterable[PrivateKey], messages: Iterable[bytes], hasher: Hasher = sha256) -> list[bytes]:
    return _batch_sign_digests(private_keys, _hash_messages(messages, hasher))


def sign_digests(private_keys: Iterable[PrivateKey], digests: Iterable[bytes]) -> list[bytes]:
    return _batch_sign_digests(private_keys, digests)


def sign_recoverable(
    private_keys: Iterable[PrivateKey], messages: Iterable[bytes], hasher: Hasher = sha256
) -> list[bytes]:
    return _batch_sign_recoverable_digests(private_keys, _hash_messages(messages, hasher))


def sign_recoverable_digests(private_keys: Iterable[PrivateKey], digests: Iterable[bytes]) -> list[bytes]:
    return _batch_sign_recoverable_digests(private_keys, digests)


def sign_schnorr(private_keys: Iterable[PrivateKey], messages: Iterable[bytes], hasher: Hasher = sha256) -> list[bytes]:
    return _batch_sign_schnorr_digests(private_keys, _hash_messages(messages, hasher))


def sign_schnorr_digests(private_keys: Iterable[PrivateKey], digests: Iterable[bytes]) -> list[bytes]:
    return _batch_sign_schnorr_digests(private_keys, digests)


def verify(
    public_keys: Iterable[PublicKey], signatures: Iterable[bytes], messages: Iterable[bytes], hasher: Hasher = sha256
) -> list[bool]:
    return _batch_verify_digests(public_keys, signatures, _hash_messages(messages, hasher))


def verify_digests(
    public_keys: Iterable[PublicKey], signatures: Iterable[bytes], digests: Iterable[bytes]
) -> list[bool]:
    return _batch_verify_digests(public_keys, signatures, digests)


def verify_schnorr(
    public_keys: Iterable[XOnlyPublicKey],
    signatures: Iterable[bytes],
    messages: Iterable[bytes],
    hasher: Hasher = sha256,
) -> list[bool]:
    return _batch_verify_schnorr_digests(public_keys, signatures, _hash_messages(messages, hasher))


def verify_schnorr_digests(
    public_keys: Iterable[XOnlyPublicKey], signatures: Iterable[bytes], digests: Iterable[bytes]
) -> list[bool]:
    return _batch_verify_schnorr_digests(public_keys, signatures, digests)


def recover(signatures: Iterable[bytes], messages: Iterable[bytes], hasher: Hasher = sha256) -> list[PublicKey | None]:
    return _batch_recover_digests(signatures, _hash_messages(messages, hasher))


def recover_digests(signatures: Iterable[bytes], digests: Iterable[bytes]) -> list[PublicKey | None]:
    return _batch_recover_digests(signatures, digests)


def ecdh(private_keys: Iterable[PrivateKey], peer_public_keys: Iterable[PublicKey]) -> list[bytes]:
    return _batch_ecdh(private_keys, peer_public_keys)


def derive_public_keys(secrets: Iterable[bytes]) -> list[PublicKey]:
    return _batch_derive_public_keys(secrets)


def derive_xonly_public_keys(secrets: Iterable[bytes]) -> list[XOnlyPublicKey]:
    return _batch_derive_xonly_public_keys(secrets)


__all__ = [
    "derive_public_keys",
    "derive_xonly_public_keys",
    "ecdh",
    "packed",
    "recover",
    "recover_digests",
    "sign",
    "sign_digests",
    "sign_recoverable",
    "sign_recoverable_digests",
    "sign_schnorr",
    "sign_schnorr_digests",
    "verify",
    "verify_digests",
    "verify_schnorr",
    "verify_schnorr_digests",
]
