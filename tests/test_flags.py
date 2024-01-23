from coincurve.flags import (
    CONTEXT_NONE,
    CONTEXT_FLAGS,
    EC_COMPRESSED,
    EC_UNCOMPRESSED,
)


def test_context_flags():
    expected_flags = {CONTEXT_NONE,}
    assert CONTEXT_FLAGS == expected_flags


def test_context_none():
    assert CONTEXT_NONE == (1 << 0)


def test_ec_compressed():
    assert EC_COMPRESSED == (1 << 1) | (1 << 8)


def test_ec_uncompressed():
    assert EC_UNCOMPRESSED == (1 << 1)
