import os.path
import platform
import shutil
import subprocess
import sys

from setuptools import Distribution as _Distribution, setup, find_packages, __version__ as setuptools_version
from setuptools._distutils import log
from setuptools._distutils.errors import DistutilsError
from setuptools.extension import Extension
from setuptools.command.develop import develop as _develop
from setuptools.command.dist_info import dist_info as _dist_info
from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.sdist import sdist as _sdist

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from setup_support import detect_dll, has_system_lib, download_library  # noqa: E402

BUILDING_FOR_WINDOWS = detect_dll()

MAKE = 'gmake' if platform.system() in ['FreeBSD', 'OpenBSD'] else 'make'

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_TAG') or '1ad5185cd42c0636104129fcc9f6a4bf9c67cc40'

LIB_NAME = 'libsecp256k1'
LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'

# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.', 2)[:2]] < [3, 3]:
    raise SystemExit(
        f'Your setuptools version ({setuptools_version}) is too old to correctly install this package. Please upgrade '
        f'to a newer version (>= 3.3).'
    )


class egg_info(_egg_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        _egg_info.run(self)


class dist_info(_dist_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self, force=True)

        _dist_info.run(self)


class sdist(_sdist):
    def run(self):
        if not has_system_lib():
            download_library(self, force=True)
        _sdist.run(self)


if _bdist_wheel:

    class bdist_wheel(_bdist_wheel):
        def run(self):
            if not has_system_lib():
                download_library(self)
            _bdist_wheel.run(self)

else:
    bdist_wheel = None


class develop(_develop):
    def run(self):
        if not has_system_lib():
            raise DistutilsError(
                "This library is not usable in 'develop' mode when using the "
                f'bundled {LIB_NAME}. See README for details.'
            )
        _develop.run(self)


class Distribution(_Distribution):
    def has_c_libraries(self):
        return not has_system_lib()


pkgconfig = shutil.which('pkg-config')
if pkgconfig is None:
    raise DistutilsError('pkg-config is required')

package_data = {'coincurve': ['py.typed']}

extension = Extension(
    name='coincurve._libsecp256k1',
    sources=[os.path.join('coincurve', '_libsecp256k1.c')],
    # ABI?: py_limited_api=True,
)

# Cases to consider:
# . Building for any OS, use system libsecp256k1
# . Building for Windows Native, build secp256k1 locally
# . Building for Windows with cross-compile, build secp256k1 locally
# . Building for other OS, build secp256k1 locally

# Building for any OS, use system libsecp256k1

if has_system_lib():
    from setup_build_extension import BuildCFFIForStaticLib

    log.info('Using system library')

    extension.extra_compile_args = [
        subprocess.check_output([pkgconfig, '--cflags-only-I', 'libsecp256k1']).strip().decode('utf-8')  # noqa S603
    ]
    extension.extra_link_args = [
        subprocess.check_output([pkgconfig, '--libs-only-L', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
        subprocess.check_output([pkgconfig, '--libs-only-l', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
    ]

    setup_kwargs = dict(
        ext_modules=[extension],
        cmdclass={
            'build_ext': BuildCFFIForStaticLib,
            'develop': develop,
            'egg_info': egg_info,
            'sdist': sdist,
            'bdist_wheel': bdist_wheel,
        },
    )

else:
    from setup_build_extension import BuildCFFIForStaticLib
    from setup_build_secp256k1_with_make import BuildClibWithMake
    setup_kwargs = dict(
        ext_modules=[extension],
        cmdclass={
            'build_clib': BuildClibWithMake,
            'build_ext': BuildCFFIForStaticLib,
            'develop': develop,
            'egg_info': egg_info,
            'sdist': sdist,
            'bdist_wheel': bdist_wheel,
        },
    )

    if BUILDING_FOR_WINDOWS:
        package_data['coincurve'].append('libsecp256k1.dll')

setup(
    name='coincurve',
    version='19.0.0',
    requires=['asn1crypto', 'cffi(>=1.3.0)'],

    packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', LIB_NAME, 'tests')),
    package_data=package_data,

    distclass=Distribution,
    zip_safe=False,
    **setup_kwargs
)
