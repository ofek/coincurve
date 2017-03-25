import pytest

import secp256k1

def test_schnorr_simple():
    if not secp256k1.HAS_SCHNORR:
        pytest.skip('secp256k1_schnorr not enabled, skipping')
        return

    inst = secp256k1.PrivateKey()
    raw_sig = inst.schnorr_sign(b'hello')

    assert inst.pubkey.schnorr_verify(b'hello', raw_sig)
    key2 = secp256k1.PrivateKey()
    assert not key2.pubkey.schnorr_verify(b'hello', raw_sig)

    blank = secp256k1.PublicKey()
    pubkey = blank.schnorr_recover(b'hello', raw_sig)
    pub = secp256k1.PublicKey(pubkey)
    assert pub.serialize() == inst.pubkey.serialize()

def test_schnorr_partial():
    if not secp256k1.HAS_SCHNORR:
        pytest.skip('secp256k1_schnorr not enabled, skipping')
        return

    signer1 = secp256k1.PrivateKey()
    pubnonce1, privnonce1 = signer1.schnorr_generate_nonce_pair(b'hello')

    signer2 = secp256k1.PrivateKey()
    pubnonce2, privnonce2 = signer2.schnorr_generate_nonce_pair(b'hello')

    # First test partial signatures with only two signers.
    partial1 = signer1.schnorr_partial_sign(b'hello', privnonce1, pubnonce2)
    partial2 = signer2.schnorr_partial_sign(b'hello', privnonce2, pubnonce1)
    blank = secp256k1.PublicKey(flags=secp256k1.NO_FLAGS)
    sig = blank.schnorr_partial_combine([partial1, partial2])

    # Recover the public key from the combined signature.
    pubkey = secp256k1.PublicKey().schnorr_recover(b'hello', sig)

    assert blank.public_key is None
    # Check that the combined public keys from signer1 and signer2
    # match the recovered public key.
    blank.combine(
        [signer1.pubkey.public_key, signer2.pubkey.public_key])
    assert blank.public_key
    assert secp256k1.PublicKey(pubkey).serialize() == blank.serialize()
