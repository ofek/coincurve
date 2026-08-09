#include "coincurve.h"

#include <limits.h>
#include <string.h>

enum {
    CC_BATCH_ECDSA = 0,
    CC_BATCH_RECOVERABLE = 1,
    CC_BATCH_SCHNORR = 2,
};

static void *batch_allocate(Py_ssize_t count, size_t width)
{
    void *memory;
    if (count < 0 || width == 0 || (size_t)count > (size_t)PY_SSIZE_T_MAX / width) {
        PyErr_SetString(PyExc_OverflowError, "The batch is too large.");
        return NULL;
    }
    memory = PyMem_Malloc(count == 0 ? 1 : (size_t)count * width);
    if (memory == NULL) {
        PyErr_NoMemory();
    }
    return memory;
}

static PyObject *batch_materialize(PyObject *object, const char *error_message)
{
    PyObject *sequence = PySequence_Fast(object, error_message);
    PyObject *snapshot;

    if (sequence == NULL || PyTuple_CheckExact(sequence)) {
        return sequence;
    }
    snapshot = PyList_AsTuple(sequence);
    Py_DECREF(sequence);
    return snapshot;
}

static void batch_add_hash_error_note(const char *name, Py_ssize_t index)
{
#if PY_VERSION_HEX >= 0x030B0000
    PyObject *error_type = NULL;
    PyObject *error_value = NULL;
    PyObject *traceback = NULL;
    PyObject *note;
    PyObject *result;

    PyErr_Fetch(&error_type, &error_value, &traceback);
    PyErr_NormalizeException(&error_type, &error_value, &traceback);
    note = PyUnicode_FromFormat("The hasher failed for %s[%zd].", name, index);
    if (note != NULL && error_value != NULL) {
        result = PyObject_CallMethod(error_value, "add_note", "O", note);
        if (result == NULL) {
            PyErr_Clear();
        } else {
            Py_DECREF(result);
        }
    } else {
        PyErr_Clear();
    }
    Py_XDECREF(note);
    PyErr_Restore(error_type, error_value, traceback);
#else
    (void)name;
    (void)index;
#endif
}

static int batch_copy_sequence(
    PyObject *object,
    const char *name,
    Py_ssize_t width,
    int sensitive,
    PyObject **sequence,
    unsigned char **data,
    Py_ssize_t *count
)
{
    Py_ssize_t index;

    *sequence = batch_materialize(object, "Batch inputs must be iterable.");
    if (*sequence == NULL) {
        return -1;
    }
    *count = PySequence_Fast_GET_SIZE(*sequence);
    *data = batch_allocate(*count, (size_t)width);
    if (*data == NULL) {
        Py_CLEAR(*sequence);
        return -1;
    }
    for (index = 0; index < *count; index++) {
        if (cc_copy_fixed_item(
                PySequence_Fast_GET_ITEM(*sequence, index),
                *data + (size_t)index * (size_t)width,
                width,
                name,
                index
            ) < 0) {
            if (sensitive) {
                cc_secure_zero(*data, (size_t)index * (size_t)width);
            }
            PyMem_Free(*data);
            *data = NULL;
            Py_CLEAR(*sequence);
            return -1;
        }
    }
    return 0;
}

static int batch_hash_sequence(
    CoincurveState *state,
    PyObject *object,
    PyObject *hasher,
    const char *name,
    PyObject **sequence,
    unsigned char **digests,
    Py_ssize_t *count
)
{
    Py_ssize_t index;

    *sequence = batch_materialize(object, "Messages must be iterable.");
    if (*sequence == NULL) {
        return -1;
    }
    *count = PySequence_Fast_GET_SIZE(*sequence);
    *digests = batch_allocate(*count, CC_DIGEST_SIZE);
    if (*digests == NULL) {
        Py_CLEAR(*sequence);
        return -1;
    }
    for (index = 0; index < *count; index++) {
        if (cc_hash_message(
                state,
                PySequence_Fast_GET_ITEM(*sequence, index),
                hasher,
                *digests + (size_t)index * CC_DIGEST_SIZE
            ) < 0) {
            batch_add_hash_error_note(name, index);
            PyMem_Free(*digests);
            *digests = NULL;
            Py_CLEAR(*sequence);
            return -1;
        }
    }
    return 0;
}

static int batch_check_equal(Py_ssize_t left, Py_ssize_t right)
{
    if (left != right) {
        PyErr_Format(
            PyExc_ValueError,
            "Pairwise batch inputs must have equal lengths, got %zd and %zd.",
            left,
            right
        );
        return -1;
    }
    return 0;
}

