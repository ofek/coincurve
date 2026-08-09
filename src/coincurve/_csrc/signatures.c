#include "coincurve.h"

#include <string.h>

int cc_xonly_from_secret(
    const secp256k1_context *context,
    secp256k1_xonly_pubkey *public_key,
    int *parity,
    const unsigned char secret[CC_SECRET_SIZE]
)
{
    secp256k1_keypair keypair;
    int result = secp256k1_keypair_create(context, &keypair, secret) &&
                 secp256k1_keypair_xonly_pub(context, public_key, parity, &keypair);

    cc_secure_zero(&keypair, sizeof(keypair));
    return result;
}

int cc_ecdsa_sign_der(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    const unsigned char *extra_entropy,
    unsigned char output[CC_MAX_DER_SIGNATURE_SIZE],
    size_t *output_size
)
{
    secp256k1_ecdsa_signature signature;
    int result = secp256k1_ecdsa_sign(
        context,
        &signature,
        digest,
        secret,
        secp256k1_nonce_function_rfc6979,
        extra_entropy
    );
    if (result) {
        *output_size = CC_MAX_DER_SIGNATURE_SIZE;
        result = secp256k1_ecdsa_signature_serialize_der(context, output, output_size, &signature);
    }
    cc_secure_zero(&signature, sizeof(signature));
    return result;
}

int cc_ecdsa_sign_compact(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    const unsigned char *extra_entropy,
    unsigned char output[CC_COMPACT_SIGNATURE_SIZE]
)
{
    secp256k1_ecdsa_signature signature;
    int result = secp256k1_ecdsa_sign(
        context,
        &signature,
        digest,
        secret,
        secp256k1_nonce_function_rfc6979,
        extra_entropy
    );
    if (result) {
        result = secp256k1_ecdsa_signature_serialize_compact(context, output, &signature);
    }
    cc_secure_zero(&signature, sizeof(signature));
    return result;
}

int cc_ecdsa_sign_recoverable(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    const unsigned char *extra_entropy,
    unsigned char output[CC_RECOVERABLE_SIGNATURE_SIZE]
)
{
    secp256k1_ecdsa_recoverable_signature signature;
    int recovery_id = 0;
    int result = secp256k1_ecdsa_sign_recoverable(
        context,
        &signature,
        digest,
        secret,
        secp256k1_nonce_function_rfc6979,
        extra_entropy
    );
    if (result) {
        result = secp256k1_ecdsa_recoverable_signature_serialize_compact(
            context,
            output,
            &recovery_id,
            &signature
        );
        output[CC_COMPACT_SIGNATURE_SIZE] = (unsigned char)recovery_id;
    }
    cc_secure_zero(&signature, sizeof(signature));
    return result;
}

int cc_ecdsa_verify_der(
    const secp256k1_context *context,
    const secp256k1_pubkey *public_key,
    const unsigned char *signature,
    size_t signature_size,
    const unsigned char digest[CC_DIGEST_SIZE]
)
{
    secp256k1_ecdsa_signature parsed;
    int result = secp256k1_ecdsa_signature_parse_der(context, &parsed, signature, signature_size);
    if (result) {
        result = secp256k1_ecdsa_verify(context, &parsed, digest, public_key);
    }
    return result;
}

int cc_ecdsa_verify_compact(
    const secp256k1_context *context,
    const secp256k1_pubkey *public_key,
    const unsigned char signature[CC_COMPACT_SIGNATURE_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE]
)
{
    secp256k1_ecdsa_signature parsed;
    int result = secp256k1_ecdsa_signature_parse_compact(context, &parsed, signature);
    if (result) {
        result = secp256k1_ecdsa_verify(context, &parsed, digest, public_key);
    }
    return result;
}

static int parse_recoverable(
    const secp256k1_context *context,
    const unsigned char signature[CC_RECOVERABLE_SIGNATURE_SIZE],
    secp256k1_ecdsa_recoverable_signature *parsed
)
{
    int recovery_id = signature[CC_COMPACT_SIGNATURE_SIZE];
    return recovery_id <= 3 && secp256k1_ecdsa_recoverable_signature_parse_compact(
                                   context,
                                   parsed,
                                   signature,
                                   recovery_id
                               );
}

