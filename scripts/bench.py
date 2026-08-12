# /// script
# dependencies = [
#   "coincurve",
#   "pyperf>=2.9",
# ]
# [tool.uv.sources]
# coincurve = { path = ".." }
# ///
from __future__ import annotations

from hashlib import sha256

import pyperf

from coincurve import PrivateKey, PublicKey, batch, verify_signature_digest
from coincurve.batch import packed

LIBSECP256K1_COMMIT = "0cdc758a56360bf58a851fe91085a327ec97685a"
SECRET = bytes.fromhex("00" * 31 + "01")
PEER_SECRET = bytes.fromhex("00" * 31 + "02")
DIGEST = sha256(b"binding overhead").digest()
MESSAGE = b"binding overhead"
PRIVATE_KEY = PrivateKey(SECRET)
PUBLIC_KEY = PRIVATE_KEY.public_key
XONLY_PUBLIC_KEY = PRIVATE_KEY.xonly_public_key
PEER_PUBLIC_KEY = PrivateKey(PEER_SECRET).public_key
PEER_PUBLIC_KEY_BYTES = bytes(PEER_PUBLIC_KEY)
ECDSA_SIGNATURE = PRIVATE_KEY.sign_digest(DIGEST)
RECOVERABLE_SIGNATURE = PRIVATE_KEY.sign_recoverable_digest(DIGEST)
SCHNORR_SIGNATURE = PRIVATE_KEY.sign_schnorr_digest(DIGEST, aux_randomness=bytes(32))
PUBLIC_KEY_BYTES = bytes(PUBLIC_KEY)
PRIVATE_KEY_DER = PRIVATE_KEY.to_der()
PRIVATE_KEY_PEM = PRIVATE_KEY.to_pem()
TWEAK = PEER_SECRET
BATCH_SIZES = (1, 16, 256, 4096)


def benchmark_scalar(runner: pyperf.Runner) -> None:
    runner.bench_func("hash_sha256", lambda: sha256(MESSAGE).digest())
    runner.bench_func("private_key_from_fixed_secret", lambda: PrivateKey(SECRET))
    runner.bench_func("private_key_random", PrivateKey)
    runner.bench_func("ecdsa_sign_digest", lambda: PRIVATE_KEY.sign_digest(DIGEST))
    runner.bench_func("ecdsa_sign_message", lambda: PRIVATE_KEY.sign(MESSAGE))
    runner.bench_func("ecdsa_verify_cached", lambda: PUBLIC_KEY.verify_digest(ECDSA_SIGNATURE, DIGEST))
    runner.bench_func(
        "ecdsa_verify_serialized",
        lambda: verify_signature_digest(ECDSA_SIGNATURE, DIGEST, PUBLIC_KEY_BYTES),
    )
    runner.bench_func("recoverable_sign_digest", lambda: PRIVATE_KEY.sign_recoverable_digest(DIGEST))
    runner.bench_func("recover_public_key", lambda: PublicKey.recover_digest(RECOVERABLE_SIGNATURE, DIGEST))
    runner.bench_func(
        "schnorr_sign_digest",
        lambda: PRIVATE_KEY.sign_schnorr_digest(DIGEST, aux_randomness=bytes(32)),
    )
    runner.bench_func(
        "schnorr_verify_digest",
        lambda: XONLY_PUBLIC_KEY.verify_digest(SCHNORR_SIGNATURE, DIGEST),
    )
    runner.bench_func("ecdh", lambda: PRIVATE_KEY.ecdh(PEER_PUBLIC_KEY_BYTES))
    runner.bench_func("public_key_parse", lambda: PublicKey(PUBLIC_KEY_BYTES))
    runner.bench_func("public_key_serialize_compressed", lambda: bytes(PUBLIC_KEY))
    runner.bench_func("public_key_serialize_uncompressed", lambda: PUBLIC_KEY.format(compressed=False))
    runner.bench_func("private_key_tweak_add", lambda: PRIVATE_KEY.add(TWEAK))
    runner.bench_func("public_key_tweak_add", lambda: PUBLIC_KEY.add(TWEAK))
    runner.bench_func("private_key_to_der", PRIVATE_KEY.to_der)
    runner.bench_func("private_key_from_der", lambda: PrivateKey.from_der(PRIVATE_KEY_DER))
    runner.bench_func("private_key_to_pem", PRIVATE_KEY.to_pem)
    runner.bench_func("private_key_from_pem", lambda: PrivateKey.from_pem(PRIVATE_KEY_PEM))


def benchmark_batches(runner: pyperf.Runner) -> None:
    for size in BATCH_SIZES:
        digests = [DIGEST] * size
        keys = [PRIVATE_KEY] * size
        public_keys = [PUBLIC_KEY] * size
        signatures = [ECDSA_SIGNATURE] * size
        packed_secrets = SECRET * size
        packed_digests = DIGEST * size
        packed_public_keys = PUBLIC_KEY_BYTES * size
        packed_signatures = packed.sign_ecdsa_digests(packed_secrets, packed_digests)[0]
        runner.bench_func(
            f"ecdsa_sign_scalar_loop_{size}",
            lambda digests=digests: [PRIVATE_KEY.sign_digest(digest) for digest in digests],
        )
        runner.bench_func(
            f"ecdsa_sign_same_key_batch_{size}",
            lambda digests=digests: PRIVATE_KEY.sign_digests(digests),
        )
        runner.bench_func(
            f"ecdsa_sign_pairwise_batch_{size}",
            lambda keys=keys, digests=digests: batch.sign_digests(keys, digests),
        )
        runner.bench_func(
            f"ecdsa_sign_packed_batch_{size}",
            lambda secrets=packed_secrets, digests=packed_digests: packed.sign_ecdsa_digests(secrets, digests),
        )
        runner.bench_func(
            f"ecdsa_verify_scalar_loop_{size}",
            lambda signatures=signatures, digests=digests: [
                PUBLIC_KEY.verify_digest(signature, digest)
                for signature, digest in zip(signatures, digests, strict=True)
            ],
        )
        runner.bench_func(
            f"ecdsa_verify_pairwise_batch_{size}",
            lambda public_keys=public_keys, signatures=signatures, digests=digests: batch.verify_digests(
                public_keys, signatures, digests
            ),
        )
        runner.bench_func(
            f"ecdsa_verify_packed_batch_{size}",
            lambda public_keys=packed_public_keys, signatures=packed_signatures, digests=packed_digests: (
                packed.verify_ecdsa_digests(public_keys, signatures, digests)
            ),
        )


def main() -> None:
    runner = pyperf.Runner()
    runner.metadata["implementation"] = "handwritten CPython extension"
    runner.metadata["libsecp256k1_commit"] = LIBSECP256K1_COMMIT
    benchmark_scalar(runner)
    benchmark_batches(runner)


if __name__ == "__main__":
    main()
