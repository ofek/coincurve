import pytest

from coincurve.ecdsa import compact_to_der, der_to_compact, normalize_signature, recoverable_to_der


def test_der_and_compact_roundtrip(samples):
    assert compact_to_der(der_to_compact(samples["SIGNATURE"])) == samples["SIGNATURE"]


def test_recoverable_to_der(samples):
    assert recoverable_to_der(samples["RECOVERABLE_SIGNATURE"]) == samples["SIGNATURE"]


def test_normalize(samples):
    changed, signature = normalize_signature(samples["SIGNATURE"])
    assert not changed
    assert signature == samples["SIGNATURE"]


@pytest.mark.parametrize("signature", [b"", b"not DER", bytes(73)])
def test_invalid_der(signature):
    with pytest.raises(ValueError, match="could not be parsed"):
        der_to_compact(signature)


def test_invalid_fixed_width_signatures():
    with pytest.raises(ValueError, match="exactly 64 bytes"):
        compact_to_der(bytes(63))
    with pytest.raises(ValueError, match="could not be parsed"):
        recoverable_to_der(bytes(64) + b"\x04")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
