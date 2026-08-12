#include "coincurve.h"

#include <string.h>

CoincurveState *cc_state_from_module(PyObject *module)
{
    return (CoincurveState *)PyModule_GetState(module);
}

CoincurveState *cc_state_from_type(PyTypeObject *type)
{
    return (CoincurveState *)PyType_GetModuleState(type);
}

CoincurveState *cc_state_from_object(PyObject *object)
{
    return cc_state_from_type(Py_TYPE(object));
}

int cc_parse_fastcall(
    PyObject *const *args,
    Py_ssize_t nargs,
    PyObject *kwnames,
    const char *function_name,
    const char *const *parameter_names,
    Py_ssize_t parameter_count,
    Py_ssize_t positional_limit,
    PyObject **values
)
{
    Py_ssize_t index;
    Py_ssize_t keyword_count = kwnames == NULL ? 0 : PyTuple_GET_SIZE(kwnames);

    if (nargs > positional_limit) {
        PyErr_Format(
            PyExc_TypeError,
            "%s() takes at most %zd positional argument%s (%zd given)",
            function_name,
            positional_limit,
            positional_limit == 1 ? "" : "s",
            nargs
        );
        return -1;
    }

    for (index = 0; index < parameter_count; index++) {
        values[index] = index < nargs ? args[index] : NULL;
    }

    for (index = 0; index < keyword_count; index++) {
        PyObject *keyword = PyTuple_GET_ITEM(kwnames, index);
        PyObject *value = args[nargs + index];
        Py_ssize_t parameter_index;
        int matched = 0;

        if (!PyUnicode_Check(keyword)) {
            PyErr_SetString(PyExc_TypeError, "Keyword names must be strings.");
            return -1;
        }

        for (parameter_index = 0; parameter_index < parameter_count; parameter_index++) {
            int comparison =
                PyUnicode_CompareWithASCIIString(keyword, parameter_names[parameter_index]);
            if (comparison < 0 && PyErr_Occurred()) {
                return -1;
            }
            if (comparison == 0) {
                if (values[parameter_index] != NULL) {
                    PyErr_Format(
                        PyExc_TypeError,
                        "%s() got multiple values for argument '%s'",
                        function_name,
                        parameter_names[parameter_index]
                    );
                    return -1;
                }
                values[parameter_index] = value;
                matched = 1;
                break;
            }
        }

        if (!matched) {
            PyErr_Format(
                PyExc_TypeError,
                "%s() got an unexpected keyword argument '%U'",
                function_name,
                keyword
            );
            return -1;
        }
    }

    return 0;
}

int cc_get_buffer(PyObject *object, CoincurveBuffer *buffer, const char *name)
{
    memset(buffer, 0, sizeof(*buffer));
    if (!PyObject_CheckBuffer(object)) {
        PyErr_Format(
            PyExc_TypeError,
            "%s must be a one-dimensional C-contiguous readable buffer.",
            name
        );
        return -1;
    }
    if (PyObject_GetBuffer(object, &buffer->view, PyBUF_CONTIG_RO) < 0) {
        return -1;
    }
    buffer->acquired = 1;
    if (buffer->view.ndim != 1 || !PyBuffer_IsContiguous(&buffer->view, 'C')) {
        cc_release_buffer(buffer);
        PyErr_Format(
            PyExc_TypeError,
            "%s must be a one-dimensional C-contiguous readable buffer.",
            name
        );
        return -1;
    }
    return 0;
}

int cc_get_buffer_item(
    PyObject *object,
    CoincurveBuffer *buffer,
    const char *name,
    Py_ssize_t index
)
{
    memset(buffer, 0, sizeof(*buffer));
    if (!PyObject_CheckBuffer(object)) {
        PyErr_Format(
            PyExc_TypeError,
            "%s[%zd] must be a one-dimensional C-contiguous readable buffer.",
            name,
            index
        );
        return -1;
    }
    if (PyObject_GetBuffer(object, &buffer->view, PyBUF_CONTIG_RO) < 0) {
        return -1;
    }
    buffer->acquired = 1;
    if (buffer->view.ndim != 1 || !PyBuffer_IsContiguous(&buffer->view, 'C')) {
        cc_release_buffer(buffer);
        PyErr_Format(
            PyExc_TypeError,
            "%s[%zd] must be a one-dimensional C-contiguous readable buffer.",
            name,
            index
        );
        return -1;
    }
    return 0;
}

