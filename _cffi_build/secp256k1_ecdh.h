typedef int (*secp256k1_ecdh_hash_function)(
  unsigned char *output,
  const unsigned char *x32,
  const unsigned char *y32,
  void *data
);
extern const secp256k1_ecdh_hash_function secp256k1_ecdh_hash_function_sha256;
extern const secp256k1_ecdh_hash_function secp256k1_ecdh_hash_function_default;
extern int secp256k1_ecdh(
  const secp256k1_context *ctx,
  unsigned char *output,
  const secp256k1_pubkey *pubkey,
  const unsigned char *seckey,
  secp256k1_ecdh_hash_function hashfp,
  void *data
) ;
