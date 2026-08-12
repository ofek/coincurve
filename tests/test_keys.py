from hashlib import sha256, sha512
from os import urandom

import pytest

from coincurve import PrivateKey, PublicKey, XOnlyPublicKey, batch, verify_signature, verify_signature_digest
from coincurve.batch import packed

G = PublicKey(
    b"\x04y\xbef~\xf9\xdc\xbb\xacU\xa0b\x95\xce\x87\x0b\x07\x02\x9b"
    b"\xfc\xdb-\xce(\xd9Y\xf2\x81[\x16\xf8\x17\x98H:\xdaw&\xa3\xc4e"
    b"]\xa4\xfb\xfc\x0e\x11\x08\xa8\xfd\x17\xb4H\xa6\x85T\x19\x9cG"
    b"\xd0\x8f\xfb\x10\xd4\xb8"
)
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


class TestPrivateKey:
    def test_public_keys(self, samples):
        key = PrivateKey(samples["PRIVATE_KEY_BYTES"])
        assert key.public_key.format() == samples["PUBLIC_KEY_COMPRESSED"]
        assert key.xonly_public_key.format() == samples["PUBLIC_KEY_COMPRESSED"][1:]

    def test_sign_and_verify(self):
        private_key = PrivateKey()
        message = urandom(200)
        signature = private_key.sign(message)
        digest = sha256(message).digest()
        assert private_key.public_key.verify(signature, message)
        assert private_key.public_key.verify_digest(signature, digest)
        assert verify_signature(signature, message, private_key.public_key.format())
        assert verify_signature_digest(signature, digest, private_key.public_key.format(compressed=False))

    def test_signature_deterministic(self, samples):
        private_key = PrivateKey(samples["PRIVATE_KEY_BYTES"])
        assert private_key.sign(samples["MESSAGE"]) == samples["SIGNATURE"]
        assert private_key.sign_digest(sha256(samples["MESSAGE"]).digest()) == samples["SIGNATURE"]

    def test_invalid_hasher(self, samples):
        with pytest.raises(ValueError, match="exactly 32 bytes"):
            PrivateKey().sign(samples["MESSAGE"], lambda value: sha512(value).digest())

    def test_recoverable_signature(self, samples):
        private_key = PrivateKey(samples["PRIVATE_KEY_BYTES"])
        signature = private_key.sign_recoverable(samples["MESSAGE"])
        digest = sha256(samples["MESSAGE"]).digest()
        assert signature == samples["RECOVERABLE_SIGNATURE"]
        assert PublicKey.recover(signature, samples["MESSAGE"]) == private_key.public_key
        assert PublicKey.recover_digest(signature, digest) == private_key.public_key
        assert private_key.sign_recoverable_digests([digest]) == [signature]
        assert batch.sign_recoverable_digests([private_key], [digest]) == [signature]
        assert batch.recover_digests([signature], [digest]) == [private_key.public_key]
        packed_signature, sign_status = packed.sign_recoverable_digests(private_key.secret, digest)
        packed_public_key, recover_status = packed.recover_public_keys(packed_signature, digest)
        assert packed_signature == signature
        assert sign_status == recover_status == b"\x01"
        assert packed_public_key == bytes(private_key.public_key)

    def test_schnorr_signature(self):
        private_key = PrivateKey()
        digest = urandom(32)
        signature = private_key.sign_schnorr_digest(digest, aux_randomness=bytes(32))
        assert private_key.xonly_public_key.verify_digest(signature, digest)
        assert private_key.xonly_public_key.verify(private_key.sign_schnorr(digest), digest)
        message_signature = private_key.sign_schnorr_message(b"message", aux_randomness=bytes(32))
        assert private_key.xonly_public_key.verify_message(message_signature, b"message")
        with pytest.raises(ValueError, match="exactly 32 bytes"):
            private_key.sign_schnorr_digest(digest + b"\x01")

    def test_serialization(self, samples):
        private_key = PrivateKey(samples["PRIVATE_KEY_BYTES"])
        assert private_key.to_hex() == samples["PRIVATE_KEY_HEX"]
        assert private_key.to_int() == samples["PRIVATE_KEY_NUM"]
        assert private_key.to_pem() == samples["PRIVATE_KEY_PEM"]
        assert private_key.to_der() == samples["PRIVATE_KEY_DER"]
        assert PrivateKey.from_hex(samples["PRIVATE_KEY_HEX"]) == private_key
        assert PrivateKey.from_int(samples["PRIVATE_KEY_NUM"]) == private_key
        assert PrivateKey.from_pem(samples["PRIVATE_KEY_PEM"]) == private_key
        assert PrivateKey.from_der(samples["PRIVATE_KEY_DER"]) == private_key

    def test_ecdh(self):
        first = PrivateKey()
        second = PrivateKey()
        assert first.ecdh(second.public_key) == second.ecdh(first.public_key)
        generator = PrivateKey.from_int(1)
        assert generator.ecdh(generator.public_key) == sha256(bytes(generator.public_key)).digest()

    def test_immutable_tweaks(self):
        one = PrivateKey.from_int(1)
        five = PrivateKey.from_int(5)
        assert one.add((9).to_bytes(32, "big")).to_int() == 10
        assert five.multiply((5).to_bytes(32, "big")).to_int() == 25
        assert one.to_int() == 1
        assert five.to_int() == 5


