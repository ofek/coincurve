import pytest

import secp256k1

def test_ecdh():
    if not secp256k1.HAS_ECDH:
        pytest.skip('secp256k1_ecdh not enabled, skipping')
        return

    pubkey = secp256k1.PrivateKey().pubkey

    p = secp256k1.PublicKey(pubkey.public_key)
    with pytest.raises(Exception):
        # Bad scalar length.
        p.ecdh(b'')
    with pytest.raises(Exception):
        # Bad scalar type.
        p.ecdh([])

    res = p.ecdh(b'0' * 32)
    assert type(res) == bytes
