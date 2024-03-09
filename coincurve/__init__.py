def load_secp256k1_conda_library():
    """Load the secp256k1 library from the conda environment."""
    import warnings

    from coincurve._secp256k1_library_info import SECP256K1_LIBRARY_NAME, SECP256K1_LIBRARY_TYPE

    if SECP256K1_LIBRARY_TYPE != 'EXTERNAL':
        warnings.warn(f'DBG: {SECP256K1_LIBRARY_NAME}:{SECP256K1_LIBRARY_TYPE}', stacklevel=2)
        return

    import os

    if (conda := os.getenv('CONDA_PREFIX')) is None:
        warnings.warn('This coincurve package requires a CONDA environment', stacklevel=2)
        return

    import platform

    if platform.system() == 'Windows':
        library = os.path.join(conda, 'Library', 'bin', f'{SECP256K1_LIBRARY_NAME}.dll')
    elif platform.system() == 'Darwin':
        library = os.path.join(conda, 'lib', f'{SECP256K1_LIBRARY_NAME}.dylib')
    else:
        library = os.path.join(conda, 'lib', f'{SECP256K1_LIBRARY_NAME}.so')

    try:
        import ctypes

        ctypes.CDLL(library)
    except Exception as e:
        warnings.warn(f'The required library {SECP256K1_LIBRARY_NAME}.so/dylib/dll is not loaded.\n{e}', stacklevel=2)


load_secp256k1_conda_library()

from coincurve.context import GLOBAL_CONTEXT, Context  # noqa: E402
from coincurve.keys import PrivateKey, PublicKey, PublicKeyXOnly  # noqa: E402
from coincurve.utils import verify_signature  # noqa: E402

__all__ = [
    'GLOBAL_CONTEXT',
    'Context',
    'PrivateKey',
    'PublicKey',
    'PublicKeyXOnly',
    'verify_signature',
]
