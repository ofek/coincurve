import logging
import os
import subprocess


def absolute(*paths):
    op = os.path
    return op.realpath(op.abspath(op.join(op.dirname(__file__), *paths)))


def build_flags(library, type_, path):
    """Return separated build flags from pkg-config output"""

    pkg_config_path = [path]
    if 'PKG_CONFIG_PATH' in os.environ:
        pkg_config_path.append(os.environ['PKG_CONFIG_PATH'])
    if 'LIB_DIR' in os.environ:
        pkg_config_path.append(os.environ['LIB_DIR'])
        pkg_config_path.append(os.path.join(os.environ['LIB_DIR'], 'pkgconfig'))

    # Update PKG_CONFIG_PATH, it may be needed in later stages
    new_path = str(os.pathsep).join(pkg_config_path)
    os.environ['PKG_CONFIG_PATH'] = new_path + os.pathsep + os.environ.get('PKG_CONFIG_PATH', '')

    options = {'I': '--cflags-only-I', 'L': '--libs-only-L', 'l': '--libs-only-l'}
    if os.name == 'nt':
        cmd = ['pkg-config', options[type_], '--dont-define-prefix', library]
    else:
        cmd = ['pkg-config', options[type_], library]
    flags = subprocess_run(cmd)
    flags = list(flags.split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    if os.getenv('COINCURVE_IGNORE_SYSTEM_LIB', '1') == '1':
        return False

    update_pkg_config_path()

    try:
        if os.name == 'nt':
            cmd = ['pkg-config', '--libs-only-L', '--dont-define-prefix', 'libsecp256k1']
        else:
            cmd = ['pkg-config', '--libs-only-L', 'libsecp256k1']
        lib_dir = subprocess_run(cmd)

        return verify_system_lib(lib_dir[2:].strip())

    except (OSError, subprocess.CalledProcessError):
        from ctypes.util import find_library

        return bool(find_library('secp256k1'))


_has_system_lib = None


def has_system_lib():
    global _has_system_lib
    if _has_system_lib is None:
        _has_system_lib = _find_lib()
    return _has_system_lib


def subprocess_run(cmd, *, debug=False):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa S603
        if debug:
            logging.info(f'Command log:\n{result.stderr}')

        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        logging.error(f'An error occurred during the command execution: {e}')
        logging.error(f'Command log:\n{e.stderr}')
        raise e


def call_pkg_config(options, library, *, debug=False):
    """Calls pkg-config with the given options and returns the output."""
    import shutil

    from setup import SYSTEM

    if SYSTEM == 'Windows':
        options.append('--dont-define-prefix')

    pkg_config = shutil.which('pkg-config')
    cmd = [pkg_config, *options, library]

    return subprocess_run(cmd, debug=debug)


def define_secp256k1_local_lib_info():
    """
    Define the library name and the installation directory
    The purpose is to automatically include the shared library in the package and
    prevent inclusion the static library. This is probably hacky, but it works.
    """
    from setup import LIB_NAME, PKG_NAME, SECP256K1_BUILD

    if SECP256K1_BUILD == 'SHARED':
        return PKG_NAME, 'lib'
    return LIB_NAME, 'x_lib'


def update_pkg_config_path(path='.'):
    """Updates the PKG_CONFIG_PATH environment variable to include the given path."""
    pkg_config_paths = [path, os.getenv('PKG_CONFIG_PATH', '').strip('"')]

    if cpf := os.getenv('CONDA_PREFIX'):
        conda_paths = [os.path.join(cpf, sbd, 'pkgconfig') for sbd in ('lib', 'lib64', os.path.join('Library', 'lib'))]
        pkg_config_paths.extend([p for p in conda_paths if os.path.isdir(p)])

    if lbd := os.getenv('LIB_DIR'):
        pkg_config_paths.append(os.path.join(lbd, 'pkgconfig'))

    # Update environment
    os.environ['PKG_CONFIG_PATH'] = os.pathsep.join(pkg_config_paths)


def verify_system_lib(lib_dir):
    """Verifies that the system library is installed and of the expected type."""
    import ctypes
    import platform
    from ctypes.util import find_library
    from pathlib import Path

    LIB_NAME = 'libsecp256k1'  # noqa N806
    PKG_NAME = 'coincurve'  # noqa N806
    SECP256K1_BUILD = os.getenv('COINCURVE_SECP256K1_BUILD') or 'STATIC'  # noqa N806
    SYSTEM = platform.system()  # noqa N806

    def load_library(lib):
        try:
            return ctypes.CDLL(lib)
        except OSError:
            return None

    logging.warning(f'find_library: {find_library(LIB_NAME[3:])}')
    lib_dir = Path(lib_dir).with_name('bin') if SYSTEM == 'Windows' else Path(lib_dir)
    lib_ext = '.dll' if SYSTEM == 'Windows' else '.[sd][oy]*'
    logging.warning(f'dir: {lib_dir}')
    logging.warning(f'patt: *{LIB_NAME[3:]}{lib_ext}')
    l_dyn = list(lib_dir.glob(f'*{LIB_NAME[3:]}*{lib_ext}'))

    # Evaluates the dynamic libraries found,
    logging.warning(f'Found libraries: {l_dyn}')
    dyn_lib = next((lib for lib in l_dyn if load_library(lib) is not None), False)

    found = any((dyn_lib and SECP256K1_BUILD == 'SHARED', not dyn_lib and SECP256K1_BUILD != 'SHARED'))
    if not found:
        logging.warning(
            f'WARNING: {LIB_NAME} is installed, but it is not the expected type. '
            f'Please ensure that the {SECP256K1_BUILD} library is installed.'
        )

    if dyn_lib:
        lib_base = dyn_lib.stem
        # Update coincurve._secp256k1_library_info
        info_file = Path(PKG_NAME, '_secp256k1_library_info.py')
        info_file.write_text(f"SECP256K1_LIBRARY_NAME = '{lib_base}'\nSECP256K1_LIBRARY_TYPE = 'EXTERNAL'\n")

    return found