int cc_ecdsa_recover(
    const secp256k1_context *context,
    const unsigned char signature[CC_RECOVERABLE_SIGNATURE_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE],
    secp256k1_pubkey *public_key
)
{
    secp256k1_ecdsa_recoverable_signature parsed;
    return parse_recoverable(context, signature, &parsed) &&
           secp256k1_ecdsa_recover(context, public_key, &parsed, digest);
}

int cc_schnorr_verify(
    const secp256k1_context *context,
    const secp256k1_xonly_pubkey *public_key,
    const unsigned char signature[CC_COMPACT_SIGNATURE_SIZE],
    const unsigned char digest[CC_DIGEST_SIZE]
)
{
    return secp256k1_schnorrsig_verify(context, signature, digest, CC_DIGEST_SIZE, public_key);
}

int cc_ecdh(
    const secp256k1_context *context,
    const unsigned char secret[CC_SECRET_SIZE],
    const secp256k1_pubkey *public_key,
    unsigned char output[CC_DIGEST_SIZE]
)
{
    return secp256k1_ecdh(context, output, public_key, secret, NULL, NULL);
}

int cc_copy_der_signature(
    PyObject *object,
    unsigned char output[CC_MAX_DER_SIGNATURE_SIZE],
    size_t *size
)
{
    CoincurveBuffer buffer;

    if (cc_get_buffer(object, &buffer, "signature") < 0) {
        return -1;
    }
    if (buffer.view.len < 1 || buffer.view.len > CC_MAX_DER_SIGNATURE_SIZE) {
        cc_release_buffer(&buffer);
        *size = 0;
        return 0;
    }
    *size = (size_t)buffer.view.len;
    memcpy(output, buffer.view.buf, *size);
    cc_release_buffer(&buffer);
    return 1;
}

int cc_copy_schnorr_signature(PyObject *object, unsigned char output[CC_COMPACT_SIGNATURE_SIZE])
{
    CoincurveBuffer buffer;

    if (PyBytes_CheckExact(object)) {
        if (PyBytes_GET_SIZE(object) != CC_COMPACT_SIGNATURE_SIZE) {
            return 0;
        }
        memcpy(output, PyBytes_AS_STRING(object), CC_COMPACT_SIGNATURE_SIZE);
        return 1;
    }
    if (cc_get_buffer(object, &buffer, "signature") < 0) {
        return -1;
    }
    if (buffer.view.len != CC_COMPACT_SIGNATURE_SIZE) {
        cc_release_buffer(&buffer);
        return 0;
    }
    memcpy(output, buffer.view.buf, CC_COMPACT_SIGNATURE_SIZE);
    cc_release_buffer(&buffer);
    return 1;
}

PyObject *cc_verify_der_signature(
    CoincurveState *state,
    const secp256k1_pubkey *public_key,
    PyObject *signature_object,
    const unsigned char digest[CC_DIGEST_SIZE]
)
{
    unsigned char signature[CC_MAX_DER_SIGNATURE_SIZE];
    size_t signature_size;
    int copied = cc_copy_der_signature(signature_object, signature, &signature_size);
    int verified;

    if (copied < 0) {
        return NULL;
    }
    if (!copied) {
        Py_RETURN_FALSE;
    }
    Py_BEGIN_ALLOW_THREADS verified =
        cc_ecdsa_verify_der(state->context, public_key, signature, signature_size, digest);
    Py_END_ALLOW_THREADS return PyBool_FromLong(verified);
}

static PyObject *verify_signature_common(
    PyObject *module,
    PyObject *signature_object,
    const unsigned char digest[CC_DIGEST_SIZE],
    PyObject *public_key_object
)
{
    CoincurveState *state = cc_state_from_module(module);
    secp256k1_pubkey public_key;

    if (cc_public_key_from_object(state, public_key_object, &public_key, "public_key") < 0) {
        return NULL;
    }
    return cc_verify_der_signature(state, &public_key, signature_object, digest);
}

