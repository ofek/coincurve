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
    expected_flags = {
        CONTEXT_SIGN,
        CONTEXT_VERIFY,
        CONTEXT_ALL,
        CONTEXT_NONE,
    }
    assert CONTEXT_FLAGS == expected_flags


def test_context_none():
    # From libsecp256k1's include/secp256k1.h
    assert CONTEXT_NONE == (1 << 0)


def test_context_sign():
    # From libsecp256k1's include/secp256k1.h
    assert CONTEXT_SIGN == ((1 << 0) | (1 << 9))


def test_context_verify():
    # From libsecp256k1's include/secp256k1.h
    assert CONTEXT_VERIFY == ((1 << 0) | (1 << 8))


def test_context_all():
    # From libsecp256k1's include/secp256k1.h
    assert CONTEXT_ALL == (CONTEXT_SIGN | CONTEXT_VERIFY)


def test_ec_compressed():
    # From libsecp256k1's include/secp256k1.h
    assert EC_COMPRESSED == (1 << 1) | (1 << 8)


def test_ec_uncompressed():
    # From libsecp256k1's include/secp256k1.h
    assert EC_UNCOMPRESSED == (1 << 1)
