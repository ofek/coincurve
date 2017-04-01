from ._libsecp256k1 import ffi, lib


def ecdsa_serialize(raw_sig):
    len_sig = 74
    output = ffi.new('unsigned char[%d]' % len_sig)
    outputlen = ffi.new('size_t *', len_sig)

    res = lib.secp256k1_ecdsa_signature_serialize_der(
        self.ctx, output, outputlen, raw_sig)
    assert res == 1

    return bytes(ffi.buffer(output, outputlen[0]))


def ecdsa_deserialize(ser_sig):
    raw_sig = ffi.new('secp256k1_ecdsa_signature *')
    res = lib.secp256k1_ecdsa_signature_parse_der(
        self.ctx, raw_sig, ser_sig, len(ser_sig))
    assert res == 1

    return raw_sig


def ecdsa_serialize_compact(raw_sig):
    len_sig = 64
    output = ffi.new('unsigned char[%d]' % len_sig)

    res = lib.secp256k1_ecdsa_signature_serialize_compact(
        self.ctx, output, raw_sig)
    assert res == 1

    return bytes(ffi.buffer(output, len_sig))


def ecdsa_deserialize_compact(ser_sig):
    if len(ser_sig) != 64:
        raise Exception("invalid signature length")

    raw_sig = ffi.new('secp256k1_ecdsa_signature *')
    res = lib.secp256k1_ecdsa_signature_parse_compact(
        self.ctx, raw_sig, ser_sig)
    assert res == 1

    return raw_sig


def ecdsa_signature_normalize(raw_sig, check_only=False):
    """
    Check and optionally convert a signature to a normalized lower-S form.
    If check_only is True then the normalized signature is not returned.

    This function always return a tuple containing a boolean (True if
    not previously normalized or False if signature was already
    normalized), and the normalized signature. When check_only is True,
    the normalized signature returned is always None.
    """
    if check_only:
        sigout = ffi.NULL
    else:
        sigout = ffi.new('secp256k1_ecdsa_signature *')

    result = lib.secp256k1_ecdsa_signature_normalize(
        self.ctx, sigout, raw_sig)

    return (bool(result), sigout if sigout != ffi.NULL else None)


def ecdsa_recover(msg, recover_sig, raw=False, digest=hashlib.sha256):
    if not HAS_RECOVERABLE:
        raise Exception("secp256k1_recovery not enabled")
    if self.flags & ALL_FLAGS != ALL_FLAGS:
        raise Exception("instance not configured for ecdsa recover")

    msg32 = _hash32(msg, raw, digest)
    pubkey = ffi.new('secp256k1_pubkey *')

    recovered = lib.secp256k1_ecdsa_recover(
        self.ctx, pubkey, recover_sig, msg32)
    if recovered:
        return pubkey
    raise Exception('failed to recover ECDSA public key')


def ecdsa_recoverable_serialize(recover_sig):
    if not HAS_RECOVERABLE:
        raise Exception("secp256k1_recovery not enabled")

    outputlen = 64
    output = ffi.new('unsigned char[%d]' % outputlen)
    recid = ffi.new('int *')

    lib.secp256k1_ecdsa_recoverable_signature_serialize_compact(
        self.ctx, output, recid, recover_sig)

    return bytes(ffi.buffer(output, outputlen)), recid[0]


def ecdsa_recoverable_deserialize(ser_sig, rec_id):
    if not HAS_RECOVERABLE:
        raise Exception("secp256k1_recovery not enabled")
    if rec_id < 0 or rec_id > 3:
        raise Exception("invalid rec_id")
    if len(ser_sig) != 64:
        raise Exception("invalid signature length")

    recover_sig = ffi.new('secp256k1_ecdsa_recoverable_signature *')

    parsed = lib.secp256k1_ecdsa_recoverable_signature_parse_compact(
        self.ctx, recover_sig, ser_sig, rec_id)
    if parsed:
        return recover_sig
    else:
        raise Exception('failed to parse ECDSA compact sig')


def ecdsa_recoverable_convert(recover_sig):
    if not HAS_RECOVERABLE:
        raise Exception("secp256k1_recovery not enabled")

    normal_sig = ffi.new('secp256k1_ecdsa_signature *')

    lib.secp256k1_ecdsa_recoverable_signature_convert(
        self.ctx, normal_sig, recover_sig)

    return normal_sig
