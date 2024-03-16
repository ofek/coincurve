import glob
import logging
import os
import shutil
import subprocess
import tarfile
from contextlib import suppress
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
    cmd = ['pkg-config', options[type_], library]
    flags = subprocess_run(cmd)
    flags = list(flags.split())

    return [flag.strip(f'-{type_}') for flag in flags]


def _find_lib():
    if 'COINCURVE_IGNORE_SYSTEM_LIB' in os.environ:
        return False

    from cffi import FFI

    try:
        cmd = ['pkg-config', '--cflags-only-I', 'libsecp256k1']
        includes = subprocess_run(cmd)

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


def detect_dll(root_dir):
    for fn in os.listdir(os.path.join(root_dir)):
        if fn.endswith('.dll'):
            return True
    return False


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
