from os import urandom

GROUP_ORDER = (b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
               b'\xfe\xba\xae\xdc\xe6\xafH\xa0;\xbf\xd2^\x8c\xd06AA')
KEY_SIZE = 32
ZERO = b'\x00'


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
