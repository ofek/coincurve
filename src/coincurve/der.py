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
    - Context-specific EXPLICIT tags (for the optional public key)

The expected DER structure is as follows:

    PrivateKeyInfo ::= SEQUENCE {
        version             INTEGER,           -- must be 0
        privateKeyAlgorithm SEQUENCE {
            algorithm       OBJECT IDENTIFIER, -- id-ecPublicKey (1.2.840.10045.2.1)
            parameters      OBJECT IDENTIFIER  -- secp256k1 (1.3.132.0.10)
        },
        privateKey          OCTET STRING       -- DER encoding of ECPrivateKey
    }

    ECPrivateKey ::= SEQUENCE {
        version        INTEGER,                     -- must be 1
        privateKey     OCTET STRING,                -- the secret bytes
        publicKey  [1] EXPLICIT BIT STRING OPTIONAL -- uncompressed public key
    }
"""

from __future__ import annotations

from coincurve.utils import int_to_bytes

# ASN.1 DER tag bytes
INTEGER_TAG = 0x02
BIT_STRING_TAG = 0x03
OCTET_STRING_TAG = 0x04
OBJECT_IDENTIFIER_TAG = 0x06
SEQUENCE_TAG = 0x30

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
        ec_key_buffer.append(0xA1)  # context-specific [1] constructed
        ec_key_buffer.extend(encode_length(pubkey_len))
        ec_key_buffer.extend(public_key_bs)

    # Wrap EC private key in sequence
    ec_key_seq = bytearray([SEQUENCE_TAG])
    ec_key_seq.extend(encode_length(len(ec_key_buffer)))
    ec_key_seq.extend(ec_key_buffer)

    # Wrap in octet string for outer structure
    ec_key_os = encode_octet_string(ec_key_seq)

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
    length_byte = data[offset]
    offset += 1

    # Short form
    if length_byte < 128:  # noqa: PLR2004
        return length_byte, offset

    # Long form
    num_length_bytes = length_byte & 0x7F
    length = 0
    for _ in range(num_length_bytes):
        length = (length << 8) | data[offset]
        offset += 1
    return length, offset


def decode_der(der_data: bytes) -> bytes:
    """
    Decode a DER-encoded EC private key to extract the private key secret.
    Optimized for secp256k1 keys.

    Parameters:
        der_data: The DER-encoded private key in PKCS#8 format

    Returns:
        The private key secret as bytes
    """
    # Quick validation for performance
    if len(der_data) < 34 or der_data[0] != SEQUENCE_TAG:  # noqa: PLR2004
        msg = "Invalid DER: not a valid PKCS#8 structure"
        raise ValueError(msg)

    # Skip outer sequence tag and length
    offset = 1
    _, offset = decode_length(der_data, offset)

    # Skip version INTEGER (should be 0)
    if der_data[offset] != INTEGER_TAG:
        msg = "Invalid DER: expected INTEGER tag for version"
        raise ValueError(msg)
    offset += 1
    version_len, offset = decode_length(der_data, offset)
    offset += version_len  # Skip version value

    # Validate algorithm identifier is for EC
    if der_data[offset] != SEQUENCE_TAG:
        msg = "Invalid DER: expected SEQUENCE tag for algorithm"
        raise ValueError(msg)
    offset += 1

    alg_len, offset = decode_length(der_data, offset)
    alg_end = offset + alg_len  # Store the end position of algorithm identifier

    # Check if first OID is EC
    if der_data[offset] != OBJECT_IDENTIFIER_TAG:
        msg = "Invalid DER: expected OBJECT IDENTIFIER tag"
        raise ValueError(msg)
    offset += 1
    oid_len, offset = decode_length(der_data, offset)
    algorithm_oid = der_data[offset : offset + oid_len]

    # Check if it's an EC key
    if oid_len != len(EC_PUBKEY_OID) or algorithm_oid != EC_PUBKEY_OID:
        msg = "Not an EC private key"
        raise ValueError(msg)

    # Skip to the end of algorithm identifier section
    offset = alg_end

    # Extract private key octet string
    if der_data[offset] != OCTET_STRING_TAG:
        msg = "Invalid DER: expected OCTET STRING for private key"
        raise ValueError(msg)
    offset += 1
    priv_len, offset = decode_length(der_data, offset)

    # Parse EC private key structure
    ec_data = der_data[offset : offset + priv_len]

    # Verify EC structure starts with sequence
    if len(ec_data) < 2 or ec_data[0] != SEQUENCE_TAG:  # noqa: PLR2004
        msg = "Invalid EC key format: missing sequence"
        raise ValueError(msg)

    # Skip sequence tag and length
    ec_offset = 1
    _, ec_offset = decode_length(ec_data, ec_offset)

    # Skip version INTEGER (should be 1)
    if ec_data[ec_offset] != INTEGER_TAG:
        msg = "Invalid EC key format: missing version"
        raise ValueError(msg)
    ec_offset += 1
    ec_ver_len, ec_offset = decode_length(ec_data, ec_offset)
    ec_offset += ec_ver_len  # Skip version value

    # Get private key octet string
    if ec_data[ec_offset] != OCTET_STRING_TAG:
        msg = "Invalid DER: expected OCTET STRING for EC private key"
        raise ValueError(msg)
    ec_offset += 1

    key_len, ec_offset = decode_length(ec_data, ec_offset)

    # Extract private key
    return ec_data[ec_offset : ec_offset + key_len]
