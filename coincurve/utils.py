from base64 import b64decode, b64encode
from binascii import hexlify, unhexlify
from hashlib import sha256 as _sha256
from os import urandom

from coincurve.context import GLOBAL_CONTEXT
from ._libsecp256k1 import ffi, lib

GROUP_ORDER = (b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
               b'\xfe\xba\xae\xdc\xe6\xafH\xa0;\xbf\xd2^\x8c\xd06AA')
GROUP_ORDER_INT = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
KEY_SIZE = 32
ZERO = b'\x00'
PEM_HEADER = b'-----BEGIN PRIVATE KEY-----\n'
PEM_FOOTER = b'-----END PRIVATE KEY-----\n'


def ensure_unicode(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return s


def pad_hex(hexed):
    # Pad odd-length hex strings.
    return hexed if not len(hexed) & 1 else '0' + hexed


if hasattr(int, "from_bytes"):
    def bytes_to_int(bytestr):
        return int.from_bytes(bytestr, 'big')
else:
    def bytes_to_int(bytestr):
        return int(bytestr.encode('hex'), 16)


if hasattr(int, "to_bytes"):
    def int_to_bytes(num):
        return num.to_bytes((num.bit_length() + 7) // 8 or 1, 'big')


    def int_to_bytes_padded(num):
        return pad_scalar(
            num.to_bytes((num.bit_length() + 7) // 8 or 1, 'big')
        )
else:
    def int_to_bytes(num):
        return unhexlify(pad_hex('%x' % num))


    def int_to_bytes_padded(num):
        return pad_scalar(unhexlify(pad_hex('%x' % num)))


if hasattr(bytes, "hex"):
    def bytes_to_hex(bytestr):
        return bytestr.hex()
else:
    def bytes_to_hex(bytestr):
        return ensure_unicode(hexlify(bytestr))


if hasattr(bytes, "fromhex"):
    def hex_to_bytes(hexed):
        return pad_scalar(bytes.fromhex(pad_hex(hexed)))
else:
    def hex_to_bytes(hexed):
        return pad_scalar(unhexlify(pad_hex(hexed)))


def sha256(bytestr):
    return _sha256(bytestr).digest()


def chunk_data(data, size):
    return (data[i:i + size] for i in range(0, len(data), size))


def der_to_pem(der):
    return b''.join([
        PEM_HEADER,
        b'\n'.join(chunk_data(b64encode(der), 64)), b'\n',
        PEM_FOOTER
    ])


def pem_to_der(pem):
    return b64decode(
        pem.strip()[28:-25].replace(b'\n', b'')
    )


def get_valid_secret():
    while True:
        secret = urandom(KEY_SIZE)
        if ZERO < secret < GROUP_ORDER:
            return secret


def pad_scalar(scalar):
    return (ZERO * (KEY_SIZE - len(scalar))) + scalar


def validate_secret(secret):
    if not 0 < bytes_to_int(secret) < GROUP_ORDER_INT:
        raise ValueError('Secret scalar must be greater than 0 and less than '
                         '{}.'.format(GROUP_ORDER_INT))
    return pad_scalar(secret)


def verify_signature(signature, message, public_key, hasher=sha256, context=GLOBAL_CONTEXT):
    pubkey = ffi.new('secp256k1_pubkey *')

    pubkey_parsed = lib.secp256k1_ec_pubkey_parse(
        context.ctx, pubkey, public_key, len(public_key)
    )

    if not pubkey_parsed:
        raise ValueError('The public key could not be parsed or is invalid.')

    msg_hash = hasher(message) if hasher is not None else message
    if len(msg_hash) != 32:
        raise ValueError('Message hash must be 32 bytes long.')

    sig = ffi.new('secp256k1_ecdsa_signature *')

    sig_parsed = lib.secp256k1_ecdsa_signature_parse_der(
        context.ctx, sig, signature, len(signature)
    )

    if not sig_parsed:
        raise ValueError('The DER-encoded signature could not be parsed.')

    verified = lib.secp256k1_ecdsa_verify(
        context.ctx, sig, msg_hash, pubkey
    )

    # A performance hack to avoid global bool() lookup.
    return not not verified
