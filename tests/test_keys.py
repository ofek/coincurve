from coincurve import PrivateKey, PublicKey
from .samples import PRIVATE_KEY_BYTES, PUBLIC_KEY_COMPRESSED


class TestPrivateKey:
    def test_public_key(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).public_key.format() == PUBLIC_KEY_COMPRESSED
