typedef int (*secp256k1_ellswift_xdh_hash_function)(
    unsigned char *output,
    const unsigned char *x32,
    const unsigned char *ell_a64,
    const unsigned char *ell_b64,
    void *data
);

const secp256k1_ellswift_xdh_hash_function secp256k1_ellswift_xdh_hash_function_prefix;

const secp256k1_ellswift_xdh_hash_function secp256k1_ellswift_xdh_hash_function_bip324;

int secp256k1_ellswift_encode(
    const secp256k1_context *ctx,
    unsigned char *ell64,
    const secp256k1_pubkey *pubkey,
    const unsigned char *rnd32
);

int secp256k1_ellswift_decode(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *ell64
);

int secp256k1_ellswift_xdh(
    const secp256k1_context *ctx,
    unsigned char *result,
    const secp256k1_pubkey *pubkey,
    const unsigned char *privkey,
    secp256k1_ellswift_xdh_hash_function hashfp,
    void *data
);
