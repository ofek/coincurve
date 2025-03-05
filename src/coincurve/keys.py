from __future__ import annotations

import os
from typing import TYPE_CHECKING

from coincurve._libsecp256k1 import ffi, lib
from coincurve.context import GLOBAL_CONTEXT, Context
from coincurve.der import decode_der, encode_der
from coincurve.ecdsa import cdata_to_der, der_to_cdata, deserialize_recoverable, recover, serialize_recoverable
from coincurve.flags import EC_COMPRESSED, EC_UNCOMPRESSED
from coincurve.utils import (
    DEFAULT_NONCE,
    bytes_to_int,
    der_to_pem,
    get_valid_secret,
    hex_to_bytes,
    int_to_bytes_padded,
    pad_scalar,
    pem_to_der,
    sha256,
    validate_secret,
)

if TYPE_CHECKING:
    from coincurve.types import Hasher, Nonce


class PrivateKey:
    def __init__(self, secret: bytes | None = None, context: Context = GLOBAL_CONTEXT):
        """
        Initializes a private key.

        Parameters:
            secret: The secret used to initialize the private key.
                    If not provided, a new key will be generated.
            context: The context to use.
        """
        self.secret: bytes = validate_secret(secret) if secret is not None else get_valid_secret()
        self.context = context
        self.public_key: PublicKey = PublicKey.from_valid_secret(self.secret, self.context)
        self.public_key_xonly: PublicKeyXOnly = PublicKeyXOnly.from_valid_secret(self.secret, self.context)

    def sign(self, message: bytes, hasher: Hasher = sha256, custom_nonce: Nonce = DEFAULT_NONCE) -> bytes:
        """
        Creates an ECDSA signature.

        Parameters:
            message: The message to sign.
            hasher (collections.abc.Callable[[bytes], bytes] | None): The hash function to use, which must
                return 32 bytes. By default, the `sha256` algorithm is used. If `None`, no hashing occurs.
            custom_nonce (tuple[ffi.CData, ffi.CData]): Custom nonce data in the form `(nonce_function, input_data)`.
                For more information, refer to the `libsecp256k1` documentation
                [here](https://github.com/bitcoin-core/secp256k1/blob/v0.6.0/include/secp256k1.h#L637-L642).

        Returns:
            The ECDSA signature.

        Raises:
            ValueError: If the message hash was not 32 bytes long, the nonce generation
                        function failed, or the private key was invalid.
        """
        msg_hash = hasher(message) if hasher is not None else message
        if len(msg_hash) != 32:  # noqa: PLR2004
            msg = "Message hash must be 32 bytes long."
            raise ValueError(msg)

        signature = ffi.new("secp256k1_ecdsa_signature *")
        nonce_fn, nonce_data = custom_nonce

        signed = lib.secp256k1_ecdsa_sign(self.context.ctx, signature, msg_hash, self.secret, nonce_fn, nonce_data)

        if not signed:
            msg = "The nonce generation function failed, or the private key was invalid."
            raise ValueError(msg)

        return cdata_to_der(signature, self.context)

    def sign_schnorr(self, message: bytes, aux_randomness: bytes = b"") -> bytes:
        """
        Creates a Schnorr signature.

        Parameters:
            message: The message to sign.
            aux_randomness: 32 bytes of fresh randomness, empty bytestring (auto-generated),
                or None (no randomness).

        Returns:
            The Schnorr signature.

        Raises:
            ValueError: If the message was not 32 bytes long, the optional auxiliary
                random data was not 32 bytes long, signing failed, or the signature was invalid.
        """
        if len(message) != 32:  # noqa: PLR2004
            msg = "Message must be 32 bytes long."
            raise ValueError(msg)
        if aux_randomness == b"":
            aux_randomness = os.urandom(32)
        elif aux_randomness is None:
            aux_randomness = ffi.NULL
        elif len(aux_randomness) != 32:  # noqa: PLR2004
            msg = "Auxiliary random data must be 32 bytes long."
            raise ValueError(msg)

        keypair = ffi.new("secp256k1_keypair *")
        res = lib.secp256k1_keypair_create(self.context.ctx, keypair, self.secret)
        if not res:
            msg = "Secret was invalid"
            raise ValueError(msg)

        signature = ffi.new("unsigned char[64]")
        res = lib.secp256k1_schnorrsig_sign32(self.context.ctx, signature, message, keypair, aux_randomness)
        if not res:
            msg = "Signing failed"
            raise ValueError(msg)

        res = lib.secp256k1_schnorrsig_verify(
            self.context.ctx, signature, message, len(message), self.public_key_xonly.public_key
        )
        if not res:
            msg = "Invalid signature"
            raise ValueError(msg)

        return bytes(ffi.buffer(signature))

    def sign_recoverable(self, message: bytes, hasher: Hasher = sha256, custom_nonce: Nonce = DEFAULT_NONCE) -> bytes:
        """
        Creates a recoverable ECDSA signature.

        Parameters:
            message: The message to sign.
            hasher (collections.abc.Callable[[bytes], bytes] | None): The hash function to use, which must
                return 32 bytes. By default, the `sha256` algorithm is used. If `None`, no hashing occurs.
            custom_nonce (tuple[ffi.CData, ffi.CData]): Custom nonce data in the form `(nonce_function, input_data)`.
                For more information, refer to the `libsecp256k1` documentation
                [here](https://github.com/bitcoin-core/secp256k1/blob/v0.6.0/include/secp256k1.h#L637-L642).

        Returns:
            The recoverable ECDSA signature.

        Raises:
            ValueError: If the message hash was not 32 bytes long, the nonce generation
                function failed, or the private key was invalid.
        """
        msg_hash = hasher(message) if hasher is not None else message
        if len(msg_hash) != 32:  # noqa: PLR2004
            msg = "Message hash must be 32 bytes long."
            raise ValueError(msg)

        signature = ffi.new("secp256k1_ecdsa_recoverable_signature *")
        nonce_fn, nonce_data = custom_nonce

        signed = lib.secp256k1_ecdsa_sign_recoverable(
            self.context.ctx, signature, msg_hash, self.secret, nonce_fn, nonce_data
        )

        if not signed:
            msg = "The nonce generation function failed, or the private key was invalid."
            raise ValueError(msg)

        return serialize_recoverable(signature, self.context)

    def ecdh(self, public_key: bytes) -> bytes:
        """
        Computes an EC Diffie-Hellman secret in constant time.

        !!! note
            This prevents malleability by returning `sha256(compressed_public_key)` instead of the `x` coordinate
            directly.

        Parameters:
            public_key: The formatted public key.

        Returns:
            The 32-byte shared secret.

        Raises:
            ValueError: If the public key could not be parsed or was invalid.
        """
        secret = ffi.new("unsigned char [32]")

        lib.secp256k1_ecdh(self.context.ctx, secret, PublicKey(public_key).public_key, self.secret, ffi.NULL, ffi.NULL)

        return bytes(ffi.buffer(secret, 32))

    def add(self, scalar: bytes, update: bool = False) -> PrivateKey:  # noqa: FBT001, FBT002
        """
        Adds a scalar to the private key.

        Parameters:
            scalar: The scalar with which to add.
            update: Whether to update the private key in-place.

        Returns:
            The new private key, or the modified private key if `update` is `True`.

        Raises:
            ValueError: If the tweak was out of range or the resulting private key was invalid.
        """
        scalar = pad_scalar(scalar)

        secret = ffi.new("unsigned char [32]", self.secret)

        success = lib.secp256k1_ec_seckey_tweak_add(self.context.ctx, secret, scalar)

        if not success:
            msg = "The tweak was out of range, or the resulting private key is invalid."
            raise ValueError(msg)

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self._update_public_key()
            return self

        return PrivateKey(secret, self.context)

    def multiply(self, scalar: bytes, update: bool = False) -> PrivateKey:  # noqa: FBT001, FBT002
        """
        Multiplies the private key by a scalar.

        Parameters:
            scalar: The scalar with which to multiply.
            update: Whether to update the private key in-place.

        Returns:
            The new private key, or the modified private key if `update` is `True`.
        """
        scalar = validate_secret(scalar)

        secret = ffi.new("unsigned char [32]", self.secret)

        lib.secp256k1_ec_seckey_tweak_mul(self.context.ctx, secret, scalar)

        secret = bytes(ffi.buffer(secret, 32))

        if update:
            self.secret = secret
            self._update_public_key()
            return self

        return PrivateKey(secret, self.context)

    def to_hex(self) -> str:
        """
        Returns the private key encoded as a hex string.
        """
        return self.secret.hex()

    def to_int(self) -> int:
        """
        Returns the private key as an integer.
        """
        return bytes_to_int(self.secret)

    def to_pem(self) -> bytes:
        """
        Returns the private key encoded in PEM format.
        """
        return der_to_pem(self.to_der())

    def to_der(self) -> bytes:
        """
        Returns the private key encoded in DER format.
        """
        return encode_der(self.secret, self.public_key.format(compressed=False))

    @classmethod
    def from_hex(cls, hexed: str, context: Context = GLOBAL_CONTEXT) -> PrivateKey:
        """
        Creates a private key from a hex string.

        Parameters:
            hexed: The private key encoded as a hex string.
            context: The context to use.

        Returns:
            The private key.
        """
        return PrivateKey(hex_to_bytes(hexed), context)

    @classmethod
    def from_int(cls, num: int, context: Context = GLOBAL_CONTEXT) -> PrivateKey:
        """
        Creates a private key from an integer.

        Parameters:
            num: The private key as an integer.
            context: The context to use.

        Returns:
            The private key.
        """
        return PrivateKey(int_to_bytes_padded(num), context)

    @classmethod
    def from_pem(cls, pem: bytes, context: Context = GLOBAL_CONTEXT) -> PrivateKey:
        """
        Creates a private key from PEM format.

        Parameters:
            pem: The private key encoded in PEM format.
            context: The context to use.

        Returns:
            The private key.
        """
        return PrivateKey(decode_der(pem_to_der(pem)), context)

    @classmethod
    def from_der(cls, der: bytes, context: Context = GLOBAL_CONTEXT) -> PrivateKey:
        """
        Creates a private key from DER format.

        Parameters:
            der: The private key encoded in DER format.
            context: The context to use.

        Returns:
            The private key.
        """
        return PrivateKey(decode_der(der), context)

    def _update_public_key(self):
        created = lib.secp256k1_ec_pubkey_create(self.context.ctx, self.public_key.public_key, self.secret)

        if not created:
            msg = "Invalid secret."
            raise ValueError(msg)

    def __eq__(self, other) -> bool:
        return self.secret == other.secret

    def __hash__(self) -> int:
        return hash(self.secret)


