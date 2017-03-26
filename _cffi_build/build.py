import os
import sys
from collections import namedtuple
from itertools import combinations

from cffi import FFI, VerificationError

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from setup_support import has_system_lib, redirect, workdir, absolute

Source = namedtuple('Source', ('h', 'include'))


class Break(Exception):
    pass


def _mk_ffi(sources, name="_libsecp256k1", bundled=True, **kwargs):
    ffi = FFI()
    code = []
    if 'INCLUDE_DIR' in os.environ:
        kwargs['include_dirs'] = [absolute(os.environ['INCLUDE_DIR'])]
    if 'LIB_DIR' in os.environ:
        kwargs['library_dirs'] = [absolute(os.environ['LIB_DIR'])]
    for source in sources:
        with open(source.h, 'rt') as h:
            ffi.cdef(h.read())
        code.append(source.include)
    if bundled:
        code.append("#define PY_USE_BUNDLED")
    ffi.set_source(name, "\n".join(code), **kwargs)
    return ffi


_base = [Source(absolute("_cffi_build/secp256k1.h"), "#include <secp256k1.h>", )]

_modules = {
    'ecdh': Source(absolute("_cffi_build/secp256k1_ecdh.h"), "#include <secp256k1_ecdh.h>", ),
    'recovery': Source(absolute("_cffi_build/secp256k1_recovery.h"), "#include <secp256k1_recovery.h>", ),
    'schnorr': Source(absolute("_cffi_build/secp256k1_schnorr.h"), "#include <secp256k1_schnorr.h>", ),
}


ffi = None

# The following is used to detect whether the library is already installed on
# the system (and if so which modules are enabled) or if we will use the
# bundled one.
if has_system_lib():
    _available = []
    try:
        # try all combinations of optional modules that could be enabled
        # works downwards from most enabled modules to fewest
        for l in range(len(_modules), -1, -1):
            for combination in combinations(_modules.items(), l):
                try:
                    _test_ffi = _mk_ffi(
                        _base + [item[1] for item in combination],
                        name="_testcompile",
                        bundled=False,
                        libraries=['secp256k1']
                    )
                    with redirect(sys.stderr, os.devnull), workdir():
                        _test_ffi.compile()
                    _available = combination
                    raise Break()
                except VerificationError as ex:
                    pass
    except Break:
        ffi = _mk_ffi(
            _base + [i[1] for i in _available],
            bundled=False,
            libraries=['secp256k1']
        )
        print("Using system libsecp256k1 with modules: {}".format(
            ", ".join(i[0] for i in _available))
        )
    else:
        # We didn't find any functioning combination of modules
        # Normally this shouldn't happen but just in case we will fall back
        # to the bundled library
        print("Installed libsecp256k1 is unusable falling back to bundled version.")

if ffi is None:
    # Library is not installed - use bundled one
    print("Using bundled libsecp256k1")

    # By default we only build with recovery enabled since the other modules
    # are experimental
    if os.environ.get('SECP_BUNDLED_EXPERIMENTAL'):
        ffi = _mk_ffi(_base + list(_modules.values()), libraries=['secp256k1'])
    else:
        ffi = _mk_ffi(_base + [_modules['recovery']], libraries=['secp256k1'])
