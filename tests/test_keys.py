from hashlib import sha512
from os import urandom

import pytest

from coincurve.keys import PrivateKey, PublicKey
from coincurve.utils import verify_signature
from .samples import (
    PRIVATE_KEY_BYTES, PRIVATE_KEY_DER, PRIVATE_KEY_NUM, PRIVATE_KEY_PEM,
    PUBLIC_KEY_COMPRESSED, PUBLIC_KEY_UNCOMPRESSED, PUBLIC_KEY_X,
    PUBLIC_KEY_Y, MESSAGE, SIGNATURE
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

    def test_signature_invalid_hasher(self):
        with pytest.raises(ValueError):
            PrivateKey().sign(MESSAGE, lambda x:sha512(x).digest())

    def test_to_int(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).to_int() == PRIVATE_KEY_NUM

    def test_to_pem(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).to_pem() == PRIVATE_KEY_PEM

    def test_to_der(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).to_der() == PRIVATE_KEY_DER

    def test_from_int(self):
        assert PrivateKey.from_int(PRIVATE_KEY_NUM).secret == PRIVATE_KEY_BYTES

    def test_from_pem(self):
        assert PrivateKey.from_pem(PRIVATE_KEY_PEM).secret == PRIVATE_KEY_BYTES

    def test_from_der(self):
        assert PrivateKey.from_der(PRIVATE_KEY_DER).secret == PRIVATE_KEY_BYTES

    def test_add(self):
        assert PrivateKey(b'\x01').add(b'\x09').to_int() == 10

    def test_add_update(self):
        private_key = PrivateKey(b'\x01')
        new_private_key = private_key.add(b'\x09', update=True)

        assert new_private_key.to_int() == 10
        assert private_key is new_private_key

    def test_multiply(self):
        assert PrivateKey(b'\x05').multiply(b'\x05').to_int() == 25

    def test_multiply_update(self):
        private_key = PrivateKey(b'\x05')
        new_private_key = private_key.multiply(b'\x05', update=True)

        assert new_private_key.to_int() == 25
        assert private_key is new_private_key


class TestPublicKey:
    def test_from_secret(self):
        assert PublicKey.from_secret(PRIVATE_KEY_BYTES).format() == PUBLIC_KEY_COMPRESSED

    def test_from_point(self):
        assert PublicKey.from_point(PUBLIC_KEY_X, PUBLIC_KEY_Y).format() == PUBLIC_KEY_COMPRESSED

    def test_format(self):
        assert PublicKey(PUBLIC_KEY_UNCOMPRESSED).format(compressed=True) == PUBLIC_KEY_COMPRESSED
        assert PublicKey(PUBLIC_KEY_COMPRESSED).format(compressed=False) == PUBLIC_KEY_UNCOMPRESSED

    def test_point(self):
        assert PublicKey(PUBLIC_KEY_COMPRESSED).point() == (
            PUBLIC_KEY_X, PUBLIC_KEY_Y
        )

    def test_verify(self):
        public_key = PublicKey(PUBLIC_KEY_COMPRESSED)
        assert public_key.verify(SIGNATURE, MESSAGE)



















