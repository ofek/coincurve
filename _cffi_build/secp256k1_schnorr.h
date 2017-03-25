int secp256k1_schnorr_sign(
  const secp256k1_context* ctx,
  unsigned char *sig64,
  const unsigned char *msg32,
  const unsigned char *seckey,
  secp256k1_nonce_function noncefp,
  const void *ndata
);

int secp256k1_schnorr_verify(
  const secp256k1_context* ctx,
  const unsigned char *sig64,
  const unsigned char *msg32,
  const secp256k1_pubkey *pubkey
);

int secp256k1_schnorr_recover(
  const secp256k1_context* ctx,
  secp256k1_pubkey *pubkey,
  const unsigned char *sig64,
  const unsigned char *msg32
);

int secp256k1_schnorr_generate_nonce_pair(
  const secp256k1_context* ctx,
  secp256k1_pubkey *pubnonce,
  unsigned char *privnonce32,
  const unsigned char *msg32,
  const unsigned char *sec32,
  secp256k1_nonce_function noncefp,
  const void* noncedata
);

int secp256k1_schnorr_partial_sign(
  const secp256k1_context* ctx,
  unsigned char *sig64,
  const unsigned char *msg32,
  const unsigned char *sec32,
  const secp256k1_pubkey *pubnonce_others,
  const unsigned char *secnonce32
);

int secp256k1_schnorr_partial_combine(
  const secp256k1_context* ctx,
  unsigned char *sig64,
  const unsigned char * const * sig64sin,
  size_t n
);
