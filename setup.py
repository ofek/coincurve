import logging
import os.path
import platform
import sys
from os.path import join
from sys import path as PATH

from setuptools import Distribution as _Distribution, setup
from setuptools.extension import Extension

# Define the package root directory and add it to the system path
COINCURVE_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
PATH.append(COINCURVE_ROOT_DIR)

# Add setuptools local package path
PATH.insert(0, join(COINCURVE_ROOT_DIR, 'setup_tools'))

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from setup_tools.support import has_system_lib  # noqa: E402

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_REF') or '1ad5185cd42c0636104129fcc9f6a4bf9c67cc40'

LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'

LIB_NAME = 'libsecp256k1'
PKG_NAME = 'coincurve'

# Helpers for compilation instructions
# Cross-compile for Windows/ARM64, Linux/ARM64, Darwin/ARM64, Windows/x86 (GitHub)
X_HOST = os.getenv('COINCURVE_CROSS_HOST')

SYSTEM = platform.system()  # supported: Windows, Linux, Darwin
MACHINE = platform.machine()  # supported: AMD64, x86_64

logging.info(f'Building for {SYSTEM}:{MACHINE} with {X_HOST = }')
SECP256K1_BUILD = os.getenv('COINCURVE_SECP256K1_BUILD') or 'STATIC'
SECP256K1_IGNORE_EXT_LIB = os.getenv('COINCURVE_IGNORE_SYSTEM_LIB')


class Distribution(_Distribution):
    def has_c_libraries(self):
        return not has_system_lib()


def main():
    from setup_tools.commands import BdistWheel, EggInfo, Sdist, Develop
    from setup_tools.build_clib import BuildClibWithCMake
    from setup_tools.build_ext import BuildExtensionFromCFFI

    extension = Extension(
        name='coincurve._libsecp256k1',
        sources=['_c_file_for_extension.c'],
        py_limited_api=False,
        extra_compile_args=['/d2FH4-'] if SYSTEM == 'Windows' else [],
    )

    setup_kwargs = dict(
        ext_modules=[extension],
        cmdclass={
            'build_clib': None if has_system_lib() else BuildClibWithCMake,
            'build_ext': BuildExtensionFromCFFI,
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
