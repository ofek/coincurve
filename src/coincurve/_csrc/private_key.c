#include "coincurve.h"

#include <string.h>

static PyObject *
private_key_allocate(PyTypeObject *type, const unsigned char secret[CC_SECRET_SIZE])
{
    CoincurveState *state = cc_state_from_type(type);
    PrivateKeyObject *self;
    secp256k1_pubkey public_key;
    secp256k1_xonly_pubkey xonly_public_key;
    int parity = 0;
    int valid;
    int created;

    if (state == NULL) {
        return NULL;
    }
    valid = secp256k1_ec_seckey_verify(state->context, secret);
    if (!valid) {
        PyErr_SetString(
            PyExc_ValueError,
            "Secret must encode an integer greater than zero and less than the curve order."
        );
        return NULL;
    }

    self = (PrivateKeyObject *)type->tp_alloc(type, 0);
    if (self == NULL) {
        return NULL;
    }
    memcpy(self->secret, secret, CC_SECRET_SIZE);
    Py_BEGIN_ALLOW_THREADS created =
        secp256k1_keypair_create(state->context, &self->keypair, self->secret);
    Py_END_ALLOW_THREADS if (!created)
    {
        PyErr_SetString(PyExc_ValueError, "Secret must encode a valid secp256k1 private key.");
        goto error;
    }
    created = secp256k1_keypair_pub(state->context, &public_key, &self->keypair);
    if (!created) {
        PyErr_SetString(PyExc_RuntimeError, "Could not derive the public key.");
        goto error;
    }
    self->public_key =
        cc_public_key_from_native((PyTypeObject *)state->public_key_type, &public_key);
    if (self->public_key == NULL) {
        goto error;
    }
    created =
        secp256k1_keypair_xonly_pub(state->context, &xonly_public_key, &parity, &self->keypair);
    if (!created) {
        PyErr_SetString(PyExc_RuntimeError, "Could not derive the x-only public key.");
        goto error;
    }
    self->xonly_public_key = cc_xonly_public_key_from_native(
        (PyTypeObject *)state->xonly_public_key_type,
        &xonly_public_key,
        parity
    );
    if (self->xonly_public_key == NULL) {
        goto error;
    }
    return (PyObject *)self;

error:
    Py_DECREF(self);
    return NULL;
}

static PyObject *private_key_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    static char *keyword_names[] = {"secret", NULL};
    PyObject *secret_object = Py_None;
    CoincurveState *state = cc_state_from_type(type);
    unsigned char secret[CC_SECRET_SIZE];
    PyObject *result;

    if (state == NULL) {
        return NULL;
    }
    if (!PyArg_ParseTupleAndKeywords(
            args,
            kwargs,
            "|O:PrivateKey",
            keyword_names,
            &secret_object
        )) {
        return NULL;
    }
    if (secret_object == Py_None) {
        do {
            if (cc_random_bytes(state, secret, sizeof(secret)) < 0) {
                cc_secure_zero(secret, sizeof(secret));
                return NULL;
            }
        } while (!secp256k1_ec_seckey_verify(state->context, secret));
    } else if (cc_copy_fixed(secret_object, secret, sizeof(secret), "secret") < 0) {
        return NULL;
    }

    result = private_key_allocate(type, secret);
    cc_secure_zero(secret, sizeof(secret));
    return result;
}

static void private_key_dealloc(PrivateKeyObject *self)
{
    PyTypeObject *type = Py_TYPE(self);
    Py_CLEAR(self->public_key);
    Py_CLEAR(self->xonly_public_key);
    cc_secure_zero(self->secret, sizeof(self->secret));
    cc_secure_zero(&self->keypair, sizeof(self->keypair));
    type->tp_free((PyObject *)self);
    Py_DECREF(type);
}

static PyObject *private_key_repr(PrivateKeyObject *self)
{
    return PyUnicode_FromFormat("%s(<redacted>)", Py_TYPE(self)->tp_name);
}