static PyObject *batch_fixed_result(const unsigned char *data, Py_ssize_t count, Py_ssize_t width)
{
    PyObject *result = PyList_New(count);
    Py_ssize_t index;

    if (result == NULL) {
        return NULL;
    }
    for (index = 0; index < count; index++) {
        PyObject *item = cc_bytes_from_data(data + (size_t)index * (size_t)width, width);
        if (item == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyList_SET_ITEM(result, index, item);
    }
    return result;
}

static PyObject *batch_boolean_result(const unsigned char *statuses, Py_ssize_t count)
{
    PyObject *result = PyList_New(count);
    Py_ssize_t index;

    if (result == NULL) {
        return NULL;
    }
    for (index = 0; index < count; index++) {
        PyObject *item = statuses[index] ? Py_True : Py_False;
        Py_INCREF(item);
        PyList_SET_ITEM(result, index, item);
    }
    return result;
}

static PyObject *
batch_der_result(const unsigned char *outputs, const size_t *sizes, Py_ssize_t count)
{
    PyObject *result = PyList_New(count);
    Py_ssize_t index;

    if (result == NULL) {
        return NULL;
    }
    for (index = 0; index < count; index++) {
        PyObject *item = cc_bytes_from_data(
            outputs + (size_t)index * CC_MAX_DER_SIGNATURE_SIZE,
            (Py_ssize_t)sizes[index]
        );
        if (item == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyList_SET_ITEM(result, index, item);
    }
    return result;
}

static unsigned char *batch_fill_randomness(CoincurveState *state, Py_ssize_t count)
{
    unsigned char *randomness = batch_allocate(count, CC_SECRET_SIZE);

    if (randomness == NULL) {
        return NULL;
    }
    if (cc_random_bytes(state, randomness, count * CC_SECRET_SIZE) < 0) {
        PyMem_Free(randomness);
        return NULL;
    }
    return randomness;
}

static PyObject *private_key_sign_batch(
    PrivateKeyObject *self,
    PyObject *inputs,
    PyObject *hasher,
    PyObject *option,
    int messages,
    int mode
)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    PyObject *sequence = NULL;
    unsigned char *digests = NULL;
    unsigned char *outputs = NULL;
    size_t *sizes = NULL;
    unsigned char option_bytes[CC_SECRET_SIZE];
    const unsigned char *shared_option = NULL;
    unsigned char *randomness = NULL;
    Py_ssize_t count = 0;
    Py_ssize_t width = mode == CC_BATCH_ECDSA
                           ? CC_MAX_DER_SIGNATURE_SIZE
                           : (mode == CC_BATCH_RECOVERABLE ? CC_RECOVERABLE_SIGNATURE_SIZE
                                                           : CC_COMPACT_SIGNATURE_SIZE);
    Py_ssize_t index;
    int success = 1;
    PyObject *result = NULL;

    if (state == NULL) {
        return NULL;
    }
    if (messages) {
        if (batch_hash_sequence(state, inputs, hasher, "messages", &sequence, &digests, &count) <
            0) {
            return NULL;
        }
    } else if (
        batch_copy_sequence(inputs, "digests", CC_DIGEST_SIZE, 0, &sequence, &digests, &count) < 0
    ) {
        return NULL;
    }
    if (mode == CC_BATCH_SCHNORR && (option == NULL || option == Py_None)) {
        randomness = batch_fill_randomness(state, count);
        if (randomness == NULL) {
            goto cleanup;
        }
    } else if (
        cc_copy_optional_fixed(
            option,
            option_bytes,
            sizeof(option_bytes),
            &shared_option,
            mode == CC_BATCH_SCHNORR ? "aux_randomness" : "extra_entropy"
        ) < 0
    ) {
        goto cleanup;
    }
    outputs = batch_allocate(count, (size_t)width);
    if (outputs == NULL) {
        goto cleanup;
    }
    if (mode == CC_BATCH_ECDSA) {
        sizes = batch_allocate(count, sizeof(*sizes));
        if (sizes == NULL) {
            goto cleanup;
        }
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < count; index++)
    {
        unsigned char *output = outputs + (size_t)index * (size_t)width;
        const unsigned char *digest = digests + (size_t)index * CC_DIGEST_SIZE;
        const unsigned char *native_option =
            randomness != NULL ? randomness + (size_t)index * CC_SECRET_SIZE : shared_option;
        if (mode == CC_BATCH_ECDSA) {
            sizes[index] = CC_MAX_DER_SIGNATURE_SIZE;
            success = cc_ecdsa_sign_der(
                state->context,
                self->secret,
                digest,
                native_option,
                output,
                &sizes[index]
            );
        } else if (mode == CC_BATCH_RECOVERABLE) {
            success = cc_ecdsa_sign_recoverable(
                state->context,
                self->secret,
                digest,
                native_option,
                output
            );
        } else {
            success = secp256k1_schnorrsig_sign32(
                state->context,
                output,
                digest,
                &self->keypair,
                native_option
            );
        }
        if (!success) {
            break;
        }
    }
    Py_END_ALLOW_THREADS if (!success)
    {
        PyErr_SetString(PyExc_RuntimeError, "libsecp256k1 could not create a batch signature.");
        goto cleanup;
    }
    result = mode == CC_BATCH_ECDSA ? batch_der_result(outputs, sizes, count)
                                    : batch_fixed_result(outputs, count, width);

cleanup:
    cc_secure_zero(option_bytes, sizeof(option_bytes));
    if (randomness != NULL) {
        cc_secure_zero(randomness, (size_t)count * CC_SECRET_SIZE);
    }
    PyMem_Free(randomness);
    PyMem_Free(sizes);
    PyMem_Free(outputs);
    PyMem_Free(digests);
    Py_XDECREF(sequence);
    return result;
}

static int parse_instance_batch(
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames,
    const char *name,
    int messages,
    const char *option_name,
    PyObject **inputs,
    PyObject **hasher,
    PyObject **option
)
{
    const char *message_names[] = {"messages", "hasher", option_name};
    const char *digest_names[] = {"digests", option_name};
    PyObject *values[3] = {NULL, NULL, NULL};

    if (cc_parse_fastcall(
            args,
            nargs,
            kwnames,
            name,
            messages ? message_names : digest_names,
            messages ? 3 : 2,
            messages ? 2 : 1,
            values
        ) < 0) {
        return -1;
    }
    if (values[0] == NULL) {
        PyErr_Format(PyExc_TypeError, "%s() requires a batch input.", name);
        return -1;
    }
    *inputs = values[0];
    *hasher = messages ? values[1] : NULL;
    *option = messages ? values[2] : values[1];
    return 0;
}

#define DEFINE_PRIVATE_SIGN_BATCH(NAME, MESSAGES, MODE)                                            \
    PyObject *cc_private_key_##NAME(                                                               \
        PrivateKeyObject *self,                                                                    \
        PyObject *const *args,                                                                     \
        Py_ssize_t nargs,                                                                          \
        PyObject *kwnames                                                                          \
    )                                                                                              \
    {                                                                                              \
        PyObject *inputs;                                                                          \
        PyObject *hasher;                                                                          \
        PyObject *option;                                                                          \
        if (parse_instance_batch(                                                                  \
                args,                                                                              \
                nargs,                                                                             \
                kwnames,                                                                           \
                #NAME,                                                                             \
                MESSAGES,                                                                          \
                MODE == CC_BATCH_SCHNORR ? "aux_randomness" : "extra_entropy",                     \
                &inputs,                                                                           \
                &hasher,                                                                           \
                &option                                                                            \
            ) < 0) {                                                                               \
            return NULL;                                                                           \
        }                                                                                          \
        return private_key_sign_batch(self, inputs, hasher, option, MESSAGES, MODE);               \
    }

DEFINE_PRIVATE_SIGN_BATCH(sign_many, 1, CC_BATCH_ECDSA)
DEFINE_PRIVATE_SIGN_BATCH(sign_digests, 0, CC_BATCH_ECDSA)
DEFINE_PRIVATE_SIGN_BATCH(sign_recoverable_many, 1, CC_BATCH_RECOVERABLE)
DEFINE_PRIVATE_SIGN_BATCH(sign_recoverable_digests, 0, CC_BATCH_RECOVERABLE)
DEFINE_PRIVATE_SIGN_BATCH(sign_schnorr_many, 1, CC_BATCH_SCHNORR)
DEFINE_PRIVATE_SIGN_BATCH(sign_schnorr_digests, 0, CC_BATCH_SCHNORR)

PyObject *cc_private_key_ecdh_many(PrivateKeyObject *self, PyObject *peers_object)
{
    CoincurveState *state = cc_state_from_object((PyObject *)self);
    PyObject *peers = NULL;
    secp256k1_pubkey *native_peers = NULL;
    unsigned char *outputs = NULL;
    Py_ssize_t count;
    Py_ssize_t index;
    int success = 1;
    PyObject *result = NULL;

    if (state == NULL) {
        return NULL;
    }
    peers = batch_materialize(peers_object, "peer_public_keys must be iterable.");
    if (peers == NULL) {
        return NULL;
    }
    count = PySequence_Fast_GET_SIZE(peers);
    native_peers = batch_allocate(count, sizeof(*native_peers));
    outputs = batch_allocate(count, CC_DIGEST_SIZE);
    if (native_peers == NULL || outputs == NULL) {
        goto cleanup;
    }
    for (index = 0; index < count; index++) {
        PyObject *item = PySequence_Fast_GET_ITEM(peers, index);
        if (!PyObject_TypeCheck(item, (PyTypeObject *)state->public_key_type)) {
            PyErr_Format(PyExc_TypeError, "peer_public_keys[%zd] must be a PublicKey.", index);
            goto cleanup;
        }
        native_peers[index] = ((PublicKeyObject *)item)->public_key;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < count; index++)
    {
        success = cc_ecdh(
            state->context,
            self->secret,
            &native_peers[index],
            outputs + (size_t)index * CC_DIGEST_SIZE
        );
        if (!success) {
            break;
        }
    }
    Py_END_ALLOW_THREADS if (!success)
    {
        PyErr_SetString(PyExc_ValueError, "Could not derive a batch ECDH shared secret.");
        goto cleanup;
    }
    result = batch_fixed_result(outputs, count, CC_DIGEST_SIZE);

cleanup:
    if (outputs != NULL) {
        cc_secure_zero(outputs, (size_t)count * CC_DIGEST_SIZE);
    }
    PyMem_Free(outputs);
    PyMem_Free(native_peers);
    Py_DECREF(peers);
    return result;
}