static PyObject *coincurve_verify_signature_digest(
    PyObject *module,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"signature", "digest", "public_key"};
    PyObject *values[3];
    unsigned char digest[CC_DIGEST_SIZE];

    if (cc_parse_fastcall(args, nargs, kwnames, "verify_signature_digest", names, 3, 3, values) <
        0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL || values[2] == NULL) {
        PyErr_SetString(
            PyExc_TypeError,
            "verify_signature_digest() requires signature, digest, and public_key."
        );
        return NULL;
    }
    if (cc_copy_fixed(values[1], digest, sizeof(digest), "digest") < 0) {
        return NULL;
    }
    return verify_signature_common(module, values[0], digest, values[2]);
}

static PyObject *coincurve_verify_signature(
    PyObject *module,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"signature", "message", "public_key", "hasher"};
    PyObject *values[4];
    CoincurveState *state = cc_state_from_module(module);
    unsigned char digest[CC_DIGEST_SIZE];

    if (cc_parse_fastcall(args, nargs, kwnames, "verify_signature", names, 4, 4, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL || values[2] == NULL) {
        PyErr_SetString(
            PyExc_TypeError,
            "verify_signature() requires signature, message, and public_key."
        );
        return NULL;
    }
    if (cc_hash_message(state, values[1], values[3], digest) < 0) {
        return NULL;
    }
    return verify_signature_common(module, values[0], digest, values[2]);
}

static PyObject *coincurve_der_to_compact(PyObject *module, PyObject *signature_object)
{
    CoincurveState *state = cc_state_from_module(module);
    CoincurveBuffer buffer;
    secp256k1_ecdsa_signature signature;
    PyObject *output;
    int parsed;

    if (cc_get_buffer(signature_object, &buffer, "signature") < 0) {
        return NULL;
    }
    parsed = secp256k1_ecdsa_signature_parse_der(
        state->context,
        &signature,
        (const unsigned char *)buffer.view.buf,
        (size_t)buffer.view.len
    );
    cc_release_buffer(&buffer);
    if (!parsed) {
        PyErr_SetString(PyExc_ValueError, "The DER-encoded signature could not be parsed.");
        return NULL;
    }
    output = PyBytes_FromStringAndSize(NULL, CC_COMPACT_SIGNATURE_SIZE);
    if (output == NULL) {
        return NULL;
    }
    secp256k1_ecdsa_signature_serialize_compact(
        state->context,
        (unsigned char *)PyBytes_AS_STRING(output),
        &signature
    );
    return output;
}

static PyObject *coincurve_compact_to_der(PyObject *module, PyObject *signature_object)
{
    CoincurveState *state = cc_state_from_module(module);
    unsigned char compact[CC_COMPACT_SIGNATURE_SIZE];
    unsigned char output[CC_MAX_DER_SIGNATURE_SIZE];
    secp256k1_ecdsa_signature signature;
    size_t output_size = sizeof(output);

    if (cc_copy_fixed(signature_object, compact, sizeof(compact), "signature") < 0) {
        return NULL;
    }
    if (!secp256k1_ecdsa_signature_parse_compact(state->context, &signature, compact)) {
        PyErr_SetString(PyExc_ValueError, "The compact signature could not be parsed.");
        return NULL;
    }
    if (!secp256k1_ecdsa_signature_serialize_der(
            state->context,
            output,
            &output_size,
            &signature
        )) {
        PyErr_SetString(PyExc_RuntimeError, "Could not serialize the ECDSA signature.");
        return NULL;
    }
    return cc_bytes_from_data(output, (Py_ssize_t)output_size);
}

