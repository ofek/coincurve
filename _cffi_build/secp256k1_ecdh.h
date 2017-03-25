int secp256k1_ecdh(
  const secp256k1_context* ctx,
  unsigned char *result,
  const secp256k1_pubkey *pubkey,
  const unsigned char *privkey
);
