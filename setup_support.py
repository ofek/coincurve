import glob
import hashlib
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager, suppress
from io import BytesIO
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


def absolute_from_setup_dir(*paths):
    from setup import PACKAGE_SETUP_DIR

    op = os.path
    return op.realpath(op.abspath(op.join(PACKAGE_SETUP_DIR, *paths)))


def build_flags(library, type_, path='.'):
    """Return separated build flags from pkg-config output"""
    from setup import PKGCONFIG

    pkg_config_path = [path]
    if 'PKG_CONFIG_PATH' in os.environ:
        pkg_config_path.append(os.environ['PKG_CONFIG_PATH'])
    if 'LIB_DIR' in os.environ:
        pkg_config_path.append(os.environ['LIB_DIR'])
        pkg_config_path.append(os.path.join(os.environ['LIB_DIR'], 'pkgconfig'))
    if 'CONDA_PREFIX' in os.environ:
        pkg_config_path.append(os.path.join(os.environ['CONDA_PREFIX'], 'lib', 'pkgconfig'))

    options = {'I': '--cflags-only-I', 'L': '--libs-only-L', 'l': '--libs-only-l'}
    env = dict(os.environ, PKG_CONFIG_PATH=':'.join(pkg_config_path))
    flags = subprocess.check_output([PKGCONFIG, options[type_], library], env=env)  # noqa S603
    flags = list(flags.decode('UTF-8').split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    if 'COINCURVE_IGNORE_SYSTEM_LIB' in os.environ:
        return False

    try:
        from setup import PKGCONFIG

        # Update the environment CONDA_PREFIX to the current environment
        if 'CONDA_PREFIX' in os.environ:
            os.environ['PKG_CONFIG_PATH'] = (
                    os.path.join(os.environ['CONDA_PREFIX'], 'lib', 'pkgconfig')
                    + ':'
                    + os.environ.get('PKG_CONFIG_PATH', '')
            )

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
    for fn in os.listdir(os.path.join(here, 'coincurve')):
        if fn.endswith('.dll'):
            return True
    return False


def download_library(command, lib_dir='libsecp256k1', force=False):
    if command.dry_run:
        return

    if force:
        shutil.rmtree(lib_dir, ignore_errors=True)

    if os.path.exists(os.path.join(lib_dir, 'autogen.sh')) or os.path.exists(os.path.join(lib_dir, 'libsecp256k1.pc')):
        # Library already downloaded
        return

    # Ensure the path exists
    os.makedirs(lib_dir, exist_ok=True)

    # _download will use shutil.move, thus remove the directory
    os.rmdir(lib_dir)

    logging.info(f'Downloading {lib_dir} source code')

    from requests.exceptions import RequestException

    try:
        _download_library(lib_dir)
    except RequestException as e:
        raise SystemExit(
            f'Unable to download {lib_dir} library: {e!s}',
        ) from e


def _download_library(lib_dir=None):
    import requests

    from setup import LIB_NAME, LIB_TARBALL_HASH, LIB_TARBALL_URL, TAR_NAME, UPSTREAM_REF

    if lib_dir is None:
        lib_dir = LIB_NAME
        try:
            os.makedirs(lib_dir)
        except OSError:
            logging.info(f'Library directory {lib_dir} already exists')
            return

    r = requests.get(LIB_TARBALL_URL, stream=True, timeout=10, verify=True)
    status_code = r.status_code
    if status_code != 200:
        raise SystemExit(f'Unable to download {lib_dir} library: HTTP-Status: {status_code}')

    content = BytesIO(r.raw.read())
    content.seek(0)

    # Verify the integrity of the downloaded library
    sha256_hash = hashlib.sha256(content.getvalue()).hexdigest()
    if sha256_hash != LIB_TARBALL_HASH:
        raise SystemExit(f'Integrity check failed for {lib_dir}{sha256_hash} library: Hash mismatch')

    # Write the content to a file
    with open(f'{UPSTREAM_REF}.tar.gz', 'wb') as f:
        f.write(content.getvalue())

    with tarfile.open(f'{UPSTREAM_REF}.tar.gz') as tf:
        for member in tf.getmembers():
            if member.name.startswith(f'{TAR_NAME}/'):
                member.name = member.name[len(f'{TAR_NAME}/'):]
                tf.extract(member, path=lib_dir)

    os.remove(f'{UPSTREAM_REF}.tar.gz')


def execute_command_with_temp_log(cmd, cwd=None, debug=False):
    with tempfile.NamedTemporaryFile(mode='w+') as temp_log:
        try:
            subprocess.check_call(cmd, stdout=temp_log, stderr=temp_log, cwd=cwd)  # noqa S603
            if debug:
                temp_log.seek(0)
                log_contents = temp_log.read()
                logging.info(f'Command log:\n{log_contents}')
        except subprocess.CalledProcessError as e:
            logging.error(f'An error occurred during the command execution: {e}')
            temp_log.seek(0)
            log_contents = temp_log.read()
            logging.error(f'Command log:\n{log_contents}')
            raise e
