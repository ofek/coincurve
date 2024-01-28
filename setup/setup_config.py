import os
import platform
import shutil
import sysconfig

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_TAG') or '1ad5185cd42c0636104129fcc9f6a4bf9c67cc40'

LIB_NAME = 'libsecp256k1'
LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'

MAKE = 'gmake' if platform.system() in ['FreeBSD', 'OpenBSD'] else 'make'
PKGCONFIG = shutil.which('pkg-config')
COMPILER = sysconfig.get_config_var('CC')
EXTRA_COMPILE_ARGS = sysconfig.get_config_var('CFLAGS').split()

