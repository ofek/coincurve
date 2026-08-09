#ifndef COINCURVE_H
#define COINCURVE_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stddef.h>
#include <stdint.h>

#include <secp256k1.h>
#include <secp256k1_ecdh.h>
#include <secp256k1_extrakeys.h>
#include <secp256k1_recovery.h>
#include <secp256k1_schnorrsig.h>

#define CC_SECRET_SIZE 32
#define CC_DIGEST_SIZE 32
#define CC_PUBLIC_KEY_COMPRESSED_SIZE 33
#define CC_PUBLIC_KEY_UNCOMPRESSED_SIZE 65
#define CC_XONLY_PUBLIC_KEY_SIZE 32
#define CC_COMPACT_SIGNATURE_SIZE 64
#define CC_RECOVERABLE_SIGNATURE_SIZE 65
#define CC_MAX_DER_SIGNATURE_SIZE 72

typedef struct {
    secp256k1_context *context;
    PyObject *private_key_type;
    PyObject *public_key_type;
    PyObject *xonly_public_key_type;
    PyObject *default_hasher;
    PyObject *urandom;
} CoincurveState;

typedef struct {
    PyObject_HEAD unsigned char secret[CC_SECRET_SIZE];
    secp256k1_keypair keypair;
    PyObject *public_key;
    PyObject *xonly_public_key;
} PrivateKeyObject;

typedef struct {
    PyObject_HEAD secp256k1_pubkey public_key;
    unsigned char compressed[CC_PUBLIC_KEY_COMPRESSED_SIZE];
} PublicKeyObject;

typedef struct {
    PyObject_HEAD secp256k1_xonly_pubkey public_key;
    unsigned char serialized[CC_XONLY_PUBLIC_KEY_SIZE];
    int parity;
} XOnlyPublicKeyObject;

typedef struct {
    Py_buffer view;
    int acquired;
} CoincurveBuffer;

CoincurveState *cc_state_from_module(PyObject *module);
CoincurveState *cc_state_from_type(PyTypeObject *type);
CoincurveState *cc_state_from_object(PyObject *object);

int cc_parse_fastcall(
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames,
    const char *function_name,
    const char *const *parameter_names,
    Py_ssize_t parameter_count,
    Py_ssize_t positional_limit,
    PyObject **values
);
int cc_get_buffer(PyObject *object, CoincurveBuffer *buffer, const char *name);
int cc_get_buffer_item(
    PyObject *object,
    CoincurveBuffer *buffer,
    const char *name,
    Py_ssize_t index
);
void cc_release_buffer(CoincurveBuffer *buffer);
int cc_copy_fixed(PyObject *object, unsigned char *output, Py_ssize_t size, const char *name);
int cc_copy_scalar(PyObject *object, unsigned char output[CC_SECRET_SIZE], const char *name);
int cc_copy_fixed_item(
    PyObject *object,
    unsigned char *output,
    Py_ssize_t size,
    const char *name,
    Py_ssize_t index
);
int cc_copy_optional_fixed(
    PyObject *object,
    unsigned char *output,
    Py_ssize_t size,
    const unsigned char **result,
    const char *name
);
int cc_hash_message(
    CoincurveState *state,
    PyObject *message,
    PyObject *hasher,
    unsigned char digest[CC_DIGEST_SIZE]
);
int cc_random_bytes(CoincurveState *state, unsigned char *output, Py_ssize_t size);
void cc_secure_zero(void *memory, size_t size);
PyObject *cc_bytes_from_data(const unsigned char *data, Py_ssize_t size);
Py_hash_t cc_hash_data(const unsigned char *data, Py_ssize_t size);
PyObject *cc_hex_from_data(const unsigned char *data, Py_ssize_t size);
PyObject *cc_hex_repr(PyObject *self, const unsigned char *data, Py_ssize_t size);
PyObject *
cc_richcompare_fixed(PyObject *left, PyObject *right, int operation, size_t offset, size_t size);
PyObject *cc_integer_from_bytes(const unsigned char *data, Py_ssize_t size);
PyObject *cc_integer_to_32_bytes(PyObject *integer, const char *name);

