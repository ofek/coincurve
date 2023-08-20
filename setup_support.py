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


def find_conda_executable(executable: str):
    exec_path = None
    for path in ('LIBRARY_BIN', 'PREFIX', 'BUILD_PREFIX', 'SP_DIR', 'PATH'):
        if os.environ.get(path, None) is None:
            continue

        if exec_path is not None:
            # For windows, we need to replace backslashes with forward slashes
            exec_path = exec_path.replace('\\', '/')
            break

        for root, _, filenames in os.walk(os.environ.get(path)):
            if 'bin' not in root.split(os.sep):
                continue

            for filename in filenames:
                # Strip .exe suffix on Windows
                executable = executable.replace('.exe', '')
                if filename in (executable, f'{executable}.exe'):
                    exec_path = os.path.join(root, filename)
                    break
    return exec_path


def build_flags(library, type_, path):
    """Return separated build flags from pkg-config output"""

    pkg_config_path = [path]
    if 'PKG_CONFIG_PATH' in os.environ:
        pkg_config_path.append(os.environ['PKG_CONFIG_PATH'])
    if 'LIB_DIR' in os.environ:
        pkg_config_path.append(os.environ['LIB_DIR'])
        pkg_config_path.append(os.path.join(os.environ['LIB_DIR'], 'pkgconfig'))

    pkgconfig = find_conda_executable('pkg-config') or 'pkg-config'

    options = {'I': '--cflags-only-I', 'L': '--libs-only-L', 'l': '--libs-only-l'}
    env = dict(os.environ, PKG_CONFIG_PATH=':'.join(pkg_config_path))

    flags = subprocess.check_output([pkgconfig, '--static', options[type_], library], env=env)  # noqa S603
    flags = list(flags.decode('UTF-8').split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    if 'COINCURVE_IGNORE_SYSTEM_LIB' in os.environ:
        return False

    from cffi import FFI

    ffi = FFI()
    try:
        ffi.dlopen('secp256k1')
        return bool(os.path.exists('/usr/include/secp256k1_ecdh.h'))
    except OSError:
        if 'LIB_DIR' in os.environ:
            for path in glob.glob(os.path.join(os.environ['LIB_DIR'], '*secp256k1*')):
                with suppress(OSError):
                    FFI().dlopen(path)
                    return True
        # We couldn't locate libsecp256k1 so we'll use the bundled one
        return False


_has_system_lib = None


def has_system_lib():
    global _has_system_lib
    if _has_system_lib is None:
        _has_system_lib = _find_lib()
    return _has_system_lib


def detect_dll():
    here = os.path.dirname(os.path.abspath(__file__))
    return any(fn.endswith('.dll') for fn in os.listdir(os.path.join(here, 'coincurve')))
