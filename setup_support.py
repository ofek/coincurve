import glob
import logging
import os
import shutil
import subprocess
import tempfile
from contextlib import suppress


def absolute(*paths):
    op = os.path
    return op.realpath(op.abspath(op.join(op.dirname(__file__), *paths)))


def update_pkg_config_path(path='.'):
    """Updates the PKG_CONFIG_PATH environment variable to include the given path."""

    pkg_config_path = [path]
    if 'PKG_CONFIG_PATH' in os.environ:
        pkg_config_path.append(os.environ['PKG_CONFIG_PATH'])
    if 'CONDA_PREFIX' in os.environ:
        pkg_config_path.extend(
            [
                p
                for p in (
                    os.path.join(os.environ['CONDA_PREFIX'], 'lib', 'pkgconfig'),
                    os.path.join(os.environ['CONDA_PREFIX'], 'lib64', 'pkgconfig'),
                    os.path.join(os.environ['CONDA_PREFIX'], 'Library', 'lib', 'pkgconfig'),
                )
                if os.path.isdir(p)
            ]
        )
    if 'LIB_DIR' in os.environ:
        pkg_config_path.append(os.environ['LIB_DIR'])
        pkg_config_path.append(os.path.join(os.environ['LIB_DIR'], 'pkgconfig'))

    # Update environment
    os.environ['PKG_CONFIG_PATH'] = str(os.pathsep).join(pkg_config_path)


def build_flags(library, type_, path):
    """Return separated build flags from pkg-config output"""

    update_pkg_config_path(path)

    options = {'I': '--cflags-only-I', 'L': '--libs-only-L', 'l': '--libs-only-l'}
    # flags = subprocess.check_output(['pkg-config', options[type_], library])  # S603
    flags = call_pkg_config([options[type_]], library, capture_output=True)
    flags = list(flags.split())

    return [flag.strip(f'-{type_}') for flag in flags]


def call_pkg_config(options, library, *, debug=False, capture_output=False):
    from setup import SYSTEM

    if SYSTEM == 'Windows':
        options.append('--dont-define-prefix')

    with tempfile.NamedTemporaryFile(mode='w+') as temp_log:
        try:
            pkg_config = shutil.which('pkg-config')
            cmd = [pkg_config, *options, library]

            if capture_output:
                ret = subprocess.check_output(cmd, stderr=temp_log)  # noqa S603
            else:
                subprocess.check_call(cmd, stdout=temp_log, stderr=temp_log)  # noqa S603

            if debug:
                temp_log.seek(0)
                log_contents = temp_log.read()
                logging.info(f'Command log:\n{log_contents}')

            if capture_output:
                return ret.rstrip().decode()

        except subprocess.CalledProcessError as e:
            logging.error(f'An error occurred during the command execution: {e}')
            temp_log.seek(0)
            log_contents = temp_log.read()
            logging.error(f'Command log:\n{log_contents}')
            raise e


def has_installed_libsecp256k1():
    if os.getenv('COINCURVE_IGNORE_SYSTEM_LIB', '1') == '1':
        return False

    from cffi import FFI

    from setup import LIB_NAME, SECP256K1_BUILD, SYSTEM

    update_pkg_config_path()

    try:
        lib_dir = call_pkg_config(['--libs-only-L'], LIB_NAME, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        if 'LIB_DIR' in os.environ:
            for path in glob.glob(os.path.join(os.environ['LIB_DIR'], f'*{LIB_NAME[3:]}*')):
                with suppress(OSError):
                    FFI().dlopen(path)
                    return True
        # We couldn't locate libsecp256k1, so we'll use the bundled one
        return False

    # tox fails when the dynamic library is installed for a STATIC linkage,
    # so we need to check the type of the installed library
    lib_dir = lib_dir[2:].strip()
    if SYSTEM == 'Windows':
        no_lib_path = os.path.join(lib_dir[:-3], "bin", f"{LIB_NAME[3:]}.dll")
        lib_path = os.path.join(lib_dir[:-3], 'bin', f'{LIB_NAME}.dll')
        logging.info(f'DBG:\n   {no_lib_path = }\n   {lib_path = }')
        dyn_lib = any(
            (
                os.path.exists(no_lib_path),
                os.path.exists(lib_path),
            )
        )
    else:
        dyn_lib = any(
            (
                os.path.exists(os.path.join(lib_dir, f'{LIB_NAME}.so')),
                os.path.exists(os.path.join(lib_dir, f'{LIB_NAME}.dylib')),
            )
        )
    found = any((dyn_lib and SECP256K1_BUILD == 'SHARED', not dyn_lib and SECP256K1_BUILD != 'SHARED'))

    if not found:
        logging.warning(
            f'WARNING: {LIB_NAME} is installed, but it is not the expected type. '
            'Please ensure that the shared library is installed.'
        )
    return found
