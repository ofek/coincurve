#include "coincurve.h"

#include <string.h>

PyObject *cc_xonly_public_key_from_native(
    PyTypeObject *type,
    const secp256k1_xonly_pubkey *public_key,
    int parity
)
{
    CoincurveState *state = cc_state_from_type(type);
    XOnlyPublicKeyObject *self;

    if (state == NULL) {
        return NULL;
    }
    self = (XOnlyPublicKeyObject *)type->tp_alloc(type, 0);
    if (self == NULL) {
        return NULL;
    }
    memcpy(&self->public_key, public_key, sizeof(self->public_key));
    self->parity = parity;
    if (!secp256k1_xonly_pubkey_serialize(state->context, self->serialized, &self->public_key)) {
        Py_DECREF(self);
        PyErr_SetString(PyExc_RuntimeError, "Could not serialize the x-only public key.");
        return NULL;
    }
    return (PyObject *)self;
}

static PyObject *xonly_public_key_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    static char *keyword_names[] = {"data", "parity", NULL};
    PyObject *data;
    PyObject *parity_object = Py_None;
    CoincurveState *state = cc_state_from_type(type);
    unsigned char serialized[CC_XONLY_PUBLIC_KEY_SIZE];
    secp256k1_xonly_pubkey public_key;
    int parity = -1;

    if (state == NULL) {
        return NULL;
    }
    if (!PyArg_ParseTupleAndKeywords(
            args,
            kwargs,
            "O|O:XOnlyPublicKey",
            keyword_names,
            &data,
            &parity_object
        )) {
        return NULL;
    }
    if (parity_object != Py_None) {
        if (!PyBool_Check(parity_object)) {
            PyErr_SetString(PyExc_TypeError, "parity must be a bool or None.");
            return NULL;
        }
        parity = parity_object == Py_True;
    }
    if (cc_copy_fixed(data, serialized, sizeof(serialized), "data") < 0) {
        return NULL;
    }
    if (!secp256k1_xonly_pubkey_parse(state->context, &public_key, serialized)) {
        PyErr_SetString(PyExc_ValueError, "The x-only public key could not be parsed.");
        return NULL;
    }
    return cc_xonly_public_key_from_native(type, &public_key, parity);
}

static PyObject *xonly_public_key_repr(XOnlyPublicKeyObject *self)
{
    return cc_hex_repr((PyObject *)self, self->serialized, sizeof(self->serialized));
}

static PyObject *xonly_public_key_richcompare(PyObject *left, PyObject *right, int operation)
{
    return cc_richcompare_fixed(
        left,
        right,
        operation,
        offsetof(XOnlyPublicKeyObject, serialized),
        CC_XONLY_PUBLIC_KEY_SIZE
    );
}

static Py_hash_t xonly_public_key_hash(XOnlyPublicKeyObject *self)
{
    return cc_hash_data(self->serialized, (Py_ssize_t)sizeof(self->serialized));
}

static PyObject *xonly_public_key_bytes(XOnlyPublicKeyObject *self, PyObject *ignored)
{
    (void)ignored;
    return cc_bytes_from_data(self->serialized, sizeof(self->serialized));
}

