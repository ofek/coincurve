import pytest

import coincurve

def test_schnorr_simple():
    if not coincurve.HAS_SCHNORR:
        pytest.skip('secp256k1_schnorr not enabled, skipping')
        return

    inst = coincurve.PrivateKey()
    raw_sig = inst.schnorr_sign(b'hello')

    assert inst.pubkey.schnorr_verify(b'hello', raw_sig)
    key2 = coincurve.PrivateKey()
    assert not key2.pubkey.schnorr_verify(b'hello', raw_sig)

    blank = coincurve.PublicKey()
    pubkey = blank.schnorr_recover(b'hello', raw_sig)
    pub = coincurve.PublicKey(pubkey)
    assert pub.serialize() == inst.pubkey.serialize()

def test_schnorr_partial():
    if not coincurve.HAS_SCHNORR:
        pytest.skip('secp256k1_schnorr not enabled, skipping')
        return

    signer1 = coincurve.PrivateKey()
    pubnonce1, privnonce1 = signer1.schnorr_generate_nonce_pair(b'hello')

    signer2 = coincurve.PrivateKey()
    pubnonce2, privnonce2 = signer2.schnorr_generate_nonce_pair(b'hello')

    # First test partial signatures with only two signers.
    partial1 = signer1.schnorr_partial_sign(b'hello', privnonce1, pubnonce2)
    partial2 = signer2.schnorr_partial_sign(b'hello', privnonce2, pubnonce1)
    blank = coincurve.PublicKey(flags=coincurve.NO_FLAGS)
    sig = blank.schnorr_partial_combine([partial1, partial2])

    # Recover the public key from the combined signature.
    pubkey = coincurve.PublicKey().schnorr_recover(b'hello', sig)

    assert blank.public_key is None
    # Check that the combined public keys from signer1 and signer2
    # match the recovered public key.
    blank.combine(
        [signer1.pubkey.public_key, signer2.pubkey.public_key])
    assert blank.public_key
    assert coincurve.PublicKey(pubkey).serialize() == blank.serialize()