void cc_release_buffer(CoincurveBuffer *buffer)
{
    if (buffer->acquired) {
        PyBuffer_Release(&buffer->view);
        buffer->acquired = 0;
    }
}

int cc_copy_fixed(PyObject *object, unsigned char *output, Py_ssize_t size, const char *name)
{
    CoincurveBuffer buffer;

    if (PyBytes_CheckExact(object)) {
        if (PyBytes_GET_SIZE(object) != size) {
            PyErr_Format(PyExc_ValueError, "%s must be exactly %zd bytes long.", name, size);
            return -1;
        }
        memcpy(output, PyBytes_AS_STRING(object), (size_t)size);
        return 0;
    }
    if (cc_get_buffer(object, &buffer, name) < 0) {
        return -1;
    }
    if (buffer.view.len != size) {
        cc_release_buffer(&buffer);
        PyErr_Format(PyExc_ValueError, "%s must be exactly %zd bytes long.", name, size);
        return -1;
    }
    memcpy(output, buffer.view.buf, (size_t)size);
    cc_release_buffer(&buffer);
    return 0;
}

int cc_copy_scalar(PyObject *object, unsigned char output[CC_SECRET_SIZE], const char *name)
{
    CoincurveBuffer buffer = {0};
    const unsigned char *source;
    Py_ssize_t size;

    if (PyBytes_CheckExact(object)) {
        source = (const unsigned char *)PyBytes_AS_STRING(object);
        size = PyBytes_GET_SIZE(object);
    } else {
        if (cc_get_buffer(object, &buffer, name) < 0) {
            return -1;
        }
        source = (const unsigned char *)buffer.view.buf;
        size = buffer.view.len;
    }
    if (size > CC_SECRET_SIZE) {
        cc_release_buffer(&buffer);
        PyErr_Format(PyExc_ValueError, "%s must be at most %d bytes long.", name, CC_SECRET_SIZE);
        return -1;
    }
    memset(output, 0, CC_SECRET_SIZE);
    if (size > 0) {
        memcpy(output + CC_SECRET_SIZE - size, source, (size_t)size);
    }
    cc_release_buffer(&buffer);
    return 0;
}

int cc_copy_fixed_item(
    PyObject *object,
    unsigned char *output,
    Py_ssize_t size,
    const char *name,
    Py_ssize_t index
)
{
    CoincurveBuffer buffer;

    if (PyBytes_CheckExact(object)) {
        if (PyBytes_GET_SIZE(object) != size) {
            PyErr_Format(
                PyExc_ValueError,
                "%s[%zd] must be exactly %zd bytes long.",
                name,
                index,
                size
            );
            return -1;
        }
        memcpy(output, PyBytes_AS_STRING(object), (size_t)size);
        return 0;
    }
    if (cc_get_buffer_item(object, &buffer, name, index) < 0) {
        return -1;
    }
    if (buffer.view.len != size) {
        cc_release_buffer(&buffer);
        PyErr_Format(
            PyExc_ValueError,
            "%s[%zd] must be exactly %zd bytes long.",
            name,
            index,
            size
        );
        return -1;
    }
    memcpy(output, buffer.view.buf, (size_t)size);
    cc_release_buffer(&buffer);
    return 0;
}

int cc_copy_optional_fixed(
    PyObject *object,
    unsigned char *output,
    Py_ssize_t size,
    const unsigned char **result,
    const char *name
)
{
    if (object == NULL || object == Py_None) {
        *result = NULL;
        return 0;
    }
    if (cc_copy_fixed(object, output, size, name) < 0) {
        return -1;
    }
    *result = output;
    return 0;
}

