import os.path
import sys

from setuptools import Distribution as _Distribution, setup, find_packages, __version__ as setuptools_version
from setuptools._distutils import log
from setuptools._distutils.errors import DistutilsError
from setuptools.command.develop import develop as _develop
from setuptools.command.dist_info import dist_info as _dist_info
from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.sdist import sdist as _sdist
from setuptools.extension import Extension

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from setup.setup_config import LIB_NAME, PKGCONFIG  # noqa: E402
from setup.setup_support import detect_dll, has_system_lib, download_library  # noqa: E402

BUILDING_FOR_WINDOWS = detect_dll()

# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.', 2)[:2]] < [3, 3]:
    raise SystemExit(
        f'Your setuptools version ({setuptools_version}) is too old to correctly install this package. Please upgrade '
        f'to a newer version (>= 3.3).'
    )


class EggInfo(_egg_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        super().run()


class DistInfo(_dist_info):
    def run(self):
        if not has_system_lib():
            download_library(self)
        super().run()


class Sdist(_sdist):
    def run(self):
        if not has_system_lib():
            download_library(self, force=True)
        super().run()


if _bdist_wheel:

    class BdistWheel(_bdist_wheel):
        def run(self):
            if not has_system_lib():
                download_library(self)
            super().run()

else:
    BdistWheel = None


class Develop(_develop):
    def run(self):
        if not has_system_lib():
            raise DistutilsError(
                "This library is not usable in 'develop' mode when using the "
                f'bundled {LIB_NAME}. See README for details.'
            )
        super().run()


class Distribution(_Distribution):
    def has_c_libraries(self):
        return not has_system_lib()


def main():
    if PKGCONFIG is None:
        raise DistutilsError('pkg-config is required')

    package_data = {'coincurve': ['py.typed']}

    extension = Extension(
        name='coincurve._libsecp256k1',
        sources=[os.path.join('coincurve', '_libsecp256k1.c')],
        # ABI?: py_limited_api=True,
    )

    setup_kwargs = dict(
        ext_modules=[extension],
        cmdclass={
            'develop': Develop,
            'egg_info': EggInfo,
            'sdist': Sdist,
            'bdist_wheel': BdistWheel,
        }
    )

    from setup.setup_build_extension import BuildCFFIForStaticLib

    # Cases to consider:
    # . Building for any OS, use system libsecp256k1
    # . Building for Windows Native, build secp256k1 locally
    # . Building for Windows with cross-compile, build secp256k1 locally
    # . Building for other OS, build secp256k1 locally

    # Building for any OS, use system libsecp256k1

    if has_system_lib():
        log.info('Using system library')

        setup_kwargs['cmdclass'] |= dict(
            build_ext=BuildCFFIForStaticLib,
        )
    else:
        from setup.setup_build_secp256k1_with_make import BuildClibWithMake

        log.info('Building SECP256K1 locally')

        setup_kwargs['cmdclass'] |= dict(
            build_clib=BuildClibWithMake,
            build_ext=BuildCFFIForStaticLib,
        )

        if BUILDING_FOR_WINDOWS:
            package_data['coincurve'].append('libsecp256k1.dll')

    setup(
        name='coincurve',
        version='19.0.0',
        requires=['asn1crypto', 'cffi(>=1.3.0)'],

        packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', LIB_NAME, 'tests')),
        package_data=package_data,
        include_package_data=True,

        distclass=Distribution,
        zip_safe=False,

        **setup_kwargs,
    )


if __name__ == '__main__':
    main()
