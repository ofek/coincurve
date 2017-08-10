from asn1crypto.keys import (
    ECDomainParameters, ECPointBitString, ECPrivateKey, PrivateKeyAlgorithm,
    PrivateKeyInfo
)

from coincurve.context import GLOBAL_CONTEXT
from coincurve.ecdsa import (
    cdata_to_der, der_to_cdata, deserialize_recoverable, recover,
    serialize_recoverable
)
from coincurve.flags import EC_COMPRESSED, EC_UNCOMPRESSED
from coincurve.utils import (
    bytes_to_hex, bytes_to_int, der_to_pem, ensure_unicode, get_valid_secret,
    hex_to_bytes, int_to_bytes_padded, pad_scalar, pem_to_der, sha256,
    validate_secret
)
from ._libsecp256k1 import ffi, lib

DEFAULT_NONCE = (ffi.NULL, ffi.NULL)


class PrivateKey:
    def __init__(self, secret=None, context=GLOBAL_CONTEXT):
        self.secret = (validate_secret(secret) if secret is not None
                       else get_valid_secret())
        self.context = context
        self.public_key = PublicKey.from_valid_secret(
            self.secret, self.context
        )

    def sign(self, message, hasher=sha256, custom_nonce=None):
        msg_hash = hasher(message) if hasher is not None else message
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        signature = ffi.new('secp256k1_ecdsa_signature *')
        nonce_fn, nonce_data = custom_nonce or DEFAULT_NONCE

        signed = lib.secp256k1_ecdsa_sign(
            self.context.ctx, signature, msg_hash, self.secret, nonce_fn,
            nonce_data
        )

        if not signed:
            raise ValueError('The nonce generation function failed, or the '
                             'private key was invalid.')

        return cdata_to_der(signature, self.context)

    def sign_recoverable(self, message, hasher=sha256):
        msg_hash = hasher(message) if hasher is not None else message
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        signature = ffi.new('secp256k1_ecdsa_recoverable_signature *')

        signed = lib.secp256k1_ecdsa_sign_recoverable(
            self.context.ctx, signature, msg_hash, self.secret, ffi.NULL,
            ffi.NULL
        )

        if not signed:
            raise ValueError('The nonce generation function failed, or the '
                             'private key was invalid.')

        return serialize_recoverable(signature, self.context)

    def ecdh(self, public_key):
        secret = ffi.new('unsigned char [32]')

        lib.secp256k1_ecdh(
            self.context.ctx, secret, PublicKey(public_key).public_key,
            self.secret
        )

        return bytes(ffi.buffer(secret, 32))

    def add(self, scalar, update=False):
        scalar = pad_scalar(scalar)

        secret = ffi.new('unsigned char [32]', self.secret)

        success = lib.secp256k1_ec_privkey_tweak_add(
            self.context.ctx, secret, scalar
        )

        if not success:
            raise ValueError('The tweak was out of range, or the resulting '
                             'private key is invalid.')

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self._update_public_key()
            return self

        return PrivateKey(secret, self.context)

    def multiply(self, scalar, update=False):
        scalar = validate_secret(scalar)

        secret = ffi.new('unsigned char [32]', self.secret)

        lib.secp256k1_ec_privkey_tweak_mul(
            self.context.ctx, secret, scalar
        )

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self._update_public_key()
            return self

        return PrivateKey(secret, self.context)

    def to_hex(self):
        return bytes_to_hex(self.secret)

    def to_int(self):
        return bytes_to_int(self.secret)

    def to_pem(self):
        return der_to_pem(self.to_der())

    def to_der(self):
        pk = ECPrivateKey({
            'version': ensure_unicode('ecPrivkeyVer1'),
            'private_key': self.to_int(),
            'public_key': ECPointBitString(
                self.public_key.format(compressed=False)
            )
        })

        return PrivateKeyInfo({
            'version': 0,
            'private_key_algorithm': PrivateKeyAlgorithm({
                'algorithm': ensure_unicode('ec'),
                'parameters': ECDomainParameters(
                    name='named',
                    value=ensure_unicode('1.3.132.0.10')
                )}),
            'private_key': pk
        }).dump()

    @classmethod
    def from_hex(cls, hexed, context=GLOBAL_CONTEXT):
        return PrivateKey(hex_to_bytes(hexed), context)

    @classmethod
    def from_int(cls, num, context=GLOBAL_CONTEXT):
        return PrivateKey(int_to_bytes_padded(num), context)

    @classmethod
    def from_pem(cls, pem, context=GLOBAL_CONTEXT):
        return PrivateKey(
            int_to_bytes_padded(PrivateKeyInfo.load(
                pem_to_der(pem)
            ).native['private_key']['private_key']),
            context
        )

    @classmethod
    def from_der(cls, der, context=GLOBAL_CONTEXT):
        return PrivateKey(
            int_to_bytes_padded(
                PrivateKeyInfo.load(der).native['private_key']['private_key']
            ),
            context
        )

    def _update_public_key(self):
        created = lib.secp256k1_ec_pubkey_create(
            self.context.ctx, self.public_key.public_key, self.secret
        )

        if not created:
            raise ValueError('Invalid secret.')

    def __eq__(self, other):
        return self.secret == other.secret


