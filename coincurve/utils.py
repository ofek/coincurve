from base64 import b64decode, b64encode
from hashlib import sha256 as _sha256
from os import urandom

GROUP_ORDER = (b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
               b'\xfe\xba\xae\xdc\xe6\xafH\xa0;\xbf\xd2^\x8c\xd06AA')
KEY_SIZE = 32
ZERO = b'\x00'
PEM_HEADER = b'-----BEGIN PRIVATE KEY-----\n'
PEM_FOOTER = b'-----END PRIVATE KEY-----\n'


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
        if ZERO < secret <= GROUP_ORDER:
            return secret


def pad_scalar(scalar):
    return (ZERO * (KEY_SIZE - len(scalar))) + scalar[-KEY_SIZE:]


def validate_secret(secret):
    if not ZERO < secret <= GROUP_ORDER:
        raise ValueError('Secret scalar must be greater than 0 and less than '
                         'or equal to the group order.')
    return pad_scalar(secret)
