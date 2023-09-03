size_t secp256k1_context_preallocated_size(
    unsigned int flags
);

secp256k1_context* secp256k1_context_preallocated_create(
    void* prealloc,
    unsigned int flags
);

size_t secp256k1_context_preallocated_clone_size(
    const secp256k1_context *ctx
);

void secp256k1_context_preallocated_destroy(
    secp256k1_context* ctx
);
