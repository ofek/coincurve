typedef struct secp256k1_context_struct secp256k1_context;

typedef struct {
    unsigned char data[64];
} secp256k1_pubkey;

typedef struct {
    unsigned char data[64];
} secp256k1_ecdsa_signature;

typedef int (*secp256k1_nonce_function)(
    unsigned char *nonce32,
    const unsigned char *msg32,
    const unsigned char *key32,
    const unsigned char *algo16,
    void *data,
    unsigned int attempt
);

#define SECP256K1_FLAGS_TYPE_MASK ...
#define SECP256K1_FLAGS_TYPE_CONTEXT ...
#define SECP256K1_FLAGS_TYPE_COMPRESSION ...
#define SECP256K1_FLAGS_BIT_CONTEXT_VERIFY ...
#define SECP256K1_FLAGS_BIT_CONTEXT_SIGN ...
#define SECP256K1_FLAGS_BIT_COMPRESSION ...

#define SECP256K1_CONTEXT_VERIFY ...
#define SECP256K1_CONTEXT_SIGN ...
#define SECP256K1_CONTEXT_NONE ...

#define SECP256K1_EC_COMPRESSED ...
#define SECP256K1_EC_UNCOMPRESSED ...

secp256k1_context* secp256k1_context_create(
    unsigned int flags
);

secp256k1_context* secp256k1_context_clone(
    const secp256k1_context* ctx
);

void secp256k1_context_destroy(
    secp256k1_context* ctx
);

void secp256k1_context_set_illegal_callback(
    secp256k1_context* ctx,
    void (*fun)(const char* message, void* data),
    const void* data
);

void secp256k1_context_set_error_callback(
    secp256k1_context* ctx,
    void (*fun)(const char* message, void* data),
    const void* data
);

int secp256k1_ec_pubkey_parse(
    const secp256k1_context* ctx,
    secp256k1_pubkey* pubkey,
    const unsigned char *input,
    size_t inputlen
);

int secp256k1_ec_pubkey_serialize(
    const secp256k1_context* ctx,
    unsigned char *output,
    size_t *outputlen,
    const secp256k1_pubkey* pubkey,
    unsigned int flags
);

int secp256k1_ecdsa_signature_parse_compact(
    const secp256k1_context* ctx,
    secp256k1_ecdsa_signature* sig,
    const unsigned char *input64
);

int secp256k1_ecdsa_signature_parse_der(
    const secp256k1_context* ctx,
    secp256k1_ecdsa_signature* sig,
    const unsigned char *input,
    size_t inputlen
);

int secp256k1_ecdsa_signature_serialize_der(
    const secp256k1_context* ctx,
    unsigned char *output,
    size_t *outputlen,
    const secp256k1_ecdsa_signature* sig
);

int secp256k1_ecdsa_signature_serialize_compact(
    const secp256k1_context* ctx,
    unsigned char *output64,
    const secp256k1_ecdsa_signature* sig
);

int secp256k1_ecdsa_verify(
    const secp256k1_context* ctx,
    const secp256k1_ecdsa_signature *sig,
    const unsigned char *msg32,
    const secp256k1_pubkey *pubkey
);

int secp256k1_ecdsa_signature_normalize(
    const secp256k1_context* ctx,
    secp256k1_ecdsa_signature *sigout,
    const secp256k1_ecdsa_signature *sigin
);

extern const secp256k1_nonce_function secp256k1_nonce_function_rfc6979;

extern const secp256k1_nonce_function secp256k1_nonce_function_default;

int secp256k1_ecdsa_sign(
    const secp256k1_context* ctx,
    secp256k1_ecdsa_signature *sig,
    const unsigned char *msg32,
    const unsigned char *seckey,
    secp256k1_nonce_function noncefp,
    const void *ndata
);

int secp256k1_ec_seckey_verify(
    const secp256k1_context* ctx,
    const unsigned char *seckey
);

int secp256k1_ec_pubkey_create(
    const secp256k1_context* ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *seckey
);

int secp256k1_ec_privkey_tweak_add(
    const secp256k1_context* ctx,
    unsigned char *seckey,
    const unsigned char *tweak
);

int secp256k1_ec_pubkey_tweak_add(
    const secp256k1_context* ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *tweak
);

int secp256k1_ec_privkey_tweak_mul(
    const secp256k1_context* ctx,
    unsigned char *seckey,
    const unsigned char *tweak
);

int secp256k1_ec_pubkey_tweak_mul(
    const secp256k1_context* ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *tweak
);

int secp256k1_context_randomize(
    secp256k1_context* ctx,
    const unsigned char *seed32
);

int secp256k1_ec_pubkey_combine(
    const secp256k1_context* ctx,
    secp256k1_pubkey *out,
    const secp256k1_pubkey * const * ins,
    size_t n
);