class PublicKey:
    def __init__(self, data, context=GLOBAL_CONTEXT):
        if not isinstance(data, bytes):
            self.public_key = data
        else:
            public_key = ffi.new('secp256k1_pubkey *')

            parsed = lib.secp256k1_ec_pubkey_parse(
                context.ctx, public_key, data, len(data)
            )

            if not parsed:
                raise ValueError('The public key could not be parsed or is '
                                 'invalid.')

            self.public_key = public_key

        self.context = context

    @classmethod
    def from_secret(cls, secret, context=GLOBAL_CONTEXT):
        public_key = ffi.new('secp256k1_pubkey *')

        created = lib.secp256k1_ec_pubkey_create(
            context.ctx, public_key, validate_secret(secret)
        )

        if not created:
            raise ValueError('Somehow an invalid secret was used. Please '
                             'submit this as an issue here: '
                             'https://github.com/ofek/coincurve/issues/new')

        return PublicKey(public_key, context)

    @classmethod
    def from_valid_secret(cls, secret, context=GLOBAL_CONTEXT):
        public_key = ffi.new('secp256k1_pubkey *')

        created = lib.secp256k1_ec_pubkey_create(
            context.ctx, public_key, secret
        )

        if not created:
            raise ValueError('Invalid secret.')

        return PublicKey(public_key, context)

    @classmethod
    def from_point(cls, x, y, context=GLOBAL_CONTEXT):
        return PublicKey(
            b'\x04' + int_to_bytes_padded(x) + int_to_bytes_padded(y),
            context
        )

    @classmethod
    def from_signature_and_message(cls, serialized_sig, message, hasher=sha256,
                                   context=GLOBAL_CONTEXT):
        return PublicKey(recover(
            message,
            deserialize_recoverable(serialized_sig, context=context),
            hasher=hasher,
            context=context
        ))

    @classmethod
    def combine_keys(cls, public_keys, context=GLOBAL_CONTEXT):
        public_key = ffi.new('secp256k1_pubkey *')

        combined = lib.secp256k1_ec_pubkey_combine(
            context.ctx, public_key, [pk.public_key for pk in public_keys],
            len(public_keys)
        )

        if not combined:
            raise ValueError('The sum of the public keys is invalid.')

        return PublicKey(public_key, context)

    def format(self, compressed=True):
        length = 33 if compressed else 65
        serialized = ffi.new('unsigned char [%d]' % length)
        output_len = ffi.new('size_t *', length)

        lib.secp256k1_ec_pubkey_serialize(
            self.context.ctx, serialized, output_len, self.public_key,
            EC_COMPRESSED if compressed else EC_UNCOMPRESSED
        )

        return bytes(ffi.buffer(serialized, length))

    def point(self):
        public_key = self.format(compressed=False)
        return bytes_to_int(public_key[1:33]), bytes_to_int(public_key[33:])

    def verify(self, signature, message, hasher=sha256):
        msg_hash = hasher(message) if hasher is not None else message
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        verified = lib.secp256k1_ecdsa_verify(
            self.context.ctx, der_to_cdata(signature), msg_hash, self.public_key
        )

        # A performance hack to avoid global bool() lookup.
        return not not verified

    def add(self, scalar, update=False):
        scalar = pad_scalar(scalar)

        new_key = ffi.new('secp256k1_pubkey *', self.public_key[0])

        success = lib.secp256k1_ec_pubkey_tweak_add(
            self.context.ctx, new_key, scalar
        )

        if not success:
            raise ValueError('The tweak was out of range, or the resulting '
                             'public key is invalid.')

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)

    def multiply(self, scalar, update=False):
        scalar = validate_secret(scalar)

        new_key = ffi.new('secp256k1_pubkey *', self.public_key[0])

        lib.secp256k1_ec_pubkey_tweak_mul(
            self.context.ctx, new_key, scalar
        )

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)

    def combine(self, public_keys, update=False):
        new_key = ffi.new('secp256k1_pubkey *')

        combined = lib.secp256k1_ec_pubkey_combine(
            self.context.ctx, new_key, [pk.public_key for pk in public_keys],
            len(public_keys)
        )

        if not combined:
            raise ValueError('The sum of the public keys is invalid.')

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)

    def __eq__(self, other):
        return self.format(compressed=False) == other.format(compressed=False)
