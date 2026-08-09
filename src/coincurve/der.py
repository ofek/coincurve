"""
Minimal, dependency-free ASN.1/DER encoder & decoder for secp256k1 EC private keys.

This module implements just enough DER encoding/decoding to support:

    1. Outputting a DER-encoded PKCS#8 EC private key (with an embedded ECPrivateKey per RFC 5915)
    2. Reading such a DER-encoded EC private key

Only the following ASN.1 types are supported:

    - INTEGER
    - BIT STRING
    - OCTET STRING
    - OBJECT IDENTIFIER
    - SEQUENCE
    - Context-specific tags for optional parameters, public keys, and attributes

The expected DER structure is as follows:

    PrivateKeyInfo ::= SEQUENCE {
        version             INTEGER,           -- must be 0
        privateKeyAlgorithm SEQUENCE {
            algorithm       OBJECT IDENTIFIER, -- id-ecPublicKey (1.2.840.10045.2.1)
            parameters      OBJECT IDENTIFIER  -- secp256k1 (1.3.132.0.10)
        },
        privateKey          OCTET STRING,      -- DER encoding of ECPrivateKey
        attributes      [0] IMPLICIT OPTIONAL
    }

    ECPrivateKey ::= SEQUENCE {
        version        INTEGER,                     -- must be 1
        privateKey     OCTET STRING,                -- the secret bytes
        parameters [0] EXPLICIT OPTIONAL,           -- secp256k1 parameters
        publicKey  [1] EXPLICIT BIT STRING OPTIONAL -- compressed or uncompressed public key
    }
"""

from __future__ import annotations

from coincurve.utils import _as_bytes, int_to_bytes

# ASN.1 DER tag bytes
INTEGER_TAG = 0x02
BIT_STRING_TAG = 0x03
OCTET_STRING_TAG = 0x04
OBJECT_IDENTIFIER_TAG = 0x06
SEQUENCE_TAG = 0x30
CONTEXT_ZERO_TAG = 0xA0
CONTEXT_ONE_TAG = 0xA1

# OIDs
EC_PUBKEY_OID = bytes([0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x02, 0x01])  # 1.2.840.10045.2.1 (ecPublicKey)
SECP256K1_OID = bytes([0x2B, 0x81, 0x04, 0x00, 0x0A])  # 1.3.132.0.10 (secp256k1)

# Pre-computed structures
VERSION_INTEGER_ZERO = bytes([INTEGER_TAG, 0x01, 0x00])  # INTEGER 0
VERSION_INTEGER_ONE = bytes([INTEGER_TAG, 0x01, 0x01])  # INTEGER 1
EC_ALGORITHM_IDENTIFIER = bytes([
    SEQUENCE_TAG,
    16,
    OBJECT_IDENTIFIER_TAG,
    len(EC_PUBKEY_OID),
    *EC_PUBKEY_OID,
    OBJECT_IDENTIFIER_TAG,
    len(SECP256K1_OID),
    *SECP256K1_OID,
])


def encode_length(length: int) -> bytes:
    """Encode a length in DER format."""
    # Short form
    if length < 128:  # noqa: PLR2004
        return bytes([length])

    # Long form
    length_bytes = int_to_bytes(length)
    return bytes([0x80 | len(length_bytes)]) + length_bytes


def encode_octet_string(value: bytes) -> bytes:
    """Encode an OCTET STRING in DER format."""
    length_bytes = encode_length(len(value))
    length_bytes_len = len(length_bytes)
    result = bytearray(1 + length_bytes_len + len(value))
    result[0] = OCTET_STRING_TAG
    result[1 : 1 + length_bytes_len] = length_bytes
    result[1 + length_bytes_len :] = value
    return bytes(result)


def encode_bit_string(value: bytes, unused_bits: int = 0) -> bytes:
    """Encode a BIT STRING in DER format."""
    length_bytes = encode_length(len(value) + 1)
    length_bytes_len = len(length_bytes)
    result = bytearray(1 + length_bytes_len + 1 + len(value))
    result[0] = BIT_STRING_TAG
    result[1 : 1 + length_bytes_len] = length_bytes
    result[1 + length_bytes_len] = unused_bits
    result[1 + length_bytes_len + 1 :] = value
    return bytes(result)


