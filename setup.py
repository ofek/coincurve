import logging
import os
import os.path
import pathlib
import platform
import shutil
import sys
import sysconfig

from setuptools import Distribution as _Distribution, setup, find_packages
from setuptools.command import build_clib, build_ext, develop, dist_info, egg_info, sdist
from setuptools.extension import Extension

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None

PACKAGE_SETUP_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(PACKAGE_SETUP_DIR)
from setup_support import absolute_from_setup_dir, build_flags, detect_dll, download_library, has_system_lib, \
    execute_command_with_temp_log  # noqa: E402

BUILDING_FOR_WINDOWS = detect_dll()

MAKE = 'gmake' if platform.system() in ['FreeBSD', 'OpenBSD'] else 'make'
PKGCONFIG = shutil.which('pkg-config')

logging.info(sysconfig.get_config_var('CC'))
logging.info(sysconfig.get_config_var('CFLAGS'))

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_TAG') or '1ad5185cd42c0636104129fcc9f6a4bf9c67cc40'
UPSTREAM_HSH = os.getenv('COINCURVE_UPSTREAM_HSH') or 'ba34be4319f505c5766aa80b99cfa696cbb2993bfecf7d7eb8696106c493cb8c'

LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'
LIB_TARBALL_HASH = f'{UPSTREAM_HSH}'


