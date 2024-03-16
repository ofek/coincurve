import logging
import os
import shutil
import subprocess
import tarfile
from io import BytesIO


def absolute(*paths):
    from setup import COINCURVE_ROOT_DIR

    op = os.path
    return op.realpath(op.abspath(op.join(COINCURVE_ROOT_DIR, *paths)))


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
    flags = call_pkg_config([options[type_]], library)
    flags = list(flags.split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    if os.getenv('COINCURVE_IGNORE_SYSTEM_LIB', '1') == '1':
        return False

    update_pkg_config_path()

    try:
        options = ['--libs-only-L']
        lib_dir = call_pkg_config(options, 'libsecp256k1')

        return verify_system_lib(lib_dir[2:].strip(), None)

    except (OSError, subprocess.CalledProcessError):
        from ctypes.util import find_library

        return bool(find_library('secp256k1'))


_has_system_lib = None


def has_system_lib():
    global _has_system_lib
    if _has_system_lib is None:
        _has_system_lib = _find_lib()
    return _has_system_lib


def detect_dll(root_dir: str):
    return any(fn.endswith('.dll') for fn in os.listdir(os.path.join(root_dir)))


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
    from platform import system

    if system() == 'Windows':
        options.append('--dont-define-prefix')

    pkg_config = shutil.which('pkg-config')
    cmd = [pkg_config, *options, library]

    return subprocess_run(cmd, debug=debug)


def download_library(command):
    if command.dry_run:
        return

    from setup import COINCURVE_ROOT_DIR

    libdir = absolute(COINCURVE_ROOT_DIR, 'libsecp256k1')
    if os.path.exists(os.path.join(libdir, 'autogen.sh')):
        # Library already downloaded
        return
    if not os.path.exists(libdir):
        import logging

        command.announce('downloading libsecp256k1 source code', level=logging.INFO)
        try:
            import requests

            try:
                from setup import LIB_TARBALL_URL

                r = requests.get(LIB_TARBALL_URL, stream=True, timeout=10)
                status_code = r.status_code
                if status_code == 200:
                    content = BytesIO(r.raw.read())
                    content.seek(0)
                    with tarfile.open(fileobj=content) as tf:
                        dirname = tf.getnames()[0].partition('/')[0]
                        tf.extractall()  # noqa: S202
                    shutil.move(dirname, libdir)
                else:
                    raise SystemExit('Unable to download secp256k1 library: HTTP-Status: %d', status_code)
            except requests.exceptions.RequestException as e:
                raise SystemExit('Unable to download secp256k1 library: %s') from e
        except ImportError as e:
            raise SystemExit('Unable to download secp256k1 library: %s') from e


def update_pkg_config_path(path='.'):
    """Updates the PKG_CONFIG_PATH environment variable to include the given path."""
    pkg_config_paths = [path, os.getenv('PKG_CONFIG_PATH', '').strip('"')]
    logging.warning(f'env: {os.getenv("PKG_CONFIG_PATH")}')

    if cpf := os.getenv('CONDA_PREFIX'):
        conda_paths = [os.path.join(cpf, sbd, 'pkgconfig') for sbd in ('lib', 'lib64', os.path.join('Library', 'lib'))]
        pkg_config_paths.extend([p for p in conda_paths if os.path.isdir(p)])

    if lbd := os.getenv('LIB_DIR'):
        pkg_config_paths.append(os.path.join(lbd, 'pkgconfig'))

    logging.warning(f'env: {pkg_config_paths}')
    # Update environment
    os.environ['PKG_CONFIG_PATH'] = os.pathsep.join(pkg_config_paths)


def verify_system_lib(lib_dir, inst_dir):
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

    logging.warning(f'   {inst_dir = }')
    if dyn_lib and inst_dir is not None:
        lib_base = dyn_lib.stem
        # Update coincurve._secp256k1_library_info
        info_file = Path(inst_dir, '_secp256k1_library_info.py')
        logging.warning(f'   {info_file = }')
        info_file.write_text(f"SECP256K1_LIBRARY_NAME = '{lib_base}'\nSECP256K1_LIBRARY_TYPE = 'EXTERNAL'\n")

    return found
