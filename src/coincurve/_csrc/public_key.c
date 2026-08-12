#include "coincurve.h"

#include <string.h>

int cc_serialize_compressed(
    const secp256k1_context *context,
    const secp256k1_pubkey *public_key,
    unsigned char output[CC_PUBLIC_KEY_COMPRESSED_SIZE]
)
{
    size_t output_size = CC_PUBLIC_KEY_COMPRESSED_SIZE;
    return secp256k1_ec_pubkey_serialize(
        context,
        output,
        &output_size,
        public_key,
        SECP256K1_EC_COMPRESSED
    );
}

PyObject *cc_public_key_from_native(PyTypeObject *type, const secp256k1_pubkey *public_key)
{
    CoincurveState *state = cc_state_from_type(type);
    PublicKeyObject *self;

    if (state == NULL) {
        return NULL;
    }
    self = (PublicKeyObject *)type->tp_alloc(type, 0);
    if (self == NULL) {
        return NULL;
    }
    memcpy(&self->public_key, public_key, sizeof(self->public_key));
    if (!cc_serialize_compressed(state->context, &self->public_key, self->compressed)) {
        Py_DECREF(self);
        PyErr_SetString(PyExc_RuntimeError, "Could not serialize the public key.");
        return NULL;
    }
    return (PyObject *)self;
}

int cc_public_key_from_object(
    CoincurveState *state,
    PyObject *object,
    secp256k1_pubkey *public_key,
    const char *name
)
{
    CoincurveBuffer buffer;
    const unsigned char *serialized;
    size_t serialized_size;
    int parsed;

    if (PyObject_TypeCheck(object, (PyTypeObject *)state->public_key_type)) {
        memcpy(public_key, &((PublicKeyObject *)object)->public_key, sizeof(*public_key));
        return 0;
    }
    if (PyBytes_CheckExact(object)) {
        serialized = (const unsigned char *)PyBytes_AS_STRING(object);
        serialized_size = (size_t)PyBytes_GET_SIZE(object);
        parsed = secp256k1_ec_pubkey_parse(state->context, public_key, serialized, serialized_size);
        if (!parsed) {
            PyErr_Format(
                PyExc_ValueError,
                "%s could not be parsed as a secp256k1 public key.",
                name
            );
            return -1;
        }
        return 0;
    }
    if (cc_get_buffer(object, &buffer, name) < 0) {
        return -1;
    }
    parsed = secp256k1_ec_pubkey_parse(
        state->context,
        public_key,
        (const unsigned char *)buffer.view.buf,
        (size_t)buffer.view.len
    );
    cc_release_buffer(&buffer);
    if (!parsed) {
        PyErr_Format(PyExc_ValueError, "%s could not be parsed as a secp256k1 public key.", name);
        return -1;
    }
    return 0;
}

static PyObject *public_key_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    static char *keyword_names[] = {"data", NULL};
    PyObject *data;
    CoincurveState *state = cc_state_from_type(type);
    secp256k1_pubkey public_key;

    if (state == NULL) {
        return NULL;
    }
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O:PublicKey", keyword_names, &data)) {
        return NULL;
    }
    if (cc_public_key_from_object(state, data, &public_key, "data") < 0) {
        return NULL;
    }
    return cc_public_key_from_native(type, &public_key);
}

static PyObject *public_key_repr(PublicKeyObject *self)
{
    return cc_hex_repr((PyObject *)self, self->compressed, sizeof(self->compressed));
}

static PyObject *public_key_richcompare(PyObject *left, PyObject *right, int operation)
{
    return cc_richcompare_fixed(
        left,
        right,
        operation,
        offsetof(PublicKeyObject, compressed),
        CC_PUBLIC_KEY_COMPRESSED_SIZE
    );
}

static Py_hash_t public_key_hash(PublicKeyObject *self)
{
    return cc_hash_data(self->compressed, (Py_ssize_t)sizeof(self->compressed));
}

static PyObject *public_key_bytes(PublicKeyObject *self, PyObject *ignored)
{
    (void)ignored;
    return cc_bytes_from_data(self->compressed, sizeof(self->compressed));
}