class EggInfo(egg_info.egg_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        super().run()


class DistInfo(dist_info.dist_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        super().run()


class Sdist(sdist.sdist):
    def run(self):
        if not has_system_lib():
            download_library(self)
        super().run()


class Develop(develop.develop):
    def run(self):
        if not has_system_lib():
            raise RuntimeError(
                "This library is not usable in 'develop' mode when using the "
                'bundled libsecp256k1. See README for details.'
            )
        super().run()


if _bdist_wheel:
    class BdistWheel(_bdist_wheel):
        def run(self):
            if not has_system_lib():
                download_library(self)
            super().run()


class BuildClibWithCmake(build_clib.build_clib):
    def __init__(self, dist):
        super().__init__(dist)
        self.pkgconfig_dir = None

    def get_source_files(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        # This seems to create issues in MANIFEST.in
        return [f for _, _, fs in os.walk(absolute_from_setup_dir('libsecp256k1')) for f in fs]

    def run(self):
        if has_system_lib():
            logging.info('Using system library')
            return

        logging.info('SECP256K1 C library build (CMake):')

        cwd = pathlib.Path().cwd()
        build_temp = os.path.abspath(self.build_temp)
        os.makedirs(build_temp, exist_ok=True)

        lib_src = os.path.join(cwd, 'libsecp256k1')

        install_dir = str(build_temp).replace('temp', 'lib')
        install_dir = os.path.join(install_dir, 'coincurve')

        if not os.path.exists(lib_src):
            # library needs to be downloaded
            self.get_source_files()

        cmake_args = [
            '-DCMAKE_BUILD_TYPE=Release',
            f'-DCMAKE_INSTALL_PREFIX={install_dir}',
            '-DBUILD_SHARED_LIBS=ON',
            '-DSECP256K1_BUILD_BENCHMARKS=OFF',
            '-DSECP256K1_BUILD_TESTS=ON',
            '-DSECP256K1_ENABLE_MODULE_ECDH=ON',
            '-DSECP256K1_ENABLE_MODULE_RECOVERY=ON',
            '-DSECP256K1_ENABLE_MODULE_SCHNORRSIG=ON',
            '-DSECP256K1_ENABLE_MODULE_EXTRAKEYS=ON',
        ]

        if (x_host := os.environ.get('COINCURVE_CROSS_HOST')) is not None:
            logging.info(f'Cross-compiling for {x_host}:{os.name}')
            if platform.system() == 'Darwin' or platform.machine() == 'arm64':
                # Let's try to not cross-compile on MacOS
                cmake_args.append(
                    '-DCMAKE_OSX_ARCHITECTURES=arm64'
                )
            else:
                # Note, only 2 toolchain files are provided (2/1/24)
                cmake_args.append(
                    f'-DCMAKE_TOOLCHAIN_FILE=../cmake/{x_host}.toolchain.cmake'
                )

        elif os.name == 'nt':
            # For windows, select the correct toolchain file
            cmake_args.append(
                '-G "Visual Studio 16 2019" -A x64'
            )

        logging.info('    cmake config')
        execute_command_with_temp_log(['cmake', '-S', lib_src, '-B', build_temp, *cmake_args])

        try:
            os.chdir(build_temp)
            logging.info('    cmake build')
            execute_command_with_temp_log(['cmake', '--build', '.'])

            logging.info('    cmake install')
            execute_command_with_temp_log(['cmake', '--install', '.'], debug=True)
        finally:
            os.chdir(cwd)

        self.pkgconfig_dir = [
            os.path.join(install_dir, 'lib', 'pkgconfig'),
            os.path.join(install_dir, 'lib64', 'pkgconfig'),
        ]
        os.environ['PKG_CONFIG_PATH'] = f'{":".join(self.pkgconfig_dir)}:{os.environ.get("PKG_CONFIG_PATH", "")}'

        logging.info('build_clib: Done')


class BuildClib(build_clib.build_clib):
    def __init__(self, dist):
        super().__init__(dist)
        self.pkgconfig_dir = None

    def get_source_files(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        # This seems to create issues in MANIFEST.in
        return [f for _, _, fs in os.walk(absolute_from_setup_dir('libsecp256k1')) for f in fs]

    def run(self):
        if has_system_lib():
            logging.info('Using system library')
            return

        logging.info('SECP256K1 C library build (make):')

        cwd = pathlib.Path().cwd()
        build_temp = os.path.abspath(self.build_temp)
        os.makedirs(build_temp, exist_ok=True)

        lib_src = os.path.join(cwd, 'libsecp256k1')

        install_dir = str(build_temp).replace('temp', 'lib')
        install_dir = os.path.join(install_dir, 'coincurve')

        if not os.path.exists(lib_src):
            # library needs to be downloaded
            self.get_source_files()

        autoreconf = 'autoreconf -if --warnings=all'
        bash = shutil.which('bash')

        logging.info('    autoreconf')
        execute_command_with_temp_log([bash, '-c', autoreconf], cwd=lib_src)

        # Keep downloaded source dir pristine (hopefully)
        try:
            os.chdir(build_temp)
            cmd = [
                absolute_from_setup_dir('libsecp256k1/configure'),
                '--prefix',
                install_dir.replace('\\', '/'),
                '--disable-static',
                '--disable-dependency-tracking',
                '--with-pic',
                '--enable-module-extrakeys',
                '--enable-module-recovery',
                '--enable-module-schnorrsig',
                '--enable-experimental',
                '--enable-module-ecdh',
                '--enable-benchmark=no',
                '--enable-tests=no',
                '--enable-exhaustive-tests=no',
            ]

            if 'COINCURVE_CROSS_HOST' in os.environ:
                cmd.append(f"--host={os.environ['COINCURVE_CROSS_HOST']}")

            logging.info('    configure')
            execute_command_with_temp_log([bash, '-c', ' '.join(cmd)])

            logging.info('    make')
            execute_command_with_temp_log([MAKE])

            logging.info('    make check')
            execute_command_with_temp_log([MAKE, 'check'])

            logging.info('    make install')
            execute_command_with_temp_log([MAKE, 'install'])
        finally:
            os.chdir(cwd)

        self.pkgconfig_dir = os.path.join(install_dir, 'lib', 'pkgconfig')

        logging.info('build_clib: Done')


class _BuildExtensionFromCFFI(build_ext.build_ext):
    static_lib = None

    def update_link_args(self, libraries, libraries_dirs, extra_link_args):
        raise NotImplementedError('update_link_args')

    def build_extension(self, ext):
        logging.info(
            f'Extension build:'
            f'\n         OS:{os.name}'
            f'\n   Platform:{sys.platform}'
            f'\n   Compiler:{self.compiler.__class__.__name__}'
            f'\n     Static:{self.static_lib}'
        )

        # Enforce API interface
        ext.py_limited_api = False

        # PKG_CONFIG_PATH is updated by build_clib if built locally
        ext.include_dirs.extend(build_flags('libsecp256k1', 'I'))
        ext.library_dirs.extend(build_flags('libsecp256k1', 'L'))

        libraries = build_flags('libsecp256k1', 'l')
        logging.info(f'  Libraries:{libraries}')

        # We do not set ext.libraries, this would add the default link instruction
        # Instead, we use extra_link_args to customize the link command
        self.update_link_args(libraries, ext.library_dirs, ext.extra_link_args)

        super().build_extension(ext)


class _BuildCFFI(_BuildExtensionFromCFFI):
    def build_extension(self, ext):
        logging.info(
            f'Cmdline CFFI build:'
            f'\n     Source: {absolute_from_setup_dir(ext.sources[0])}'
        )

        build_script = os.path.join('_cffi_build', 'build.py')
        for c_file in ext.sources:
            cmd = [sys.executable, build_script, c_file, '1' if self.static_lib else '0']
            execute_command_with_temp_log(cmd)

        super().build_extension(ext)


class BuildCFFIForSharedLib(_BuildCFFI):
    static_lib = False

    def update_link_args(self, libraries, libraries_dirs, extra_link_args):
        if self.compiler.__class__.__name__ == 'UnixCCompiler':
            extra_link_args.extend([f'-l{lib}' for lib in libraries])
            if sys.platform == 'darwin':
                # It seems that the syntax may be: -Wl,-rpath,@loader_path/lib
                extra_link_args.extend([
                    # f'-Wl,-rpath,{self.build_lib}/lib',
                    '-Wl,-rpath,@loader_path/lib',
                ])
            else:
                extra_link_args.extend([
                    '-Wl,-rpath,$ORIGIN/lib',
                    '-Wl,-rpath,$ORIGIN/lib64',
                ])
        elif self.compiler.__class__.__name__ == 'MSVCCompiler':
            # This section is not used yet since we still cross-compile on Windows
            # TODO: write the windows native build here when finalized
            raise NotImplementedError(f'Unsupported compiler: {self.compiler.__class__.__name__}')
        else:
            raise NotImplementedError(f'Unsupported compiler: {self.compiler.__class__.__name__}')


class BuildCFFIForStaticLib(_BuildCFFI):
    static_lib = True

    def update_link_args(self, libraries, libraries_dirs, extra_link_args):
        if self.compiler.__class__.__name__ == 'UnixCCompiler':
            # It is possible that the library was compiled without fPIC option
            for lib in libraries:
                # On MacOS the mix static/dynamic option is different
                # It requires a -force_load <full_lib_path> option for each library
                if sys.platform == 'darwin':
                    for lib_dir in libraries_dirs:
                        if os.path.exists(os.path.join(lib_dir, f'lib{lib}.a')):
                            extra_link_args.extend(
                                ['-Wl,-force_load', os.path.join(lib_dir, f'lib{lib}.a')]
                            )
                            break
                else:
                    extra_link_args.extend(['-Wl,-Bstatic', f'-l{lib}', '-Wl,-Bdynamic'])

        elif self.compiler.__class__.__name__ == 'MSVCCompiler':
            # This section is not used yet since we still cross-compile on Windows
            # TODO: write the windows native build here when finalized
            raise NotImplementedError(f'Unsupported compiler: {self.compiler.__class__.__name__}')
        else:
            raise NotImplementedError(f'Unsupported compiler: {self.compiler.__class__.__name__}')


package_data = {'coincurve': ['py.typed']}

extension = Extension(
    name='coincurve._libsecp256k1',
    sources=[os.path.join('coincurve', '_libsecp256k1.c')],
    py_limited_api=False,
)

if has_system_lib():

    class Distribution(_Distribution):
        def has_c_libraries(self):
            return not has_system_lib()


    # TODO: This has not been tested yet. has_system_lib() does not find conda install lib yet
    setup_kwargs = dict(
        setup_requires=['cffi>=1.3.0', 'requests'],
        ext_modules=[extension],
        cmdclass={
            'build_clib': BuildClib,
            'build_ext': BuildCFFIForSharedLib,
            'develop': Develop,
            'egg_info': EggInfo,
            'sdist': Sdist,
            'bdist_wheel': BdistWheel if _bdist_wheel else None,
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
            setup_requires=['cffi>=1.3.0', 'requests'],
            ext_modules=[extension],
            cmdclass={
                'build_clib': BuildClibWithCmake,
                'build_ext': BuildCFFIForSharedLib,
                'develop': Develop,
                'egg_info': EggInfo,
                'sdist': Sdist,
                'bdist_wheel': BdistWheel if _bdist_wheel else None,
            },
        )


def main():
    setup(
        name='coincurve',
        version='19.0.0',

        packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', 'libsecp256k1', 'tests')),
        package_data=package_data,

        distclass=Distribution,
        zip_safe=False,
        **setup_kwargs
    )


if __name__ == '__main__':
    main()
