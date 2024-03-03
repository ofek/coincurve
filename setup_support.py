import glob
import os
import shutil
import subprocess
from contextlib import contextmanager, suppress
from tempfile import mkdtemp


@contextmanager
def workdir():
    cwd = os.getcwd()
    tmpdir = mkdtemp()
    os.chdir(tmpdir)
    try:
        yield
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmpdir)


@contextmanager
def redirect(stdchannel, dest_filename):
    oldstdchannel = os.dup(stdchannel.fileno())
    dest_file = open(dest_filename, 'w')
    os.dup2(dest_file.fileno(), stdchannel.fileno())
    try:
        yield
    finally:
        if oldstdchannel is not None:
            os.dup2(oldstdchannel, stdchannel.fileno())
        if dest_file is not None:
            dest_file.close()


def absolute(*paths):
    op = os.path
    return op.realpath(op.abspath(op.join(op.dirname(__file__), *paths)))


def _update_pkg_config_path(path='.'):
    """Return separated build flags from pkg-config output"""

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

    _update_pkg_config_path(path)

    options = {'I': '--cflags-only-I', 'L': '--libs-only-L', 'l': '--libs-only-l'}
    flags = subprocess.check_output(['pkg-config', '--static', options[type_], library])  # noqa S603
    flags = list(flags.decode('UTF-8').split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    if 'COINCURVE_IGNORE_SYSTEM_LIB' in os.environ:
        return False

    import logging

    from cffi import FFI

    from setup import SECP256K1_BUILD

    _update_pkg_config_path()
    logging.info(f'\n   PKG_CONFIG_PATH: {os.environ["PKG_CONFIG_PATH"]}\n')

    try:
        lib_dir = subprocess.check_output(['pkg-config', '--libs-only-L', 'libsecp256k1'])  # noqa S603
    except (OSError, subprocess.CalledProcessError):
        if 'LIB_DIR' in os.environ:
            for path in glob.glob(os.path.join(os.environ['LIB_DIR'], '*secp256k1*')):
                with suppress(OSError):
                    FFI().dlopen(path)
                    return True
        # We couldn't locate libsecp256k1, so we'll use the bundled one
        return False

    # tox fails when the dynamic library is installed for a STATIC linkage
    # so we need to check the type of the installed library
    lib_dir = lib_dir[2:].strip().decode('utf-8')
    if os.name == 'nt':
        dyn_lib = any(
            (
                os.path.exists(os.path.join(lib_dir[:-3], 'bin', 'secp256k1.dll')),
                os.path.exists(os.path.join(lib_dir[:-3], 'bin', 'libsecp256k1.dll')),
            )
        )
    else:
        dyn_lib = any(
            (
                os.path.exists(os.path.join(lib_dir, 'libsecp256k1.so')),
                os.path.exists(os.path.join(lib_dir, 'libsecp256k1.dylib')),
            )
        )
    return any((dyn_lib and SECP256K1_BUILD == 'SHARED', not dyn_lib and SECP256K1_BUILD != 'SHARED'))


_has_system_lib = None


def has_system_lib():
    import logging

    global _has_system_lib
    if _has_system_lib is None:
        _has_system_lib = _find_lib()
    logging.info(f'\n   SYSTEM LIB: {_has_system_lib}\n')
    return _has_system_lib