static PyObject *private_key_richcompare(PyObject *left, PyObject *right, int operation)
{
    const PrivateKeyObject *left_key;
    const PrivateKeyObject *right_key;
    unsigned char difference = 0;
    size_t index;
    int equal;

    if (Py_TYPE(left) != Py_TYPE(right)) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    if (operation != Py_EQ && operation != Py_NE) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    left_key = (const PrivateKeyObject *)left;
    right_key = (const PrivateKeyObject *)right;
    for (index = 0; index < CC_SECRET_SIZE; index++) {
        difference |= left_key->secret[index] ^ right_key->secret[index];
    }
    equal = difference == 0;
    if ((operation == Py_EQ && equal) || (operation == Py_NE && !equal)) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static Py_hash_t private_key_hash(PrivateKeyObject *self)
{
    PublicKeyObject *public_key = (PublicKeyObject *)self->public_key;
    return cc_hash_data(public_key->compressed, (Py_ssize_t)sizeof(public_key->compressed));
}

static PyObject *private_key_get_secret(PrivateKeyObject *self, void *closure)
{
    (void)closure;
    return cc_bytes_from_data(self->secret, sizeof(self->secret));
}

static PyObject *private_key_get_public_key(PrivateKeyObject *self, void *closure)
{
    (void)closure;
    return Py_NewRef(self->public_key);
}

static PyObject *private_key_get_xonly_public_key(PrivateKeyObject *self, void *closure)
{
    (void)closure;
    return Py_NewRef(self->xonly_public_key);
}

static PyObject *private_key_sign_digest_native(
    PrivateKeyObject *self,
    const unsigned char digest[CC_DIGEST_SIZE],
    PyObject *extra_entropy_object,
    int recoverable
)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char entropy[CC_SECRET_SIZE];
    const unsigned char *extra_entropy = NULL;
    unsigned char der_output[CC_MAX_DER_SIGNATURE_SIZE];
    unsigned char *output = der_output;
    size_t output_size = sizeof(der_output);
    PyObject *fixed_output = NULL;
    int signed_result;

    if (state == NULL) {
        return NULL;
    }
    if (cc_copy_optional_fixed(
            extra_entropy_object,
            entropy,
            sizeof(entropy),
            &extra_entropy,
            "extra_entropy"
        ) < 0) {
        return NULL;
    }
    if (recoverable) {
        fixed_output = PyBytes_FromStringAndSize(NULL, CC_RECOVERABLE_SIGNATURE_SIZE);
        if (fixed_output == NULL) {
            cc_secure_zero(entropy, sizeof(entropy));
            return NULL;
        }
        output = (unsigned char *)PyBytes_AS_STRING(fixed_output);
    }

    Py_BEGIN_ALLOW_THREADS if (recoverable)
    {
        signed_result =
            cc_ecdsa_sign_recoverable(state->context, self->secret, digest, extra_entropy, output);
        output_size = CC_RECOVERABLE_SIGNATURE_SIZE;
    }
    else
    {
        signed_result = cc_ecdsa_sign_der(
            state->context,
            self->secret,
            digest,
            extra_entropy,
            output,
            &output_size
        );
    }
    Py_END_ALLOW_THREADS cc_secure_zero(entropy, sizeof(entropy));
    if (!signed_result) {
        Py_XDECREF(fixed_output);
        PyErr_SetString(PyExc_RuntimeError, "libsecp256k1 could not create the signature.");
        return NULL;
    }
    if (recoverable) {
        return fixed_output;
    }
    return cc_bytes_from_data(der_output, (Py_ssize_t)output_size);
}

static PyObject *private_key_sign_digest_impl(
    PrivateKeyObject *self,
    PyObject *digest_object,
    PyObject *extra_entropy_object,
    int recoverable
)
{
    unsigned char digest[CC_DIGEST_SIZE];

    if (cc_copy_fixed(digest_object, digest, sizeof(digest), "digest") < 0) {
        return NULL;
    }
    return private_key_sign_digest_native(self, digest, extra_entropy_object, recoverable);
}

