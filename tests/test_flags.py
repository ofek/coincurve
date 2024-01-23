from coincurve.flags import (
    CONTEXT_ALL,
    CONTEXT_FLAGS,
    CONTEXT_NONE,
    CONTEXT_SIGN,
    CONTEXT_VERIFY,
    EC_COMPRESSED,
    EC_UNCOMPRESSED,
)


def test_context_flags():
    expected_flags = {CONTEXT_SIGN, CONTEXT_VERIFY, CONTEXT_ALL, CONTEXT_NONE}
    assert CONTEXT_FLAGS == expected_flags


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
