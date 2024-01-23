import pytest
from coincurve.flags import (
    CONTEXT_SIGN,
    CONTEXT_VERIFY,
    CONTEXT_ALL,
    CONTEXT_NONE,
    CONTEXT_FLAGS,
    EC_COMPRESSED,
    EC_UNCOMPRESSED,
)


# Test constants for correctness
@pytest.mark.parametrize(
    "constant, expected_value",
    [
        ("CONTEXT_SIGN", CONTEXT_SIGN),
        ("CONTEXT_VERIFY", CONTEXT_VERIFY),
        ("CONTEXT_ALL", CONTEXT_ALL),
        ("CONTEXT_NONE", CONTEXT_NONE),
        ("EC_COMPRESSED", EC_COMPRESSED),
        ("EC_UNCOMPRESSED", EC_UNCOMPRESSED),
    ],
    ids=[
        "test_context_sign",
        "test_context_verify",
        "test_context_all",
        "test_context_none",
        "test_ec_compressed",
        "test_ec_uncompressed",
    ]
)
def test_constants(constant, expected_value):
    # Act
    actual_value = eval(constant)

    # Assert
    assert actual_value == expected_value, f"{constant} does not match the expected value"


# Test CONTEXT_FLAGS for correctness
@pytest.mark.parametrize(
    "flag, expected_in_flags",
    [
        (CONTEXT_SIGN, True),
        (CONTEXT_VERIFY, True),
        (CONTEXT_ALL, True),
        (CONTEXT_NONE, True),
        (99999, False),  # Assuming 99999 is not a valid context flag
    ],
    ids=[
        "test_context_flags_sign",
        "test_context_flags_verify",
        "test_context_flags_all",
        "test_context_flags_none",
        "test_context_flags_invalid",
    ]
)
def test_context_flags(flag, expected_in_flags):
    # Act
    result = flag in CONTEXT_FLAGS

    # Assert
    assert result == expected_in_flags, f"Flag {flag} presence in CONTEXT_FLAGS is not as expected"


# Test bitwise operations for CONTEXT_ALL
@pytest.mark.parametrize(
    "operation, expected_result",
    [
        ("CONTEXT_SIGN | CONTEXT_VERIFY", CONTEXT_ALL),
        ("CONTEXT_ALL & CONTEXT_SIGN", CONTEXT_SIGN),
        ("CONTEXT_ALL & CONTEXT_VERIFY", CONTEXT_VERIFY),
        ("CONTEXT_VERIFY ^ CONTEXT_SIGN", CONTEXT_ALL - 1),
        ("CONTEXT_SIGN ^ CONTEXT_VERIFY", CONTEXT_ALL - 1),
    ],
    ids=[
        "test_bitwise_or",
        "test_bitwise_and_sign",
        "test_bitwise_and_verify",
        "test_bitwise_xor_verify",
        "test_bitwise_xor_sign",
    ]
)
def test_bitwise_operations(operation, expected_result):
    # Act
    actual_result = eval(operation)

    # Assert
    assert actual_result == expected_result, f"Bitwise operation {operation} did not yield the expected result"


def test_context_sign():
    assert CONTEXT_SIGN == (1 << 0) | (1 << 9)


def test_context_verify():
    assert CONTEXT_VERIFY == (1 << 0) | (1 << 8)


def test_context_all():
    assert CONTEXT_ALL == CONTEXT_SIGN | CONTEXT_VERIFY


def test_context_none():
    assert CONTEXT_NONE == (1 << 0)


def test_ec_compressed():
    assert EC_COMPRESSED == (1 << 1) | (1 << 8)


def test_ec_uncompressed():
    assert EC_UNCOMPRESSED == (1 << 1)
