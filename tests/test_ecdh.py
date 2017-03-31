import pytest

import coincurve


def test_ecdh():
    if not coincurve.HAS_ECDH:
        pytest.skip('secp256k1_ecdh not enabled, skipping')
        return

    pubkey = coincurve.PrivateKey().pubkey

    p = coincurve.PublicKey(pubkey.public_key)
    with pytest.raises(Exception):
        # Bad scalar length.
        p.ecdh(b'')
    with pytest.raises(Exception):
        # Bad scalar type.
        p.ecdh([])

    res = p.ecdh(b'0' * 32)
    assert type(res) == bytes