static PyObject *
public_key_format(PublicKeyObject *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    static const char *const names[] = {"compressed"};
    PyObject *values[1];
    int compressed = 1;
    CoincurveState *state;
    PyObject *serialized;
    size_t serialized_size;

    if (cc_parse_fastcall(args, nargs, kwnames, "format", names, 1, 1, values) < 0) {
        return NULL;
    }
    if (values[0] != NULL) {
        compressed = PyObject_IsTrue(values[0]);
        if (compressed < 0) {
            return NULL;
        }
    }
    if (compressed) {
        return cc_bytes_from_data(self->compressed, sizeof(self->compressed));
    }
    state = cc_state_from_object((PyObject *)self);
    if (state == NULL) {
        return NULL;
    }
    serialized = PyBytes_FromStringAndSize(NULL, CC_PUBLIC_KEY_UNCOMPRESSED_SIZE);
    if (serialized == NULL) {
        return NULL;
    }
    serialized_size = CC_PUBLIC_KEY_UNCOMPRESSED_SIZE;
    if (!secp256k1_ec_pubkey_serialize(
            state->context,
            (unsigned char *)PyBytes_AS_STRING(serialized),
            &serialized_size,
            &self->public_key,
            SECP256K1_EC_UNCOMPRESSED
        )) {
        Py_DECREF(serialized);
        PyErr_SetString(PyExc_RuntimeError, "Could not serialize the public key.");
        return NULL;
    }
    return serialized;
}

static PyObject *public_key_point(PublicKeyObject *self, PyObject *ignored)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char serialized[CC_PUBLIC_KEY_UNCOMPRESSED_SIZE];
    size_t serialized_size = sizeof(serialized);
    PyObject *x;
    PyObject *y;
    PyObject *result;

    (void)ignored;

    if (state == NULL) {
        return NULL;
    }
    if (!secp256k1_ec_pubkey_serialize(
            state->context,
            serialized,
            &serialized_size,
            &self->public_key,
            SECP256K1_EC_UNCOMPRESSED
        )) {
        PyErr_SetString(PyExc_RuntimeError, "Could not serialize the public key.");
        return NULL;
    }
    x = cc_integer_from_bytes(serialized + 1, 32);
    y = cc_integer_from_bytes(serialized + 33, 32);
    if (x == NULL || y == NULL) {
        Py_XDECREF(x);
        Py_XDECREF(y);
        return NULL;
    }
    result = PyTuple_Pack(2, x, y);
    Py_DECREF(x);
    Py_DECREF(y);
    return result;
}

static PyObject *public_key_verify_digest_native(
    PublicKeyObject *self,
    PyObject *signature_object,
    const unsigned char digest[CC_DIGEST_SIZE]
)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);

    if (state == NULL) {
        return NULL;
    }
    return cc_verify_der_signature(state, &self->public_key, signature_object, digest);
}

static PyObject *public_key_verify_digest_impl(
    PublicKeyObject *self,
    PyObject *signature_object,
    PyObject *digest_object
)
{
    unsigned char digest[CC_DIGEST_SIZE];

    if (cc_copy_fixed(digest_object, digest, sizeof(digest), "digest") < 0) {
        return NULL;
    }
    return public_key_verify_digest_native(self, signature_object, digest);
}

static PyObject *public_key_verify_digest(
    PublicKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"signature", "digest"};
    PyObject *values[2];
    if (cc_parse_fastcall(args, nargs, kwnames, "verify_digest", names, 2, 2, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_SetString(PyExc_TypeError, "verify_digest() requires signature and digest.");
        return NULL;
    }
    return public_key_verify_digest_impl(self, values[0], values[1]);
}