static int batch_copy_signatures(
    PyObject *object,
    const char *name,
    int schnorr,
    PyObject **sequence,
    unsigned char **data,
    size_t **sizes,
    unsigned char **valid,
    Py_ssize_t *count
)
{
    Py_ssize_t index;
    Py_ssize_t width = schnorr ? CC_COMPACT_SIGNATURE_SIZE : CC_MAX_DER_SIGNATURE_SIZE;

    *sequence = batch_materialize(object, "signatures must be iterable.");
    if (*sequence == NULL) {
        return -1;
    }
    *count = PySequence_Fast_GET_SIZE(*sequence);
    *data = batch_allocate(*count, (size_t)width);
    *sizes = batch_allocate(*count, sizeof(**sizes));
    *valid = batch_allocate(*count, 1);
    if (*data == NULL || *sizes == NULL || *valid == NULL) {
        goto error;
    }
    memset(*data, 0, (size_t)*count * (size_t)width);
    for (index = 0; index < *count; index++) {
        PyObject *item = PySequence_Fast_GET_ITEM(*sequence, index);
        CoincurveBuffer buffer = {0};
        const unsigned char *source;
        Py_ssize_t size;

        if (PyBytes_CheckExact(item)) {
            source = (const unsigned char *)PyBytes_AS_STRING(item);
            size = PyBytes_GET_SIZE(item);
        } else {
            if (cc_get_buffer_item(item, &buffer, name, index) < 0) {
                goto error;
            }
            source = (const unsigned char *)buffer.view.buf;
            size = buffer.view.len;
        }
        (*sizes)[index] = (size_t)size;
        (*valid)[index] = (unsigned char)(schnorr ? size == CC_COMPACT_SIGNATURE_SIZE
                                                  : size <= CC_MAX_DER_SIGNATURE_SIZE);
        if ((*valid)[index]) {
            memcpy(*data + (size_t)index * (size_t)width, source, (size_t)size);
        }
        cc_release_buffer(&buffer);
    }
    return 0;

error:
    PyMem_Free(*valid);
    PyMem_Free(*sizes);
    PyMem_Free(*data);
    *valid = NULL;
    *sizes = NULL;
    *data = NULL;
    Py_CLEAR(*sequence);
    return -1;
}

static PyObject *key_verify_batch(
    PyObject *self,
    PyObject *signatures_object,
    PyObject *inputs_object,
    PyObject *hasher,
    int messages,
    int schnorr
)
{
    CoincurveState *state = cc_state_from_object(self);
    PyObject *signatures = NULL;
    PyObject *inputs = NULL;
    unsigned char *signature_data = NULL;
    size_t *signature_sizes = NULL;
    unsigned char *signature_valid = NULL;
    unsigned char *digests = NULL;
    unsigned char *statuses = NULL;
    Py_ssize_t signature_count = 0;
    Py_ssize_t input_count = 0;
    Py_ssize_t signature_width = schnorr ? CC_COMPACT_SIGNATURE_SIZE : CC_MAX_DER_SIGNATURE_SIZE;
    Py_ssize_t index;
    PyObject *result = NULL;

    if (state == NULL) {
        return NULL;
    }
    if (batch_copy_signatures(
            signatures_object,
            "signatures",
            schnorr,
            &signatures,
            &signature_data,
            &signature_sizes,
            &signature_valid,
            &signature_count
        ) < 0) {
        return NULL;
    }
    if (messages) {
        if (batch_hash_sequence(
                state,
                inputs_object,
                hasher,
                "messages",
                &inputs,
                &digests,
                &input_count
            ) < 0) {
            goto cleanup;
        }
    } else if (
        batch_copy_sequence(
            inputs_object,
            "digests",
            CC_DIGEST_SIZE,
            0,
            &inputs,
            &digests,
            &input_count
        ) < 0
    ) {
        goto cleanup;
    }
    if (batch_check_equal(signature_count, input_count) < 0) {
        goto cleanup;
    }
    statuses = batch_allocate(input_count, 1);
    if (statuses == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < input_count; index++)
    {
        if (!signature_valid[index]) {
            statuses[index] = 0;
        } else if (schnorr) {
            statuses[index] = (unsigned char)cc_schnorr_verify(
                state->context,
                &((XOnlyPublicKeyObject *)self)->public_key,
                signature_data + (size_t)index * (size_t)signature_width,
                digests + (size_t)index * CC_DIGEST_SIZE
            );
        } else {
            statuses[index] = (unsigned char)cc_ecdsa_verify_der(
                state->context,
                &((PublicKeyObject *)self)->public_key,
                signature_data + (size_t)index * (size_t)signature_width,
                signature_sizes[index],
                digests + (size_t)index * CC_DIGEST_SIZE
            );
        }
    }
    Py_END_ALLOW_THREADS result = batch_boolean_result(statuses, input_count);

cleanup:
    PyMem_Free(statuses);
    PyMem_Free(digests);
    PyMem_Free(signature_valid);
    PyMem_Free(signature_sizes);
    PyMem_Free(signature_data);
    Py_XDECREF(inputs);
    Py_XDECREF(signatures);
    return result;
}

static int parse_verify_batch(
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames,
    const char *name,
    int messages,
    PyObject **signatures,
    PyObject **inputs,
    PyObject **hasher
)
{
    static const char *const message_names[] = {"signatures", "messages", "hasher"};
    static const char *const digest_names[] = {"signatures", "digests"};
    PyObject *values[3] = {NULL, NULL, NULL};
    if (cc_parse_fastcall(
            args,
            nargs,
            kwnames,
            name,
            messages ? message_names : digest_names,
            messages ? 3 : 2,
            messages ? 3 : 2,
            values
        ) < 0) {
        return -1;
    }
    if (values[0] == NULL || values[1] == NULL) {
        PyErr_Format(PyExc_TypeError, "%s() requires signatures and inputs.", name);
        return -1;
    }
    *signatures = values[0];
    *inputs = values[1];
    *hasher = messages ? values[2] : NULL;
    return 0;
}

#define DEFINE_VERIFY_BATCH(PREFIX, NAME, MESSAGES, SCHNORR)                                       \
    PyObject *cc_##PREFIX##_##NAME(                                                                \
        PyObject *self,                                                                            \
        PyObject *const *args,                                                                     \
        Py_ssize_t nargs,                                                                          \
        PyObject *kwnames                                                                          \
    )                                                                                              \
    {                                                                                              \
        PyObject *signatures;                                                                      \
        PyObject *inputs;                                                                          \
        PyObject *hasher;                                                                          \
        if (parse_verify_batch(                                                                    \
                args,                                                                              \
                nargs,                                                                             \
                kwnames,                                                                           \
                #NAME,                                                                             \
                MESSAGES,                                                                          \
                &signatures,                                                                       \
                &inputs,                                                                           \
                &hasher                                                                            \
            ) < 0) {                                                                               \
            return NULL;                                                                           \
        }                                                                                          \
        return key_verify_batch(self, signatures, inputs, hasher, MESSAGES, SCHNORR);              \
    }

DEFINE_VERIFY_BATCH(public_key, verify_many, 1, 0)
DEFINE_VERIFY_BATCH(public_key, verify_digests, 0, 0)
DEFINE_VERIFY_BATCH(xonly_public_key, verify_many, 1, 1)
DEFINE_VERIFY_BATCH(xonly_public_key, verify_digests, 0, 1)

