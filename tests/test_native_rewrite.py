from __future__ import annotations

import builtins
import gc
import inspect
import json
import sys
import sysconfig
from ctypes import Structure, c_ubyte
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

import coincurve
from coincurve import PrivateKey, PublicKey, XOnlyPublicKey, batch, verify_signature, verify_signature_digest
from coincurve.batch import packed
from coincurve.der import (
    CONTEXT_ONE_TAG,
    CONTEXT_ZERO_TAG,
    EC_ALGORITHM_IDENTIFIER,
    OBJECT_IDENTIFIER_TAG,
    SECP256K1_OID,
    SEQUENCE_TAG,
    VERSION_INTEGER_ONE,
    VERSION_INTEGER_ZERO,
    encode_bit_string,
    encode_length,
    encode_octet_string,
)
from coincurve.ecdsa import compact_to_der, der_to_compact, normalize_signature, recoverable_to_der

if TYPE_CHECKING:
    from collections.abc import Callable

SECRET_ONE = bytes.fromhex("00" * 31 + "01")
SECRET_TWO = bytes.fromhex("00" * 31 + "02")
DIGEST_A = sha256(b"a").digest()
DIGEST_B = sha256(b"b").digest()


def der_value(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + encode_length(len(value)) + value


def pkcs8_variant(secret: bytes, public_key: bytes, *, attributes: bytes = b"") -> bytes:
    parameters = der_value(CONTEXT_ZERO_TAG, der_value(OBJECT_IDENTIFIER_TAG, SECP256K1_OID))
    embedded_public_key = der_value(CONTEXT_ONE_TAG, encode_bit_string(public_key))
    ec_private_key = der_value(
        SEQUENCE_TAG, VERSION_INTEGER_ONE + encode_octet_string(secret) + parameters + embedded_public_key
    )
    outer = VERSION_INTEGER_ZERO + EC_ALGORITHM_IDENTIFIER + encode_octet_string(ec_private_key)
    if attributes:
        outer += der_value(CONTEXT_ZERO_TAG, attributes)
    return der_value(SEQUENCE_TAG, outer)


def test_calver_and_native_types() -> None:
    assert coincurve.__version__ == "2026.8.0"
    key = PrivateKey(SECRET_ONE)
    assert "01" not in repr(key)
    assert key.secret == SECRET_ONE
    assert PrivateKey.from_int(1) == key
    assert PrivateKey.from_hex("1") == key
    assert hash(PrivateKey(SECRET_ONE)) == hash(key)
    assert hash(key) == hash(bytes(key.public_key))
    assert hash(key.public_key) == hash(bytes(key.public_key))
    assert hash(key.xonly_public_key) == hash(bytes(key.xonly_public_key))
    assert key.public_key is key.public_key
    assert key.xonly_public_key is key.xonly_public_key
    with pytest.raises(TypeError):
        type("DerivedPrivateKey", (PrivateKey,), {})
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        PrivateKey(b"\x01")
    assert "secret=None" in str(inspect.signature(PrivateKey))
    assert (
        str(inspect.signature(packed.sign_ecdsa_digests))
        == "(secrets: 'ReadableBuffer', digests: 'ReadableBuffer') -> 'tuple[bytes, bytes]'"
    )


def native_callables() -> list[tuple[str, Callable[..., object]]]:
    callables: list[tuple[str, Callable[..., object]]] = [
        ("verify_signature", verify_signature),
        ("verify_signature_digest", verify_signature_digest),
        ("compact_to_der", compact_to_der),
        ("der_to_compact", der_to_compact),
        ("normalize_signature", normalize_signature),
        ("recoverable_to_der", recoverable_to_der),
    ]
    for key_type in (PrivateKey, PublicKey, XOnlyPublicKey):
        callables.append((key_type.__name__, key_type))
        for name, member in inspect.getmembers(key_type, callable):
            if not name.startswith("_"):
                callables.append((f"{key_type.__name__}.{name}", member))
    return callables


def test_native_callables_expose_signatures() -> None:
    callables = native_callables()
    assert len(callables) >= 58
    for name, native_callable in callables:
        assert inspect.signature(native_callable), name


def test_hasher_defaults_do_not_advertise_none() -> None:
    hasher_defaults = {
        name: signature.parameters["hasher"].default
        for name, native_callable in native_callables()
        if "hasher" in (signature := inspect.signature(native_callable)).parameters
    }
    assert len(hasher_defaults) >= 12
    for name, default in hasher_defaults.items():
        assert default is Ellipsis, name
    with pytest.raises(TypeError, match="hasher must be callable"):
        PrivateKey(SECRET_ONE).sign(b"message", cast("Callable[[bytes], bytes]", None))


def test_integer_conversion_uses_the_builtin_type(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnexpectedInt:
        @classmethod
        def from_bytes(cls, *_args: object, **_kwargs: object) -> None:
            raise AssertionError

    key = PrivateKey(SECRET_ONE)
    with monkeypatch.context() as context:
        context.setattr(builtins, "int", UnexpectedInt)
        assert key.to_int() == 1
        assert key.public_key.point()[0] > 0


def test_combine_preserves_iterator_errors() -> None:
    key = PrivateKey(SECRET_ONE).public_key

    def broken_keys():
        yield key
        msg = "iteration failed"
        raise TypeError(msg)

    with pytest.raises(TypeError, match="iteration failed"):
        PublicKey.combine_keys(broken_keys())


def test_combine_includes_the_receiver() -> None:
    first = PrivateKey(SECRET_ONE)
    second = PrivateKey(SECRET_TWO)
    expected = PrivateKey.from_int(3).public_key
    assert first.public_key.combine([second.public_key]) == expected
    assert PublicKey.combine_keys([first.public_key, second.public_key]) == expected


def test_private_key_deallocation_releases_the_heap_type() -> None:
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        pytest.skip("Exact reference counts are unavailable on free-threaded CPython.")

    key_types = (PrivateKey, PublicKey, XOnlyPublicKey)
    reference_counts = tuple(sys.getrefcount(key_type) for key_type in key_types)

    def create_keys() -> None:
        for _ in range(100):
            PrivateKey(SECRET_ONE)

    create_keys()
    gc.collect()
    assert tuple(sys.getrefcount(key_type) for key_type in key_types) == reference_counts


def test_ecdsa_scalar_digest_and_recovery() -> None:
    key = PrivateKey(SECRET_ONE)
    signature = key.sign(b"message")
    digest = sha256(b"message").digest()
    assert signature == key.sign_digest(digest)
    assert key.public_key.verify(signature, b"message")
    assert key.public_key.verify_digest(signature, digest)
    assert verify_signature(signature, b"message", bytes(key.public_key))
    assert verify_signature_digest(signature, digest, bytes(key.public_key))
    assert not key.public_key.verify(b"malformed", b"message")
    assert not verify_signature(b"malformed", b"message", bytes(key.public_key))
    recoverable = key.sign_recoverable_digest(digest)
    assert PublicKey.recover_digest(recoverable, digest) == key.public_key
    assert PublicKey.recover(recoverable, b"message") == key.public_key
    assert recoverable_to_der(recoverable) == signature


def test_extra_entropy_and_signature_conversion() -> None:
    key = PrivateKey(SECRET_ONE)
    entropy = bytes(range(32))
    default = key.sign_digest(DIGEST_A)
    changed = key.sign_digest(DIGEST_A, extra_entropy=entropy)
    assert changed == key.sign_digest(DIGEST_A, extra_entropy=entropy)
    assert changed != default
    compact = der_to_compact(changed)
    assert len(compact) == 64
    assert compact_to_der(compact) == changed
    was_normalized, normalized = normalize_signature(changed)
    assert not was_normalized
    assert normalized == changed


def test_upstream_deterministic_ecdsa_vectors() -> None:
    vectors = json.loads((Path(__file__).parent / "data" / "ecdsa_sig.json").read_text(encoding="utf-8"))["vectors"]
    private_keys = [PrivateKey(bytes.fromhex(vector["privkey"])) for vector in vectors]
    digests = [bytes.fromhex(vector["msg"]) for vector in vectors]
    expected_signatures = [bytes.fromhex(vector["sig"][:-2]) for vector in vectors]
    public_keys = [private_key.public_key for private_key in private_keys]

    assert [
        private_key.sign_digest(digest) for private_key, digest in zip(private_keys, digests, strict=True)
    ] == expected_signatures
    assert batch.sign_digests(private_keys, digests) == expected_signatures
    assert batch.verify_digests(public_keys, expected_signatures, digests) == [True] * len(vectors)

    packed_signatures, statuses = packed.sign_ecdsa_digests(
        b"".join(private_key.secret for private_key in private_keys), b"".join(digests)
    )
    assert statuses == b"\x01" * len(vectors)
    assert packed_signatures == b"".join(der_to_compact(signature) for signature in expected_signatures)
    assert (
        packed.verify_ecdsa_digests(
            b"".join(bytes(public_key) for public_key in public_keys), packed_signatures, b"".join(digests)
        )
        == statuses
    )


def test_schnorr_and_xonly_keys() -> None:
    key = PrivateKey(SECRET_ONE)
    signature = key.sign_schnorr_digest(DIGEST_A, aux_randomness=bytes(32))
    assert signature == key.sign_schnorr_digest(DIGEST_A, aux_randomness=bytes(32))
    assert key.xonly_public_key.verify_digest(signature, DIGEST_A)
    assert key.sign_schnorr(DIGEST_A, bytes(32)) == signature
    assert key.xonly_public_key.verify(signature, DIGEST_A)
    message_signature = key.sign_schnorr_message(b"a", aux_randomness=bytes(32))
    assert message_signature == signature
    assert key.xonly_public_key.verify_message(message_signature, b"a")
    parsed = XOnlyPublicKey(bytes(key.xonly_public_key))
    assert parsed == key.xonly_public_key
    assert parsed.parity is None
    assert XOnlyPublicKey(bytes(key.xonly_public_key), parity=False).parity is False
    assert key.xonly_public_key.parity is False
    tweaked = parsed.add_tweak(SECRET_TWO)
    assert tweaked != parsed
    assert tweaked.parity is not None
    with pytest.raises(TypeError, match="add_tweak"):
        parsed.tweak_add(SECRET_TWO)


@pytest.mark.parametrize("empty_aux_randomness", [bytearray(), memoryview(b"")])
def test_empty_readable_buffers_request_schnorr_randomness(
    empty_aux_randomness: bytearray | memoryview,
) -> None:
    key = PrivateKey(SECRET_ONE)
    raw_signature = key.sign_schnorr(DIGEST_A, empty_aux_randomness)
    digest_signature = key.sign_schnorr_digest(DIGEST_A, aux_randomness=empty_aux_randomness)
    message_signature = key.sign_schnorr_message(b"a", aux_randomness=empty_aux_randomness)
    assert key.xonly_public_key.verify(raw_signature, DIGEST_A)
    assert key.xonly_public_key.verify_digest(digest_signature, DIGEST_A)
    assert key.xonly_public_key.verify_message(message_signature, b"a")
    no_randomness_signature = key.sign_schnorr_digest(DIGEST_A, aux_randomness=None)
    assert key.sign_schnorr(DIGEST_A, None) == no_randomness_signature
    assert key.sign_schnorr_message(b"a", aux_randomness=None) == no_randomness_signature


def test_bip340_official_vectors() -> None:
    secret = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000003")
    public_key = bytes.fromhex("F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9")
    digest = bytes(32)
    signature = bytes.fromhex(
        "E907831F80848D1069A5371B402410364BDF1C5F8307B0084C55F1CE2DCA8215"
        "25F66A4A85EA8B71E482A74F382D2CE5EBEEE8FDB2172F477DF4900D310536C0"
    )
    assert bytes(PrivateKey(secret).xonly_public_key) == public_key
    assert PrivateKey(secret).sign_schnorr_digest(digest, aux_randomness=bytes(32)) == signature
    assert PrivateKey(secret).sign_schnorr(digest, None) == signature
    assert XOnlyPublicKey(public_key).verify_digest(signature, digest)
    assert XOnlyPublicKey(public_key).verify(signature, digest)
    assert batch.verify_schnorr_digests([XOnlyPublicKey(public_key)], [signature], [digest]) == [True]
    assert packed.verify_schnorr_digests(public_key, signature, digest) == b"\x01"
    invalid_signature = bytes.fromhex(
        "FFF97BD5755EEEA420453A14355235D382F6472F8568A18B2F057A1460297556"
        "3CC27944640AC607CD107AE10923D9EF7A73C643E166BE5EBEAFA34B1AC553E2"
    )
    invalid_public_key = XOnlyPublicKey(
        bytes.fromhex("DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659")
    )
    invalid_digest = bytes.fromhex("243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89")
    assert not invalid_public_key.verify_digest(invalid_signature, invalid_digest)
    assert invalid_public_key.verify_digests([invalid_signature], [invalid_digest]) == [False]


def test_bip341_official_taproot_tweak_vector() -> None:
    internal_public_key = bytes.fromhex("d6889cb081036e0faefa3a35157ad71086b123b2b144b649798b494c300a961d")
    tweak = bytes.fromhex("b86e7be8f39bab32a6f2c0443abbc210f0edac0e2c53d501b36b64437d9c6c70")
    expected_public_key = bytes.fromhex("53a1f6e454df1aa2776a2814a721372d6258050de330b3c6d10ee8f4e0dda343")

    tweaked = XOnlyPublicKey(internal_public_key).add_tweak(tweak)
    assert bytes(tweaked) == expected_public_key
    assert tweaked.parity is True


def test_immutable_tweaks_and_ecdh() -> None:
    first = PrivateKey(SECRET_ONE)
    second = PrivateKey(SECRET_TWO)
    added = first.add(SECRET_ONE)
    multiplied = first.multiply(SECRET_TWO)
    assert first.secret == SECRET_ONE
    assert added == second
    assert multiplied == second
    expected_shared_secret = bytes.fromhex("b1c9938f01121e159887ac2c8d393a22e4476ff8212de13fe1939de2a236f0a7")
    assert first.ecdh(second.public_key) == second.ecdh(first.public_key) == expected_shared_secret
    assert first.ecdh_many([second.public_key]) == [expected_shared_secret]
    assert batch.ecdh([first], [second.public_key]) == [expected_shared_secret]
    packed_shared_secret, packed_status = packed.ecdh(first.secret, bytes(second.public_key))
    assert packed_shared_secret == expected_shared_secret
    assert packed_status == b"\x01"
    assert first.public_key.add(SECRET_ONE) == second.public_key
    assert first.public_key.multiply(SECRET_TWO) == second.public_key


@pytest.mark.parametrize(
    ("short_scalar", "empty_scalar"),
    [
        (b"\x01", b""),
        (bytearray(b"\x01"), bytearray()),
        (memoryview(b"\x01"), memoryview(b"")),
    ],
)
def test_retained_scalar_apis_left_pad_short_buffers(
    short_scalar: bytes | bytearray | memoryview,
    empty_scalar: bytes | bytearray | memoryview,
) -> None:
    first = PrivateKey(SECRET_ONE)
    second = PrivateKey(SECRET_TWO)
    assert first.add(short_scalar) == second
    assert first.multiply(short_scalar) == first
    assert first.add(empty_scalar) == first
    assert PublicKey.from_secret(short_scalar) == first.public_key
    assert first.public_key.add(short_scalar) == second.public_key
    assert first.public_key.multiply(short_scalar) == first.public_key
    assert first.public_key.add(empty_scalar) == first.public_key
    assert XOnlyPublicKey.from_secret(short_scalar) == first.xonly_public_key
    assert first.xonly_public_key.add_tweak(short_scalar) == second.xonly_public_key
    assert first.xonly_public_key.add_tweak(empty_scalar) == first.xonly_public_key
    with pytest.raises(ValueError, match="scalar or resulting private key"):
        first.multiply(empty_scalar)
    with pytest.raises(ValueError, match="scalar or resulting public key"):
        first.public_key.multiply(empty_scalar)
    with pytest.raises(ValueError, match="valid secp256k1 private key"):
        PublicKey.from_secret(empty_scalar)
    with pytest.raises(ValueError, match="valid secp256k1 private key"):
        XOnlyPublicKey.from_secret(empty_scalar)


def test_der_and_pem_round_trip() -> None:
    key = PrivateKey(SECRET_TWO)
    der = key.to_der()
    pem = key.to_pem()
    assert PrivateKey.from_der(der) == key
    assert PrivateKey.from_pem(pem) == key
    assert PrivateKey.from_der(memoryview(der)) == key
    assert PrivateKey.from_pem(bytearray(pem)) == key
    with pytest.raises(ValueError, match="truncated"):
        PrivateKey.from_der(der[:-1])
    with pytest.raises(ValueError, match="trailing"):
        PrivateKey.from_der(der + b"\x00")
    with pytest.raises(ValueError, match="Invalid PEM"):
        PrivateKey.from_pem(pem.replace(b"BEGIN PRIVATE KEY", b"BEGIN WRONG KEY"))


def test_der_compatibility_variants() -> None:
    key = PrivateKey(SECRET_TWO)
    compressed_variant = pkcs8_variant(b"\x02", bytes(key.public_key), attributes=b"\x31\x00")
    uncompressed_variant = pkcs8_variant(SECRET_TWO, key.public_key.format(compressed=False))
    assert PrivateKey.from_der(compressed_variant) == key
    assert PrivateKey.from_der(uncompressed_variant) == key


def test_batch_hasher_preserves_exception_subclasses() -> None:
    def invalid_utf8(_message: bytes) -> bytes:
        encoding = "utf-8"
        reason = "invalid start byte"
        raise UnicodeDecodeError(encoding, b"\xff", 0, 1, reason)

    with pytest.raises(UnicodeDecodeError) as captured:
        PrivateKey(SECRET_ONE).sign_many([b"message"], invalid_utf8)
    if hasattr(captured.value, "__notes__"):
        assert captured.value.__notes__ == ["The hasher failed for messages[0]."]


def test_instance_batches() -> None:
    key = PrivateKey(SECRET_ONE)
    digests = [DIGEST_A, DIGEST_B]
    signatures = key.sign_digests(digests)
    assert signatures == [key.sign_digest(digest) for digest in digests]
    assert key.public_key.verify_digests(signatures, digests) == [True, True]
    assert key.public_key.verify_many(key.sign_many([b"a", b"b"]), [b"a", b"b"]) == [True, True]
    recoverable = key.sign_recoverable_digests(digests)
    assert [
        PublicKey.recover_digest(signature, digest) for signature, digest in zip(recoverable, digests, strict=True)
    ] == [
        key.public_key,
        key.public_key,
    ]
    schnorr = key.sign_schnorr_digests(digests, aux_randomness=bytes(32))
    assert key.xonly_public_key.verify_digests(schnorr, digests) == [True, True]
    assert key.ecdh_many([key.public_key, PrivateKey(SECRET_TWO).public_key]) == [
        key.ecdh(key.public_key),
        key.ecdh(PrivateKey(SECRET_TWO).public_key),
    ]
    assert key.sign_digests([]) == []


def test_pairwise_batches_and_indexed_errors() -> None:
    keys = [PrivateKey(SECRET_ONE), PrivateKey(SECRET_TWO)]
    digests = [DIGEST_A, DIGEST_B]
    messages = [b"a", b"b"]
    signatures = batch.sign_digests(keys, digests)
    assert batch.verify_digests([key.public_key for key in keys], signatures, digests) == [True, True]
    message_signatures = batch.sign(keys, messages)
    assert batch.verify([key.public_key for key in keys], message_signatures, messages) == [True, True]
    recoverable = batch.sign_recoverable_digests(keys, digests)
    assert batch.recover_digests(recoverable, digests) == [key.public_key for key in keys]
    recoverable_messages = batch.sign_recoverable(keys, messages)
    assert batch.recover(recoverable_messages, messages) == [key.public_key for key in keys]
    schnorr = batch.sign_schnorr_digests(keys, digests)
    assert batch.verify_schnorr_digests([key.xonly_public_key for key in keys], schnorr, digests) == [True, True]
    schnorr_messages = batch.sign_schnorr(keys, messages)
    assert batch.verify_schnorr([key.xonly_public_key for key in keys], schnorr_messages, messages) == [True, True]
    assert (
        batch.ecdh(keys, [keys[1].public_key, keys[0].public_key])[0]
        == batch.ecdh(keys, [keys[1].public_key, keys[0].public_key])[1]
    )
    assert batch.derive_public_keys([SECRET_ONE, SECRET_TWO]) == [key.public_key for key in keys]
    assert batch.derive_xonly_public_keys([SECRET_ONE, SECRET_TWO]) == [key.xonly_public_key for key in keys]
    assert batch.sign_digests([], []) == []
    assert batch.recover_digests([bytes(65)], [DIGEST_A]) == [None]
    assert batch.verify_digests([keys[0].public_key], [b"malformed"], [DIGEST_A]) == [False]
    with pytest.raises(ValueError, match="equal lengths"):
        batch.sign_digests(keys, [DIGEST_A])
    with pytest.raises(TypeError, match=r"private_keys\[1\]"):
        batch.sign_digests([keys[0], cast(PrivateKey, object())], digests)
    with pytest.raises(ValueError, match=r"digests\[1\]"):
        keys[0].sign_digests([DIGEST_A, b"short"])


def test_batch_secret_validation_after_prior_copy() -> None:
    for derive in (batch.derive_public_keys, batch.derive_xonly_public_keys):
        with pytest.raises(ValueError, match=r"secrets\[1\]"):
            derive([SECRET_ONE, b"short"])


def test_packed_batches() -> None:
    assert packed.derive_public_keys(b"") == (b"", b"")
    secrets = SECRET_ONE + bytes(32) + SECRET_TWO
    digests = DIGEST_A * 3
    public_keys, derive_status = packed.derive_public_keys(secrets)
    assert derive_status == b"\x01\x00\x01"
    assert public_keys[33:66] == bytes(33)
    signatures, sign_status = packed.sign_ecdsa_digests(secrets, digests)
    assert sign_status == b"\x01\x00\x01"
    assert signatures[64:128] == bytes(64)
    verify_status = packed.verify_ecdsa_digests(public_keys, signatures, digests)
    assert verify_status == b"\x01\x00\x01"
    recovered, recover_status = packed.recover_public_keys(
        packed.sign_recoverable_digests(SECRET_ONE + SECRET_TWO, DIGEST_A + DIGEST_B)[0], DIGEST_A + DIGEST_B
    )
    assert recover_status == b"\x01\x01"
    assert recovered == bytes(PrivateKey(SECRET_ONE).public_key) + bytes(PrivateKey(SECRET_TWO).public_key)
    schnorr_keys, xonly_status = packed.derive_xonly_public_keys(SECRET_ONE + SECRET_TWO)
    schnorr_signatures, schnorr_status = packed.sign_schnorr_digests(SECRET_ONE + SECRET_TWO, DIGEST_A + DIGEST_B)
    assert xonly_status == schnorr_status == b"\x01\x01"
    assert packed.verify_schnorr_digests(schnorr_keys, schnorr_signatures, DIGEST_A + DIGEST_B) == b"\x01\x01"
    shared, shared_status = packed.ecdh(
        SECRET_ONE + SECRET_TWO, bytes(PrivateKey(SECRET_TWO).public_key) + bytes(PrivateKey(SECRET_ONE).public_key)
    )
    assert shared_status == b"\x01\x01"
    assert shared[:32] == shared[32:]
    with pytest.raises(ValueError, match="multiple of 32"):
        packed.derive_public_keys(b"short")
    with pytest.raises(ValueError, match="equal lengths"):
        packed.sign_ecdsa_digests(SECRET_ONE, DIGEST_A + DIGEST_B)


def test_non_contiguous_buffer_error_is_preserved() -> None:
    non_contiguous = memoryview(bytearray(64))[::2]
    with pytest.raises(BufferError):
        PrivateKey(non_contiguous)


def test_zero_dimensional_buffers_are_rejected() -> None:
    class SecretStructure(Structure):
        _fields_ = [("data", c_ubyte * 32)]  # noqa: RUF012

    zero_dimensional = memoryview(SecretStructure())
    with pytest.raises(TypeError, match="one-dimensional"):
        PrivateKey(zero_dimensional)


def test_integer_subclass_cannot_return_an_invalid_point_buffer() -> None:
    class InvalidInteger(int):
        def to_bytes(self, *_args: object, **_kwargs: object) -> None:  # type: ignore[override]
            return None

    with pytest.raises(TypeError, match="to_bytes"):
        PublicKey.from_point(InvalidInteger(1), 2)