class TestPublicKey:
    def test_construction_and_serialization(self, samples):
        assert PublicKey.from_secret(samples["PRIVATE_KEY_BYTES"]).format() == samples["PUBLIC_KEY_COMPRESSED"]
        assert (
            PublicKey.from_point(samples["PUBLIC_KEY_X"], samples["PUBLIC_KEY_Y"]).format()
            == samples["PUBLIC_KEY_COMPRESSED"]
        )
        key = PublicKey(samples["PUBLIC_KEY_UNCOMPRESSED"])
        assert bytes(key) == samples["PUBLIC_KEY_COMPRESSED"]
        assert key.format(compressed=False) == samples["PUBLIC_KEY_UNCOMPRESSED"]
        assert key.point() == (samples["PUBLIC_KEY_X"], samples["PUBLIC_KEY_Y"])

    def test_verify(self, samples):
        assert PublicKey(samples["PUBLIC_KEY_COMPRESSED"]).verify(samples["SIGNATURE"], samples["MESSAGE"])

    def test_transform(self):
        scalar = urandom(32)
        tweak = urandom(32)
        point = G.multiply(scalar)
        combined = (int.from_bytes(scalar, "big") + int.from_bytes(tweak, "big")) % N
        assert point.add(tweak) == G.multiply(combined.to_bytes(32, "big"))

    def test_combine(self):
        first = PrivateKey()
        second = PrivateKey()
        expected = PrivateKey.from_int((first.to_int() + second.to_int()) % N).public_key
        assert first.public_key.combine([second.public_key]) == expected
        assert PublicKey.combine_keys([first.public_key, second.public_key]) == expected


class TestXOnlyPublicKey:
    def test_parse_invalid(self, samples):
        with pytest.raises(ValueError, match="valid secp256k1 private key"):
            XOnlyPublicKey.from_secret(bytes(32))
        with pytest.raises(ValueError, match="could not be parsed"):
            XOnlyPublicKey(samples["X_ONLY_PUBKEY_INVALID"])

    def test_roundtrip(self, samples):
        key = XOnlyPublicKey(samples["X_ONLY_PUBKEY"])
        assert key.format() == samples["X_ONLY_PUBKEY"]
        assert key == XOnlyPublicKey(samples["X_ONLY_PUBKEY"])
        assert key.parity is None
        assert XOnlyPublicKey(samples["X_ONLY_PUBKEY"], parity=False).parity is False

    @pytest.mark.parametrize(
        ("key_hex", "tweak_hex", "expected_hex", "parity"),
        [
            (
                "187791b6f712a8ea41c8ecdd0ee77fab3e85263b37e1ec18a3651926b3a6cf27",
                "cbd8679ba636c1110ea247542cfbd964131a6be84f873f7f3b62a777528ed001",
                "147c9c57132f6e7ecddba9800bb0c4449251c92a1e60371ee77557b6620f3ea3",
                True,
            ),
            (
                "93478e9488f956df2396be2ce6c5cced75f900dfa18e7dabd2428aae78451820",
                "6af9e28dbf9d6aaf027696e2598a5b3d056f5fd2355a7fd5a37a0e5008132d30",
                "e4d810fd50586274face62b8a807eb9719cef49c04177cc6b76a9a4251d5450e",
                False,
            ),
        ],
    )
    def test_bip341_tweak(self, key_hex, tweak_hex, expected_hex, parity):
        original = XOnlyPublicKey(bytes.fromhex(key_hex))
        tweaked = original.add_tweak(bytes.fromhex(tweak_hex))
        assert tweaked.format() == bytes.fromhex(expected_hex)
        assert tweaked.parity is parity
        assert original.format() == bytes.fromhex(key_hex)
        with pytest.raises(TypeError, match="add_tweak"):
            original.tweak_add(bytes.fromhex(tweak_hex))


if __name__ == "__main__":
    pytest.main(["-v", __file__])
