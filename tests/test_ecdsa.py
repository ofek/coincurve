import os
import json
import pytest
from io import StringIO

import coincurve

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')


def test_ecdsa():
    data = open(os.path.join(DATA, 'ecdsa_sig.json')).read()
    vec = json.loads(data)['vectors']

    inst = coincurve.PrivateKey()

    for item in vec:
        seckey = bytes(bytearray.fromhex(item['privkey']))
        msg32 = bytes(bytearray.fromhex(item['msg']))
        sig = bytes(bytearray.fromhex(item['sig'])[:-1])

        inst.set_raw_privkey(seckey)

        sig_raw = inst.ecdsa_sign(msg32, raw=True)
        sig_check = inst.ecdsa_serialize(sig_raw)
        assert sig_check == sig
        assert inst.ecdsa_serialize(inst.ecdsa_deserialize(sig_check)) == sig_check

        assert inst.pubkey.ecdsa_verify(msg32, sig_raw, raw=True)

def test_ecdsa_compact():
    key = coincurve.PrivateKey()
    raw_sig = key.ecdsa_sign(b'test')
    assert key.pubkey.ecdsa_verify(b'test', raw_sig)

    compact = key.ecdsa_serialize_compact(raw_sig)
    assert len(compact) == 64

    sig_raw = key.ecdsa_deserialize_compact(compact)
    assert key.ecdsa_serialize_compact(sig_raw) == compact
    assert key.pubkey.ecdsa_verify(b'test', sig_raw)

def test_ecdsa_normalize():
    key = coincurve.PrivateKey()
    raw_sig = key.ecdsa_sign(b'hi')

    had_to_normalize, normsig = key.ecdsa_signature_normalize(raw_sig)
    assert had_to_normalize == False
    assert key.ecdsa_serialize(normsig) == key.ecdsa_serialize(raw_sig)
    assert key.ecdsa_serialize_compact(normsig) == \
            key.ecdsa_serialize_compact(raw_sig)

    had_to_normalize, normsig = key.ecdsa_signature_normalize(
        raw_sig, check_only=True)
    assert had_to_normalize == False
    assert normsig == None

    sig = b'\xAA' + (b'\xFF' * 31) + b'\xAA' + (b'\xFF' * 31)
    raw_sig = key.ecdsa_deserialize_compact(sig)
    normalized, normsig = key.ecdsa_signature_normalize(raw_sig)
    assert normalized == True
    assert key.ecdsa_serialize(normsig) != key.ecdsa_serialize(raw_sig)
    normalized, normsig = key.ecdsa_signature_normalize(raw_sig, True)
    assert normalized == True
    assert normsig == None

def test_ecdsa_recover():
    if not coincurve.HAS_RECOVERABLE:
        pytest.skip('secp256k1_recovery not enabled, skipping')
        return

    class MyECDSA(coincurve.Base, coincurve.ECDSA):
        def __init__(self):
            coincurve.Base.__init__(self, ctx=None, flags=coincurve.ALL_FLAGS)

    privkey = coincurve.PrivateKey()
    unrelated = MyECDSA()

    # Create a signature that allows recovering the public key.
    recsig = privkey.ecdsa_sign_recoverable(b'hello')
    # Recover the public key.
    pubkey = unrelated.ecdsa_recover(b'hello', recsig)
    # Check that the recovered public key matches the one used
    # in privkey.pubkey.
    pubser = coincurve.PublicKey(pubkey).serialize()
    assert privkey.pubkey.serialize() == pubser

    # Check that after serializing and deserializing recsig
    # we still recover the same public key.
    recsig_ser = unrelated.ecdsa_recoverable_serialize(recsig)
    recsig2 = unrelated.ecdsa_recoverable_deserialize(*recsig_ser)
    pubkey2 = unrelated.ecdsa_recover(b'hello', recsig2)
    pubser2 = coincurve.PublicKey(pubkey2).serialize()
    assert pubser == pubser2

    raw_sig = unrelated.ecdsa_recoverable_convert(recsig2)
    unrelated.ecdsa_deserialize(unrelated.ecdsa_serialize(raw_sig))
