import os
from collections import namedtuple

from cffi import FFI

Source = namedtuple('Source', ('h', 'include'))


def _mk_ffi(sources, name='_libsecp256k1', **kwargs):
    _ffi = FFI()
    code = []

    for source in sources:
        with open(os.path.join(here, source.h), 'rt') as h:
            _ffi.cdef(h.read())
        code.append(source.include)

    code.append('#define PY_USE_BUNDLED')
    _ffi.set_source(name, '\n'.join(code), **kwargs)

    return _ffi


_base = [Source('secp256k1.h', '#include <secp256k1.h>')]

_modules = {
    'ecdh': Source('secp256k1_ecdh.h', '#include <secp256k1_ecdh.h>'),
    'recovery': Source('secp256k1_recovery.h', '#include <secp256k1_recovery.h>'),
    'schnorr': Source('secp256k1_schnorr.h', '#include <secp256k1_schnorr.h>'),
}

# By default we only build with recovery enabled since the other modules
# are experimental
if os.environ.get('SECP_BUNDLED_EXPERIMENTAL'):
    ffi = _mk_ffi(_base + list(_modules.values()), libraries=['secp256k1'])
else:
    ffi = _mk_ffi(_base + [_modules['recovery']], libraries=['secp256k1'])
