import pytest
import coincurve


def test_pubkey_tweak():
    inst = coincurve.PrivateKey()
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
    assert isinstance(res, coincurve.PublicKey)
    assert res.serialize() != pub.serialize()


def test_privkey_tweak():
    key = coincurve.PrivateKey()

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
