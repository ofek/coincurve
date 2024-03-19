import os
import os.path
import platform
import sys
from os.path import join
from sys import path as PATH

from setuptools import Distribution as _Distribution, setup, __version__ as setuptools_version
from setuptools.extension import Extension

# Define the package root directory and add it to the system path
COINCURVE_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
PATH.append(COINCURVE_ROOT_DIR)

# Add setuptools local package path
PATH.insert(0, join(COINCURVE_ROOT_DIR, 'setup_tools'))

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from setup_tools.support import detect_dll, has_system_lib  # noqa: E402

BUILDING_FOR_WINDOWS = detect_dll(COINCURVE_ROOT_DIR)

MAKE = 'gmake' if platform.system() in ['FreeBSD', 'OpenBSD'] else 'make'

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_REF') or '1ad5185cd42c0636104129fcc9f6a4bf9c67cc40'

LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'

globals_ = {}
with open(join(COINCURVE_ROOT_DIR, 'src', 'coincurve', '_version.py')) as fp:
    exec(fp.read(), globals_)  # noqa S102
    __version__ = globals_['__version__']

# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.', 2)[:2]] < [3, 3]:
    raise SystemExit(
        f'Your setuptools version ({setuptools_version}) is too old to correctly install this package. Please upgrade '
        f'to a newer version (>= 3.3).'
    )

package_data = {'coincurve': ['py.typed']}


def main():
    from setup_tools.commands import BdistWheel, EggInfo, Sdist, Develop
    from setup_tools.build_clib import BuildClib
    from setup_tools.build_ext import BuildCFFIForSharedLib, BuildExt
    from setup_tools.support import call_pkg_config

    if has_system_lib():

        class Distribution(_Distribution):
            def has_c_libraries(self):
                return not has_system_lib()

        extension = Extension(
            name='coincurve._libsecp256k1',
            sources=[os.path.join('src/coincurve', '_libsecp256k1.c')],
            # ABI?: py_limited_api=True,
        )

        extension.extra_compile_args = [call_pkg_config(['--cflags-only-I'], 'libsecp256k1')]
        extension.extra_link_args = [
            call_pkg_config(['--libs-only-L'], 'libsecp256k1'),
            call_pkg_config(['--libs-only-l'], 'libsecp256k1'),
        ]

        if os.name == 'nt' or sys.platform == 'win32':
            # Apparently, the linker on Windows interprets -lxxx as xxx.lib, not libxxx.lib
            for i, v in enumerate(extension.__dict__.get('extra_link_args')):
                extension.__dict__['extra_link_args'][i] = v.replace('-L', '/LIBPATH:')

                if v.startswith('-l'):
                    v = v.replace('-l', 'lib')
                    extension.__dict__['extra_link_args'][i] = f'{v}.lib'

        setup_kwargs = dict(
            ext_modules=[extension],
            cmdclass={
                'build_clib': BuildClib,
                'build_ext': BuildCFFIForSharedLib,
                'develop': Develop,
                'egg_info': EggInfo,
                'sdist': Sdist,
                'bdist_wheel': BdistWheel,
            },
        )

    else:
        if BUILDING_FOR_WINDOWS:

            class Distribution(_Distribution):
                def is_pure(self):
                    return False

            package_data['coincurve'].append('libsecp256k1.dll')
            setup_kwargs = {}

        else:

            class Distribution(_Distribution):
                def has_c_libraries(self):
                    return not has_system_lib()

            setup_kwargs = dict(
                ext_package='coincurve',
                cffi_modules=['_cffi_build/build.py:ffi'],
                cmdclass={
                    'build_clib': BuildClib,
                    'build_ext': BuildExt,
                    'develop': Develop,
                    'egg_info': EggInfo,
                    'sdist': Sdist,
                    'bdist_wheel': BdistWheel,
                },
            )

    setup(
        distclass=Distribution,
        zip_safe=False,
        **setup_kwargs
    )


if __name__ == '__main__':
    main()
