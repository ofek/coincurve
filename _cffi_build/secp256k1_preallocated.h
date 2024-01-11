extern size_t secp256k1_context_preallocated_size(
    unsigned int flags
) ;
extern secp256k1_context *secp256k1_context_preallocated_create(
    void *prealloc,
    unsigned int flags
) ;
extern size_t secp256k1_context_preallocated_clone_size(
    const secp256k1_context *ctx
) ;
extern secp256k1_context *secp256k1_context_preallocated_clone(
    const secp256k1_context *ctx,
    void *prealloc
) ;
extern void secp256k1_context_preallocated_destroy(
    secp256k1_context *ctx
) ;