static int batch_typed_keys(
    PyObject *object,
    PyTypeObject *type,
    const char *type_name,
    const char *iterable_message,
    const char *name,
    PyObject **sequence,
    PyObject ***keys,
    Py_ssize_t *count
)
{
    Py_ssize_t index;
    PyObject **items;

    *sequence = batch_materialize(object, iterable_message);
    if (*sequence == NULL) {
        return -1;
    }
    *count = PySequence_Fast_GET_SIZE(*sequence);
    items = batch_allocate(*count, sizeof(*items));
    if (items == NULL) {
        Py_CLEAR(*sequence);
        return -1;
    }
    for (index = 0; index < *count; index++) {
        PyObject *item = PySequence_Fast_GET_ITEM(*sequence, index);
        if (!PyObject_TypeCheck(item, type)) {
            PyErr_Format(PyExc_TypeError, "%s[%zd] must be %s.", name, index, type_name);
            PyMem_Free(items);
            Py_CLEAR(*sequence);
            return -1;
        }
        items[index] = item;
    }
    *keys = items;
    return 0;
}

static int batch_private_keys(
    CoincurveState *state,
    PyObject *object,
    const char *name,
    PyObject **sequence,
    PyObject ***keys,
    Py_ssize_t *count
)
{
    return batch_typed_keys(
        object,
        (PyTypeObject *)state->private_key_type,
        "a PrivateKey",
        "Private keys must be iterable.",
        name,
        sequence,
        keys,
        count
    );
}

static int batch_public_keys(
    CoincurveState *state,
    PyObject *object,
    const char *name,
    PyObject **sequence,
    PyObject ***keys,
    Py_ssize_t *count
)
{
    return batch_typed_keys(
        object,
        (PyTypeObject *)state->public_key_type,
        "a PublicKey",
        "Public keys must be iterable.",
        name,
        sequence,
        keys,
        count
    );
}

static int batch_xonly_keys(
    CoincurveState *state,
    PyObject *object,
    const char *name,
    PyObject **sequence,
    PyObject ***keys,
    Py_ssize_t *count
)
{
    return batch_typed_keys(
        object,
        (PyTypeObject *)state->xonly_public_key_type,
        "an XOnlyPublicKey",
        "X-only public keys must be iterable.",
        name,
        sequence,
        keys,
        count
    );
}

static PyObject *
module_sign_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs, int mode)
{
    CoincurveState *state = cc_state_from_module(module);
    PyObject *key_sequence = NULL;
    PyObject *digest_sequence = NULL;
    PyObject **keys = NULL;
    unsigned char *digests = NULL;
    unsigned char *outputs = NULL;
    size_t *sizes = NULL;
    unsigned char *randomness = NULL;
    Py_ssize_t key_count = 0;
    Py_ssize_t digest_count = 0;
    Py_ssize_t width = mode == CC_BATCH_ECDSA
                           ? CC_MAX_DER_SIGNATURE_SIZE
                           : (mode == CC_BATCH_RECOVERABLE ? CC_RECOVERABLE_SIGNATURE_SIZE
                                                           : CC_COMPACT_SIGNATURE_SIZE);
    Py_ssize_t index;
    int success = 1;
    PyObject *result = NULL;

    if (nargs != 2) {
        PyErr_SetString(PyExc_TypeError, "The batch operation requires private_keys and digests.");
        return NULL;
    }
    if (batch_private_keys(state, args[0], "private_keys", &key_sequence, &keys, &key_count) < 0 ||
        batch_copy_sequence(
            args[1],
            "digests",
            CC_DIGEST_SIZE,
            0,
            &digest_sequence,
            &digests,
            &digest_count
        ) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(key_count, digest_count) < 0) {
        goto cleanup;
    }
    outputs = batch_allocate(key_count, (size_t)width);
    if (outputs == NULL) {
        goto cleanup;
    }
    if (mode == CC_BATCH_ECDSA) {
        sizes = batch_allocate(key_count, sizeof(*sizes));
        if (sizes == NULL) {
            goto cleanup;
        }
    }
    if (mode == CC_BATCH_SCHNORR) {
        randomness = batch_fill_randomness(state, key_count);
        if (randomness == NULL) {
            goto cleanup;
        }
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < key_count; index++)
    {
        PrivateKeyObject *key = (PrivateKeyObject *)keys[index];
        unsigned char *output = outputs + (size_t)index * (size_t)width;
        const unsigned char *digest = digests + (size_t)index * CC_DIGEST_SIZE;
        if (mode == CC_BATCH_ECDSA) {
            sizes[index] = CC_MAX_DER_SIGNATURE_SIZE;
            success =
                cc_ecdsa_sign_der(state->context, key->secret, digest, NULL, output, &sizes[index]);
        } else if (mode == CC_BATCH_RECOVERABLE) {
            success = cc_ecdsa_sign_recoverable(state->context, key->secret, digest, NULL, output);
        } else {
            success = secp256k1_schnorrsig_sign32(
                state->context,
                output,
                digest,
                &key->keypair,
                randomness + (size_t)index * CC_SECRET_SIZE
            );
        }
        if (!success) {
            break;
        }
    }
    Py_END_ALLOW_THREADS if (!success)
    {
        PyErr_Format(PyExc_RuntimeError, "libsecp256k1 could not sign item %zd.", index);
        goto cleanup;
    }
    result = mode == CC_BATCH_ECDSA ? batch_der_result(outputs, sizes, key_count)
                                    : batch_fixed_result(outputs, key_count, width);

cleanup:
    if (randomness != NULL) {
        cc_secure_zero(randomness, (size_t)key_count * CC_SECRET_SIZE);
    }
    PyMem_Free(randomness);
    PyMem_Free(sizes);
    PyMem_Free(outputs);
    PyMem_Free(digests);
    PyMem_Free(keys);
    Py_XDECREF(digest_sequence);
    Py_XDECREF(key_sequence);
    return result;
}

static PyObject *
module_batch_sign_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return module_sign_digests(module, args, nargs, CC_BATCH_ECDSA);
}

static PyObject *
module_batch_sign_recoverable_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return module_sign_digests(module, args, nargs, CC_BATCH_RECOVERABLE);
}

static PyObject *
module_batch_sign_schnorr_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return module_sign_digests(module, args, nargs, CC_BATCH_SCHNORR);
}

