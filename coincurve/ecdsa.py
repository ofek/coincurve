from coincurve import GLOBAL_CONTEXT
from ._libsecp256k1 import ffi, lib

MAX_SIG_LENGTH = 72
CDATA_SIG_LENGTH = 64


def cdata_to_der(cdata, context=GLOBAL_CONTEXT):
    der = ffi.new('unsigned char[%d]' % MAX_SIG_LENGTH)
    der_length = ffi.new('size_t *', MAX_SIG_LENGTH)

    res = lib.secp256k1_ecdsa_signature_serialize_der(
        context.ctx, der, der_length, cdata
    )
    assert res == 1

    return bytes(ffi.buffer(der, der_length[0]))


def der_to_cdata(der, context=GLOBAL_CONTEXT):
    cdata = ffi.new('secp256k1_ecdsa_signature *')
    res = lib.secp256k1_ecdsa_signature_parse_der(
        context.ctx, cdata, der, len(der)
    )
    assert res == 1

    return cdata


def serialize_compact(raw_sig, context=GLOBAL_CONTEXT):
    output = ffi.new('unsigned char[%d]' % CDATA_SIG_LENGTH)

    res = lib.secp256k1_ecdsa_signature_serialize_compact(
        context.ctx, output, raw_sig
    )
    assert res == 1

    return bytes(ffi.buffer(output, CDATA_SIG_LENGTH))


def deserialize_compact(ser_sig, context=GLOBAL_CONTEXT):
    if len(ser_sig) != 64:
        raise Exception("invalid signature length")

    raw_sig = ffi.new('secp256k1_ecdsa_signature *')
    res = lib.secp256k1_ecdsa_signature_parse_compact(
        context.ctx, raw_sig, ser_sig
    )
    assert res == 1

    return raw_sig


def signature_normalize(raw_sig, context=GLOBAL_CONTEXT):
    """
    Check and optionally convert a signature to a normalized lower-S form.
    If check_only is True then the normalized signature is not returned.

    This function always return a tuple containing a boolean (True if
    not previously normalized or False if signature was already
    normalized), and the normalized signature. When check_only is True,
    the normalized signature returned is always None.
    """
    sigout = ffi.new('secp256k1_ecdsa_signature *')

    res = lib.secp256k1_ecdsa_signature_normalize(
        context.ctx, sigout, raw_sig
    )

    return not not res, sigout


def recover(msg, recover_sig, context=GLOBAL_CONTEXT):
    pubkey = ffi.new('secp256k1_pubkey *')

    recovered = lib.secp256k1_ecdsa_recover(
        context.ctx, pubkey, recover_sig, msg
    )
    if recovered:
        return pubkey
    raise Exception('failed to recover ECDSA public key')


def recoverable_to_der(recover_sig, context=GLOBAL_CONTEXT):
    output = ffi.new('unsigned char[%d]' % CDATA_SIG_LENGTH)
    recid = ffi.new('int *')

    lib.secp256k1_ecdsa_recoverable_signature_serialize_compact(
        context.ctx, output, recid, recover_sig
    )

    return bytes(ffi.buffer(output, CDATA_SIG_LENGTH)), recid[0]


def der_to_recoverable(ser_sig, rec_id, context=GLOBAL_CONTEXT):
    if rec_id < 0 or rec_id > 3:
        raise Exception("invalid rec_id")
    if len(ser_sig) != 64:
        raise Exception("invalid signature length")

    recover_sig = ffi.new('secp256k1_ecdsa_recoverable_signature *')

    parsed = lib.secp256k1_ecdsa_recoverable_signature_parse_compact(
        context.ctx, recover_sig, ser_sig, rec_id
    )
    if parsed:
        return recover_sig
    else:
        raise Exception('failed to parse ECDSA compact sig')


def recoverable_convert(recover_sig, context=GLOBAL_CONTEXT):
    normal_sig = ffi.new('secp256k1_ecdsa_signature *')

    lib.secp256k1_ecdsa_recoverable_signature_convert(
        context.ctx, normal_sig, recover_sig
    )

    return normal_sig