static PyObject *private_key_sign_digest_method(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames,
    const char *name,
    int recoverable
)
{
    static const char *const names[] = {"digest", "extra_entropy"};
    PyObject *values[2];

    if (cc_parse_fastcall(args, nargs, kwnames, name, names, 2, 1, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL) {
        PyErr_Format(PyExc_TypeError, "%s() requires a digest.", name);
        return NULL;
    }
    return private_key_sign_digest_impl(self, values[0], values[1], recoverable);
}

static PyObject *private_key_sign_message_method(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames,
    const char *name,
    int recoverable
)
{
    static const char *const names[] = {"message", "hasher", "extra_entropy"};
    PyObject *values[3];
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char digest[CC_DIGEST_SIZE];

    if (state == NULL) {
        return NULL;
    }
    if (cc_parse_fastcall(args, nargs, kwnames, name, names, 3, 2, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL) {
        PyErr_Format(PyExc_TypeError, "%s() requires a message.", name);
        return NULL;
    }
    if (cc_hash_message(state, values[0], values[1], digest) < 0) {
        return NULL;
    }
    return private_key_sign_digest_native(self, digest, values[2], recoverable);
}

static PyObject *private_key_sign_digest(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    return private_key_sign_digest_method(self, args, nargs, kwnames, "sign_digest", 0);
}

static PyObject *
private_key_sign(PrivateKeyObject *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    return private_key_sign_message_method(self, args, nargs, kwnames, "sign", 0);
}

static PyObject *private_key_sign_recoverable_digest(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    return private_key_sign_digest_method(self, args, nargs, kwnames, "sign_recoverable_digest", 1);
}

static PyObject *private_key_sign_recoverable(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    return private_key_sign_message_method(self, args, nargs, kwnames, "sign_recoverable", 1);
}

static PyObject *private_key_sign_schnorr_digest_native(
    PrivateKeyObject *self,
    const unsigned char digest[CC_DIGEST_SIZE],
    PyObject *aux_randomness_object
)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    CoincurveBuffer aux_randomness_buffer = {0};
    unsigned char aux_randomness[CC_SECRET_SIZE] = {0};
    const unsigned char *aux_randomness_pointer = aux_randomness;
    PyObject *output;
    int generate_randomness = 0;
    int signed_result;

    if (state == NULL) {
        return NULL;
    }
    if (aux_randomness_object == NULL) {
        generate_randomness = 1;
    } else if (aux_randomness_object == Py_None) {
        aux_randomness_pointer = NULL;
    } else {
        if (cc_get_buffer(aux_randomness_object, &aux_randomness_buffer, "aux_randomness") < 0) {
            return NULL;
        }
        if (aux_randomness_buffer.view.len == 0) {
            generate_randomness = 1;
        } else if (aux_randomness_buffer.view.len != CC_SECRET_SIZE) {
            cc_release_buffer(&aux_randomness_buffer);
            PyErr_Format(
                PyExc_ValueError,
                "aux_randomness must be exactly %d bytes long.",
                CC_SECRET_SIZE
            );
            return NULL;
        } else {
            memcpy(aux_randomness, aux_randomness_buffer.view.buf, sizeof(aux_randomness));
        }
        cc_release_buffer(&aux_randomness_buffer);
    }
    if (generate_randomness) {
        if (cc_random_bytes(state, aux_randomness, sizeof(aux_randomness)) < 0) {
            cc_secure_zero(aux_randomness, sizeof(aux_randomness));
            return NULL;
        }
    }
    output = PyBytes_FromStringAndSize(NULL, CC_COMPACT_SIGNATURE_SIZE);
    if (output == NULL) {
        cc_secure_zero(aux_randomness, sizeof(aux_randomness));
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS signed_result = secp256k1_schnorrsig_sign32(
        state->context,
        (unsigned char *)PyBytes_AS_STRING(output),
        digest,
        &self->keypair,
        aux_randomness_pointer
    );
    Py_END_ALLOW_THREADS cc_secure_zero(aux_randomness, sizeof(aux_randomness));
    if (!signed_result) {
        Py_DECREF(output);
        PyErr_SetString(PyExc_RuntimeError, "libsecp256k1 could not create the Schnorr signature.");
        return NULL;
    }
    return output;
}

static PyObject *private_key_sign_schnorr_digest_impl(
    PrivateKeyObject *self,
    PyObject *digest_object,
    PyObject *aux_randomness_object
)
{
    unsigned char digest[CC_DIGEST_SIZE];

    if (cc_copy_fixed(digest_object, digest, sizeof(digest), "digest") < 0) {
        return NULL;
    }
    return private_key_sign_schnorr_digest_native(self, digest, aux_randomness_object);
}

static PyObject *private_key_sign_schnorr_method(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames,
    const char *name,
    const char *input_name,
    Py_ssize_t positional_limit
)
{
    const char *names[] = {input_name, "aux_randomness"};
    PyObject *values[2];

    if (cc_parse_fastcall(args, nargs, kwnames, name, names, 2, positional_limit, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL) {
        PyErr_Format(PyExc_TypeError, "%s() requires a %s.", name, input_name);
        return NULL;
    }
    return private_key_sign_schnorr_digest_impl(self, values[0], values[1]);
}

static PyObject *private_key_sign_schnorr_digest(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    return private_key_sign_schnorr_method(
        self,
        args,
        nargs,
        kwnames,
        "sign_schnorr_digest",
        "digest",
        1
    );
}

static PyObject *private_key_sign_schnorr(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    return private_key_sign_schnorr_method(
        self,
        args,
        nargs,
        kwnames,
        "sign_schnorr",
        "message",
        2
    );
}

static PyObject *private_key_sign_schnorr_message(
    PrivateKeyObject *self,
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames
)
{
    static const char *const names[] = {"message", "hasher", "aux_randomness"};
    PyObject *values[3];
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char digest[CC_DIGEST_SIZE];

    if (state == NULL) {
        return NULL;
    }
    if (cc_parse_fastcall(args, nargs, kwnames, "sign_schnorr_message", names, 3, 2, values) < 0) {
        return NULL;
    }
    if (values[0] == NULL) {
        PyErr_SetString(PyExc_TypeError, "sign_schnorr_message() requires a message.");
        return NULL;
    }
    if (cc_hash_message(state, values[0], values[1], digest) < 0) {
        return NULL;
    }
    return private_key_sign_schnorr_digest_native(self, digest, values[2]);
}

static PyObject *private_key_ecdh(PrivateKeyObject *self, PyObject *peer_object)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    secp256k1_pubkey peer;
    PyObject *output;
    int result;

    if (state == NULL) {
        return NULL;
    }
    if (cc_public_key_from_object(state, peer_object, &peer, "peer_public_key") < 0) {
        return NULL;
    }
    output = PyBytes_FromStringAndSize(NULL, CC_DIGEST_SIZE);
    if (output == NULL) {
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS result =
        cc_ecdh(state->context, self->secret, &peer, (unsigned char *)PyBytes_AS_STRING(output));
    Py_END_ALLOW_THREADS if (!result)
    {
        Py_DECREF(output);
        PyErr_SetString(PyExc_ValueError, "Could not derive the ECDH shared secret.");
        return NULL;
    }
    return output;
}

static PyObject *private_key_tweak(PrivateKeyObject *self, PyObject *scalar_object, int multiply)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    unsigned char scalar[CC_SECRET_SIZE];
    unsigned char secret[CC_SECRET_SIZE];
    int result;
    PyObject *new_key;

    if (state == NULL) {
        return NULL;
    }
    if (cc_copy_scalar(scalar_object, scalar, "scalar") < 0) {
        return NULL;
    }
    memcpy(secret, self->secret, sizeof(secret));
    Py_BEGIN_ALLOW_THREADS if (multiply)
    {
        result = secp256k1_ec_seckey_tweak_mul(state->context, secret, scalar);
    }
    else
    {
        result = secp256k1_ec_seckey_tweak_add(state->context, secret, scalar);
    }
    Py_END_ALLOW_THREADS cc_secure_zero(scalar, sizeof(scalar));
    if (!result) {
        cc_secure_zero(secret, sizeof(secret));
        PyErr_SetString(PyExc_ValueError, "The scalar or resulting private key is invalid.");
        return NULL;
    }
    new_key = private_key_allocate(Py_TYPE(self), secret);
    cc_secure_zero(secret, sizeof(secret));
    return new_key;
}

static PyObject *private_key_add(PrivateKeyObject *self, PyObject *scalar_object)
{
    return private_key_tweak(self, scalar_object, 0);
}

static PyObject *private_key_multiply(PrivateKeyObject *self, PyObject *scalar_object)
{
    return private_key_tweak(self, scalar_object, 1);
}

static PyObject *private_key_to_int(PrivateKeyObject *self, PyObject *ignored)
{
    (void)ignored;
    return cc_integer_from_bytes(self->secret, sizeof(self->secret));
}

static PyObject *private_key_to_hex(PrivateKeyObject *self, PyObject *ignored)
{
    (void)ignored;
    return cc_hex_from_data(self->secret, sizeof(self->secret));
}

static PyObject *
call_module_function(const char *module_name, const char *function_name, PyObject *args)
{
    PyObject *module = PyImport_ImportModule(module_name);
    PyObject *function;
    PyObject *result;

    if (module == NULL) {
        return NULL;
    }
    function = PyObject_GetAttrString(module, function_name);
    Py_DECREF(module);
    if (function == NULL) {
        return NULL;
    }
    result = PyObject_CallObject(function, args);
    Py_DECREF(function);
    return result;
}

static PyObject *private_key_to_der(PrivateKeyObject *self, PyObject *ignored)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    secp256k1_pubkey public_key;
    unsigned char serialized[CC_PUBLIC_KEY_UNCOMPRESSED_SIZE];
    size_t serialized_size = sizeof(serialized);
    PyObject *secret;
    PyObject *public_bytes;
    PyObject *args;
    PyObject *result;

    (void)ignored;

    if (state == NULL) {
        return NULL;
    }
    if (!secp256k1_keypair_pub(state->context, &public_key, &self->keypair) ||
        !secp256k1_ec_pubkey_serialize(
            state->context,
            serialized,
            &serialized_size,
            &public_key,
            SECP256K1_EC_UNCOMPRESSED
        )) {
        PyErr_SetString(PyExc_RuntimeError, "Could not serialize the public key.");
        return NULL;
    }
    secret = cc_bytes_from_data(self->secret, sizeof(self->secret));
    public_bytes = cc_bytes_from_data(serialized, (Py_ssize_t)serialized_size);
    if (secret == NULL || public_bytes == NULL) {
        Py_XDECREF(secret);
        Py_XDECREF(public_bytes);
        return NULL;
    }
    args = PyTuple_Pack(2, secret, public_bytes);
    Py_DECREF(secret);
    Py_DECREF(public_bytes);
    if (args == NULL) {
        return NULL;
    }
    result = call_module_function("coincurve.der", "encode_der", args);
    Py_DECREF(args);
    return result;
}

static PyObject *private_key_to_pem(PrivateKeyObject *self, PyObject *ignored)
{
    PyObject *der = private_key_to_der(self, NULL);
    PyObject *args;
    PyObject *result;

    (void)ignored;
    if (der == NULL) {
        return NULL;
    }
    args = PyTuple_Pack(1, der);
    Py_DECREF(der);
    if (args == NULL) {
        return NULL;
    }
    result = call_module_function("coincurve.utils", "der_to_pem", args);
    Py_DECREF(args);
    return result;
}

static PyObject *private_key_from_int(PyObject *type_object, PyObject *integer)
{
    PyObject *bytes_object = cc_integer_to_32_bytes(integer, "value");
    unsigned char secret[CC_SECRET_SIZE];
    PyObject *result;

    if (bytes_object == NULL) {
        return NULL;
    }
    memcpy(secret, PyBytes_AS_STRING(bytes_object), sizeof(secret));
    Py_DECREF(bytes_object);
    result = private_key_allocate((PyTypeObject *)type_object, secret);
    cc_secure_zero(secret, sizeof(secret));
    return result;
}

static int hex_nibble(char character)
{
    if (character >= '0' && character <= '9') {
        return character - '0';
    }
    if (character >= 'a' && character <= 'f') {
        return character - 'a' + 10;
    }
    if (character >= 'A' && character <= 'F') {
        return character - 'A' + 10;
    }
    return -1;
}

static PyObject *private_key_from_hex(PyObject *type_object, PyObject *hex_object)
{
    const char *text;
    Py_ssize_t length;
    Py_ssize_t source_index = 0;
    Py_ssize_t destination_index;
    unsigned char secret[CC_SECRET_SIZE] = {0};
    PyObject *result;

    if (!PyUnicode_Check(hex_object)) {
        PyErr_SetString(PyExc_TypeError, "value must be a hexadecimal string.");
        return NULL;
    }
    text = PyUnicode_AsUTF8AndSize(hex_object, &length);
    if (text == NULL) {
        return NULL;
    }
    if (length < 1 || length > CC_SECRET_SIZE * 2) {
        PyErr_SetString(
            PyExc_ValueError,
            "The hexadecimal secret must encode between 1 and 32 bytes."
        );
        return NULL;
    }
    destination_index = CC_SECRET_SIZE - (length + 1) / 2;
    if (length % 2 != 0) {
        int nibble = hex_nibble(text[source_index++]);
        if (nibble < 0) {
            goto invalid;
        }
        secret[destination_index++] = (unsigned char)nibble;
    }
    while (source_index < length) {
        int high = hex_nibble(text[source_index]);
        int low = hex_nibble(text[source_index + 1]);
        if (high < 0 || low < 0) {
            goto invalid;
        }
        secret[destination_index++] = (unsigned char)((high << 4) | low);
        source_index += 2;
    }
    result = private_key_allocate((PyTypeObject *)type_object, secret);
    cc_secure_zero(secret, sizeof(secret));
    return result;

invalid:
    cc_secure_zero(secret, sizeof(secret));
    PyErr_SetString(PyExc_ValueError, "value must contain only hexadecimal digits.");
    return NULL;
}

static PyObject *private_key_from_der(PyObject *type_object, PyObject *der_object)
{
    PyObject *args = PyTuple_Pack(1, der_object);
    PyObject *secret_object;
    unsigned char secret[CC_SECRET_SIZE];
    PyObject *result;

    if (args == NULL) {
        return NULL;
    }
    secret_object = call_module_function("coincurve.der", "decode_der", args);
    Py_DECREF(args);
    if (secret_object == NULL) {
        return NULL;
    }
    if (cc_copy_fixed(secret_object, secret, sizeof(secret), "decoded secret") < 0) {
        Py_DECREF(secret_object);
        return NULL;
    }
    Py_DECREF(secret_object);
    result = private_key_allocate((PyTypeObject *)type_object, secret);
    cc_secure_zero(secret, sizeof(secret));
    return result;
}

static PyObject *private_key_from_pem(PyObject *type_object, PyObject *pem_object)
{
    PyObject *args = PyTuple_Pack(1, pem_object);
    PyObject *der;
    PyObject *result;

    if (args == NULL) {
        return NULL;
    }
    der = call_module_function("coincurve.utils", "pem_to_der", args);
    Py_DECREF(args);
    if (der == NULL) {
        return NULL;
    }
    result = private_key_from_der(type_object, der);
    Py_DECREF(der);
    return result;
}

static PyGetSetDef private_key_getset[] = {
    {"secret", (getter)private_key_get_secret, NULL, "The 32-byte private key secret.", NULL},
    {"public_key", (getter)private_key_get_public_key, NULL, "The corresponding public key.", NULL},
    {"xonly_public_key",
     (getter)private_key_get_xonly_public_key,
     NULL,
     "The corresponding x-only public key.",
     NULL},
    {NULL, NULL, NULL, NULL, NULL}
};

static PyMethodDef private_key_methods[] = {
    {"sign_many",
     (PyCFunction)(void (*)(void))cc_private_key_sign_many,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_many($self, messages, hasher=..., *, extra_entropy=None)\n--\n\nSign a sequence of "
     "messages."},
    {"sign_digests",
     (PyCFunction)(void (*)(void))cc_private_key_sign_digests,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_digests($self, digests, *, extra_entropy=None)\n--\n\nSign a sequence of 32-byte "
     "digests."},
    {"sign_recoverable_many",
     (PyCFunction)(void (*)(void))cc_private_key_sign_recoverable_many,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_recoverable_many($self, messages, hasher=..., *, extra_entropy=None)\n--\n\nCreate "
     "recoverable "
     "signatures for a sequence of messages."},
    {"sign_recoverable_digests",
     (PyCFunction)(void (*)(void))cc_private_key_sign_recoverable_digests,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_recoverable_digests($self, digests, *, extra_entropy=None)\n--\n\nCreate recoverable "
     "signatures for a "
     "sequence of digests."},
    {"sign_schnorr_many",
     (PyCFunction)(void (*)(void))cc_private_key_sign_schnorr_many,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_schnorr_many($self, messages, hasher=..., *, aux_randomness=None)\n--\n\nCreate "
     "Schnorr signatures for "
     "a sequence of messages."},
    {"sign_schnorr_digests",
     (PyCFunction)(void (*)(void))cc_private_key_sign_schnorr_digests,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_schnorr_digests($self, digests, *, aux_randomness=None)\n--\n\nCreate Schnorr "
     "signatures for a sequence "
     "of digests."},
    {"ecdh_many",
     (PyCFunction)cc_private_key_ecdh_many,
     METH_O,
     "ecdh_many($self, peer_public_keys, /)\n--\n\nDerive shared secrets for a sequence of public "
     "keys."},
    {"sign",
     (PyCFunction)(void (*)(void))private_key_sign,
     METH_FASTCALL | METH_KEYWORDS,
     "sign($self, message, hasher=..., *, extra_entropy=None)\n--\n\nCreate a DER-encoded ECDSA "
     "signature."},
    {"sign_digest",
     (PyCFunction)(void (*)(void))private_key_sign_digest,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_digest($self, digest, *, extra_entropy=None)\n--\n\nCreate a DER-encoded ECDSA "
     "signature over a 32-byte "
     "digest."},
    {"sign_recoverable",
     (PyCFunction)(void (*)(void))private_key_sign_recoverable,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_recoverable($self, message, hasher=..., *, extra_entropy=None)\n--\n\nCreate a "
     "recoverable ECDSA "
     "signature."},
    {"sign_recoverable_digest",
     (PyCFunction)(void (*)(void))private_key_sign_recoverable_digest,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_recoverable_digest($self, digest, *, extra_entropy=None)\n--\n\nCreate a recoverable "
     "ECDSA signature "
     "over a 32-byte digest."},
    {"sign_schnorr",
     (PyCFunction)(void (*)(void))private_key_sign_schnorr,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_schnorr($self, message, aux_randomness=b'')\n--\n\nCreate a BIP340 Schnorr "
     "signature over an exactly 32-byte message."},
    {"sign_schnorr_message",
     (PyCFunction)(void (*)(void))private_key_sign_schnorr_message,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_schnorr_message($self, message, hasher=..., *, aux_randomness=b'')\n--\n\nCreate "
     "a BIP340 Schnorr signature over a hashed message."},
    {"sign_schnorr_digest",
     (PyCFunction)(void (*)(void))private_key_sign_schnorr_digest,
     METH_FASTCALL | METH_KEYWORDS,
     "sign_schnorr_digest($self, digest, *, aux_randomness=b'')\n--\n\nCreate a BIP340 Schnorr "
     "signature over a "
     "32-byte digest."},
    {"ecdh",
     (PyCFunction)private_key_ecdh,
     METH_O,
     "ecdh($self, peer_public_key, /)\n--\n\nDerive an ECDH shared secret."},
    {"add",
     (PyCFunction)private_key_add,
     METH_O,
     "add($self, scalar, /)\n--\n\nReturn a private key with the scalar added."},
    {"multiply",
     (PyCFunction)private_key_multiply,
     METH_O,
     "multiply($self, scalar, /)\n--\n\nReturn a private key multiplied by the scalar."},
    {"to_int",
     (PyCFunction)private_key_to_int,
     METH_NOARGS,
     "to_int($self, /)\n--\n\nReturn the private key as an integer."},
    {"to_hex",
     (PyCFunction)private_key_to_hex,
     METH_NOARGS,
     "to_hex($self, /)\n--\n\nReturn the private key as hexadecimal text."},
    {"to_der",
     (PyCFunction)private_key_to_der,
     METH_NOARGS,
     "to_der($self, /)\n--\n\nReturn the private key in PKCS#8 DER form."},
    {"to_pem",
     (PyCFunction)private_key_to_pem,
     METH_NOARGS,
     "to_pem($self, /)\n--\n\nReturn the private key in PKCS#8 PEM form."},
    {"from_int",
     (PyCFunction)private_key_from_int,
     METH_CLASS | METH_O,
     "from_int($type, value, /)\n--\n\nCreate a private key from an integer."},
    {"from_hex",
     (PyCFunction)private_key_from_hex,
     METH_CLASS | METH_O,
     "from_hex($type, value, /)\n--\n\nCreate a private key from hexadecimal text."},
    {"from_der",
     (PyCFunction)private_key_from_der,
     METH_CLASS | METH_O,
     "from_der($type, value, /)\n--\n\nCreate a private key from PKCS#8 DER."},
    {"from_pem",
     (PyCFunction)private_key_from_pem,
     METH_CLASS | METH_O,
     "from_pem($type, value, /)\n--\n\nCreate a private key from PKCS#8 PEM."},
    {NULL, NULL, 0, NULL}
};

static PyType_Slot private_key_slots[] = {
    {Py_tp_doc, "PrivateKey(secret=None)\n--\n\nAn immutable secp256k1 private key."},
    {Py_tp_new, private_key_new},
    {Py_tp_dealloc, private_key_dealloc},
    {Py_tp_repr, private_key_repr},
    {Py_tp_hash, private_key_hash},
    {Py_tp_richcompare, private_key_richcompare},
    {Py_tp_methods, private_key_methods},
    {Py_tp_getset, private_key_getset},
    {0, NULL}
};

static PyType_Spec private_key_spec = {
    .name = "coincurve.PrivateKey",
    .basicsize = sizeof(PrivateKeyObject),
    .itemsize = 0,
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_IMMUTABLETYPE,
    .slots = private_key_slots,
};

PyObject *cc_create_private_key_type(PyObject *module)
{
    return PyType_FromModuleAndSpec(module, &private_key_spec, NULL);
}