static PyObject *coincurve_normalize_signature(PyObject *module, PyObject *signature_object)
{
    CoincurveState *state = cc_state_from_module(module);
    CoincurveBuffer buffer;
    secp256k1_ecdsa_signature signature;
    secp256k1_ecdsa_signature normalized;
    unsigned char output[CC_MAX_DER_SIGNATURE_SIZE];
    size_t output_size = sizeof(output);
    int changed;
    PyObject *serialized;
    PyObject *result;

    if (cc_get_buffer(signature_object, &buffer, "signature") < 0) {
        return NULL;
    }
    if (!secp256k1_ecdsa_signature_parse_der(
            state->context,
            &signature,
            (const unsigned char *)buffer.view.buf,
            (size_t)buffer.view.len
        )) {
        cc_release_buffer(&buffer);
        PyErr_SetString(PyExc_ValueError, "The DER-encoded signature could not be parsed.");
        return NULL;
    }
    cc_release_buffer(&buffer);
    changed = secp256k1_ecdsa_signature_normalize(state->context, &normalized, &signature);
    if (!secp256k1_ecdsa_signature_serialize_der(
            state->context,
            output,
            &output_size,
            &normalized
        )) {
        PyErr_SetString(PyExc_RuntimeError, "Could not serialize the ECDSA signature.");
        return NULL;
    }
    serialized = cc_bytes_from_data(output, (Py_ssize_t)output_size);
    if (serialized == NULL) {
        return NULL;
    }
    result = PyTuple_Pack(2, changed ? Py_True : Py_False, serialized);
    Py_DECREF(serialized);
    return result;
}

static PyObject *coincurve_recoverable_to_der(PyObject *module, PyObject *signature_object)
{
    CoincurveState *state = cc_state_from_module(module);
    unsigned char serialized[CC_RECOVERABLE_SIGNATURE_SIZE];
    secp256k1_ecdsa_recoverable_signature recoverable;
    secp256k1_ecdsa_signature signature;
    unsigned char output[CC_MAX_DER_SIGNATURE_SIZE];
    size_t output_size = sizeof(output);

    if (cc_copy_fixed(signature_object, serialized, sizeof(serialized), "signature") < 0) {
        return NULL;
    }
    if (!parse_recoverable(state->context, serialized, &recoverable)) {
        PyErr_SetString(PyExc_ValueError, "The recoverable signature could not be parsed.");
        return NULL;
    }
    secp256k1_ecdsa_recoverable_signature_convert(state->context, &signature, &recoverable);
    secp256k1_ecdsa_signature_serialize_der(state->context, output, &output_size, &signature);
    return cc_bytes_from_data(output, (Py_ssize_t)output_size);
}

static PyMethodDef signature_methods[] = {
    {"verify_signature",
     (PyCFunction)(void (*)(void))coincurve_verify_signature,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_signature($module, signature, message, public_key, hasher=...)\n--\n\nVerify an "
     "ECDSA signature."},
    {"verify_signature_digest",
     (PyCFunction)(void (*)(void))coincurve_verify_signature_digest,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_signature_digest($module, signature, digest, public_key)\n--\n\nVerify an ECDSA "
     "signature over a "
     "32-byte digest."},
    {"der_to_compact",
     coincurve_der_to_compact,
     METH_O,
     "der_to_compact($module, signature, /)\n--\n\nConvert a DER-encoded ECDSA signature to "
     "64-byte compact form."},
    {"compact_to_der",
     coincurve_compact_to_der,
     METH_O,
     "compact_to_der($module, signature, /)\n--\n\nConvert a 64-byte compact ECDSA signature to "
     "DER."},
    {"normalize_signature",
     coincurve_normalize_signature,
     METH_O,
     "normalize_signature($module, signature, /)\n--\n\nReturn whether a DER signature changed and "
     "its lower-S "
     "form."},
    {"recoverable_to_der",
     coincurve_recoverable_to_der,
     METH_O,
     "recoverable_to_der($module, signature, /)\n--\n\nConvert a recoverable signature to DER."},
    {NULL, NULL, 0, NULL}
};

int cc_add_signature_functions(PyObject *module)
{
    return PyModule_AddFunctions(module, signature_methods);
}
