typedef int (*secp256k1_ecdh_hash_function)(
  unsigned char *output,
  const unsigned char *x32,
  const unsigned char *y32,
  void *data
);

const secp256k1_ecdh_hash_function secp256k1_ecdh_hash_function_sha256;

const secp256k1_ecdh_hash_function secp256k1_ecdh_hash_function_default;

int secp256k1_ecdh(
  const secp256k1_context* ctx,
  unsigned char *result,
  const secp256k1_pubkey *pubkey,
  const unsigned char *privkey,
  secp256k1_ecdh_hash_function hashfp,
  void *data
);
