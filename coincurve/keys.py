from coincurve import GLOBAL_CONTEXT
from coincurve.flags import EC_COMPRESSED, EC_UNCOMPRESSED
from coincurve.utils import get_valid_secret, validate_secret
from ._libsecp256k1 import ffi, lib


class PrivateKey:
    def __init__(self, secret=None, context=GLOBAL_CONTEXT):
        self.secret = (validate_secret(secret) if secret is not None
                       else get_valid_secret())
        self.context = context
        self.public_key = ffi.new('secp256k1_pubkey *')

        self.update_public_key()

    def update_public_key(self):
        res = lib.secp256k1_ec_pubkey_create(
            self.context, self.public_key, self.secret
        )
        assert res == 1

    def ecdsa_sign(self, msg_hash, nonce=None):
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        signature = ffi.new('secp256k1_ecdsa_signature *')

        if not nonce:
            nonce_fn = ffi.NULL
            nonce_data = ffi.NULL
        else:
            nonce_fn, nonce_data = nonce

        res = lib.secp256k1_ecdsa_sign(
            self.context, signature, msg_hash, self.secret, nonce_fn, nonce_data
        )
        assert res == 1

        return signature

    def ecdsa_sign_recoverable(self, msg_hash):
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        signature = ffi.new('secp256k1_ecdsa_recoverable_signature *')

        res = lib.secp256k1_ecdsa_sign_recoverable(
            self.context, signature, msg_hash, self.secret, ffi.NULL, ffi.NULL
        )
        assert res == 1

        return signature

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
            self.context, secret, scalar
        )
        assert res == 1

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self.update_public_key()
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
            self.context, secret, scalar
        )
        assert res == 1

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self.update_public_key()
            return self

        return PrivateKey(secret, self.context)


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
                context, public_key, data, length
            )
            assert res == 1

        self.context = context

    @classmethod
    def from_secret(cls, secret, context=GLOBAL_CONTEXT):
        public_key = ffi.new('secp256k1_pubkey *')

        res = lib.secp256k1_ec_pubkey_create(
            context, public_key, secret
        )
        assert res == 1

        return PublicKey(public_key, context)

    def format(self, compressed=True):
        length = 33 if compressed else 65
        serialized = ffi.new('unsigned char [%d]' % length)
        output_len = ffi.new('size_t *', length)
        compression = EC_COMPRESSED if compressed else EC_UNCOMPRESSED

        lib.secp256k1_ec_pubkey_serialize(
            self.context, serialized, output_len, self.public_key, compression
        )

        return bytes(ffi.buffer(serialized, length))

    def combine(self, public_keys):
        """Add a number of public keys together."""
        new_key = ffi.new('secp256k1_pubkey *')

        res = lib.secp256k1_ec_pubkey_combine(
            self.context, new_key, [pk.public_key for pk in public_keys],
            len(public_keys)
        )
        assert res == 1

        self.public_key = new_key

    def ecdsa_verify(self, msg_hash, signature):
        if len(msg_hash) != 32:
            raise ValueError('Message hash must be 32 bytes long.')

        verified = lib.secp256k1_ecdsa_verify(
            self.context, signature, msg_hash, self.public_key
        )

        # Performance hack to avoid global bool() lookup.
        return not not verified

    def ecdh(self, scalar):
        if len(scalar) != 32:
            raise TypeError('Scalar must be composed of 32 bytes.')

        secret = ffi.new('unsigned char [32]')

        res = lib.secp256k1_ecdh(self.context, secret, self.public_key, scalar)
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
        new_key = ffi.new('secp256k1_pubkey *', self.public_key)

        res = lib.secp256k1_ec_pubkey_tweak_add(
            self.context, new_key, scalar
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
        new_key = ffi.new('secp256k1_pubkey *', self.public_key)

        res = lib.secp256k1_ec_pubkey_tweak_mul(
            self.context, new_key, scalar
        )
        assert res == 1

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)
