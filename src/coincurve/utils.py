from __future__ import annotations

from base64 import b64decode, b64encode
from hashlib import sha256 as _sha256
from os import environ, urandom
from typing import TYPE_CHECKING

from coincurve._libsecp256k1 import ffi, lib
from coincurve.context import GLOBAL_CONTEXT, Context

if TYPE_CHECKING:
    from collections.abc import Generator

    from coincurve.types import Hasher

GROUP_ORDER = (
    b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xba\xae\xdc\xe6\xafH\xa0;\xbf\xd2^\x8c\xd06AA"
)
GROUP_ORDER_INT = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
KEY_SIZE = 32
MSG_HASH_SIZE = 32
ZERO = b"\x00"
PEM_HEADER = b"-----BEGIN PRIVATE KEY-----\n"
PEM_FOOTER = b"-----END PRIVATE KEY-----\n"


if environ.get("COINCURVE_BUILDING_DOCS") != "true":
    DEFAULT_NONCE = (ffi.NULL, ffi.NULL)

    def sha256(bytestr: bytes) -> bytes:
        return _sha256(bytestr).digest()

else:  # no cov

    class __Nonce(tuple):  # noqa: SLOT001
        def __repr__(self) -> str:
            return "(ffi.NULL, ffi.NULL)"

    class __HasherSHA256:
        def __call__(self, bytestr: bytes) -> bytes:
            return _sha256(bytestr).digest()

        def __repr__(self) -> str:
            return "sha256"

    DEFAULT_NONCE = __Nonce((ffi.NULL, ffi.NULL))
    sha256 = __HasherSHA256()


def pad_hex(hexed: str) -> str:
    # Pad odd-length hex strings.
    return hexed if not len(hexed) & 1 else f"0{hexed}"


def bytes_to_int(bytestr: bytes) -> int:
    return int.from_bytes(bytestr, "big")


def int_to_bytes(num: int) -> bytes:
    return num.to_bytes((num.bit_length() + 7) // 8 or 1, "big")


def int_to_bytes_padded(num: int) -> bytes:
    return pad_scalar(num.to_bytes((num.bit_length() + 7) // 8 or 1, "big"))


def hex_to_bytes(hexed: str) -> bytes:
    return pad_scalar(bytes.fromhex(pad_hex(hexed)))


def chunk_data(data: bytes, size: int) -> Generator[bytes, None, None]:
    return (data[i : i + size] for i in range(0, len(data), size))


def der_to_pem(der: bytes) -> bytes:
    return b"".join([PEM_HEADER, b"\n".join(chunk_data(b64encode(der), 64)), b"\n", PEM_FOOTER])


def pem_to_der(pem: bytes) -> bytes:
    return b64decode(b"".join(pem.strip().splitlines()[1:-1]))


def get_valid_secret() -> bytes:
    while True:
        secret = urandom(KEY_SIZE)
        if ZERO < secret < GROUP_ORDER:
            return secret


def pad_scalar(scalar: bytes) -> bytes:
    return (ZERO * (KEY_SIZE - len(scalar))) + scalar


def validate_secret(secret: bytes) -> bytes:
    if not 0 < bytes_to_int(secret) < GROUP_ORDER_INT:
        msg = f"Secret scalar must be greater than 0 and less than {GROUP_ORDER_INT}."
        raise ValueError(msg)
    return pad_scalar(secret)


def verify_signature(
    signature: bytes, message: bytes, public_key: bytes, hasher: Hasher = sha256, context: Context = GLOBAL_CONTEXT
) -> bool:
    """
    Verify an ECDSA signature.

    Parameters:
        signature: The ECDSA signature.
        message: The message that was supposedly signed.
        public_key: The formatted public key.
        hasher (collections.abc.Callable[[bytes], bytes] | None): The hash function to use, which must return 32 bytes.
            By default, the `sha256` algorithm is used. If `None`, no hashing occurs.
        context: The secp256k1 context.

    Returns:
        A boolean indicating whether or not the signature is correct.

    Raises:
        ValueError: If the public key could not be parsed or was invalid, the
            message hash was not 32 bytes long, or the DER-encoded signature
            could not be parsed.
    """
    pubkey = ffi.new("secp256k1_pubkey *")

    pubkey_parsed = lib.secp256k1_ec_pubkey_parse(context.ctx, pubkey, public_key, len(public_key))

    if not pubkey_parsed:
        msg = "The public key could not be parsed or is invalid."
        raise ValueError(msg)

    msg_hash = hasher(message) if hasher is not None else message
    if len(msg_hash) != MSG_HASH_SIZE:
        msg = "Message hash must be 32 bytes long."
        raise ValueError(msg)

    sig = ffi.new("secp256k1_ecdsa_signature *")

    sig_parsed = lib.secp256k1_ecdsa_signature_parse_der(context.ctx, sig, signature, len(signature))

    if not sig_parsed:
        msg = "The DER-encoded signature could not be parsed."
        raise ValueError(msg)

    verified = lib.secp256k1_ecdsa_verify(context.ctx, sig, msg_hash, pubkey)

    # A performance hack to avoid global bool() lookup.
    return not not verified  # noqa: SIM208
