from __future__ import annotations

from hashlib import sha256

import pyperf

from coincurve import PrivateKey, PublicKey
from coincurve.utils import verify_signature

BASELINE_COMMIT = "2d11b1160c75ae8fd94fe8fe3f226aec176bf9bf"
SECRET = bytes.fromhex("00" * 31 + "01")
PEER_SECRET = bytes.fromhex("00" * 31 + "02")
DIGEST = sha256(b"binding overhead").digest()
MESSAGE = b"binding overhead"
PRIVATE_KEY = PrivateKey(SECRET)
PUBLIC_KEY = PRIVATE_KEY.public_key
XONLY_PUBLIC_KEY = PRIVATE_KEY.public_key_xonly
PEER_PUBLIC_KEY = PrivateKey(PEER_SECRET).public_key
PEER_PUBLIC_KEY_BYTES = PEER_PUBLIC_KEY.format()
ECDSA_SIGNATURE = PRIVATE_KEY.sign(DIGEST, hasher=None)
RECOVERABLE_SIGNATURE = PRIVATE_KEY.sign_recoverable(DIGEST, hasher=None)
SCHNORR_SIGNATURE = PRIVATE_KEY.sign_schnorr(DIGEST, aux_randomness=bytes(32))
PUBLIC_KEY_BYTES = PUBLIC_KEY.format()
PRIVATE_KEY_DER = PRIVATE_KEY.to_der()
PRIVATE_KEY_PEM = PRIVATE_KEY.to_pem()
TWEAK = PEER_SECRET


def main() -> None:
    runner = pyperf.Runner()
    runner.metadata["implementation"] = "CFFI"
    runner.metadata["source_commit"] = BASELINE_COMMIT
    runner.bench_func("hash_sha256", lambda: sha256(MESSAGE).digest())
    runner.bench_func("private_key_from_fixed_secret", lambda: PrivateKey(SECRET))
    runner.bench_func("private_key_random", PrivateKey)
    runner.bench_func("ecdsa_sign_digest", lambda: PRIVATE_KEY.sign(DIGEST, hasher=None))
    runner.bench_func("ecdsa_sign_message", lambda: PRIVATE_KEY.sign(MESSAGE))
    runner.bench_func("ecdsa_verify_cached", lambda: PUBLIC_KEY.verify(ECDSA_SIGNATURE, DIGEST, hasher=None))
    runner.bench_func(
        "ecdsa_verify_serialized",
        lambda: verify_signature(ECDSA_SIGNATURE, DIGEST, PUBLIC_KEY_BYTES, hasher=None),
    )
    runner.bench_func("recoverable_sign_digest", lambda: PRIVATE_KEY.sign_recoverable(DIGEST, hasher=None))
    runner.bench_func(
        "recover_public_key",
        lambda: PublicKey.from_signature_and_message(RECOVERABLE_SIGNATURE, DIGEST, hasher=None),
    )
    runner.bench_func(
        "schnorr_sign_digest",
        lambda: PRIVATE_KEY.sign_schnorr(DIGEST, aux_randomness=bytes(32)),
    )
    runner.bench_func(
        "schnorr_verify_digest",
        lambda: XONLY_PUBLIC_KEY.verify(SCHNORR_SIGNATURE, DIGEST),
    )
    runner.bench_func("ecdh", lambda: PRIVATE_KEY.ecdh(PEER_PUBLIC_KEY_BYTES))
    runner.bench_func("public_key_parse", lambda: PublicKey(PUBLIC_KEY_BYTES))
    runner.bench_func("public_key_serialize_compressed", PUBLIC_KEY.format)
    runner.bench_func("public_key_serialize_uncompressed", lambda: PUBLIC_KEY.format(compressed=False))
    runner.bench_func("private_key_tweak_add", lambda: PRIVATE_KEY.add(TWEAK))
    runner.bench_func("public_key_tweak_add", lambda: PUBLIC_KEY.add(TWEAK))
    runner.bench_func("private_key_to_der", PRIVATE_KEY.to_der)
    runner.bench_func("private_key_from_der", lambda: PrivateKey.from_der(PRIVATE_KEY_DER))
    runner.bench_func("private_key_to_pem", PRIVATE_KEY.to_pem)
    runner.bench_func("private_key_from_pem", lambda: PrivateKey.from_pem(PRIVATE_KEY_PEM))


if __name__ == "__main__":
    main()