def encode_der(private_key: bytes, public_key: bytes | None = None) -> bytes:
    """
    Encode an EC private key in DER format (PKCS#8/RFC 5208).
    Optimized for secp256k1 keys.

    Parameters:
        private_key: The private key as bytes (32 bytes for secp256k1)
        public_key: The public key as bytes (65 bytes uncompressed for secp256k1, starting with 0x04)

    Returns:
        The DER-encoded private key
    """
    # EC private key contains version(1) + octet string + optional pubkey
    ec_key_buffer = bytearray(VERSION_INTEGER_ONE)

    # Add private key as octet string
    private_key_os = encode_octet_string(private_key)
    ec_key_buffer.extend(private_key_os)

    # Add public key if provided (optional)
    if public_key is not None:
        public_key_bs = encode_bit_string(public_key)
        pubkey_len = len(public_key_bs)
        ec_key_buffer.append(CONTEXT_ONE_TAG)
        ec_key_buffer.extend(encode_length(pubkey_len))
        ec_key_buffer.extend(public_key_bs)

    # Wrap EC private key in sequence
    ec_key_seq = bytearray([SEQUENCE_TAG])
    ec_key_seq.extend(encode_length(len(ec_key_buffer)))
    ec_key_seq.extend(ec_key_buffer)

    # Wrap in octet string for outer structure
    ec_key_os = encode_octet_string(bytes(ec_key_seq))

    # Build the outer PKCS#8 structure
    result = bytearray([SEQUENCE_TAG])

    # Calculate total length: version(3) + alg_id(18) + octet_string(len)
    outer_len = 3 + len(EC_ALGORITHM_IDENTIFIER) + len(ec_key_os)
    result.extend(encode_length(outer_len))

    # Version 0
    result.extend(VERSION_INTEGER_ZERO)

    # Algorithm identifier (pre-computed)
    result.extend(EC_ALGORITHM_IDENTIFIER)

    # EC key wrapped in octet string
    result.extend(ec_key_os)

    return bytes(result)


def decode_length(data: bytes, offset: int) -> tuple[int, int]:
    """
    Decode a DER length field.

    Parameters:
        data: The DER-encoded data
        offset: The current offset in the data

    Returns:
        Tuple of (length, new_offset)
    """
    if offset >= len(data):
        msg = "Invalid DER: truncated length"
        raise ValueError(msg)

    length_byte = data[offset]
    offset += 1

    # Decode the short form.
    if length_byte < 128:  # noqa: PLR2004
        return length_byte, offset

    # Decode the canonical long form.
    num_length_bytes = length_byte & 0x7F
    if num_length_bytes == 0 or offset + num_length_bytes > len(data):
        msg = "Invalid DER: invalid or truncated long-form length"
        raise ValueError(msg)
    length_data = data[offset : offset + num_length_bytes]
    if length_data[0] == 0:
        msg = "Invalid DER: non-canonical long-form length"
        raise ValueError(msg)
    length = int.from_bytes(length_data, "big")
    if length < 128:  # noqa: PLR2004
        msg = "Invalid DER: long-form length was used unnecessarily"
        raise ValueError(msg)
    offset += num_length_bytes
    return length, offset


def decode_value(data: bytes, offset: int, tag: int, name: str) -> tuple[bytes, int]:
    """Decode one complete DER value with the expected tag."""
    if offset >= len(data) or data[offset] != tag:
        msg = f"Invalid DER: expected {name}"
        raise ValueError(msg)
    length, value_offset = decode_length(data, offset + 1)
    end = value_offset + length
    if end < value_offset or end > len(data):
        msg = f"Invalid DER: truncated {name}"
        raise ValueError(msg)
    return data[value_offset:end], end


