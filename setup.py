import errno
import logging
import os
import os.path
import pathlib
import platform
import shutil
import subprocess
import tarfile
from io import BytesIO
import sys

from setuptools import Distribution as _Distribution, setup, find_packages, __version__ as setuptools_version
from setuptools._distutils import log
from setuptools._distutils.errors import DistutilsError
from setuptools.command.build_clib import build_clib as _build_clib
from setuptools.command.build_ext import build_ext as _build_ext
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
from setup_support import absolute, build_flags, detect_dll, has_system_lib

BUILDING_FOR_WINDOWS = detect_dll()

MAKE = 'gmake' if platform.system() in ['FreeBSD', 'OpenBSD'] else 'make'

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_TAG') or '1ad5185cd42c0636104129fcc9f6a4bf9c67cc40'

LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'

LIB_NAME = 'libsecp256k1'
PKG_NAME = 'coincurve'

# Helpers for compilation instructions
# Cross-compile for Windows/ARM64, Linux/ARM64, Darwin/ARM64, Windows/x86 (GitHub)
X_HOST = os.getenv('COINCURVE_CROSS_HOST')

SYSTEM = platform.system()  # supported: Windows, Linux, Darwin
MACHINE = platform.machine()  # supported: AMD64, x86_64

_SECP256K1_BUILD_TYPE = 'STATIC'

# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.', 2)[:2]] < [3, 3]:
    raise SystemExit(
        f'Your setuptools version ({setuptools_version}) is too old to correctly install this package. Please upgrade '
        f'to a newer version (>= 3.3).'
    )


def download_library(command):
    if command.dry_run:
        return
    libdir = absolute('libsecp256k1')
    if os.path.exists(os.path.join(libdir, 'autogen.sh')):
        # Library already downloaded
        return
    if not os.path.exists(libdir):
        command.announce('downloading libsecp256k1 source code', level=log.INFO)
        try:
            import requests
            try:
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
                raise SystemExit('Unable to download secp256k1 library: %s', str(e))
        except ImportError as e:
            raise SystemExit('Unable to download secp256k1 library: %s', str(e))


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
            download_library(self)

        _dist_info.run(self)


class sdist(_sdist):
    def run(self):
        if not has_system_lib():
            download_library(self)
        _sdist.run(self)


if _bdist_wheel:

    class bdist_wheel(_bdist_wheel):
        def run(self):
            if not has_system_lib():
                download_library(self)
            _bdist_wheel.run(self)


else:
    bdist_wheel = None


