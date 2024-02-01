import glob
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

    pkg_config_path = [path]
    if 'PKG_CONFIG_PATH' in os.environ:
        pkg_config_path.append(os.environ['PKG_CONFIG_PATH'])
    if 'LIB_DIR' in os.environ:
        pkg_config_path.append(os.environ['LIB_DIR'])
        pkg_config_path.append(os.path.join(os.environ['LIB_DIR'], 'pkgconfig'))

    options = {'I': '--cflags-only-I', 'L': '--libs-only-L', 'l': '--libs-only-l'}
    env = dict(os.environ, PKG_CONFIG_PATH=':'.join(pkg_config_path))
    logging.info('Debug info\n\n\n')
    logging.info(f'DBG:   pkg-config path: {env["PKG_CONFIG_PATH"]}')
    logging.info(f'DBG:   {path}')
    logging.info(f'DBG:   {os.path.isfile(os.path.join(path, "libsecp256k1.pc"))}')
    logging.info('\n\n\n')
    flags = subprocess.check_output(['pkg-config', options[type_], library], env=env)  # noqa S603
    flags = list(flags.decode('UTF-8').split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    if 'COINCURVE_IGNORE_SYSTEM_LIB' in os.environ:
        return False

    from cffi import FFI

    try:
        subprocess.check_output(['pkg-config', '--exists', 'libsecp256k1'])  # noqa S603

        includes = subprocess.check_output(['pkg-config', '--cflags-only-I', 'libsecp256k1'])  # noqa S603
        includes = includes.strip().decode('utf-8')

        return os.path.exists(os.path.join(includes[2:], 'secp256k1_ecdh.h'))

    except (OSError, subprocess.CalledProcessError):
        if 'LIB_DIR' in os.environ:
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


def download_library(command):
    if command.dry_run:
        return

    libdir = absolute_from_setup_dir('libsecp256k1')
    if os.path.exists(os.path.join(libdir, 'autogen.sh')):
        # Library already downloaded
        return
    if not os.path.exists(libdir):
        logging.info('downloading libsecp256k1 source code')
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
                        tf.extractall()
                    shutil.move(dirname, libdir)
                else:
                    raise SystemExit('Unable to download secp256k1 library: HTTP-Status: %d', status_code)
            except requests.exceptions.RequestException as e:
                raise SystemExit('Unable to download secp256k1 library: %s', str(e)) from e
        except ImportError as e:
            raise SystemExit('Unable to download secp256k1 library: %s', str(e)) from e


def execute_command_with_temp_log(cmd, cwd=None):
    with tempfile.NamedTemporaryFile(mode='w+') as temp_log:
        try:
            subprocess.check_call(cmd, stdout=temp_log, stderr=temp_log, cwd=cwd)  # noqa S603
        except subprocess.CalledProcessError as e:
            logging.error(f'An error occurred during the command execution: {e}')
            temp_log.seek(0)
            log_contents = temp_log.read()
            logging.error(f'Command log:\n{log_contents}')
            raise e