static PyObject *xonly_public_key_get_parity(XOnlyPublicKeyObject *self, void *closure)
{
    (void)closure;
    if (self->parity < 0) {
        Py_RETURN_NONE;
    }
    if (self->parity) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static PyObject *xonly_public_key_from_secret(PyObject *type_object, PyObject *secret_object)
{
    CoincurveState *state = cc_state_from_type((PyTypeObject *)type_object);
    unsigned char secret[CC_SECRET_SIZE];
    secp256k1_xonly_pubkey public_key;
    int parity = 0;
    int result;
    PyObject *key;

    if (state == NULL) {
        return NULL;
    }
    if (cc_copy_scalar(secret_object, secret, "secret") < 0) {
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS result =
        cc_xonly_from_secret(state->context, &public_key, &parity, secret);
    Py_END_ALLOW_THREADS cc_secure_zero(secret, sizeof(secret));
    if (!result) {
        PyErr_SetString(PyExc_ValueError, "Secret must encode a valid secp256k1 private key.");
        return NULL;
    }
    key = cc_xonly_public_key_from_native((PyTypeObject *)type_object, &public_key, parity);
    return key;
}

static PyObject *
xonly_public_key_from_public_key(PyObject *type_object, PyObject *public_key_object)
{
    CoincurveState *state = cc_state_from_type((PyTypeObject *)type_object);
    secp256k1_pubkey public_key;
    secp256k1_xonly_pubkey xonly;
    int parity = 0;

    if (state == NULL) {
        return NULL;
    }
    if (cc_public_key_from_object(state, public_key_object, &public_key, "public_key") < 0) {
        return NULL;
    }
    if (!secp256k1_xonly_pubkey_from_pubkey(state->context, &xonly, &parity, &public_key)) {
        PyErr_SetString(PyExc_ValueError, "The public key could not be converted to x-only form.");
        return NULL;
    }
    return cc_xonly_public_key_from_native((PyTypeObject *)type_object, &xonly, parity);
}

static PyObject *xonly_public_key_verify_digest_native(
    XOnlyPublicKeyObject *self,
    PyObject *signature_object,
    const unsigned char digest[CC_DIGEST_SIZE]
)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char signature[CC_COMPACT_SIGNATURE_SIZE];
    int copied;
    int verified;

    if (state == NULL) {
        return NULL;
    }
    copied = cc_copy_schnorr_signature(signature_object, signature);
    if (copied < 0) {
        return NULL;
    }
    if (!copied) {
        Py_RETURN_FALSE;
    }
    Py_BEGIN_ALLOW_THREADS verified =
        cc_schnorr_verify(state->context, &self->public_key, signature, digest);
    Py_END_ALLOW_THREADS if (verified)
    {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static PyObject *xonly_public_key_verify_digest_impl(
    XOnlyPublicKeyObject *self,
    PyObject *signature_object,
    PyObject *digest_object
)
{
    unsigned char digest[CC_DIGEST_SIZE];

    if (cc_copy_fixed(digest_object, digest, sizeof(digest), "digest") < 0) {
        return NULL;
    }
    return xonly_public_key_verify_digest_native(self, signature_object, digest);
}

static PyObject *xonly_public_key_verify_digest(
    XOnlyPublicKeyObject *self,
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
    return xonly_public_key_verify_digest_impl(self, values[0], values[1]);
}

static PyObject *xonly_public_key_verify(
    XOnlyPublicKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"signature", "message"};
    PyObject *values[2];
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    CoincurveBuffer message_buffer = {0};
    unsigned char signature[CC_COMPACT_SIGNATURE_SIZE];
    int copied;
    int verified;

    if (state == NULL) {
        return NULL;
    }
    if (cc_parse_fastcall(args, nargs, kwnames, "verify", names, 2, 2, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_SetString(PyExc_TypeError, "verify() requires signature and message.");
        return NULL;
    }
    copied = cc_copy_schnorr_signature(values[0], signature);
    if (copied < 0) {
        return NULL;
    }
    if (!copied) {
        Py_RETURN_FALSE;
    }
    if (cc_get_buffer(values[1], &message_buffer, "message") < 0) {
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS verified = secp256k1_schnorrsig_verify(
        state->context,
        signature,
        message_buffer.view.buf,
        (size_t)message_buffer.view.len,
        &self->public_key
    );
    Py_END_ALLOW_THREADS cc_release_buffer(&message_buffer);
    if (verified) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static PyObject *xonly_public_key_verify_message(
    XOnlyPublicKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"signature", "message", "hasher"};
    PyObject *values[3];
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char digest[CC_DIGEST_SIZE];

    if (state == NULL) {
        return NULL;
    }
    if (cc_parse_fastcall(args, nargs, kwnames, "verify_message", names, 3, 3, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_SetString(PyExc_TypeError, "verify_message() requires signature and message.");
        return NULL;
    }
    if (cc_hash_message(state, values[1], values[2], digest) < 0) {
        return NULL;
    }
    return xonly_public_key_verify_digest_native(self, values[0], digest);
}

static PyObject *xonly_public_key_add_tweak(XOnlyPublicKeyObject *self, PyObject *scalar_object)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char scalar[CC_SECRET_SIZE];
    secp256k1_pubkey tweaked;
    secp256k1_xonly_pubkey xonly;
    int parity = 0;
    int result;

    if (state == NULL) {
        return NULL;
    }
    if (cc_copy_scalar(scalar_object, scalar, "scalar") < 0) {
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS result =
        secp256k1_xonly_pubkey_tweak_add(state->context, &tweaked, &self->public_key, scalar);
    if (result) {
        result = secp256k1_xonly_pubkey_from_pubkey(state->context, &xonly, &parity, &tweaked);
    }
    Py_END_ALLOW_THREADS cc_secure_zero(scalar, sizeof(scalar));
    if (!result) {
        PyErr_SetString(PyExc_ValueError, "The scalar or resulting x-only public key is invalid.");
        return NULL;
    }
    return cc_xonly_public_key_from_native(Py_TYPE(self), &xonly, parity);
}

static PyObject *xonly_public_key_tweak_add(XOnlyPublicKeyObject *self, PyObject *scalar_object)
{
    (void)self;
    (void)scalar_object;
    PyErr_SetString(
        PyExc_TypeError,
        "tweak_add() no longer mutates in place; use key = key.add_tweak(scalar)."
    );
    return NULL;
}

static PyGetSetDef xonly_public_key_getset[] = {
    {"parity",
     (getter)xonly_public_key_get_parity,
     NULL,
     "The known parity, or None when unavailable.",
     NULL},
    {NULL, NULL, NULL, NULL, NULL}
};

static PyMethodDef xonly_public_key_methods[] = {
    {"verify_many",
     (PyCFunction)(void (*)(void))cc_xonly_public_key_verify_many,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_many($self, signatures, messages, hasher=...)\n--\n\nVerify Schnorr signatures for a "
     "sequence of "
     "messages."},
    {"verify_digests",
     (PyCFunction)(void (*)(void))cc_xonly_public_key_verify_digests,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_digests($self, signatures, digests)\n--\n\nVerify Schnorr signatures for a sequence "
     "of digests."},
    {"__bytes__",
     (PyCFunction)xonly_public_key_bytes,
     METH_NOARGS,
     "__bytes__($self, /)\n--\n\nReturn the serialized x-only public key."},
    {"format",
     (PyCFunction)xonly_public_key_bytes,
     METH_NOARGS,
     "format($self, /)\n--\n\nSerialize the x-only public key."},
    {"verify",
     (PyCFunction)(void (*)(void))xonly_public_key_verify,
     METH_FASTCALL | METH_KEYWORDS,
     "verify($self, signature, message)\n--\n\nVerify a BIP340 Schnorr signature over a raw "
     "message."},
    {"verify_message",
     (PyCFunction)(void (*)(void))xonly_public_key_verify_message,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_message($self, signature, message, hasher=...)\n--\n\nVerify a BIP340 Schnorr "
     "signature over a hashed message."},
    {"verify_digest",
     (PyCFunction)(void (*)(void))xonly_public_key_verify_digest,
     METH_FASTCALL | METH_KEYWORDS,
     "verify_digest($self, signature, digest)\n--\n\nVerify a BIP340 Schnorr signature over a "
     "digest."},
    {"tweak_add",
     (PyCFunction)xonly_public_key_tweak_add,
     METH_O,
     "tweak_add($self, scalar, /)\n--\n\nRaise an error explaining the immutable replacement."},
    {"add_tweak",
     (PyCFunction)xonly_public_key_add_tweak,
     METH_O,
     "add_tweak($self, scalar, /)\n--\n\nReturn a tweaked x-only public key with known parity."},
    {"from_secret",
     (PyCFunction)xonly_public_key_from_secret,
     METH_CLASS | METH_O,
     "from_secret($type, secret, /)\n--\n\nDerive an x-only public key from a secret."},
    {"from_public_key",
     (PyCFunction)xonly_public_key_from_public_key,
     METH_CLASS | METH_O,
     "from_public_key($type, public_key, /)\n--\n\nConvert a public key to x-only form."},
    {NULL, NULL, 0, NULL}
};

static PyType_Slot xonly_public_key_slots[] = {
    {Py_tp_doc,
     "XOnlyPublicKey(data, parity=None)\n--\n\nAn immutable secp256k1 x-only public key."},
    {Py_tp_new, xonly_public_key_new},
    {Py_tp_repr, xonly_public_key_repr},
    {Py_tp_hash, xonly_public_key_hash},
    {Py_tp_richcompare, xonly_public_key_richcompare},
    {Py_tp_methods, xonly_public_key_methods},
    {Py_tp_getset, xonly_public_key_getset},
    {0, NULL}
};

static PyType_Spec xonly_public_key_spec = {
    .name = "coincurve.XOnlyPublicKey",
    .basicsize = sizeof(XOnlyPublicKeyObject),
    .itemsize = 0,
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_IMMUTABLETYPE,
    .slots = xonly_public_key_slots,
};

PyObject *cc_create_xonly_public_key_type(PyObject *module)
{
    return PyType_FromModuleAndSpec(module, &xonly_public_key_spec, NULL);
}