class build_clib(_build_clib):
    def initialize_options(self):
        _build_clib.initialize_options(self)
        self.build_flags = None

    def finalize_options(self):
        _build_clib.finalize_options(self)
        if self.build_flags is None:
            self.build_flags = {'include_dirs': [], 'library_dirs': [], 'define': []}

    def get_source_files(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        return [
            absolute(os.path.join(root, filename))
            for root, _, filenames in os.walk(absolute('libsecp256k1'))
            for filename in filenames
        ]

    def build_libraries(self, libraries):
        raise Exception('build_libraries')

    def check_library_list(self, libraries):
        raise Exception('check_library_list')

    def get_library_names(self):
        return build_flags('libsecp256k1', 'l', os.path.abspath(self.build_temp))

    def run(self):
        if has_system_lib():
            log.info('Using system library')
            return

        build_temp = os.path.abspath(self.build_temp)

        try:
            os.makedirs(build_temp)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        if not os.path.exists(absolute('libsecp256k1')):
            # library needs to be downloaded
            self.get_source_files()

        if not os.path.exists(absolute('libsecp256k1/configure')):
            # configure script hasn't been generated yet
            autogen = absolute('libsecp256k1/autogen.sh')
            os.chmod(absolute(autogen), 0o700)
            subprocess.check_call([autogen], cwd=absolute('libsecp256k1'))  # noqa S603

        for filename in [
            'libsecp256k1/configure',
            'libsecp256k1/build-aux/compile',
            'libsecp256k1/build-aux/config.guess',
            'libsecp256k1/build-aux/config.sub',
            'libsecp256k1/build-aux/depcomp',
            'libsecp256k1/build-aux/install-sh',
            'libsecp256k1/build-aux/missing',
            'libsecp256k1/build-aux/test-driver',
        ]:
            try:
                os.chmod(absolute(filename), 0o700)
            except OSError as e:
                # some of these files might not exist depending on autoconf version
                if e.errno != errno.ENOENT:
                    # If the error isn't 'No such file or directory' something
                    # else is wrong and we want to know about it
                    raise

        cmd = [
            absolute('libsecp256k1/configure'),
            '--disable-shared',
            '--enable-static',
            '--disable-dependency-tracking',
            '--with-pic',
            '--enable-module-extrakeys',
            '--enable-module-recovery',
            '--enable-module-schnorrsig',
            '--prefix',
            os.path.abspath(self.build_clib),
            '--enable-experimental',
            '--enable-module-ecdh',
            '--enable-benchmark=no',
            '--enable-tests=no',
            '--enable-exhaustive-tests=no',
        ]
        if 'COINCURVE_CROSS_HOST' in os.environ:
            cmd.append(f"--host={os.environ['COINCURVE_CROSS_HOST']}")

        log.debug(f"Running configure: {' '.join(cmd)}")
        subprocess.check_call(cmd, cwd=build_temp)  # noqa S603

        subprocess.check_call([MAKE], cwd=build_temp)  # noqa S603
        subprocess.check_call([MAKE, 'check'], cwd=build_temp)  # noqa S603
        subprocess.check_call([MAKE, 'install'], cwd=build_temp)  # noqa S603

        self.build_flags['include_dirs'].extend(build_flags('libsecp256k1', 'I', build_temp))
        self.build_flags['library_dirs'].extend(build_flags('libsecp256k1', 'L', build_temp))
        if not has_system_lib():
            self.build_flags['define'].append(('CFFI_ENABLE_RECOVERY', None))


class _BuildClib(_build_clib):
    title = 'SECP256K1 C library build'

    def __init__(self, dist):
        super().__init__(dist)
        self.pkgconfig_dir = None

        self._cwd = None
        self._lib_src = None
        self._install_dir = None
        self._install_lib_dir = None

    def get_source_files(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        # This seems to create issues in MANIFEST.in
        return [f for _, _, fs in os.walk(absolute(LIB_NAME)) for f in fs]

    def run(self):
        if has_system_lib():
            logging.info('Using system library')
            return

        logging.info(self.title)
        self.bc_set_dirs_download()
        self.bc_prepare_build(self._install_lib_dir, self.build_temp, self._lib_src)

        try:
            os.chdir(self.build_temp)
            self.bc_build_in_temp(self._install_lib_dir, self._lib_src)
            # TODO: await PR approval
            # execute_command_with_temp_log(self.bc_build_command(), debug=True)
        finally:
            os.chdir(self._cwd)

        # Register lib installation path
        self.bc_update_pkg_config_path()

    def bc_set_dirs_download(self):
        self._cwd = pathlib.Path().cwd()
        os.makedirs(self.build_temp, exist_ok=True)
        self._install_dir = str(self.build_temp).replace('temp', 'lib')

        if _SECP256K1_BUILD_TYPE == 'SHARED':
            # Install shared library in the package directory
            self._install_lib_dir = os.path.join(self._install_dir, PKG_NAME)
        else:
            # Install static library in its own directory for retrieval by build_ext
            self._install_lib_dir = os.path.join(self._install_dir, LIB_NAME)

        self._lib_src = os.path.join(self._cwd, LIB_NAME)
        if not os.path.exists(self._lib_src):
            self.get_source_files()

    def bc_update_pkg_config_path(self):
        self.pkgconfig_dir = [
            os.path.join(self._install_lib_dir, 'lib', 'pkgconfig'),
            os.path.join(self._install_lib_dir, 'lib64', 'pkgconfig'),
        ]
        os.environ['PKG_CONFIG_PATH'] = (
            f'{str(os.pathsep).join(self.pkgconfig_dir)}'
            f'{os.pathsep}'
            f'{os.environ.get("PKG_CONFIG_PATH", "")}'
        ).replace('\\', '/')

        # Verify installation
        # TODO: await PR approval
        # execute_command_with_temp_log([PKGCONFIG, '--exists', LIB_NAME])

    @staticmethod
    def bc_prepare_build(install_lib_dir, build_temp, lib_src):
        raise NotImplementedError('This method should be implemented in a Mixin class')

    @staticmethod
    def bc_build_in_temp(install_lib_dir, lib_src):
        pass

    @staticmethod
    def bc_build_command():
        raise NotImplementedError('This method should be implemented in a Mixin class')


class BuildClibWithCMake(_BuildClib):
    @staticmethod
    def _generator(msvc):
        if '2017' in str(msvc):
            return 'Visual Studio 15 2017'
        if '2019' in str(msvc):
            return 'Visual Studio 16 2019'
        if '2022' in str(msvc):
            return 'Visual Studio 17 2022'

    @staticmethod
    def bc_prepare_build(install_lib_dir, build_temp, lib_src):
        cmake_args = [
            '-DCMAKE_BUILD_TYPE=Release',
            f'-DCMAKE_INSTALL_PREFIX={install_lib_dir}',
            f'-DCMAKE_C_FLAGS={"-fPIC" if _SECP256K1_BUILD_TYPE != "SHARED" and SYSTEM != "Windows" else ""}',
            f'-DSECP256K1_DISABLE_SHARED={"OFF" if _SECP256K1_BUILD_TYPE == "SHARED" else "ON"}',
            '-DSECP256K1_BUILD_BENCHMARK=OFF',
            '-DSECP256K1_BUILD_TESTS=ON',
            '-DSECP256K1_ENABLE_MODULE_ECDH=ON',
            '-DSECP256K1_ENABLE_MODULE_RECOVERY=ON',
            '-DSECP256K1_ENABLE_MODULE_SCHNORRSIG=ON',
            '-DSECP256K1_ENABLE_MODULE_EXTRAKEYS=ON',
        ]

        # Windows (more complex)
        if SYSTEM == 'Windows':
            # TODO: await PR approval
            # vswhere = shutil.which('vswhere')
            # msvc = execute_command_with_temp_log(
            #     [vswhere, '-latest', '-find', 'MSBuild\\**\\Bin\\MSBuild.exe'],
            #     capture_output=True,
            # )
            msvc = None

            # For windows x86/x64, select the correct architecture
            arch = 'x64' if MACHINE == 'AMD64' else 'Win32'  # Native

            if X_HOST is not None:
                logging.info(f'Cross-compiling on {SYSTEM}:{MACHINE} for {X_HOST}')
                if X_HOST in ['arm64', 'ARM64', 'x86']:
                    arch = 'Win32' if X_HOST in ['x86'] else 'arm64'
                else:
                    raise NotImplementedError(f'Unsupported architecture: {X_HOST}')

            # Place the DLL directly in the package directory
            cmake_args.append('-DCMAKE_INSTALL_BINDIR=.')
            cmake_args.extend(['-G', BuildClibWithCMake._generator(msvc), f'-A{arch}'])

        elif SYSTEM == 'Darwin':
            if X_HOST is None:
                cmake_args.append(
                    f'-DCMAKE_OSX_ARCHITECTURES={MACHINE}'  # Native
                )
            else:
                logging.info(f'Cross-compiling on {SYSTEM}:{MACHINE} for {X_HOST}')
                if X_HOST in ['armv7', 'armv7s', 'arm64', 'arm64e']:
                    cmake_args.append(
                        f'-DCMAKE_OSX_ARCHITECTURES={X_HOST}'
                    )
        else:
            if X_HOST is not None:
                if X_HOST not in [
                    'arm-linux-gnueabihf',
                    'x86_64-w64-mingw32',
                ]:
                    raise NotImplementedError(f'Unsupported architecture: {X_HOST}')

                logging.info(f'Cross-compiling on {SYSTEM}:{MACHINE} for {X_HOST}')
                cmake_args.append(
                    f'-DCMAKE_TOOLCHAIN_FILE=../cmake/{X_HOST}.toolchain.cmake'
                )

        logging.info('    Configure CMake')
        # TODO: await PR approval
        # execute_command_with_temp_log(['cmake', '-S', lib_src, '-B', build_temp, *cmake_args])

    @staticmethod
    def bc_build_command():
        logging.info('    Install with CMake')
        return ['cmake', '--build', '.', '--target', 'install', '--config', 'Release', '--clean-first']


class build_ext(_build_ext):
    def run(self):
        if self.distribution.has_c_libraries():
            _build_clib = self.get_finalized_command('build_clib')
            self.include_dirs.append(os.path.join(_build_clib.build_clib, 'include'))
            self.include_dirs.extend(_build_clib.build_flags['include_dirs'])

            self.library_dirs.insert(0, os.path.join(_build_clib.build_clib, 'lib'))
            self.library_dirs.extend(_build_clib.build_flags['library_dirs'])

            self.define = _build_clib.build_flags['define']

        return _build_ext.run(self)


class develop(_develop):
    def run(self):
        if not has_system_lib():
            raise DistutilsError(
                "This library is not usable in 'develop' mode when using the "
                'bundled libsecp256k1. See README for details.'
            )
        _develop.run(self)


package_data = {'coincurve': ['py.typed']}


class BuildCFFIForSharedLib(_build_ext):
    def build_extensions(self):
        build_script = os.path.join('_cffi_build', 'build_shared.py')
        c_file = self.extensions[0].sources[0]
        subprocess.run([sys.executable, build_script, c_file, '0'], shell=False, check=True)  # noqa S603
        super().build_extensions()


if has_system_lib():

    class Distribution(_Distribution):
        def has_c_libraries(self):
            return not has_system_lib()

    # --- SECP256K1 package definitions ---
    secp256k1_package = 'libsecp256k1'

    extension = Extension(
        name='coincurve._libsecp256k1',
        sources=[os.path.join('coincurve', '_libsecp256k1.c')],
        # ABI?: py_limited_api=True,
    )

    extension.extra_compile_args = [
        subprocess.check_output(['pkg-config', '--cflags-only-I', 'libsecp256k1']).strip().decode('utf-8')  # noqa S603
    ]
    extension.extra_link_args = [
        subprocess.check_output(['pkg-config', '--libs-only-L', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
        subprocess.check_output(['pkg-config', '--libs-only-l', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
    ]

    if os.name == 'nt' or sys.platform == 'win32':
        # Apparently, the linker on Windows interprets -lxxx as xxx.lib, not libxxx.lib
        for i, v in enumerate(extension.__dict__.get('extra_link_args')):
            extension.__dict__['extra_link_args'][i] = v.replace('-L', '/LIBPATH:')

            if v.startswith('-l'):
                v = v.replace('-l', 'lib')
                extension.__dict__['extra_link_args'][i] = f'{v}.lib'

    setup_kwargs = dict(
        setup_requires=['cffi>=1.3.0', 'requests'],
        ext_modules=[extension],
        cmdclass={
            'build_clib': build_clib,
            'build_ext': BuildCFFIForSharedLib,
            'develop': develop,
            'egg_info': egg_info,
            'sdist': sdist,
            'bdist_wheel': bdist_wheel,
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
            ext_package='coincurve',
            cffi_modules=['_cffi_build/build.py:ffi'],
            cmdclass={
                'build_clib': build_clib,
                'build_ext': build_ext,
                'develop': develop,
                'egg_info': egg_info,
                'sdist': sdist,
                'bdist_wheel': bdist_wheel,
            },
        )

setup(
    name='coincurve',
    version='19.0.0',

    packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', 'libsecp256k1', 'tests')),
    package_data=package_data,

    distclass=Distribution,
    zip_safe=False,
    **setup_kwargs
)