int cc_hash_message(
    CoincurveState *state,
    PyObject *message,
    PyObject *hasher,
    unsigned char digest[CC_DIGEST_SIZE]
)
{
    PyObject *result;

    if (hasher == NULL) {
        hasher = state->default_hasher;
    }
    if (!PyCallable_Check(hasher)) {
        PyErr_SetString(PyExc_TypeError, "hasher must be callable.");
        return -1;
    }

    result = PyObject_CallOneArg(hasher, message);
    if (result == NULL) {
        return -1;
    }
    if (cc_copy_fixed(result, digest, CC_DIGEST_SIZE, "Message hash") < 0) {
        Py_DECREF(result);
        return -1;
    }
    Py_DECREF(result);
    return 0;
}

int cc_random_bytes(CoincurveState *state, unsigned char *output, Py_ssize_t size)
{
    PyObject *result = PyObject_CallFunction(state->urandom, "n", size);
    if (result == NULL) {
        return -1;
    }
    if (!PyBytes_Check(result) || PyBytes_GET_SIZE(result) != size) {
        Py_DECREF(result);
        PyErr_SetString(PyExc_RuntimeError, "os.urandom returned an invalid result.");
        return -1;
    }
    memcpy(output, PyBytes_AS_STRING(result), (size_t)size);
    Py_DECREF(result);
    return 0;
}

void cc_secure_zero(void *memory, size_t size)
{
    volatile unsigned char *cursor = (volatile unsigned char *)memory;
    while (size-- > 0) {
        *cursor++ = 0;
    }
}

PyObject *cc_bytes_from_data(const unsigned char *data, Py_ssize_t size)
{
    return PyBytes_FromStringAndSize((const char *)data, size);
}

Py_hash_t cc_hash_data(const unsigned char *data, Py_ssize_t size)
{
    Py_hash_t hash = PyHash_GetFuncDef()->hash(data, size);
    return hash == -1 ? -2 : hash;
}

PyObject *cc_hex_from_data(const unsigned char *data, Py_ssize_t size)
{
    PyObject *serialized = cc_bytes_from_data(data, size);
    PyObject *hex;

    if (serialized == NULL) {
        return NULL;
    }
    hex = PyObject_CallMethod(serialized, "hex", NULL);
    Py_DECREF(serialized);
    return hex;
}

PyObject *cc_hex_repr(PyObject *self, const unsigned char *data, Py_ssize_t size)
{
    PyObject *hex = cc_hex_from_data(data, size);
    PyObject *result;

    if (hex == NULL) {
        return NULL;
    }
    result = PyUnicode_FromFormat("%s('%U')", Py_TYPE(self)->tp_name, hex);
    Py_DECREF(hex);
    return result;
}

PyObject *
cc_richcompare_fixed(PyObject *left, PyObject *right, int operation, size_t offset, size_t size)
{
    int equal;

    if (Py_TYPE(left) != Py_TYPE(right)) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    if (operation != Py_EQ && operation != Py_NE) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    equal =
        memcmp((const unsigned char *)left + offset, (const unsigned char *)right + offset, size) ==
        0;
    return PyBool_FromLong(operation == Py_EQ ? equal : !equal);
}

PyObject *cc_integer_from_bytes(const unsigned char *data, Py_ssize_t size)
{
    PyObject *value = cc_bytes_from_data(data, size);
    PyObject *result;

    if (value == NULL) {
        return NULL;
    }
    result = PyObject_CallMethod((PyObject *)&PyLong_Type, "from_bytes", "Os", value, "big");
    Py_DECREF(value);
    return result;
}

PyObject *cc_integer_to_32_bytes(PyObject *integer, const char *name)
{
    PyObject *result;

    if (!PyLong_Check(integer)) {
        PyErr_Format(PyExc_TypeError, "%s must be an integer.", name);
        return NULL;
    }
    result = PyObject_CallMethod(integer, "to_bytes", "is", 32, "big");
    if (result != NULL && (!PyBytes_Check(result) || PyBytes_GET_SIZE(result) != 32)) {
        Py_DECREF(result);
        PyErr_Format(PyExc_TypeError, "%s.to_bytes() must return exactly 32 bytes.", name);
        return NULL;
    }
    return result;
}