static PyObject *
module_verify_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs, int schnorr)
{
    CoincurveState *state = cc_state_from_module(module);
    PyObject *key_sequence = NULL;
    PyObject *signature_sequence = NULL;
    PyObject *digest_sequence = NULL;
    PyObject **public_keys = NULL;
    PyObject **xonly_keys = NULL;
    unsigned char *signatures = NULL;
    size_t *signature_sizes = NULL;
    unsigned char *signature_valid = NULL;
    unsigned char *digests = NULL;
    unsigned char *statuses = NULL;
    Py_ssize_t key_count = 0;
    Py_ssize_t signature_count = 0;
    Py_ssize_t digest_count = 0;
    Py_ssize_t width = schnorr ? CC_COMPACT_SIGNATURE_SIZE : CC_MAX_DER_SIGNATURE_SIZE;
    Py_ssize_t index;
    PyObject *result = NULL;

    if (nargs != 3) {
        PyErr_SetString(
            PyExc_TypeError,
            "The batch operation requires public_keys, signatures, and digests."
        );
        return NULL;
    }
    if (schnorr) {
        if (batch_xonly_keys(
                state,
                args[0],
                "public_keys",
                &key_sequence,
                &xonly_keys,
                &key_count
            ) < 0) {
            goto cleanup;
        }
    } else if (
        batch_public_keys(state, args[0], "public_keys", &key_sequence, &public_keys, &key_count) <
        0
    ) {
        goto cleanup;
    }
    if (batch_copy_signatures(
            args[1],
            "signatures",
            schnorr,
            &signature_sequence,
            &signatures,
            &signature_sizes,
            &signature_valid,
            &signature_count
        ) < 0 ||
        batch_copy_sequence(
            args[2],
            "digests",
            CC_DIGEST_SIZE,
            0,
            &digest_sequence,
            &digests,
            &digest_count
        ) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(key_count, signature_count) < 0 ||
        batch_check_equal(key_count, digest_count) < 0) {
        goto cleanup;
    }
    statuses = batch_allocate(key_count, 1);
    if (statuses == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < key_count; index++)
    {
        if (!signature_valid[index]) {
            statuses[index] = 0;
        } else if (schnorr) {
            XOnlyPublicKeyObject *key = (XOnlyPublicKeyObject *)xonly_keys[index];
            statuses[index] = (unsigned char)cc_schnorr_verify(
                state->context,
                &key->public_key,
                signatures + (size_t)index * (size_t)width,
                digests + (size_t)index * CC_DIGEST_SIZE
            );
        } else {
            PublicKeyObject *key = (PublicKeyObject *)public_keys[index];
            statuses[index] = (unsigned char)cc_ecdsa_verify_der(
                state->context,
                &key->public_key,
                signatures + (size_t)index * (size_t)width,
                signature_sizes[index],
                digests + (size_t)index * CC_DIGEST_SIZE
            );
        }
    }
    Py_END_ALLOW_THREADS result = batch_boolean_result(statuses, key_count);

cleanup:
    PyMem_Free(statuses);
    PyMem_Free(digests);
    PyMem_Free(signature_valid);
    PyMem_Free(signature_sizes);
    PyMem_Free(signatures);
    PyMem_Free(xonly_keys);
    PyMem_Free(public_keys);
    Py_XDECREF(digest_sequence);
    Py_XDECREF(signature_sequence);
    Py_XDECREF(key_sequence);
    return result;
}

static PyObject *
module_batch_verify_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return module_verify_digests(module, args, nargs, 0);
}

static PyObject *
module_batch_verify_schnorr_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return module_verify_digests(module, args, nargs, 1);
}

static PyObject *
module_batch_recover_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    CoincurveState *state = cc_state_from_module(module);
    PyObject *signature_sequence = NULL;
    PyObject *digest_sequence = NULL;
    unsigned char *signatures = NULL;
    unsigned char *digests = NULL;
    secp256k1_pubkey *public_keys = NULL;
    unsigned char *statuses = NULL;
    Py_ssize_t signature_count = 0;
    Py_ssize_t digest_count = 0;
    Py_ssize_t index;
    PyObject *result = NULL;

    if (nargs != 2) {
        PyErr_SetString(PyExc_TypeError, "recover_digests() requires signatures and digests.");
        return NULL;
    }
    if (batch_copy_sequence(
            args[0],
            "signatures",
            CC_RECOVERABLE_SIGNATURE_SIZE,
            0,
            &signature_sequence,
            &signatures,
            &signature_count
        ) < 0 ||
        batch_copy_sequence(
            args[1],
            "digests",
            CC_DIGEST_SIZE,
            0,
            &digest_sequence,
            &digests,
            &digest_count
        ) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(signature_count, digest_count) < 0) {
        goto cleanup;
    }
    public_keys = batch_allocate(signature_count, sizeof(*public_keys));
    statuses = batch_allocate(signature_count, 1);
    if (public_keys == NULL || statuses == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < signature_count; index++)
    {
        statuses[index] = (unsigned char)cc_ecdsa_recover(
            state->context,
            signatures + (size_t)index * CC_RECOVERABLE_SIGNATURE_SIZE,
            digests + (size_t)index * CC_DIGEST_SIZE,
            &public_keys[index]
        );
    }
    Py_END_ALLOW_THREADS result = PyList_New(signature_count);
    if (result == NULL) {
        goto cleanup;
    }
    for (index = 0; index < signature_count; index++) {
        PyObject *item;
        if (statuses[index]) {
            item = cc_public_key_from_native(
                (PyTypeObject *)state->public_key_type,
                &public_keys[index]
            );
            if (item == NULL) {
                Py_CLEAR(result);
                goto cleanup;
            }
        } else {
            item = Py_None;
            Py_INCREF(item);
        }
        PyList_SET_ITEM(result, index, item);
    }

cleanup:
    PyMem_Free(statuses);
    PyMem_Free(public_keys);
    PyMem_Free(digests);
    PyMem_Free(signatures);
    Py_XDECREF(digest_sequence);
    Py_XDECREF(signature_sequence);
    return result;
}

static PyObject *module_batch_ecdh(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    CoincurveState *state = cc_state_from_module(module);
    PyObject *private_sequence = NULL;
    PyObject *public_sequence = NULL;
    PyObject **private_keys = NULL;
    PyObject **public_keys = NULL;
    unsigned char *outputs = NULL;
    Py_ssize_t private_count = 0;
    Py_ssize_t public_count = 0;
    Py_ssize_t index;
    int success = 1;
    PyObject *result = NULL;

    if (nargs != 2) {
        PyErr_SetString(PyExc_TypeError, "ecdh() requires private_keys and peer_public_keys.");
        return NULL;
    }
    if (batch_private_keys(
            state,
            args[0],
            "private_keys",
            &private_sequence,
            &private_keys,
            &private_count
        ) < 0 ||
        batch_public_keys(
            state,
            args[1],
            "peer_public_keys",
            &public_sequence,
            &public_keys,
            &public_count
        ) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(private_count, public_count) < 0) {
        goto cleanup;
    }
    outputs = batch_allocate(private_count, CC_DIGEST_SIZE);
    if (outputs == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < private_count; index++)
    {
        PrivateKeyObject *private_key = (PrivateKeyObject *)private_keys[index];
        PublicKeyObject *public_key = (PublicKeyObject *)public_keys[index];
        success = cc_ecdh(
            state->context,
            private_key->secret,
            &public_key->public_key,
            outputs + (size_t)index * CC_DIGEST_SIZE
        );
        if (!success) {
            break;
        }
    }
    Py_END_ALLOW_THREADS if (!success)
    {
        PyErr_Format(PyExc_ValueError, "Could not derive ECDH shared secret at index %zd.", index);
        goto cleanup;
    }
    result = batch_fixed_result(outputs, private_count, CC_DIGEST_SIZE);

cleanup:
    if (outputs != NULL) {
        cc_secure_zero(outputs, (size_t)private_count * CC_DIGEST_SIZE);
    }
    PyMem_Free(outputs);
    PyMem_Free(public_keys);
    PyMem_Free(private_keys);
    Py_XDECREF(public_sequence);
    Py_XDECREF(private_sequence);
    return result;
}

