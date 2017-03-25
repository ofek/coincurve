typedef struct {
    unsigned char data[65];
} secp256k1_ecdsa_recoverable_signature;

int secp256k1_ecdsa_recoverable_signature_parse_compact(
    const secp256k1_context* ctx,
    secp256k1_ecdsa_recoverable_signature* sig,
    const unsigned char *input64,
    int recid
);

int secp256k1_ecdsa_recoverable_signature_convert(
    const secp256k1_context* ctx,
    secp256k1_ecdsa_signature* sig,
    const secp256k1_ecdsa_recoverable_signature* sigin
);

int secp256k1_ecdsa_recoverable_signature_serialize_compact(
    const secp256k1_context* ctx,
    unsigned char *output64,
    int *recid,
    const secp256k1_ecdsa_recoverable_signature* sig
);

int secp256k1_ecdsa_sign_recoverable(
    const secp256k1_context* ctx,
    secp256k1_ecdsa_recoverable_signature *sig,
    const unsigned char *msg32,
    const unsigned char *seckey,
    secp256k1_nonce_function noncefp,
    const void *ndata
);

int secp256k1_ecdsa_recover(
    const secp256k1_context* ctx,
    secp256k1_pubkey *pubkey,
    const secp256k1_ecdsa_recoverable_signature *sig,
    const unsigned char *msg32
);
