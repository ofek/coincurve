from coincurve.keys import PrivateKey, PublicKey
from coincurve.utils import bytes_to_int, int_to_bytes_padded, verify_signature
from .samples import (
    PRIVATE_KEY_BYTES,
    PRIVATE_KEY_DER,
    PRIVATE_KEY_HEX,
    PRIVATE_KEY_NUM,
    PRIVATE_KEY_PEM,
    PUBLIC_KEY_COMPRESSED,
    PUBLIC_KEY_UNCOMPRESSED,
    PUBLIC_KEY_X,
    PUBLIC_KEY_Y,
    MESSAGE,
    SIGNATURE,
    RECOVERABLE_SIGNATURE,
)


class TestPrivateKey:
    def test_new(self, benchmark):
        benchmark(PrivateKey)

    def test_load(self, benchmark):
        benchmark(PrivateKey, PRIVATE_KEY_BYTES)

    def test_sign(self, benchmark):
        private_key = PrivateKey(PRIVATE_KEY_BYTES)
        benchmark(private_key.sign, MESSAGE)

    def test_sign_recoverable(self, benchmark):
        private_key = PrivateKey(PRIVATE_KEY_BYTES)
        benchmark(private_key.sign_recoverable, MESSAGE)

    def test_ecdh(self, benchmark):
        private_key = PrivateKey(PRIVATE_KEY_BYTES)
        benchmark(private_key.ecdh, PUBLIC_KEY_COMPRESSED)


class TestPublicKey:
    def test_load(self, benchmark):
        benchmark(PublicKey, PUBLIC_KEY_COMPRESSED)

    def test_load_from_valid_secret(self, benchmark):
        benchmark(PublicKey.from_valid_secret, PRIVATE_KEY_BYTES)
