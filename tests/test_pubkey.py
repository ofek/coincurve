import os
import json
from io import StringIO

import coincurve

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')


def test_pubkey_from_privkey():
    with open(os.path.join(DATA, 'pubkey.json')) as f:
        data = f.read()
    vec = json.loads(data)['vectors']

    inst = coincurve.PrivateKey()

    for item in vec:
        seckey = bytes(bytearray.fromhex(item['seckey']))
        pubkey_uncp = bytes(bytearray.fromhex(item['pubkey']))
        pubkey_comp = bytes(bytearray.fromhex(item['compressed']))

        inst.set_raw_privkey(seckey)

        assert inst.pubkey.serialize(compressed=False) == pubkey_uncp
        assert inst.pubkey.serialize(compressed=True) == pubkey_comp

        assert inst.deserialize(inst.serialize()) == seckey


def test_pubkey_combine():
    k1 = coincurve.PrivateKey()
    k2 = coincurve.PrivateKey()

    pub1 = k1.pubkey.public_key
    pub2 = k2.pubkey.public_key
    new = coincurve.PublicKey()
    assert new.public_key is None
    res = new.combine([pub1, pub2])
    assert new.public_key == res

    new = coincurve.PublicKey()
    assert new.public_key is None
    res = new.combine([pub1])
    assert new.public_key == res
    assert new.serialize() == k1.pubkey.serialize()
