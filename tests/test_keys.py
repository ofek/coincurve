from os import urandom

from coincurve.keys import PrivateKey, PublicKey
from coincurve.utils import verify_signature
from .samples import (
    PRIVATE_KEY_BYTES, PUBLIC_KEY_COMPRESSED, PUBLIC_KEY_UNCOMPRESSED,
    MESSAGE, SIGNATURE
)


class TestPrivateKey:
    def test_public_key(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).public_key.format() == PUBLIC_KEY_COMPRESSED

    def test_signature_correct(self):
        private_key = PrivateKey()
        public_key = private_key.public_key

        message = urandom(200)
        signature = private_key.sign(message)

        assert verify_signature(signature, message, public_key.format(compressed=True))
        assert verify_signature(signature, message, public_key.format(compressed=False))

    def test_signature_deterministic(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).sign(MESSAGE) == SIGNATURE