static PyObject *module_derive_keys(PyObject *module, PyObject *secrets_object, int xonly)
{
    CoincurveState *state = cc_state_from_module(module);
    PyObject *sequence = NULL;
    unsigned char *secrets = NULL;
    secp256k1_pubkey *public_keys = NULL;
    secp256k1_xonly_pubkey *xonly_keys = NULL;
    int *parities = NULL;
    Py_ssize_t count = 0;
    Py_ssize_t index;
    int success = 1;
    PyObject *result = NULL;

    if (batch_copy_sequence(
            secrets_object,
            "secrets",
            CC_SECRET_SIZE,
            1,
            &sequence,
            &secrets,
            &count
        ) < 0) {
        return NULL;
    }
    for (index = 0; index < count; index++) {
        if (!secp256k1_ec_seckey_verify(state->context, secrets + (size_t)index * CC_SECRET_SIZE)) {
            PyErr_Format(
                PyExc_ValueError,
                "secrets[%zd] is not a valid secp256k1 private key.",
                index
            );
            goto cleanup;
        }
    }
    if (xonly) {
        xonly_keys = batch_allocate(count, sizeof(*xonly_keys));
        parities = batch_allocate(count, sizeof(*parities));
        if (xonly_keys == NULL || parities == NULL) {
            goto cleanup;
        }
    } else {
        public_keys = batch_allocate(count, sizeof(*public_keys));
        if (public_keys == NULL) {
            goto cleanup;
        }
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < count; index++)
    {
        const unsigned char *secret = secrets + (size_t)index * CC_SECRET_SIZE;
        if (xonly) {
            success =
                cc_xonly_from_secret(state->context, &xonly_keys[index], &parities[index], secret);
        } else {
            success = secp256k1_ec_pubkey_create(state->context, &public_keys[index], secret);
        }
        if (!success) {
            break;
        }
    }
    Py_END_ALLOW_THREADS if (!success)
    {
        PyErr_Format(PyExc_RuntimeError, "Could not derive key at index %zd.", index);
        goto cleanup;
    }
    result = PyList_New(count);
    if (result == NULL) {
        goto cleanup;
    }
    for (index = 0; index < count; index++) {
        PyObject *item = xonly ? cc_xonly_public_key_from_native(
                                     (PyTypeObject *)state->xonly_public_key_type,
                                     &xonly_keys[index],
                                     parities[index]
                                 )
                               : cc_public_key_from_native(
                                     (PyTypeObject *)state->public_key_type,
                                     &public_keys[index]
                                 );
        if (item == NULL) {
            Py_CLEAR(result);
            goto cleanup;
        }
        PyList_SET_ITEM(result, index, item);
    }

cleanup:
    if (secrets != NULL) {
        cc_secure_zero(secrets, (size_t)count * CC_SECRET_SIZE);
    }
    PyMem_Free(parities);
    PyMem_Free(xonly_keys);
    PyMem_Free(public_keys);
    PyMem_Free(secrets);
    Py_XDECREF(sequence);
    return result;
}

static PyObject *module_batch_derive_public_keys(PyObject *module, PyObject *secrets)
{
    return module_derive_keys(module, secrets, 0);
}

static PyObject *module_batch_derive_xonly_public_keys(PyObject *module, PyObject *secrets)
{
    return module_derive_keys(module, secrets, 1);
}

static int packed_input(
    PyObject *object,
    CoincurveBuffer *buffer,
    Py_ssize_t width,
    const char *name,
    Py_ssize_t *count
)
{
    if (cc_get_buffer(object, buffer, name) < 0) {
        return -1;
    }
    if (buffer->view.len % width != 0) {
        cc_release_buffer(buffer);
        PyErr_Format(
            PyExc_ValueError,
            "%s length must be an exact multiple of %zd bytes.",
            name,
            width
        );
        return -1;
    }
    *count = buffer->view.len / width;
    return 0;
}

static PyObject *packed_outputs(
    Py_ssize_t count,
    Py_ssize_t width,
    PyObject **status,
    unsigned char **output_data,
    unsigned char **status_data
)
{
    PyObject *output;
    if (count > PY_SSIZE_T_MAX / width) {
        PyErr_SetString(PyExc_OverflowError, "The packed output is too large.");
        return NULL;
    }
    output = PyBytes_FromStringAndSize(NULL, count * width);
    if (output == NULL) {
        return NULL;
    }
    *status = PyBytes_FromStringAndSize(NULL, count);
    if (*status == NULL) {
        Py_DECREF(output);
        return NULL;
    }
    *output_data = (unsigned char *)PyBytes_AS_STRING(output);
    *status_data = (unsigned char *)PyBytes_AS_STRING(*status);
    memset(*output_data, 0, (size_t)count * (size_t)width);
    memset(*status_data, 0, (size_t)count);
    return output;
}

static PyObject *packed_pair(PyObject *output, PyObject *status)
{
    PyObject *result = PyTuple_New(2);
    if (result == NULL) {
        Py_DECREF(output);
        Py_DECREF(status);
        return NULL;
    }
    PyTuple_SET_ITEM(result, 0, output);
    PyTuple_SET_ITEM(result, 1, status);
    return result;
}

static PyObject *packed_derive(PyObject *module, PyObject *secrets_object, int xonly)
{
    CoincurveState *state = cc_state_from_module(module);
    CoincurveBuffer secrets_buffer = {0};
    unsigned char *secrets = NULL;
    PyObject *output = NULL;
    PyObject *status = NULL;
    unsigned char *output_data;
    unsigned char *status_data;
    Py_ssize_t count = 0;
    Py_ssize_t width = xonly ? CC_XONLY_PUBLIC_KEY_SIZE : CC_PUBLIC_KEY_COMPRESSED_SIZE;
    Py_ssize_t index;

    if (packed_input(secrets_object, &secrets_buffer, CC_SECRET_SIZE, "secrets", &count) < 0) {
        return NULL;
    }
    secrets = batch_allocate(count, CC_SECRET_SIZE);
    if (secrets == NULL) {
        goto cleanup;
    }
    memcpy(secrets, secrets_buffer.view.buf, (size_t)count * CC_SECRET_SIZE);
    output = packed_outputs(count, width, &status, &output_data, &status_data);
    if (output == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < count; index++)
    {
        const unsigned char *secret = secrets + (size_t)index * CC_SECRET_SIZE;
        if (xonly) {
            secp256k1_xonly_pubkey public_key;
            int parity;
            status_data[index] =
                (unsigned char)(cc_xonly_from_secret(
                                    state->context,
                                    &public_key,
                                    &parity,
                                    secret
                                ) &&
                                secp256k1_xonly_pubkey_serialize(
                                    state->context,
                                    output_data + (size_t)index * CC_XONLY_PUBLIC_KEY_SIZE,
                                    &public_key
                                ));
        } else {
            secp256k1_pubkey public_key;
            status_data[index] =
                (unsigned char)(secp256k1_ec_pubkey_create(state->context, &public_key, secret) &&
                                cc_serialize_compressed(
                                    state->context,
                                    &public_key,
                                    output_data + (size_t)index * CC_PUBLIC_KEY_COMPRESSED_SIZE
                                ));
        }
        if (!status_data[index]) {
            memset(output_data + (size_t)index * (size_t)width, 0, (size_t)width);
        }
    }
    Py_END_ALLOW_THREADS

        cleanup : if (secrets != NULL)
    {
        cc_secure_zero(secrets, (size_t)count * CC_SECRET_SIZE);
    }
    PyMem_Free(secrets);
    cc_release_buffer(&secrets_buffer);
    if (output == NULL) {
        Py_XDECREF(status);
        return NULL;
    }
    return packed_pair(output, status);
}

static PyObject *module_packed_derive_public_keys(PyObject *module, PyObject *secrets)
{
    return packed_derive(module, secrets, 0);
}

static PyObject *module_packed_derive_xonly_public_keys(PyObject *module, PyObject *secrets)
{
    return packed_derive(module, secrets, 1);
}

