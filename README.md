# Coincurve

Python CFFI bindings for [libsecp256k1](https://github.com/bitcoin-core/secp256k1)
(an experimental and optimized C library for EC operations on curve secp256k1).

This is a fork of [https://github.com/ludbb/secp256k1-py](https://github.com/ludbb/secp256k1-py).

New features include:

- Support for Windows (Python 3 only though, unlike Linux/macOS)
- Linux, macOS, and Windows all have binary packages for both 64 and 32-bit architectures
- A fix to remove CFFI warnings
- A global context is used by default, drastically increasing performance
- Each release uses newest version of [libsecp256k1](https://github.com/bitcoin-core/secp256k1)
- Implements a fix for [https://bugs.python.org/issue28150](https://bugs.python.org/issue28150)
  to support Python 3.6+ on macOS
- Linux & macOS wheels now use GMP
- Endomorphism optimization is now enabled

**To retain backward compatibility with secp256k1-py, use coincurve version 2.1.1 specifically!**
Anything after that will have a modified (cleaner :) API and only support Python 3.

## Installation

```
pip install coincurve==2.1.1
```

### Precompiled binary packages (wheels)

Precompiled binary wheels is available for Python 2.7, 3.3, 3.4, and 3.5 on Linux. To take advantage of those you need to use pip >= 8.1.0.


## API

#### class `coincurve.PrivateKey(privkey, raw, flags)`

The `PrivateKey` class loads or creates a private key by obtaining 32 bytes from urandom and operates over it.

##### Instantiation parameters

- `privkey=None` - generate a new private key if None, otherwise load a private key.
- `raw=True` - if `True`, it is assumed that `privkey` is just a sequence of bytes, otherwise it is assumed that it is in the DER format. This is not used when `privkey` is not specified.
- `flags=coincurve.ALL_FLAGS` - see Constants.

##### Methods and instance attributes

- `pubkey`: an instance of `coincurve.PublicKey`.
- `private_key`: raw bytes for the private key.

- `set_raw_privkey(privkey)`<br/>
update the `private_key` for this instance with the bytes specified by `privkey`. If `privkey` is invalid, an Exception is raised. The `pubkey` is also updated based on the new private key.

- `serialize()` -> bytes<br/>
convert the raw bytes present in `private key` to a hexadecimal string.

- `deserialize(privkey_ser)` -> bytes<br/>
convert from a hexadecimal string to raw bytes and update the `pubkey` and `private_key` for this instance.

- `tweak_add(scalar)` -> bytes<br/>
tweak the current private key by adding a 32 byte scalar to it and return a new raw private key composed of 32 bytes.

- `tweak_mul(scalar)` -> bytes<br/>
tweak the current private key by multiplying it by a 32 byte scalar and return a new raw private key composed of 32 bytes.

- `ecdsa_sign(msg, raw=False, digest=hashlib.sha256)` -> internal object<br/>
by default, create an ECDSA-SHA256 signature from the bytes in `msg`. If `raw` is True, then the `digest` function is not applied over `msg`, otherwise the `digest` must produce 256 bits or an `Exception` will be raised.<br/><br/>
The returned object is a structure from the C lib. If you want to store it (on a disk or similar), use `ecdsa_serialize` and later on use `ecdsa_deserialize` when loading.

- `ecdsa_sign_recoverable(msg, raw=False, digest=hashlib.sha256)` -> internal object<br/>
create a recoverable ECDSA signature. See `ecdsa_sign` for parameters description.

> NOTE: `ecdsa_sign_recoverable` can only be used if the `secp256k1` C library is compiled with support for it. If there is no support, an Exception will be raised when calling it.

- `schnorr_sign(msg, raw=False, digest=hashlib.sha256)` -> bytes<br/>
create a signature using a custom EC-Schnorr-SHA256 construction. It
produces non-malleable 64-byte signatures which support public key recovery
batch validation, and multiparty signing. `msg`, `raw`, and `digest` are used as described in `ecdsa_sign`.

- `schnorr_generate_nonce_pair(msg, raw=False, digest=hashlib.sha256)` -> (internal object, internal object)<br/>
generate a nonce pair deterministically for use with `schnorr_partial_sign`. `msg`, `raw`, and `digest` are used as described in `ecdsa_sign`.

- `schnorr_partial_sign(msg, privnonce, pubnonce_others, raw=False, digest=hashlib.sha256)` -> bytes<br/>
produce a partial Schnorr signature, which can be combined using `schnorr_partial_combine` to end up with a full signature that is verifiable using `PublicKey.schnorr_verify`. `privnonce` is the second item in the tuple returned by `schnorr_generate_nonce_pair`, `pubnonce_others` represent the combined public nonces excluding the one associated to this `privnonce`. `msg`, `raw`, and `digest` are used as described in `ecdsa_sign`.<br/><br/>
To combine pubnonces, use `PublicKey.combine`.<br/><br/>
Do not pass the pubnonce produced for the respective privnonce; combine the pubnonces from other signers and pass that instead.


#### class `coincurve.PublicKey(pubkey, raw, flags)`

The `PublicKey` class loads an existing public key and operates over it.

##### Instantiation parameters

- `pubkey=None` - do not load a public key if None, otherwise do.
- `raw=False` - if `False`, it is assumed that `pubkey` has gone through `PublicKey.deserialize` already, otherwise it must be specified as bytes.
- `flags=coincurve.FLAG_VERIFY` - see Constants.

##### Methods and instance attributes

- `public_key`: an internal object representing the public key.

- `serialize(compressed=True)` -> bytes<br/>
convert the `public_key` to bytes. If `compressed` is True, 33 bytes will be produced, otherwise 65 will be.

- `deserialize(pubkey_ser)` -> internal object<br/>
convert the bytes resulting from a previous `serialize` call back to an internal object and update the `public_key` for this instance. The length of `pubkey_ser` determines if it was serialized with `compressed=True` or not. This will raise an Exception if the size is invalid or if the key is invalid.

- `combine(pubkeys)` -> internal object<br/>
combine multiple public keys (those returned from `PublicKey.deserialize`) and return a public key (which can be serialized as any other regular public key). The `public_key` for this instance is updated to use the resulting combined key. If it is not possible the combine the keys, an Exception is raised.

- `tweak_add(scalar)` -> internal object<br/>
tweak the current public key by adding a 32 byte scalar times the generator to it and return a new PublicKey instance.

- `tweak_mul(scalar)` -> internal object<br/>
tweak the current public key by multiplying it by a 32 byte scalar and return a new PublicKey instance.

- `ecdsa_verify(msg, raw_sig, raw=False, digest=hashlib.sha256)` -> bool<br/>
verify an ECDSA signature and return True if the signature is correct, False otherwise. `raw_sig` is expected to be an object returned from `ecdsa_sign` (or if it was serialized using `ecdsa_serialize`, then first run it through `ecdsa_deserialize`). `msg`, `raw`, and `digest` are used as described in `ecdsa_sign`.

- `schnorr_verify(msg, schnorr_sig, raw=False, digest=hashlib.sha256)` -> bool<br/>
verify a Schnorr signature and return True if the signature is correct, False otherwise. `schnorr_sig` is expected to be the result from either `schnorr_partial_combine` or `schnorr_sign`. `msg`, `raw`, and `digest` are used as described in `ecdsa_sign`.

- `ecdh(scalar)` -> bytes<br/>
compute an EC Diffie-Hellman secret in constant time. The instance `public_key` is used as the public point, and the `scalar` specified must be composed of 32 bytes. It outputs 32 bytes representing the ECDH secret computed. If the `scalar` is invalid, an Exception is raised.

> NOTE: `ecdh` can only be used if the `secp256k1` C library is compiled with support for it. If there is no support, an Exception will be raised when calling it.


#### class `coincurve.ECDSA`

The `ECDSA` class is intended to be used as a mix in. Its methods can be accessed from any `coincurve.PrivateKey` or `coincurve.PublicKey` instances.

##### Methods

- `ecdsa_serialize(raw_sig)` -> bytes<br/>
convert the result from `ecdsa_sign` to DER.

- `ecdsa_deserialie(ser_sig)` -> internal object<br/>
convert DER bytes to an internal object.

- `ecdsa_serialize_compact(raw_sig)` -> bytes<br/>
convert the result from `ecdsa_sign` to a compact serialization of 64 bytes.

- `ecdsa_deserialize_compact(ser_sig)` -> internal object<br/>
convert a compact serialization of 64 bytes to an internal object.

- `ecdsa_signature_normalize(raw_sig, check_only=False)` -> (bool, internal object | None)<br/>
check and optionally convert a signature to a normalized lower-S form. If `check_only` is True then the normalized signature is not returned.<br/><br/>
This function always return a tuple containing a boolean (True if not previously normalized or False if signature was already normalized), and the normalized signature. When `check_only` is True, the normalized signature returned is always None.

- `ecdsa_recover(msg, recover_sig, raw=False, digest=hashlib.sha256)` -> internal object<br/>
recover an ECDSA public key from a signature generated by `ecdsa_sign_recoverable`. `recover_sig` is expected to be an object returned from `ecdsa_sign_recoverable` (or if it was serialized using `ecdsa_recoverable_serialize`, then first run it through `ecdsa_recoverable_deserialize`). `msg`, `raw`, and `digest` are used as described in `ecdsa_sign`.<br/><br/>
In order to call `ecdsa_recover` from a `PublicKey` instance, it's necessary to create the instance by settings `flags` to `ALL_FLAGS`: `coincurve.PublicKey(..., flags=coincurve.ALL_FLAGS)`.

- `ecdsa_recoverable_serialize(recover_sig)` -> (bytes, int)<br/>
convert the result from `ecdsa_sign_recoverable` to a tuple composed of 65 bytesand an integer denominated as recovery id.

- `ecdsa_recoverable_deserialize(ser_sig, rec_id)`-> internal object<br/>
convert the result from `ecdsa_recoverable_serialize` back to an internal object that can be used by `ecdsa_recover`.

- `ecdsa_recoverable_convert(recover_sig)` -> internal object<br/>
convert a recoverable signature to a normal signature, i.e. one that can be used by `ecdsa_serialize` and related methods.

> NOTE: `ecdsa_recover*` can only be used if the `secp256k1` C library is compiled with support for it. If there is no support, an Exception will be raised when calling any of them.


#### Constants

##### `coincurve.FLAG_SIGN`
##### `coincurve.FLAG_VERIFY`
##### `coincurve.ALL_FLAGS`

`ALL_FLAGS` combines `FLAG_SIGN` and `FLAG_VERIFY` using bitwise OR.

These flags are used during context creation (undocumented here) and affect which parts of the context are initialized in the C library. In these bindings, some calls are disabled depending on the active flags but this should not be noticeable unless you are manually specifying flags.



## Example

```python
from coincurve import PrivateKey, PublicKey

privkey = PrivateKey()
privkey_der = privkey.serialize()
assert privkey.deserialize(privkey_der) == privkey.private_key

sig = privkey.ecdsa_sign(b'hello')
verified = privkey.pubkey.ecdsa_verify(b'hello', sig)
assert verified

sig_der = privkey.ecdsa_serialize(sig)
sig2 = privkey.ecdsa_deserialize(sig_der)
vrf2 = privkey.pubkey.ecdsa_verify(b'hello', sig2)
assert vrf2

pubkey = privkey.pubkey
pub = pubkey.serialize()

pubkey2 = PublicKey(pub, raw=True)
assert pubkey2.serialize() == pub
assert pubkey2.ecdsa_verify(b'hello', sig)
```

```python
from coincurve import PrivateKey

key = '31a84594060e103f5a63eb742bd46cf5f5900d8406e2726dedfc61c7cf43ebad'
msg = '9e5755ec2f328cc8635a55415d0e9a09c2b6f2c9b0343c945fbbfe08247a4cbe'
sig = '30440220132382ca59240c2e14ee7ff61d90fc63276325f4cbe8169fc53ade4a407c2fc802204d86fbe3bde6975dd5a91fdc95ad6544dcdf0dab206f02224ce7e2b151bd82ab'

privkey = PrivateKey(bytes(bytearray.fromhex(key)), raw=True)
sig_check = privkey.ecdsa_sign(bytes(bytearray.fromhex(msg)), raw=True)
sig_ser = privkey.ecdsa_serialize(sig_check)

assert sig_ser == bytes(bytearray.fromhex(sig))
```

```python
from coincurve import PrivateKey

key = '7ccca75d019dbae79ac4266501578684ee64eeb3c9212105f7a3bdc0ddb0f27e'
pub_compressed = '03e9a06e539d6bf5cf1ca5c41b59121fa3df07a338322405a312c67b6349a707e9'
pub_uncompressed = '04e9a06e539d6bf5cf1ca5c41b59121fa3df07a338322405a312c67b6349a707e94c181c5fe89306493dd5677143a329065606740ee58b873e01642228a09ecf9d'

privkey = PrivateKey(bytes(bytearray.fromhex(key)))
pubkey_ser = privkey.pubkey.serialize()
pubkey_ser_uncompressed = privkey.pubkey.serialize(compressed=False)

assert pubkey_ser == bytes(bytearray.fromhex(pub_compressed))
assert pubkey_ser_uncompressed == bytes(bytearray.fromhex(pub_uncompressed))
```