class PublicKey:
    def __init__(self, data: bytes | ffi.CData, context: Context = GLOBAL_CONTEXT):
        """
        Initializes a public key.

        Parameters:
            data (bytes): The formatted public key. This class supports parsing
                compressed (33 bytes, header byte `0x02` or `0x03`),
                uncompressed (65 bytes, header byte `0x04`), or
                hybrid (65 bytes, header byte `0x06` or `0x07`) format public keys.
            context: The context to use.

        Raises:
            ValueError: If the public key could not be parsed or was invalid.
        """
        if not isinstance(data, bytes):
            self.public_key = data
        else:
            public_key = ffi.new("secp256k1_pubkey *")

            parsed = lib.secp256k1_ec_pubkey_parse(context.ctx, public_key, data, len(data))

            if not parsed:
                msg = "The public key could not be parsed or is invalid."
                raise ValueError(msg)

            self.public_key = public_key

        self.context = context

    @classmethod
    def from_secret(cls, secret: bytes, context: Context = GLOBAL_CONTEXT) -> PublicKey:
        """
        Derives a public key from a private key secret.

        Parameters:
            secret: The private key secret.
            context: The context to use.

        Returns:
            The public key.

        Raises:
            ValueError: If an invalid secret was used.
        """
        public_key = ffi.new("secp256k1_pubkey *")

        created = lib.secp256k1_ec_pubkey_create(context.ctx, public_key, validate_secret(secret))

        if not created:  # no cov
            msg = (
                "Somehow an invalid secret was used. Please "
                "submit this as an issue here: "
                "https://github.com/ofek/coincurve/issues/new"
            )
            raise ValueError(msg)

        return PublicKey(public_key, context)

    @classmethod
    def from_valid_secret(cls, secret: bytes, context: Context = GLOBAL_CONTEXT) -> PublicKey:
        """
        Derives a public key from a valid private key secret, avoiding input checks.

        Parameters:
            secret: The private key secret.
            context: The context to use.

        Returns:
            The public key.

        Raises:
            ValueError: If the secret was invalid.
        """
        public_key = ffi.new("secp256k1_pubkey *")

        created = lib.secp256k1_ec_pubkey_create(context.ctx, public_key, secret)

        if not created:
            msg = "Invalid secret."
            raise ValueError(msg)

        return PublicKey(public_key, context)

    @classmethod
    def from_point(cls, x: int, y: int, context: Context = GLOBAL_CONTEXT) -> PublicKey:
        """
        Derives a public key from a coordinate point.

        Parameters:
            x: The x coordinate.
            y: The y coordinate.
            context: The context to use.

        Returns:
            The public key.
        """
        return PublicKey(b"\x04" + int_to_bytes_padded(x) + int_to_bytes_padded(y), context)

    @classmethod
    def from_signature_and_message(
        cls, signature: bytes, message: bytes, hasher: Hasher = sha256, context: Context = GLOBAL_CONTEXT
    ) -> PublicKey:
        """
        Recovers an ECDSA public key from a recoverable signature.

        Parameters:
            signature: The recoverable ECDSA signature.
            message: The message that was supposedly signed.
            hasher (collections.abc.Callable[[bytes], bytes] | None): The hash function to use, which must
                return 32 bytes. By default, the `sha256` algorithm is used. If `None`, no hashing occurs.
            context: The context to use.

        Returns:
            The public key that signed the message.

        Raises:
            ValueError: If the message hash was not 32 bytes long or recovery of the
                ECDSA public key failed.
        """
        return PublicKey(
            recover(message, deserialize_recoverable(signature, context=context), hasher=hasher, context=context)
        )

    @classmethod
    def combine_keys(cls, public_keys: list[PublicKey], context: Context = GLOBAL_CONTEXT) -> PublicKey:
        """
        Adds a number of public keys together.

        Parameters:
            public_keys: A sequence of public keys.
            context: The context to use.

        Returns:
            The combined public key.

        Raises:
            ValueError: If the sum of the public keys was invalid.
        """
        public_key = ffi.new("secp256k1_pubkey *")

        combined = lib.secp256k1_ec_pubkey_combine(
            context.ctx, public_key, [pk.public_key for pk in public_keys], len(public_keys)
        )

        if not combined:
            msg = "The sum of the public keys is invalid."
            raise ValueError(msg)

        return PublicKey(public_key, context)

    def format(self, compressed: bool = True) -> bytes:  # noqa: FBT001, FBT002
        """
        Formats the public key.

        Parameters:
            compressed: Whether to use the compressed format.

        Returns:
            The 33 byte formatted public key, or the 65 byte formatted public key
            if `compressed` is `False`.
        """
        length = 33 if compressed else 65
        serialized = ffi.new("unsigned char [%d]" % length)  # noqa: UP031
        output_len = ffi.new("size_t *", length)

        lib.secp256k1_ec_pubkey_serialize(
            self.context.ctx, serialized, output_len, self.public_key, EC_COMPRESSED if compressed else EC_UNCOMPRESSED
        )

        return bytes(ffi.buffer(serialized, length))

    def point(self) -> tuple[int, int]:
        """
        Returns the public key as a coordinate point.
        """
        public_key = self.format(compressed=False)
        return bytes_to_int(public_key[1:33]), bytes_to_int(public_key[33:])

    def verify(self, signature: bytes, message: bytes, hasher: Hasher = sha256) -> bool:
        """
        Verifies an ECDSA signature.

        Parameters:
            signature: The ECDSA signature.
            message: The message that was supposedly signed.
            hasher (collections.abc.Callable[[bytes], bytes] | None): The hash function to use, which must
                return 32 bytes. By default, the `sha256` algorithm is used. If `None`, no hashing occurs.

        Returns:
            A boolean indicating whether the signature is correct.

        Raises:
            ValueError: If the message hash was not 32 bytes long or the
                DER-encoded signature could not be parsed.
        """
        msg_hash = hasher(message) if hasher is not None else message
        if len(msg_hash) != 32:  # noqa: PLR2004
            msg = "Message hash must be 32 bytes long."
            raise ValueError(msg)

        verified = lib.secp256k1_ecdsa_verify(self.context.ctx, der_to_cdata(signature), msg_hash, self.public_key)

        # A performance hack to avoid global bool() lookup.
        return not not verified  # noqa: SIM208

    def add(self, scalar: bytes, update: bool = False) -> PublicKey:  # noqa: FBT001, FBT002
        """
        Adds a scalar to the public key.

        Parameters:
            scalar: The scalar with which to add.
            update: Whether to update the public key in-place.

        Returns:
            The new public key, or the modified public key if `update` is `True`.

        Raises:
            ValueError: If the tweak was out of range or the resulting public key was invalid.
        """
        scalar = pad_scalar(scalar)

        new_key = ffi.new("secp256k1_pubkey *", self.public_key[0])

        success = lib.secp256k1_ec_pubkey_tweak_add(self.context.ctx, new_key, scalar)

        if not success:
            msg = "The tweak was out of range, or the resulting public key is invalid."
            raise ValueError(msg)

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)

    def multiply(self, scalar: bytes, update: bool = False) -> PublicKey:  # noqa: FBT001, FBT002
        """
        Multiplies the public key by a scalar.

        Parameters:
            scalar: The scalar with which to multiply.
            update: Whether to update the public key in-place.

        Returns:
            The new public key, or the modified public key if `update` is `True`.
        """
        scalar = validate_secret(scalar)

        new_key = ffi.new("secp256k1_pubkey *", self.public_key[0])

        lib.secp256k1_ec_pubkey_tweak_mul(self.context.ctx, new_key, scalar)

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)

    def combine(self, public_keys: list[PublicKey], update: bool = False) -> PublicKey:  # noqa: FBT001, FBT002
        """
        Adds a number of public keys together.

        Parameters:
            public_keys: A sequence of public keys.
            update: Whether to update the public key in-place.

        Returns:
            The combined public key, or the modified public key if `update` is `True`.

        Raises:
            ValueError: If the sum of the public keys was invalid.
        """
        new_key = ffi.new("secp256k1_pubkey *")

        combined = lib.secp256k1_ec_pubkey_combine(
            self.context.ctx, new_key, [pk.public_key for pk in [self, *public_keys]], len(public_keys) + 1
        )

        if not combined:
            msg = "The sum of the public keys is invalid."
            raise ValueError(msg)

        if update:
            self.public_key = new_key
            return self

        return PublicKey(new_key, self.context)

    def __eq__(self, other) -> bool:
        return self.format(compressed=False) == other.format(compressed=False)

    def __hash__(self) -> int:
        return hash(self.format(compressed=False))