int cc_xonly_from_secret(
    const secp256k1_context *context,
    secp256k1_xonly_pubkey *public_key,
    int *parity,
    const unsigned char secret[CC_SECRET_SIZE]
);
int cc_ecdsa_sign_der(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    const unsigned char *extra_entropy,
    unsigned char output[CC_MAX_DER_SIGNATURE_SIZE],
    size_t *output_size
);
int cc_ecdsa_sign_compact(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    const unsigned char *extra_entropy,
    unsigned char output[CC_COMPACT_SIGNATURE_SIZE]
);
int cc_ecdsa_sign_recoverable(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    const unsigned char *extra_entropy,
    unsigned char output[CC_RECOVERABLE_SIGNATURE_SIZE]
);
int cc_ecdsa_verify_der(
    const secp256k1_context *context,
    const secp256k1_pubkey *public_key,
    const unsigned char *signature,
    size_t signature_size,
    const unsigned char digest[CC_DIGEST_SIZE]
);
int cc_copy_der_signature(
    PyObject *object,
    unsigned char output[CC_MAX_DER_SIGNATURE_SIZE],
    size_t *size
);
int cc_copy_schnorr_signature(PyObject *object, unsigned char output[CC_COMPACT_SIGNATURE_SIZE]);
PyObject *cc_verify_der_signature(
    CoincurveState *state,
    const secp256k1_pubkey *public_key,
    PyObject *signature_object,
    const unsigned char digest[CC_DIGEST_SIZE]
);
int cc_ecdsa_verify_compact(
    const secp256k1_context *context,
    const secp256k1_pubkey *public_key,
    const unsigned char signature[CC_COMPACT_SIGNATURE_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE]
);
int cc_ecdsa_recover(
    const secp256k1_context *context,
    const unsigned char signature[CC_RECOVERABLE_SIGNATURE_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    secp256k1_pubkey *public_key
);
int cc_schnorr_verify(
    const secp256k1_context *context,
    const secp256k1_xonly_pubkey *public_key,
    const unsigned char signature[CC_COMPACT_SIGNATURE_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE]
);
int cc_ecdh(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const secp256k1_pubkey *public_key,
    unsigned char output[CC_DIGEST_SIZE]
);

PyObject *cc_public_key_from_native(PyTypeObject *type, const secp256k1_pubkey *public_key);
int cc_serialize_compressed(
    const secp256k1_context *context,
    const secp256k1_pubkey *public_key,
    unsigned char output[CC_PUBLIC_KEY_COMPRESSED_SIZE]
);
PyObject *cc_xonly_public_key_from_native(
    PyTypeObject *type,
    const secp256k1_xonly_pubkey *public_key,
    int parity
);
int cc_public_key_from_object(
    CoincurveState *state,
    PyObject *object,
    secp256k1_pubkey *public_key,
    const char *name
);

PyObject *cc_create_private_key_type(PyObject *module);
PyObject *cc_create_public_key_type(PyObject *module);
PyObject *cc_create_xonly_public_key_type(PyObject *module);
int cc_add_signature_functions(PyObject *module);
int cc_add_batch_functions(PyObject *module);

PyObject *cc_private_key_sign_many(PrivateKeyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *
cc_private_key_sign_digests(PrivateKeyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *
cc_private_key_sign_recoverable_many(PrivateKeyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *cc_private_key_sign_recoverable_digests(
    PrivateKeyObject *,
    PyObject *const *,
    Py_ssize_t,
    PyObject *
);
PyObject *
cc_private_key_sign_schnorr_many(PrivateKeyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *
cc_private_key_sign_schnorr_digests(PrivateKeyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *cc_private_key_ecdh_many(PrivateKeyObject *, PyObject *);
PyObject *cc_public_key_verify_many(PyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *cc_public_key_verify_digests(PyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *cc_xonly_public_key_verify_many(PyObject *, PyObject *const *, Py_ssize_t, PyObject *);
PyObject *cc_xonly_public_key_verify_digests(PyObject *, PyObject *const *, Py_ssize_t, PyObject *);

#endif