def decode_der(der_data: bytes) -> bytes:
    """
    Decode a DER-encoded EC private key to extract the private key secret.
    Optimized for secp256k1 keys.

    Parameters:
        der_data: The DER-encoded private key in PKCS#8 format

    Returns:
        The private key secret as bytes
    """
    data = _as_bytes(der_data, "DER data")

    outer, end = decode_value(data, 0, SEQUENCE_TAG, "PKCS#8 SEQUENCE")
    if end != len(data):
        msg = "Invalid DER: trailing data after PKCS#8 SEQUENCE"
        raise ValueError(msg)

    version, offset = decode_value(outer, 0, INTEGER_TAG, "PKCS#8 version")
    if version != b"\x00":
        msg = "Invalid DER: PKCS#8 version must be zero"
        raise ValueError(msg)

    algorithm, offset = decode_value(outer, offset, SEQUENCE_TAG, "algorithm identifier")
    algorithm_oid, algorithm_offset = decode_value(algorithm, 0, OBJECT_IDENTIFIER_TAG, "EC algorithm OID")
    curve_oid, algorithm_offset = decode_value(
        algorithm, algorithm_offset, OBJECT_IDENTIFIER_TAG, "secp256k1 curve OID"
    )
    if algorithm_offset != len(algorithm) or algorithm_oid != EC_PUBKEY_OID or curve_oid != SECP256K1_OID:
        msg = "Invalid DER: key algorithm must be secp256k1"
        raise ValueError(msg)

    private_key_data, offset = decode_value(outer, offset, OCTET_STRING_TAG, "private key")
    if offset < len(outer) and outer[offset] == CONTEXT_ZERO_TAG:
        _, offset = decode_value(outer, offset, CONTEXT_ZERO_TAG, "attributes")
    if offset != len(outer):
        msg = "Invalid DER: trailing PKCS#8 fields"
        raise ValueError(msg)

    ec_key, ec_end = decode_value(private_key_data, 0, SEQUENCE_TAG, "ECPrivateKey SEQUENCE")
    if ec_end != len(private_key_data):
        msg = "Invalid DER: trailing data after ECPrivateKey SEQUENCE"
        raise ValueError(msg)
    ec_version, ec_offset = decode_value(ec_key, 0, INTEGER_TAG, "ECPrivateKey version")
    if ec_version != b"\x01":
        msg = "Invalid DER: ECPrivateKey version must be one"
        raise ValueError(msg)
    secret, ec_offset = decode_value(ec_key, ec_offset, OCTET_STRING_TAG, "EC private key")
    if not 1 <= len(secret) <= 32:  # noqa: PLR2004
        msg = "Invalid DER: EC private key must contain between 1 and 32 bytes"
        raise ValueError(msg)
    secret = secret.rjust(32, b"\x00")

    if ec_offset < len(ec_key) and ec_key[ec_offset] == CONTEXT_ZERO_TAG:
        parameters_field, ec_offset = decode_value(ec_key, ec_offset, CONTEXT_ZERO_TAG, "parameters field")
        parameters, parameters_end = decode_value(
            parameters_field, 0, OBJECT_IDENTIFIER_TAG, "secp256k1 parameters OID"
        )
        if parameters_end != len(parameters_field) or parameters != SECP256K1_OID:
            msg = "Invalid DER: ECPrivateKey parameters must be secp256k1"
            raise ValueError(msg)
    if ec_offset < len(ec_key) and ec_key[ec_offset] == CONTEXT_ONE_TAG:
        public_key_field, ec_offset = decode_value(ec_key, ec_offset, CONTEXT_ONE_TAG, "public key field")
        public_key, public_key_end = decode_value(public_key_field, 0, BIT_STRING_TAG, "public key BIT STRING")
        uncompressed = len(public_key) == 66 and public_key[:2] == b"\x00\x04"  # noqa: PLR2004
        compressed = len(public_key) == 34 and public_key[0] == 0 and public_key[1] in {2, 3}  # noqa: PLR2004
        if public_key_end != len(public_key_field) or not (uncompressed or compressed):
            msg = "Invalid DER: malformed public key"
            raise ValueError(msg)
    if ec_offset != len(ec_key):
        msg = "Invalid DER: trailing ECPrivateKey fields"
        raise ValueError(msg)
    return secret