static PyObject *packed_sign(PyObject *module, PyObject *const *args, Py_ssize_t nargs, int mode)
{
    CoincurveState *state = cc_state_from_module(module);
    CoincurveBuffer secrets_buffer = {0};
    CoincurveBuffer digests_buffer = {0};
    unsigned char *secrets = NULL;
    unsigned char *randomness = NULL;
    PyObject *output = NULL;
    PyObject *status = NULL;
    unsigned char *output_data;
    unsigned char *status_data;
    Py_ssize_t secret_count = 0;
    Py_ssize_t digest_count = 0;
    Py_ssize_t width =
        mode == CC_BATCH_RECOVERABLE ? CC_RECOVERABLE_SIGNATURE_SIZE : CC_COMPACT_SIGNATURE_SIZE;
    Py_ssize_t index;

    if (nargs != 2) {
        PyErr_SetString(PyExc_TypeError, "Packed signing requires secrets and digests.");
        return NULL;
    }
    if (packed_input(args[0], &secrets_buffer, CC_SECRET_SIZE, "secrets", &secret_count) < 0 ||
        packed_input(args[1], &digests_buffer, CC_DIGEST_SIZE, "digests", &digest_count) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(secret_count, digest_count) < 0) {
        goto cleanup;
    }
    secrets = batch_allocate(secret_count, CC_SECRET_SIZE);
    if (secrets == NULL) {
        goto cleanup;
    }
    memcpy(secrets, secrets_buffer.view.buf, (size_t)secret_count * CC_SECRET_SIZE);
    if (mode == CC_BATCH_SCHNORR) {
        randomness = batch_fill_randomness(state, secret_count);
        if (randomness == NULL) {
            goto cleanup;
        }
    }
    output = packed_outputs(secret_count, width, &status, &output_data, &status_data);
    if (output == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < secret_count; index++)
    {
        const unsigned char *secret = secrets + (size_t)index * CC_SECRET_SIZE;
        const unsigned char *digest =
            (const unsigned char *)digests_buffer.view.buf + (size_t)index * CC_DIGEST_SIZE;
        unsigned char *signature = output_data + (size_t)index * (size_t)width;
        if (mode == CC_BATCH_ECDSA) {
            status_data[index] = (unsigned char)
                cc_ecdsa_sign_compact(state->context, secret, digest, NULL, signature);
        } else if (mode == CC_BATCH_RECOVERABLE) {
            status_data[index] = (unsigned char)
                cc_ecdsa_sign_recoverable(state->context, secret, digest, NULL, signature);
        } else {
            secp256k1_keypair keypair;
            status_data[index] =
                (unsigned char)(secp256k1_keypair_create(state->context, &keypair, secret) &&
                                secp256k1_schnorrsig_sign32(
                                    state->context,
                                    signature,
                                    digest,
                                    &keypair,
                                    randomness + (size_t)index * CC_SECRET_SIZE
                                ));
            cc_secure_zero(&keypair, sizeof(keypair));
        }
        if (!status_data[index]) {
            memset(signature, 0, (size_t)width);
        }
    }
    Py_END_ALLOW_THREADS

        cleanup : if (secrets != NULL)
    {
        cc_secure_zero(secrets, (size_t)secret_count * CC_SECRET_SIZE);
    }
    if (randomness != NULL) {
        cc_secure_zero(randomness, (size_t)secret_count * CC_SECRET_SIZE);
    }
    PyMem_Free(randomness);
    PyMem_Free(secrets);
    cc_release_buffer(&digests_buffer);
    cc_release_buffer(&secrets_buffer);
    if (output == NULL) {
        Py_XDECREF(status);
        return NULL;
    }
    return packed_pair(output, status);
}

static PyObject *
module_packed_sign_ecdsa_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return packed_sign(module, args, nargs, CC_BATCH_ECDSA);
}

static PyObject *
module_packed_sign_recoverable_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return packed_sign(module, args, nargs, CC_BATCH_RECOVERABLE);
}

static PyObject *
module_packed_sign_schnorr_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return packed_sign(module, args, nargs, CC_BATCH_SCHNORR);
}

static PyObject *
packed_verify(PyObject *module, PyObject *const *args, Py_ssize_t nargs, int schnorr)
{
    CoincurveState *state = cc_state_from_module(module);
    CoincurveBuffer keys = {0};
    CoincurveBuffer signatures = {0};
    CoincurveBuffer digests = {0};
    PyObject *status = NULL;
    unsigned char *status_data;
    Py_ssize_t key_count = 0;
    Py_ssize_t signature_count = 0;
    Py_ssize_t digest_count = 0;
    Py_ssize_t key_width = schnorr ? CC_XONLY_PUBLIC_KEY_SIZE : CC_PUBLIC_KEY_COMPRESSED_SIZE;
    Py_ssize_t index;

    if (nargs != 3) {
        PyErr_SetString(
            PyExc_TypeError,
            "Packed verification requires public_keys, signatures, and digests."
        );
        return NULL;
    }
    if (packed_input(args[0], &keys, key_width, "public_keys", &key_count) < 0 ||
        packed_input(
            args[1],
            &signatures,
            CC_COMPACT_SIGNATURE_SIZE,
            "signatures",
            &signature_count
        ) < 0 ||
        packed_input(args[2], &digests, CC_DIGEST_SIZE, "digests", &digest_count) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(key_count, signature_count) < 0 ||
        batch_check_equal(key_count, digest_count) < 0) {
        goto cleanup;
    }
    status = PyBytes_FromStringAndSize(NULL, key_count);
    if (status == NULL) {
        goto cleanup;
    }
    status_data = (unsigned char *)PyBytes_AS_STRING(status);
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < key_count; index++)
    {
        const unsigned char *key =
            (const unsigned char *)keys.view.buf + (size_t)index * (size_t)key_width;
        const unsigned char *signature =
            (const unsigned char *)signatures.view.buf + (size_t)index * CC_COMPACT_SIGNATURE_SIZE;
        const unsigned char *digest =
            (const unsigned char *)digests.view.buf + (size_t)index * CC_DIGEST_SIZE;
        if (schnorr) {
            secp256k1_xonly_pubkey public_key;
            status_data[index] =
                (unsigned char)(secp256k1_xonly_pubkey_parse(state->context, &public_key, key) &&
                                cc_schnorr_verify(state->context, &public_key, signature, digest));
        } else {
            secp256k1_pubkey public_key;
            status_data[index] = (unsigned char)(secp256k1_ec_pubkey_parse(
                                                     state->context,
                                                     &public_key,
                                                     key,
                                                     CC_PUBLIC_KEY_COMPRESSED_SIZE
                                                 ) &&
                                                 cc_ecdsa_verify_compact(
                                                     state->context,
                                                     &public_key,
                                                     signature,
                                                     digest
                                                 ));
        }
    }
    Py_END_ALLOW_THREADS

        cleanup : cc_release_buffer(&digests);
    cc_release_buffer(&signatures);
    cc_release_buffer(&keys);
    return status;
}

static PyObject *
module_packed_verify_ecdsa_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return packed_verify(module, args, nargs, 0);
}

static PyObject *
module_packed_verify_schnorr_digests(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    return packed_verify(module, args, nargs, 1);
}

