import pytest
import hashlib
import coincurve

def test_privkey():
    with pytest.raises(TypeError):
        key = 'abc'
        coincurve.PrivateKey(key)

    with pytest.raises(TypeError):
        key = bytearray.fromhex('a' * 32)  # This will result in 16 bytes.
        coincurve.PrivateKey(bytes(key))

    with pytest.raises(Exception):
        coincurve.PrivateKey(bytes(bytearray.fromhex('0' * 64)))

    with pytest.raises(Exception):
        coincurve.PrivateKey(bytes(bytearray.fromhex('F' * 64)))

    with pytest.raises(Exception):
        # This is a good raw key, but here it's being passed as serialized.
        coincurve.PrivateKey(b'1' * 32, raw=False)

    # "good" key, should be fine.
    assert coincurve.PrivateKey(b'1' * 32)

def test_publickey():
    with pytest.raises(Exception):
        # Must be bytes.

        # In Python 2 this will not raise a TypeError
        # since bytes is an alias to str, instead it will fail
        # during deserialization.
        coincurve.PublicKey('abc', raw=True)
    with pytest.raises(Exception):
        coincurve.PublicKey([], raw=True)

    with pytest.raises(Exception):
        # Invalid size.
        coincurve.PublicKey(b'abc', raw=True)

    with pytest.raises(Exception):
        # Invalid public key.
        coincurve.PublicKey(b'a' * 33, raw=True)

    # Invalid usage: passing a raw public key but not specifying raw=True.
    with pytest.raises(TypeError):
        coincurve.PublicKey(b'a' * 33)

    # No public key.
    assert coincurve.PublicKey()

    pub1 = coincurve.PrivateKey().pubkey.public_key
    new = coincurve.PublicKey()
    with pytest.raises(AssertionError):
        # Trying to combine with something that is not a public key.
        new.combine([pub1, coincurve.ffi.NULL])

    new = coincurve.PublicKey()
    with pytest.raises(AssertionError):
        # Nothing to combine.
        new.combine([])

def test_ecdsa():
    rawkey = (b'\xc9\xa9)Z\xf8Er\x97\x8b\xa23\x1f\xf7\xb6\x82qQ\xdc9\xc1'
              b'\x1d\xac6\xfd\xeb\x11\x05\xb1\xdf\x86\xb3\xe6')
    priv = coincurve.PrivateKey(rawkey)
    with pytest.raises(Exception):
        # Bad digest function (doesn't produce 256 bits).
        priv.ecdsa_sign(b'hi', digest=hashlib.sha1)

    raw_sig = priv.ecdsa_sign(b'hi')
    assert priv.pubkey.ecdsa_verify(b'hi', raw_sig)

    with pytest.raises(AssertionError):
        sig = priv.ecdsa_serialize(raw_sig)[:-1]
        priv.ecdsa_deserialize(sig)

    sig = priv.ecdsa_serialize(raw_sig)
    sig = sig[:-1] + bytes(sig[0:1])  # Assuming sig[0] != sig[-1].
    invalid_sig = priv.ecdsa_deserialize(sig)
    assert not priv.pubkey.ecdsa_verify(b'hi', invalid_sig)

def test_ecdsa_compact():
    key = coincurve.PrivateKey()

    raw_sig = key.ecdsa_sign(b'hi')
    with pytest.raises(TypeError):
        # Should pass a compact serialization.
        key.ecdsa_deserialize_compact(raw_sig)

    ser = key.ecdsa_serialize(raw_sig)
    with pytest.raises(Exception):
        # A serialization that is not compact has more than 64 bytes.
        key.ecdsa_deserialize_compact(ser)

def test_ecdsa_recoverable():
    if not coincurve.HAS_RECOVERABLE:
        pytest.skip('secp256k1_recovery not enabled, skipping')
        return

    key = '32a8935ffdb984a498b0f7ac8943e0d2ac084e81c809595fd19fde41522f1837'
    priv = coincurve.PrivateKey(bytes(bytearray.fromhex(key)))
    sig = priv.ecdsa_sign_recoverable(b'hi')
    sig_ser, rec_id = priv.ecdsa_recoverable_serialize(sig)
    assert rec_id == 1

    with pytest.raises(Exception):
        # Invalid rec_id (must be between 0 and 3)
        priv.ecdsa_recoverable_deserialize(sig_ser, -1)

    # Deserialize using a rec_id that does not match.
    sig = priv.ecdsa_recoverable_deserialize(sig_ser, 2)
    with pytest.raises(Exception):
        # Now try to recover the public key.
        priv.ecdsa_recover(b'hi', sig)

    # Invalid size.
    with pytest.raises(Exception):
        priv.ecdsa_recoverable_deserialize(b'hello', 0)

def test_schnorr():
    if not coincurve.HAS_SCHNORR:
        pytest.skip('secp256k1_schnorr not enabled, skipping')
        return

    inst = coincurve.PrivateKey()
    raw_sig = inst.schnorr_sign(b'hello')

    test1 = coincurve.PublicKey(inst.pubkey.public_key,
                                flags=coincurve.NO_FLAGS)
    with pytest.raises(Exception):
        test1.schnorr_verify(b'hello', raw_sig)

    blank = coincurve.PublicKey(flags=coincurve.NO_FLAGS)
    with pytest.raises(Exception):
        blank.schnorr_recover(b'hello', raw_sig)

    blank = coincurve.PublicKey(flags=coincurve.FLAG_SIGN)
    with pytest.raises(Exception):
        blank.schnorr_recover(b'hello', raw_sig)

def test_schnorr_partial():
    if not coincurve.HAS_SCHNORR:
        pytest.skip('secp256k1_schnorr not enabled, skipping')
        return

    signer1 = coincurve.PrivateKey()
    pubnonce1, privnonce1 = signer1.schnorr_generate_nonce_pair(b'hello')

    signer2 = coincurve.PrivateKey()
    pubnonce2, privnonce2 = signer2.schnorr_generate_nonce_pair(b'hello')

    partial1 = signer1.schnorr_partial_sign(b'hello', privnonce1, pubnonce2)
    blank = coincurve.PublicKey(flags=coincurve.NO_FLAGS)

    with pytest.raises(TypeError):
        blank.schnorr_partial_combine([partial1, coincurve.ffi.NULL])

    with pytest.raises(Exception):
        blank.schnorr_partial_combine([partial1, b''])

def test_tweak():
    key = coincurve.PrivateKey()

    # Tweak out of range
    scalar = b'\xFF' * 32
    with pytest.raises(Exception):
        key.tweak_mul(scalar)
    with pytest.raises(Exception):
        key.tweak_add(scalar)
    with pytest.raises(Exception):
        key.pubkey.tweak_mul(scalar)
    with pytest.raises(Exception):
        key.pubkey.tweak_add(scalar)