static PyObject *
public_key_verify(PublicKeyObject *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    static const char *const names[] = {"signature", "message", "hasher"};
    PyObject *values[3];
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char digest[CC_DIGEST_SIZE];

    if (state == NULL) {
        return NULL;
    }
    if (cc_parse_fastcall(args, nargs, kwnames, "verify", names, 3, 3, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_SetString(PyExc_TypeError, "verify() requires signature and message.");
        return NULL;
    }
    if (cc_hash_message(state, values[1], values[2], digest) < 0) {
        return NULL;
    }
    return public_key_verify_digest_native(self, values[0], digest);
}

static PyObject *public_key_tweak(PublicKeyObject *self, PyObject *scalar_object, int multiply)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char scalar[CC_SECRET_SIZE];
    secp256k1_pubkey public_key;
    int result;

    if (state == NULL) {
        return NULL;
    }
    if (cc_copy_scalar(scalar_object, scalar, "scalar") < 0) {
        return NULL;
    }
    memcpy(&public_key, &self->public_key, sizeof(public_key));
    Py_BEGIN_ALLOW_THREADS if (multiply)
    {
        result = secp256k1_ec_pubkey_tweak_mul(state->context, &public_key, scalar);
    }
    else
    {
        result = secp256k1_ec_pubkey_tweak_add(state->context, &public_key, scalar);
    }
    Py_END_ALLOW_THREADS cc_secure_zero(scalar, sizeof(scalar));
    if (!result) {
        PyErr_SetString(PyExc_ValueError, "The scalar or resulting public key is invalid.");
        return NULL;
    }
    return cc_public_key_from_native(Py_TYPE(self), &public_key);
}

static PyObject *public_key_add(PublicKeyObject *self, PyObject *scalar_object)
{
    return public_key_tweak(self, scalar_object, 0);
}

static PyObject *public_key_multiply(PublicKeyObject *self, PyObject *scalar_object)
{
    return public_key_tweak(self, scalar_object, 1);
}