static int coincurve_traverse(PyObject *module, visitproc visit, void *arg)
{
    CoincurveState *state = cc_state_from_module(module);
    Py_VISIT(state->private_key_type);
    Py_VISIT(state->public_key_type);
    Py_VISIT(state->xonly_public_key_type);
    Py_VISIT(state->default_hasher);
    Py_VISIT(state->urandom);
    return 0;
}

static int coincurve_clear(PyObject *module)
{
    CoincurveState *state = cc_state_from_module(module);
    Py_CLEAR(state->private_key_type);
    Py_CLEAR(state->public_key_type);
    Py_CLEAR(state->xonly_public_key_type);
    Py_CLEAR(state->default_hasher);
    Py_CLEAR(state->urandom);
    return 0;
}

static void coincurve_free(void *module)
{
    CoincurveState *state = cc_state_from_module((PyObject *)module);
    if (state != NULL && state->context != NULL) {
        secp256k1_context_destroy(state->context);
        state->context = NULL;
    }
    coincurve_clear((PyObject *)module);
}

static int coincurve_exec(PyObject *module)
{
    CoincurveState *state = cc_state_from_module(module);
    PyObject *os_module = NULL;
    PyObject *utils_module = NULL;
    unsigned char randomization[CC_SECRET_SIZE];
    int randomized;

    state->context = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    if (state->context == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "Could not create the libsecp256k1 context.");
        return -1;
    }

    os_module = PyImport_ImportModule("os");
    if (os_module == NULL) {
        goto error;
    }
    state->urandom = PyObject_GetAttrString(os_module, "urandom");
    Py_CLEAR(os_module);
    if (state->urandom == NULL) {
        goto error;
    }

    utils_module = PyImport_ImportModule("coincurve.utils");
    if (utils_module == NULL) {
        goto error;
    }
    state->default_hasher = PyObject_GetAttrString(utils_module, "sha256");
    Py_CLEAR(utils_module);
    if (state->default_hasher == NULL) {
        goto error;
    }

    if (cc_random_bytes(state, randomization, sizeof(randomization)) < 0) {
        goto error;
    }
    randomized = secp256k1_context_randomize(state->context, randomization);
    cc_secure_zero(randomization, sizeof(randomization));
    if (!randomized) {
        PyErr_SetString(PyExc_RuntimeError, "Could not randomize the libsecp256k1 context.");
        goto error;
    }

    state->private_key_type = cc_create_private_key_type(module);
    if (state->private_key_type == NULL) {
        goto error;
    }
    state->public_key_type = cc_create_public_key_type(module);
    if (state->public_key_type == NULL) {
        goto error;
    }
    state->xonly_public_key_type = cc_create_xonly_public_key_type(module);
    if (state->xonly_public_key_type == NULL) {
        goto error;
    }

    if (PyModule_AddObjectRef(module, "PrivateKey", state->private_key_type) < 0 ||
        PyModule_AddObjectRef(module, "PublicKey", state->public_key_type) < 0 ||
        PyModule_AddObjectRef(module, "XOnlyPublicKey", state->xonly_public_key_type) < 0) {
        goto error;
    }
    if (cc_add_signature_functions(module) < 0 || cc_add_batch_functions(module) < 0) {
        goto error;
    }
    return 0;

error:
    return -1;
}

static PyModuleDef_Slot coincurve_slots[] = {
    {Py_mod_exec, coincurve_exec},
#if PY_VERSION_HEX >= 0x030C0000
    {Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
#endif
#if PY_VERSION_HEX >= 0x030D0000
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL}
};

static struct PyModuleDef coincurve_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "coincurve._coincurve",
    .m_doc = "Native CPython bindings for libsecp256k1.",
    .m_size = sizeof(CoincurveState),
    .m_slots = coincurve_slots,
    .m_traverse = coincurve_traverse,
    .m_clear = coincurve_clear,
    .m_free = coincurve_free,
};

PyMODINIT_FUNC PyInit__coincurve(void)
{
    return PyModuleDef_Init(&coincurve_module);
}
