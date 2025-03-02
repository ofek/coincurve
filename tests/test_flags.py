from coincurve.flags import (
    CONTEXT_FLAGS,
    CONTEXT_NONE,
    EC_COMPRESSED,
    EC_UNCOMPRESSED,
)


def test_context_flags():
    expected_flags = {
        CONTEXT_NONE,
    }
    assert expected_flags == CONTEXT_FLAGS


def test_context_none():
    # From libsecp256k1's include/secp256k1.h
    assert CONTEXT_NONE == (1 << 0)


def test_ec_compressed():
    # From libsecp256k1's include/secp256k1.h
    assert EC_COMPRESSED == (1 << 1) | (1 << 8)


def test_ec_uncompressed():
    # From libsecp256k1's include/secp256k1.h
    assert EC_UNCOMPRESSED == (1 << 1)