class PublicKeyXOnly:
    def __init__(self, data: bytes | ffi.CData, parity: bool = False, context: Context = GLOBAL_CONTEXT):  # noqa: FBT001, FBT002
        """
        Initializes a BIP340 `x-only` public key.

        Parameters:
            data (bytes): The formatted public key.
            parity: Whether the encoded point is the negation of the public key.
            context: The context to use.

        Raises:
            ValueError: If the public key could not be parsed or is invalid.
        """
        if not isinstance(data, bytes):
            self.public_key = data
        else:
            public_key = ffi.new("secp256k1_xonly_pubkey *")
            parsed = lib.secp256k1_xonly_pubkey_parse(context.ctx, public_key, data)
            if not parsed:
                msg = "The public key could not be parsed or is invalid."
                raise ValueError(msg)

            self.public_key = public_key

        self.parity = parity
        self.context = context

    @classmethod
    def from_secret(cls, secret: bytes, context: Context = GLOBAL_CONTEXT) -> PublicKeyXOnly:
        """
        Derives an x-only public key from a private key secret.

        Parameters:
            secret: The private key secret.
            context: The context to use.

        Returns:
            The x-only public key.

        Raises:
            ValueError: If the secret was invalid.
        """
        keypair = ffi.new("secp256k1_keypair *")
        res = lib.secp256k1_keypair_create(context.ctx, keypair, validate_secret(secret))
        if not res:
            msg = "Secret was invalid"
            raise ValueError(msg)

        xonly_pubkey = ffi.new("secp256k1_xonly_pubkey *")
        pk_parity = ffi.new("int *")
        res = lib.secp256k1_keypair_xonly_pub(context.ctx, xonly_pubkey, pk_parity, keypair)

        return cls(xonly_pubkey, parity=not not pk_parity[0], context=context)  # noqa: SIM208

    @classmethod
    def from_valid_secret(cls, secret: bytes, context: Context = GLOBAL_CONTEXT) -> PublicKeyXOnly:
        """
        Derives an x-only public key from a valid private key secret, avoiding input checks.

        Parameters:
            secret: The private key secret.
            context: The context to use.

        Returns:
            The x-only public key.

        Raises:
            ValueError: If the secret was invalid.
        """
        keypair = ffi.new("secp256k1_keypair *")
        res = lib.secp256k1_keypair_create(context.ctx, keypair, secret)
        if not res:
            msg = "Secret was invalid"
            raise ValueError(msg)

        xonly_pubkey = ffi.new("secp256k1_xonly_pubkey *")
        pk_parity = ffi.new("int *")
        res = lib.secp256k1_keypair_xonly_pub(context.ctx, xonly_pubkey, pk_parity, keypair)

        return cls(xonly_pubkey, parity=not not pk_parity[0], context=context)  # noqa: SIM208

    def format(self) -> bytes:
        """
        Serializes the public key.

        Returns:
            The public key serialized as 32 bytes.

        Raises:
            ValueError: If the public key in `self.public_key` is invalid.
        """
        output32 = ffi.new("unsigned char [32]")

        res = lib.secp256k1_xonly_pubkey_serialize(self.context.ctx, output32, self.public_key)
        if not res:
            msg = "Public key in self.public_key must be valid"
            raise ValueError(msg)

        return bytes(ffi.buffer(output32, 32))

    def verify(self, signature: bytes, message: bytes) -> bool:
        """
        Verifies a Schnorr signature over a given message.

        Parameters:
            signature: The 64-byte Schnorr signature to verify.
            message: The message to be verified.

        Returns:
            A boolean indicating whether the signature is correct.

        Raises:
            ValueError: If the signature is not 64 bytes long.
        """
        if len(signature) != 64:  # noqa: PLR2004
            msg = "Signature must be 64 bytes long."
            raise ValueError(msg)

        return not not lib.secp256k1_schnorrsig_verify(  # noqa: SIM208
            self.context.ctx, signature, message, len(message), self.public_key
        )

    def tweak_add(self, scalar: bytes) -> None:
        """
        Adds a scalar to the public key.

        Parameters:
            scalar: The scalar with which to add.

        Returns:
            The modified public key.

        Raises:
            ValueError: If the tweak was out of range or the resulting public key would be invalid.
        """
        scalar = pad_scalar(scalar)

        out_pubkey = ffi.new("secp256k1_pubkey *")
        res = lib.secp256k1_xonly_pubkey_tweak_add(self.context.ctx, out_pubkey, self.public_key, scalar)
        if not res:
            msg = "The tweak was out of range, or the resulting public key would be invalid"
            raise ValueError(msg)

        pk_parity = ffi.new("int *")
        lib.secp256k1_xonly_pubkey_from_pubkey(self.context.ctx, self.public_key, pk_parity, out_pubkey)
        self.parity = not not pk_parity[0]  # noqa: SIM208

    def __eq__(self, other) -> bool:
        res = lib.secp256k1_xonly_pubkey_cmp(self.context.ctx, self.public_key, other.public_key)
        return res == 0

    def __hash__(self) -> int:
        return hash(self.format())