static PyObject *public_key_from_secret(PyObject *type_object, PyObject *secret_object)
{
    CoincurveState *state = cc_state_from_type((PyTypeObject *)type_object);
    unsigned char secret[CC_SECRET_SIZE];
    secp256k1_pubkey public_key;
    int result;

    if (state == NULL) {
        return NULL;
    }
    if (cc_copy_scalar(secret_object, secret, "secret") < 0) {
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS result = secp256k1_ec_pubkey_create(state->context, &public_key, secret);
    Py_END_ALLOW_THREADS cc_secure_zero(secret, sizeof(secret));
    if (!result) {
        PyErr_SetString(PyExc_ValueError, "Secret must encode a valid secp256k1 private key.");
        return NULL;
    }
    return cc_public_key_from_native((PyTypeObject *)type_object, &public_key);
}

static PyObject *public_key_from_point(
    PyObject *type_object,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"x", "y"};
    PyObject *values[2];
    PyObject *x_bytes;
    PyObject *y_bytes;
    unsigned char serialized[CC_PUBLIC_KEY_UNCOMPRESSED_SIZE];
    CoincurveState *state;
    secp256k1_pubkey public_key;

    if (cc_parse_fastcall(args, nargs, kwnames, "from_point", names, 2, 2, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_SetString(PyExc_TypeError, "from_point() requires x and y coordinates.");
        return NULL;
    }
    x_bytes = cc_integer_to_32_bytes(values[0], "x");
    if (x_bytes == NULL) {
        return NULL;
    }
    y_bytes = cc_integer_to_32_bytes(values[1], "y");
    if (y_bytes == NULL) {
        Py_DECREF(x_bytes);
        return NULL;
    }
    serialized[0] = 4;
    memcpy(serialized + 1, PyBytes_AS_STRING(x_bytes), 32);
    memcpy(serialized + 33, PyBytes_AS_STRING(y_bytes), 32);
    Py_DECREF(x_bytes);
    Py_DECREF(y_bytes);
    state = cc_state_from_type((PyTypeObject *)type_object);
    if (state == NULL) {
        return NULL;
    }
    if (!secp256k1_ec_pubkey_parse(state->context, &public_key, serialized, sizeof(serialized))) {
        PyErr_SetString(
            PyExc_ValueError,
            "The coordinates do not encode a valid secp256k1 public key."
        );
        return NULL;
    }
    return cc_public_key_from_native((PyTypeObject *)type_object, &public_key);
}

static PyObject *public_key_recover_digest_native(
    PyTypeObject *type,
    PyObject *signature_object,
    const unsigned char digest[CC_DIGEST_SIZE]
)
{
    CoincurveState *state = cc_state_from_type(type);
    unsigned char signature[CC_RECOVERABLE_SIGNATURE_SIZE];
    secp256k1_pubkey public_key;
    int recovered;

    if (state == NULL) {
        return NULL;
    }
    if (cc_copy_fixed(signature_object, signature, sizeof(signature), "signature") < 0) {
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS recovered =
        cc_ecdsa_recover(state->context, signature, digest, &public_key);
    Py_END_ALLOW_THREADS if (!recovered)
    {
        PyErr_SetString(
            PyExc_ValueError,
            "The public key could not be recovered from the signature."
        );
        return NULL;
    }
    return cc_public_key_from_native(type, &public_key);
}

static PyObject *public_key_recover_digest_impl(
    PyTypeObject *type,
    PyObject *signature_object,
    PyObject *digest_object
)
{
    unsigned char digest[CC_DIGEST_SIZE];

    if (cc_copy_fixed(digest_object, digest, sizeof(digest), "digest") < 0) {
        return NULL;
    }
    return public_key_recover_digest_native(type, signature_object, digest);
}

static PyObject *public_key_recover_digest(
    PyObject *type_object,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"signature", "digest"};
    PyObject *values[2];
    if (cc_parse_fastcall(args, nargs, kwnames, "recover_digest", names, 2, 2, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_SetString(PyExc_TypeError, "recover_digest() requires signature and digest.");
        return NULL;
    }
    return public_key_recover_digest_impl((PyTypeObject *)type_object, values[0], values[1]);
}

static PyObject *public_key_recover(
    PyObject *type_object,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"signature", "message", "hasher"};
    PyObject *values[3];
    CoincurveState *state = cc_state_from_type((PyTypeObject *)type_object);
    unsigned char digest[CC_DIGEST_SIZE];

    if (state == NULL) {
        return NULL;
    }
    if (cc_parse_fastcall(args, nargs, kwnames, "recover", names, 3, 3, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_SetString(PyExc_TypeError, "recover() requires signature and message.");
        return NULL;
    }
    if (cc_hash_message(state, values[1], values[2], digest) < 0) {
        return NULL;
    }
    return public_key_recover_digest_native((PyTypeObject *)type_object, values[0], digest);
}

static PyObject *public_key_combine_native(
    PyTypeObject *type,
    const secp256k1_pubkey *initial_key,
    PyObject *keys_object
)
{
    CoincurveState *state = cc_state_from_type(type);
    PyObject *keys;
    Py_ssize_t count;
    Py_ssize_t total;
    const secp256k1_pubkey **pointers;
    secp256k1_pubkey combined;
    Py_ssize_t index;
    int result;

    if (state == NULL) {
        return NULL;
    }
    keys = PySequence_Tuple(keys_object);
    if (keys == NULL) {
        return NULL;
    }
    count = PySequence_Fast_GET_SIZE(keys);
    total = count + (initial_key != NULL);
    if (total < 1) {
        Py_DECREF(keys);
        PyErr_SetString(PyExc_ValueError, "keys must contain at least one public key.");
        return NULL;
    }
    if ((size_t)total > SIZE_MAX / sizeof(*pointers)) {
        Py_DECREF(keys);
        return PyErr_NoMemory();
    }
    pointers = PyMem_Malloc((size_t)total * sizeof(*pointers));
    if (pointers == NULL) {
        Py_DECREF(keys);
        return PyErr_NoMemory();
    }
    if (initial_key != NULL) {
        pointers[0] = initial_key;
    }
    for (index = 0; index < count; index++) {
        PyObject *item = PySequence_Fast_GET_ITEM(keys, index);
        if (!PyObject_TypeCheck(item, (PyTypeObject *)state->public_key_type)) {
            PyMem_Free(pointers);
            Py_DECREF(keys);
            PyErr_Format(PyExc_TypeError, "keys[%zd] must be a PublicKey.", index);
            return NULL;
        }
        pointers[index + (initial_key != NULL)] = &((PublicKeyObject *)item)->public_key;
    }
    Py_BEGIN_ALLOW_THREADS result =
        secp256k1_ec_pubkey_combine(state->context, &combined, pointers, (size_t)total);
    Py_END_ALLOW_THREADS PyMem_Free(pointers);
    Py_DECREF(keys);
    if (!result) {
        PyErr_SetString(PyExc_ValueError, "The sum of the public keys is invalid.");
        return NULL;
    }
    return cc_public_key_from_native(type, &combined);
}

static PyObject *public_key_combine(PublicKeyObject *self, PyObject *keys_object)
{
    return public_key_combine_native(Py_TYPE(self), &self->public_key, keys_object);
}

static PyObject *public_key_combine_keys(PyObject *type_object, PyObject *keys_object)
{
    return public_key_combine_native((PyTypeObject *)type_object, NULL, keys_object);
}

static PyMethodDef public_key_methods[] = {
    {"verify_many",
     (PyCFunction)(void (*)(void))cc_public_key_verify_many,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_many($self, signatures, messages, hasher=...)\n--\n\nVerify signatures for a "
     "sequence of messages."},
    {"verify_digests",
     (PyCFunction)(void (*)(void))cc_public_key_verify_digests,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_digests($self, signatures, digests)\n--\n\nVerify signatures for a sequence of "
     "digests."},
    {"__bytes__",
     (PyCFunction)public_key_bytes,
     METH_NOARGS,
     "__bytes__($self, /)\n--\n\nReturn the compressed public key."},
    {"format",
     (PyCFunction)(void (*)(void))public_key_format,
     METH_FASTCALL | METH_KEYWORDS,
     "format($self, compressed=True)\n--\n\nSerialize the public key."},
    {"point",
     (PyCFunction)public_key_point,
     METH_NOARGS,
     "point($self, /)\n--\n\nReturn the affine coordinates."},
    {"verify",
     (PyCFunction)(void (*)(void))public_key_verify,
     METH_FASTCALL | METH_KEYWORDS,
     "verify($self, signature, message, hasher=...)\n--\n\nVerify a DER-encoded ECDSA signature."},
    {"verify_digest",
     (PyCFunction)(void (*)(void))public_key_verify_digest,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_digest($self, signature, digest)\n--\n\nVerify a DER-encoded ECDSA signature over a "
     "digest."},
    {"add",
     (PyCFunction)public_key_add,
     METH_O,
     "add($self, scalar, /)\n--\n\nReturn a public key with the scalar added."},
    {"multiply",
     (PyCFunction)public_key_multiply,
     METH_O,
     "multiply($self, scalar, /)\n--\n\nReturn a public key multiplied by the scalar."},
    {"from_secret",
     (PyCFunction)public_key_from_secret,
     METH_CLASS | METH_O,
     "from_secret($type, secret, /)\n--\n\nDerive a public key from a secret."},
    {"from_point",
     (PyCFunction)(void (*)(void))public_key_from_point,
     METH_CLASS | METH_FASTCALL | METH_KEYWORDS,
     "from_point($type, x, y)\n--\n\nCreate a public key from affine coordinates."},
    {"recover",
     (PyCFunction)(void (*)(void))public_key_recover,
     METH_CLASS | METH_FASTCALL | METH_KEYWORDS,
     "recover($type, signature, message, hasher=...)\n--\n\nRecover a public key from a signature "
     "and message."},
    {"recover_digest",
     (PyCFunction)(void (*)(void))public_key_recover_digest,
     METH_CLASS | METH_FASTCALL | METH_KEYWORDS,
     "recover_digest($type, signature, digest)\n--\n\nRecover a public key from a signature and "
     "digest."},
    {"combine",
     (PyCFunction)public_key_combine,
     METH_O,
     "combine($self, keys, /)\n--\n\nAdd other public keys to this public key."},
    {"combine_keys",
     (PyCFunction)public_key_combine_keys,
     METH_CLASS | METH_O,
     "combine_keys($type, keys, /)\n--\n\nAdd public keys together."},
    {NULL, NULL, 0, NULL}
};

static PyType_Slot public_key_slots[] = {
    {Py_tp_doc, "PublicKey(data)\n--\n\nAn immutable secp256k1 public key."},
    {Py_tp_new, public_key_new},
    {Py_tp_repr, public_key_repr},
    {Py_tp_hash, public_key_hash},
    {Py_tp_richcompare, public_key_richcompare},
    {Py_tp_methods, public_key_methods},
    {0, NULL}
};

static PyType_Spec public_key_spec = {
    .name = "coincurve.PublicKey",
    .basicsize = sizeof(PublicKeyObject),
    .itemsize = 0,
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_IMMUTABLETYPE,
    .slots = public_key_slots,
};

PyObject *cc_create_public_key_type(PyObject *module)
{
    return PyType_FromModuleAndSpec(module, &public_key_spec, NULL);
}
