from __future__ import annotations

from typing import TYPE_CHECKING

from coincurve._libsecp256k1 import ffi, lib
from coincurve.context import GLOBAL_CONTEXT, Context
from coincurve.utils import bytes_to_int, int_to_bytes, sha256

if TYPE_CHECKING:
    from coincurve.types import Hasher

MAX_SIG_LENGTH = 72
CDATA_SIG_LENGTH = 64


def cdata_to_der(cdata, context: Context = GLOBAL_CONTEXT) -> bytes:
    der = ffi.new("unsigned char[72]")
    der_length = ffi.new("size_t *", MAX_SIG_LENGTH)

    lib.secp256k1_ecdsa_signature_serialize_der(context.ctx, der, der_length, cdata)

    return bytes(ffi.buffer(der, der_length[0]))


def der_to_cdata(der: bytes, context: Context = GLOBAL_CONTEXT):
    cdata = ffi.new("secp256k1_ecdsa_signature *")
    parsed = lib.secp256k1_ecdsa_signature_parse_der(context.ctx, cdata, der, len(der))

    if not parsed:
        msg = "The DER-encoded signature could not be parsed."
        raise ValueError(msg)

    return cdata


def recover(message: bytes, recover_sig, hasher: Hasher = sha256, context: Context = GLOBAL_CONTEXT):
    msg_hash = hasher(message) if hasher is not None else message
    if len(msg_hash) != 32:  # noqa: PLR2004
        msg = "Message hash must be 32 bytes long."
        raise ValueError(msg)
    pubkey = ffi.new("secp256k1_pubkey *")

    recovered = lib.secp256k1_ecdsa_recover(context.ctx, pubkey, recover_sig, msg_hash)
    if recovered:
        return pubkey
    msg = "failed to recover ECDSA public key"
    raise ValueError(msg)


def serialize_recoverable(recover_sig, context: Context = GLOBAL_CONTEXT) -> bytes:
    output = ffi.new("unsigned char[64]")
    recid = ffi.new("int *")

    lib.secp256k1_ecdsa_recoverable_signature_serialize_compact(context.ctx, output, recid, recover_sig)

    return bytes(ffi.buffer(output, CDATA_SIG_LENGTH)) + int_to_bytes(recid[0])


def deserialize_recoverable(serialized: bytes, context: Context = GLOBAL_CONTEXT):
    if len(serialized) != 65:  # noqa: PLR2004
        msg = "Serialized signature must be 65 bytes long."
        raise ValueError(msg)

    ser_sig, rec_id = serialized[:64], bytes_to_int(serialized[64:])

    if not 0 <= rec_id <= 3:  # noqa: PLR2004
        msg = "Invalid recovery id."
        raise ValueError(msg)

    recover_sig = ffi.new("secp256k1_ecdsa_recoverable_signature *")

    parsed = lib.secp256k1_ecdsa_recoverable_signature_parse_compact(context.ctx, recover_sig, ser_sig, rec_id)
    if not parsed:
        msg = "Failed to parse recoverable signature."
        raise ValueError(msg)

    return recover_sig


"""
Warning:
    The functions below may change and are not tested!
"""


def serialize_compact(raw_sig, context: Context = GLOBAL_CONTEXT):  # no cov
    output = ffi.new("unsigned char[64]")

    res = lib.secp256k1_ecdsa_signature_serialize_compact(context.ctx, output, raw_sig)
    if not res:
        msg = "secp256k1_ecdsa_signature_serialize_compact"
        raise ValueError(msg)

    return bytes(ffi.buffer(output, CDATA_SIG_LENGTH))


def deserialize_compact(ser_sig: bytes, context: Context = GLOBAL_CONTEXT):  # no cov
    if len(ser_sig) != 64:  # noqa: PLR2004
        msg = "invalid signature length"
        raise ValueError(msg)

    raw_sig = ffi.new("secp256k1_ecdsa_signature *")
    res = lib.secp256k1_ecdsa_signature_parse_compact(context.ctx, raw_sig, ser_sig)
    if not res:
        msg = "secp256k1_ecdsa_signature_parse_compact"
        raise ValueError(msg)

    return raw_sig


def signature_normalize(raw_sig, context: Context = GLOBAL_CONTEXT):  # no cov
    """
    Check and optionally convert a signature to a normalized lower-S form.

    This function always return a tuple containing a boolean (True if
    not previously normalized or False if signature was already
    normalized), and the normalized signature.
    """
    sigout = ffi.new("secp256k1_ecdsa_signature *")

    res = lib.secp256k1_ecdsa_signature_normalize(context.ctx, sigout, raw_sig)

    return not not res, sigout  # noqa: SIM208


def recoverable_convert(recover_sig, context: Context = GLOBAL_CONTEXT):  # no cov
    normal_sig = ffi.new("secp256k1_ecdsa_signature *")

    lib.secp256k1_ecdsa_recoverable_signature_convert(context.ctx, normal_sig, recover_sig)

    return normal_sig
