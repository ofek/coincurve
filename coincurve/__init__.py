def load_secp256k1_conda_library():
    """Load the secp256k1 library from the conda environment."""
    import warnings

    from coincurve._secp256k1_library_info import SECP256K1_LIBRARY_NAME, SECP256K1_LIBRARY_TYPE

    if SECP256K1_LIBRARY_TYPE != 'EXTERNAL':
        # coincurve was built with an internal library, either static or shared. It 'knows' where the library is.
        return

    import os
    from ctypes import CDLL
    from ctypes.util import find_library

    try:
        # Find the library in the typical installation paths
        if library := find_library(SECP256K1_LIBRARY_NAME):
            CDLL(library)
            return

        # Find the library in the conda environment
        if (conda := os.getenv('CONDA_PREFIX')) is not None:
            import platform

            if platform.system() == 'Windows':
                library = os.path.join(conda, 'Library', 'bin', SECP256K1_LIBRARY_NAME)
            else:
                library = os.path.join(conda, 'lib', SECP256K1_LIBRARY_NAME)

            CDLL(library)
            return
    except Exception as e:
        warnings.warn(f'The required library {SECP256K1_LIBRARY_NAME}l is not loaded.\n{e}', stacklevel=2)


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
