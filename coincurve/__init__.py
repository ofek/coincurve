import ctypes
import os
import platform
import warnings

from coincurve._secp256k1_library_info import SECP256K1_LIBRARY_NAME, SECP256K1_LIBRARY_TYPE
from coincurve.context import GLOBAL_CONTEXT, Context
from coincurve.keys import PrivateKey, PublicKey, PublicKeyXOnly
from coincurve.utils import verify_signature

__all__ = [
    'GLOBAL_CONTEXT',
    'SECP256K1_LIBRARY_TYPE',
    'SECP256K1_LIBRARY_NAME',
    'Context',
    'PrivateKey',
    'PublicKey',
    'PublicKeyXOnly',
    'verify_signature',
]


def load_secp256k1_conda_library():
    if SECP256K1_LIBRARY_TYPE != 'EXTERNAL':
        return

    if (conda := os.getenv('CONDA_PREFIX')) is None:
        warnings.warn('This coincurve package requires a CONDA environment', stacklevel=2)
        return

    if platform.system() == 'Windows':
        library = os.path.join(conda, 'Library', 'bin', f'{SECP256K1_LIBRARY_NAME}.dll')
    elif platform.system() == 'Darwin':
        library = os.path.join(conda, 'lib', f'{SECP256K1_LIBRARY_NAME}.dylib')
    else:
        library = os.path.join(conda, 'lib', f'{SECP256K1_LIBRARY_NAME}.so')

    try:
        ctypes.CDLL(library)
    except Exception as e:
        warnings.warn(f'The required library {SECP256K1_LIBRARY_NAME}.so/dylib/dll is not loaded.\n{e}', stacklevel=2)
