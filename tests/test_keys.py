from hashlib import sha512
from os import urandom

import pytest

from coincurve.ecdsa import deserialize_recoverable, recover
from coincurve.keys import PrivateKey, PublicKey
from coincurve.utils import bytes_to_int, int_to_bytes_padded, verify_signature
from .samples import (
    PRIVATE_KEY_BYTES, PRIVATE_KEY_DER, PRIVATE_KEY_HEX, PRIVATE_KEY_NUM,
    PRIVATE_KEY_PEM, PUBLIC_KEY_COMPRESSED, PUBLIC_KEY_UNCOMPRESSED,
    PUBLIC_KEY_X, PUBLIC_KEY_Y, MESSAGE, SIGNATURE, RECOVERABLE_SIGNATURE
)


G = PublicKey(b'\x04y\xbef~\xf9\xdc\xbb\xacU\xa0b\x95\xce\x87\x0b\x07\x02\x9b'
              b'\xfc\xdb-\xce(\xd9Y\xf2\x81[\x16\xf8\x17\x98H:\xdaw&\xa3\xc4e'
              b']\xa4\xfb\xfc\x0e\x11\x08\xa8\xfd\x17\xb4H\xa6\x85T\x19\x9cG'
              b'\xd0\x8f\xfb\x10\xd4\xb8')
n = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141


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
            PrivateKey().sign(MESSAGE, lambda x: sha512(x).digest())

    def test_signature_recoverable(self):
        private_key = PrivateKey(PRIVATE_KEY_BYTES)
        assert private_key.public_key.format() == PublicKey(
            recover(MESSAGE, deserialize_recoverable(private_key.sign_recoverable(MESSAGE)))
        ).format()

    def test_to_hex(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).to_hex() == PRIVATE_KEY_HEX

    def test_to_int(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).to_int() == PRIVATE_KEY_NUM

    def test_to_pem(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).to_pem() == PRIVATE_KEY_PEM

    def test_to_der(self):
        assert PrivateKey(PRIVATE_KEY_BYTES).to_der() == PRIVATE_KEY_DER

    def test_from_hex(self):
        assert PrivateKey.from_hex(PRIVATE_KEY_HEX).secret == PRIVATE_KEY_BYTES

    def test_from_int(self):
        assert PrivateKey.from_int(PRIVATE_KEY_NUM).secret == PRIVATE_KEY_BYTES

    def test_from_pem(self):
        assert PrivateKey.from_pem(PRIVATE_KEY_PEM).secret == PRIVATE_KEY_BYTES

    def test_from_der(self):
        assert PrivateKey.from_der(PRIVATE_KEY_DER).secret == PRIVATE_KEY_BYTES

    def test_ecdh(self):
        a = PrivateKey()
        b = PrivateKey()

        assert a.ecdh(b.public_key.format()) == b.ecdh(a.public_key.format())

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

    def test_from_signature_and_message(self):
        assert PublicKey.from_secret(PRIVATE_KEY_BYTES).format() == PublicKey.from_signature_and_message(
            RECOVERABLE_SIGNATURE, MESSAGE
        ).format()

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

    def test_transform(self):
        x = urandom(32)
        k = urandom(32)
        point = G.multiply(x)

        assert point.add(k) == G.multiply(int_to_bytes_padded(
            (bytes_to_int(x) + bytes_to_int(k)) % n
        ))
