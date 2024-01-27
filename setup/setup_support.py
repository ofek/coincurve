import glob
import os
import shutil
import subprocess
import tarfile
from contextlib import contextmanager, suppress
from io import BytesIO
from tempfile import mkdtemp

from setuptools._distutils import log


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
    path = op.join(op.dirname(__file__), *paths)
    normalized_path = op.normpath(path)
    return op.realpath(op.abspath(normalized_path))


def build_flags(library, type_, path=None):
    """Return separated build flags from pkg-config output"""
    from setup.setup_config import PKGCONFIG

    pkg_config_path = [path]
    if 'PKG_CONFIG_PATH' in os.environ:
        pkg_config_path.append(os.environ['PKG_CONFIG_PATH'])
    if 'LIB_DIR' in os.environ:
        pkg_config_path.append(os.environ['LIB_DIR'])
        pkg_config_path.append(os.path.join(os.environ['LIB_DIR'], 'pkgconfig'))

    options = {'I': '--cflags-only-I', 'L': '--libs-only-L', 'l': '--libs-only-l'}
    env = dict(os.environ, PKG_CONFIG_PATH=':'.join(pkg_config_path))

    try:
        subprocess.check_output([PKGCONFIG, '--exists', library], env=env)  # noqa S603
    except subprocess.CalledProcessError:
        log.warn(f'{PKGCONFIG} failed to locate {library} with path={path}')
        return []

    flags = subprocess.check_output([PKGCONFIG, '--static', options[type_], library], env=env)  # noqa S603
    flags = list(flags.decode('UTF-8').split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    from setup.setup_config import PKGCONFIG

    if 'COINCURVE_IGNORE_SYSTEM_LIB' in os.environ:
        return False

    try:
        log.debug('Trying to find libsecp256k1 using pkg-config')
        subprocess.check_output([PKGCONFIG, '--exists', 'libsecp256k1'])  # noqa S603

        includes = subprocess.check_output([PKGCONFIG, '--cflags-only-I', 'libsecp256k1'])  # noqa S603
        includes = includes.strip().decode('utf-8')

        return os.path.exists(os.path.join(includes[2:], 'secp256k1_ecdh.h'))

    except (OSError, subprocess.CalledProcessError):
        if 'LIB_DIR' in os.environ:
            from cffi import FFI

            for path in glob.glob(os.path.join(os.environ['LIB_DIR'], '*secp256k1*')):
                with suppress(OSError):
                    FFI().dlopen(path)
                    return True
        # We couldn't locate libsecp256k1, so we'll use the bundled one
        return False


_has_system_lib = None


def has_system_lib():
    global _has_system_lib
    if _has_system_lib is None:
        _has_system_lib = _find_lib()
    return _has_system_lib


def detect_dll():
    here = os.path.dirname(os.path.abspath(__file__))
    return any(fn.endswith('.dll') for fn in os.listdir(os.path.join(here, '..', 'coincurve')))


def download_library(command, libdir=None, force=False):
    if libdir is None:
        from setup.setup_config import LIB_NAME

        libdir = LIB_NAME

    if command.dry_run:
        return

    if force:
        shutil.rmtree(libdir, ignore_errors=True)

    if os.path.exists(os.path.join(libdir, 'autogen.sh')):
        # Library already downloaded
        return

    # Ensure the path exists
    os.makedirs(libdir, exist_ok=True)

    # _download will use shutil.move, thus remove the directory
    os.rmdir(libdir)

    command.announce(f'Downloading {libdir} source code', level=log.INFO)

    from requests.exceptions import RequestException

    try:
        _download_library(libdir)
    except RequestException as e:
        raise SystemExit(
            f'Unable to download {libdir} library: {e!s}',
        ) from e


def _download_library(libdir):
    import requests

    from setup.setup_config import LIB_TARBALL_URL

    r = requests.get(LIB_TARBALL_URL, stream=True, timeout=10)
    status_code = r.status_code
    if status_code != 200:
        raise SystemExit(f'Unable to download {libdir} library: HTTP-Status: {status_code}')
    content = BytesIO(r.raw.read())
    content.seek(0)
    with tarfile.open(fileobj=content) as tf:
        dirname = tf.getnames()[0].partition('/')[0]
        tf.extractall()
    shutil.move(dirname, libdir)


def exact_library_name(library, path):
    for file in (
        f'lib{library}.dylib',  # MacOS shared - not needed
        f'lib{library}.so',  # Linux shared
        f'lib{library}.a',  # Linux static
        f'lib{library}.lib',  # Windows unix-style lib... (shared or static)
        f'{library}.lib',  # Windows win-style .lib (shared or static)
    ):
        if os.path.isfile(os.path.join(path, 'lib', file)):
            return file, os.path.join(path, 'lib', file)
    raise SystemExit(f'Unable to find library {library} in {path}')
