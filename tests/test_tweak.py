import pytest
import secp256k1

def test_pubkey_tweak():
    inst = secp256k1.PrivateKey()
    pub = inst.pubkey

    scalar = [b'\x01' * 32]
    with pytest.raises(TypeError):
        pub.tweak_add(scalar)
    with pytest.raises(TypeError):
        pub.tweak_mul(scalar)

    scalar = b'\x01' * 31
    with pytest.raises(TypeError):
        pub.tweak_add(scalar)
    with pytest.raises(TypeError):
        pub.tweak_mul(scalar)

    scalar = scalar + b'\x01'
    res = pub.tweak_add(scalar)
    assert isinstance(res, secp256k1.PublicKey)
    assert res.serialize() != pub.serialize()

def test_privkey_tweak():
    key = secp256k1.PrivateKey()

    scalar = [b'\x01' * 32]
    with pytest.raises(TypeError):
        key.tweak_add(scalar)
    with pytest.raises(TypeError):
        key.tweak_mul(scalar)

    scalar = b'\x01' * 31
    with pytest.raises(TypeError):
        key.tweak_add(scalar)
    with pytest.raises(TypeError):
        key.tweak_mul(scalar)

    scalar = scalar + b'\x01'
    res = key.tweak_add(scalar)
    assert isinstance(res, bytes) and len(res) == 32