static PyObject *
module_packed_recover_public_keys(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    CoincurveState *state = cc_state_from_module(module);
    CoincurveBuffer signatures = {0};
    CoincurveBuffer digests = {0};
    PyObject *output = NULL;
    PyObject *status = NULL;
    unsigned char *output_data;
    unsigned char *status_data;
    Py_ssize_t signature_count = 0;
    Py_ssize_t digest_count = 0;
    Py_ssize_t index;

    if (nargs != 2) {
        PyErr_SetString(PyExc_TypeError, "Packed recovery requires signatures and digests.");
        return NULL;
    }
    if (packed_input(
            args[0],
            &signatures,
            CC_RECOVERABLE_SIGNATURE_SIZE,
            "signatures",
            &signature_count
        ) < 0 ||
        packed_input(args[1], &digests, CC_DIGEST_SIZE, "digests", &digest_count) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(signature_count, digest_count) < 0) {
        goto cleanup;
    }
    output = packed_outputs(
        signature_count,
        CC_PUBLIC_KEY_COMPRESSED_SIZE,
        &status,
        &output_data,
        &status_data
    );
    if (output == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < signature_count; index++)
    {
        secp256k1_pubkey public_key;
        status_data[index] =
            (unsigned char)(cc_ecdsa_recover(
                                state->context,
                                (const unsigned char *)signatures.view.buf +
                                    (size_t)index * CC_RECOVERABLE_SIGNATURE_SIZE,
                                (const unsigned char *)digests.view.buf +
                                    (size_t)index * CC_DIGEST_SIZE,
                                &public_key
                            ) &&
                            cc_serialize_compressed(
                                state->context,
                                &public_key,
                                output_data + (size_t)index * CC_PUBLIC_KEY_COMPRESSED_SIZE
                            ));
        if (!status_data[index]) {
            memset(
                output_data + (size_t)index * CC_PUBLIC_KEY_COMPRESSED_SIZE,
                0,
                CC_PUBLIC_KEY_COMPRESSED_SIZE
            );
        }
    }
    Py_END_ALLOW_THREADS

        cleanup : cc_release_buffer(&digests);
    cc_release_buffer(&signatures);
    if (output == NULL) {
        Py_XDECREF(status);
        return NULL;
    }
    return packed_pair(output, status);
}

static PyObject *module_packed_ecdh(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    CoincurveState *state = cc_state_from_module(module);
    CoincurveBuffer secrets_buffer = {0};
    CoincurveBuffer public_keys = {0};
    unsigned char *secrets = NULL;
    PyObject *output = NULL;
    PyObject *status = NULL;
    unsigned char *output_data;
    unsigned char *status_data;
    Py_ssize_t secret_count = 0;
    Py_ssize_t public_count = 0;
    Py_ssize_t index;

    if (nargs != 2) {
        PyErr_SetString(PyExc_TypeError, "Packed ECDH requires secrets and public_keys.");
        return NULL;
    }
    if (packed_input(args[0], &secrets_buffer, CC_SECRET_SIZE, "secrets", &secret_count) < 0 ||
        packed_input(
            args[1],
            &public_keys,
            CC_PUBLIC_KEY_COMPRESSED_SIZE,
            "public_keys",
            &public_count
        ) < 0) {
        goto cleanup;
    }
    if (batch_check_equal(secret_count, public_count) < 0) {
        goto cleanup;
    }
    secrets = batch_allocate(secret_count, CC_SECRET_SIZE);
    if (secrets == NULL) {
        goto cleanup;
    }
    memcpy(secrets, secrets_buffer.view.buf, (size_t)secret_count * CC_SECRET_SIZE);
    output = packed_outputs(secret_count, CC_DIGEST_SIZE, &status, &output_data, &status_data);
    if (output == NULL) {
        goto cleanup;
    }
    Py_BEGIN_ALLOW_THREADS for (index = 0; index < secret_count; index++)
    {
        secp256k1_pubkey public_key;
        status_data[index] = (unsigned char)(secp256k1_ec_pubkey_parse(
                                                 state->context,
                                                 &public_key,
                                                 (const unsigned char *)public_keys.view.buf +
                                                     (size_t)index * CC_PUBLIC_KEY_COMPRESSED_SIZE,
                                                 CC_PUBLIC_KEY_COMPRESSED_SIZE
                                             ) &&
                                             cc_ecdh(
                                                 state->context,
                                                 secrets + (size_t)index * CC_SECRET_SIZE,
                                                 &public_key,
                                                 output_data + (size_t)index * CC_DIGEST_SIZE
                                             ));
        if (!status_data[index]) {
            memset(output_data + (size_t)index * CC_DIGEST_SIZE, 0, CC_DIGEST_SIZE);
        }
    }
    Py_END_ALLOW_THREADS

        cleanup : if (secrets != NULL)
    {
        cc_secure_zero(secrets, (size_t)secret_count * CC_SECRET_SIZE);
    }
    PyMem_Free(secrets);
    cc_release_buffer(&public_keys);
    cc_release_buffer(&secrets_buffer);
    if (output == NULL) {
        Py_XDECREF(status);
        return NULL;
    }
    return packed_pair(output, status);
}

static PyMethodDef batch_methods[] = {
    {"_batch_sign_digests",
     (PyCFunction)(void (*)(void))module_batch_sign_digests,
     METH_FASTCALL,
     NULL},
    {"_batch_sign_recoverable_digests",
     (PyCFunction)(void (*)(void))module_batch_sign_recoverable_digests,
     METH_FASTCALL,
     NULL},
    {"_batch_sign_schnorr_digests",
     (PyCFunction)(void (*)(void))module_batch_sign_schnorr_digests,
     METH_FASTCALL,
     NULL},
    {"_batch_verify_digests",
     (PyCFunction)(void (*)(void))module_batch_verify_digests,
     METH_FASTCALL,
     NULL},
    {"_batch_verify_schnorr_digests",
     (PyCFunction)(void (*)(void))module_batch_verify_schnorr_digests,
     METH_FASTCALL,
     NULL},
    {"_batch_recover_digests",
     (PyCFunction)(void (*)(void))module_batch_recover_digests,
     METH_FASTCALL,
     NULL},
    {"_batch_ecdh", (PyCFunction)(void (*)(void))module_batch_ecdh, METH_FASTCALL, NULL},
    {"_batch_derive_public_keys", (PyCFunction)module_batch_derive_public_keys, METH_O, NULL},
    {"_batch_derive_xonly_public_keys",
     (PyCFunction)module_batch_derive_xonly_public_keys,
     METH_O,
     NULL},
    {"_packed_derive_public_keys", (PyCFunction)module_packed_derive_public_keys, METH_O, NULL},
    {"_packed_derive_xonly_public_keys",
     (PyCFunction)module_packed_derive_xonly_public_keys,
     METH_O,
     NULL},
    {"_packed_sign_ecdsa_digests",
     (PyCFunction)(void (*)(void))module_packed_sign_ecdsa_digests,
     METH_FASTCALL,
     NULL},
    {"_packed_sign_recoverable_digests",
     (PyCFunction)(void (*)(void))module_packed_sign_recoverable_digests,
     METH_FASTCALL,
     NULL},
    {"_packed_sign_schnorr_digests",
     (PyCFunction)(void (*)(void))module_packed_sign_schnorr_digests,
     METH_FASTCALL,
     NULL},
    {"_packed_verify_ecdsa_digests",
     (PyCFunction)(void (*)(void))module_packed_verify_ecdsa_digests,
     METH_FASTCALL,
     NULL},
    {"_packed_verify_schnorr_digests",
     (PyCFunction)(void (*)(void))module_packed_verify_schnorr_digests,
     METH_FASTCALL,
     NULL},
    {"_packed_recover_public_keys",
     (PyCFunction)(void (*)(void))module_packed_recover_public_keys,
     METH_FASTCALL,
     NULL},
    {"_packed_ecdh", (PyCFunction)(void (*)(void))module_packed_ecdh, METH_FASTCALL, NULL},
    {NULL, NULL, 0, NULL}
};

int cc_add_batch_functions(PyObject *module)
{
    return PyModule_AddFunctions(module, batch_methods);
}
