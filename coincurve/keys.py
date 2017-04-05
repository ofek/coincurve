from asn1crypto.keys import (
    ECDomainParameters, ECPointBitString, ECPrivateKey, PrivateKeyAlgorithm,
    PrivateKeyInfo
)

from coincurve.context import GLOBAL_CONTEXT
from coincurve.ecdsa import cdata_to_der, der_to_cdata, recoverable_to_der
from coincurve.flags import EC_COMPRESSED, EC_UNCOMPRESSED
from coincurve.utils import (
    bytes_to_int, der_to_pem, get_valid_secret, int_to_bytes, pem_to_der,
    sha256, validate_secret
)
from ._libsecp256k1 import ffi, lib


class PrivateKey:
    def __init__(self, secret=None, context=GLOBAL_CONTEXT):
        self.secret = (validate_secret(secret) if secret is not None
                       else get_valid_secret())
        self.context = context
        self.public_key = PublicKey.from_valid_secret(
            self.secret, self.context
        )

    def sign(self, message, hasher=sha256):
        msg_hash = hasher(message)
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        signature = ffi.new('secp256k1_ecdsa_signature *')

        res = lib.secp256k1_ecdsa_sign(
            self.context.ctx, signature, msg_hash, self.secret, ffi.NULL,
            ffi.NULL
        )
        assert res == 1

        return cdata_to_der(signature, self.context)

    def sign_recoverable(self, message, hasher=sha256):
        msg_hash = hasher(message)
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        signature = ffi.new('secp256k1_ecdsa_recoverable_signature *')

        res = lib.secp256k1_ecdsa_sign_recoverable(
            self.context.ctx, signature, msg_hash, self.secret, ffi.NULL,
            ffi.NULL
        )
        assert res == 1

        return recoverable_to_der(signature, self.context)

    def add(self, scalar, update=False):
        """
        Tweak the current private key by adding a 32 byte scalar
        to it and return a new raw private key composed of 32 bytes.
        """
        if len(scalar) != 32:
            raise TypeError('Scalar must be composed of 32 bytes.')

        # Create a copy of the current private key.
        secret = ffi.new('unsigned char [32]', self.secret)

        res = lib.secp256k1_ec_privkey_tweak_add(
            self.context.ctx, secret, scalar
        )
        assert res == 1

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self._update_public_key()
            return self

        return PrivateKey(secret, self.context)

    def multiply(self, scalar, update=False):
        """
        Tweak the current private key by multiplying it by a 32 byte scalar
        and return a new raw private key composed of 32 bytes.
        """
        if len(scalar) != 32:
            raise TypeError('Scalar must be composed of 32 bytes.')

        # Create a copy of the current private key.
        secret = ffi.new('unsigned char [32]', self.secret)

        res = lib.secp256k1_ec_privkey_tweak_mul(
            self.context.ctx, secret, scalar
        )
        assert res == 1

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self._update_public_key()
            return self

        return PrivateKey(secret, self.context)

    def to_int(self):
        return bytes_to_int(self.secret)

    def to_pem(self):
        return der_to_pem(self.to_der())

    def to_der(self):
        pk = ECPrivateKey({
            'version': 'ecPrivkeyVer1',
            'private_key': self.to_int(),
            'public_key': ECPointBitString(
                self.public_key.format(compressed=False)
            )
        })

        return PrivateKeyInfo({
            'version': 0,
            'private_key_algorithm': PrivateKeyAlgorithm({
                'algorithm': 'ec',
                'parameters': ECDomainParameters(
                    name='named',
                    value='1.3.132.0.10'
                )}),
            'private_key': pk
        }).dump()

    @classmethod
    def from_int(cls, num):
        return PrivateKey(int_to_bytes(num))

    @classmethod
    def from_pem(cls, pem):
        return PrivateKey(
            int_to_bytes(
                PrivateKeyInfo.load(
                    pem_to_der(pem)
                ).native['private_key']['private_key'])
        )

    @classmethod
    def from_der(cls, der):
        return PrivateKey(
            int_to_bytes(
                PrivateKeyInfo.load(der).native['private_key']['private_key']
            )
        )

    def _update_public_key(self):
        res = lib.secp256k1_ec_pubkey_create(
            self.context.ctx, self.public_key.public_key, self.secret
        )
        assert res == 1


class PublicKey:
    def __init__(self, data, context=GLOBAL_CONTEXT):
        if not isinstance(data, bytes):
            self.public_key = data
        else:
            length = len(data)
            if length not in (33, 65):
                raise ValueError('{} is an invalid length for a public key.'
                                 ''.format(length))

            public_key = ffi.new('secp256k1_pubkey *')

            res = lib.secp256k1_ec_pubkey_parse(
                context.ctx, public_key, data, length
            )
            assert res == 1

        self.context = context

    @classmethod
    def from_secret(cls, secret, context=GLOBAL_CONTEXT):
        public_key = ffi.new('secp256k1_pubkey *')

        res = lib.secp256k1_ec_pubkey_create(
            context.ctx, public_key, validate_secret(secret)
        )
        assert res == 1

        return PublicKey(public_key, context)

    @classmethod
    def from_valid_secret(cls, secret, context=GLOBAL_CONTEXT):
        public_key = ffi.new('secp256k1_pubkey *')

        res = lib.secp256k1_ec_pubkey_create(
            context.ctx, public_key, secret
        )
        assert res == 1

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

    def combine(self, public_keys):
        """Add a number of public keys together."""
        new_key = ffi.new('secp256k1_pubkey *')

        res = lib.secp256k1_ec_pubkey_combine(
            self.context.ctx, new_key, [pk.public_key for pk in public_keys],
            len(public_keys)
        )
        assert res == 1

        self.public_key = new_key

    def verify(self, signature, message, hasher=sha256):
        msg_hash = hasher(message)
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        verified = lib.secp256k1_ecdsa_verify(
            self.context.ctx, der_to_cdata(signature), msg_hash, self.public_key
        )

        # A performance hack to avoid global bool() lookup.
        return not not verified

    def ecdh(self, scalar):
        if len(scalar) != 32:
            raise TypeError('Scalar must be composed of 32 bytes.')

        secret = ffi.new('unsigned char [32]')

        res = lib.secp256k1_ecdh(
            self.context.ctx, secret, self.public_key, scalar
        )
        assert res == 1

        return bytes(ffi.buffer(secret, 32))

    def add(self, scalar, update=False):
        """
        Tweak the current public key by adding a 32 byte scalar times
        the generator to it and return a new PublicKey instance.
        """
        if len(scalar) != 32:
            raise TypeError('Scalar must be composed of 32 bytes.')

        # Create a copy of the current public key.
        new_key = ffi.new('secp256k1_pubkey *', self.public_key[0])

        res = lib.secp256k1_ec_pubkey_tweak_add(
            self.context.ctx, new_key, scalar
        )
        assert res == 1

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)

    def multiply(self, scalar, update=False):
        """
        Tweak the current public key by multiplying it by a 32 byte scalar
        and return a new PublicKey instance.
        """
        if len(scalar) != 32:
            raise TypeError('Scalar must be composed of 32 bytes.')

        # Create a copy of the current public key.
        new_key = ffi.new('secp256k1_pubkey *', self.public_key[0])

        res = lib.secp256k1_ec_pubkey_tweak_mul(
            self.context.ctx, new_key, scalar
        )
        assert res == 1

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)
