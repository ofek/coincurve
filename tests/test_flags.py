import pytest
import coincurve

def test_values():
    assert coincurve.FLAG_VERIFY == (
        coincurve.lib.SECP256K1_FLAGS_TYPE_CONTEXT |
        coincurve.lib.SECP256K1_FLAGS_BIT_CONTEXT_VERIFY)
    assert coincurve.FLAG_VERIFY == 257
    assert coincurve.FLAG_SIGN == (
        coincurve.lib.SECP256K1_FLAGS_TYPE_CONTEXT |
        coincurve.lib.SECP256K1_FLAGS_BIT_CONTEXT_SIGN)
    assert coincurve.FLAG_SIGN == 513
    assert coincurve.ALL_FLAGS == coincurve.FLAG_SIGN | coincurve.FLAG_VERIFY

def test_privkey():
    with pytest.raises(AssertionError):
        coincurve.PrivateKey(flags=coincurve.FLAG_VERIFY)
    with pytest.raises(AssertionError):
        coincurve.PrivateKey(flags=0)

    privkey = coincurve.PrivateKey(flags=coincurve.FLAG_SIGN)
    sig = privkey.ecdsa_sign(b'hi')
    with pytest.raises(Exception):
        # FLAG_SIGN was not specified.
        privkey.pubkey.ecdsa_verify(b'hi', sig)

    assert privkey.flags == privkey.pubkey.flags

    privkey = coincurve.PrivateKey()
    sig = privkey.ecdsa_sign(b'hi')
    assert privkey.pubkey.ecdsa_verify(b'hi', sig)

def test_pubkey():
    privkey = coincurve.PrivateKey()
    sig = privkey.ecdsa_sign(b'hello')
    pubkeyser = privkey.pubkey.serialize()

    pubkey = coincurve.PublicKey(pubkeyser, raw=True, flags=coincurve.NO_FLAGS)
    with pytest.raises(Exception):
        # FLAG_SIGN was not specified.
        pubkey.ecdsa_verify(b'hello', sig)

    pubkey = coincurve.PublicKey(pubkeyser, raw=True)
    assert pubkey.ecdsa_verify(b'hello', sig)

def test_recoverable():
    if not coincurve.HAS_RECOVERABLE:
        pytest.skip('secp256k1_recovery not enabled, skipping')
        return

    privkey = coincurve.PrivateKey(flags=coincurve.FLAG_SIGN)
    x = privkey.ecdsa_sign_recoverable(b'hi')
    with pytest.raises(Exception):
        # All flags required.
        privkey.ecdsa_recover(b'hi', x)

    privkey = coincurve.PrivateKey()
    x = privkey.ecdsa_sign_recoverable(b'hi')
    privkey.ecdsa_recover(b'hi', x)
