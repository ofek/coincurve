import pytest
import secp256k1

def test_values():
    assert secp256k1.FLAG_VERIFY == (
        secp256k1.lib.SECP256K1_FLAGS_TYPE_CONTEXT |
        secp256k1.lib.SECP256K1_FLAGS_BIT_CONTEXT_VERIFY)
    assert secp256k1.FLAG_VERIFY == 257
    assert secp256k1.FLAG_SIGN == (
        secp256k1.lib.SECP256K1_FLAGS_TYPE_CONTEXT |
        secp256k1.lib.SECP256K1_FLAGS_BIT_CONTEXT_SIGN)
    assert secp256k1.FLAG_SIGN == 513
    assert secp256k1.ALL_FLAGS == secp256k1.FLAG_SIGN | secp256k1.FLAG_VERIFY

def test_privkey():
    with pytest.raises(AssertionError):
        secp256k1.PrivateKey(flags=secp256k1.FLAG_VERIFY)
    with pytest.raises(AssertionError):
        secp256k1.PrivateKey(flags=0)

    privkey = secp256k1.PrivateKey(flags=secp256k1.FLAG_SIGN)
    sig = privkey.ecdsa_sign(b'hi')
    with pytest.raises(Exception):
        # FLAG_SIGN was not specified.
        privkey.pubkey.ecdsa_verify(b'hi', sig)

    assert privkey.flags == privkey.pubkey.flags

    privkey = secp256k1.PrivateKey()
    sig = privkey.ecdsa_sign(b'hi')
    assert privkey.pubkey.ecdsa_verify(b'hi', sig)

def test_pubkey():
    privkey = secp256k1.PrivateKey()
    sig = privkey.ecdsa_sign(b'hello')
    pubkeyser = privkey.pubkey.serialize()

    pubkey = secp256k1.PublicKey(pubkeyser, raw=True, flags=secp256k1.NO_FLAGS)
    with pytest.raises(Exception):
        # FLAG_SIGN was not specified.
        pubkey.ecdsa_verify(b'hello', sig)

    pubkey = secp256k1.PublicKey(pubkeyser, raw=True)
    assert pubkey.ecdsa_verify(b'hello', sig)

def test_recoverable():
    if not secp256k1.HAS_RECOVERABLE:
        pytest.skip('secp256k1_recovery not enabled, skipping')
        return

    privkey = secp256k1.PrivateKey(flags=secp256k1.FLAG_SIGN)
    x = privkey.ecdsa_sign_recoverable(b'hi')
    with pytest.raises(Exception):
        # All flags required.
        privkey.ecdsa_recover(b'hi', x)

    privkey = secp256k1.PrivateKey()
    x = privkey.ecdsa_sign_recoverable(b'hi')
    privkey.ecdsa_recover(b'hi', x)
