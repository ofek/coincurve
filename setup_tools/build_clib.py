import logging
import os
import shutil
import subprocess

from setuptools.command import build_clib

from setup import LIB_NAME, MACHINE, SECP256K1_BUILD, SYSTEM, X_HOST
from setup_tools.support import (
    absolute,
    call_pkg_config,
    define_secp256k1_local_lib_info,
    download_library,
    has_system_lib,
)


class BuildClibWithCMake(build_clib.build_clib):
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
            subprocess.check_call(self.bc_build_command())  # noqa S603
        finally:
            os.chdir(self._cwd)

        # Register lib installation path
        self.bc_update_pkg_config_path()

    def bc_set_dirs_download(self):
        self._cwd = os.getcwd()
        os.makedirs(self.build_temp, exist_ok=True)
        self._install_dir = self.build_temp.replace('temp', 'lib')

        # Install path
        #  SHARED: lib/coincurve       -> path/lib.xxx/coincurve/path      # included in coincurve wheel
        #  STATIC: x_lib/libsecp256k1  -> path/x_lib.xxx/libsecp256k1/path # NOT included in coincurve wheel
        lib, inst_dir = define_secp256k1_local_lib_info()
        self._install_lib_dir = os.path.join(self._install_dir.replace('lib', inst_dir), lib)

        self._lib_src = os.path.join(self._cwd, LIB_NAME)
        if not os.path.exists(self._lib_src):
            self.get_source_files()

    def bc_update_pkg_config_path(self):
        self.pkgconfig_dir = [os.path.join(self._install_lib_dir, n, 'pkgconfig') for n in ['lib', 'lib64']]
        self.pkgconfig_dir.append(os.getenv('PKG_CONFIG_PATH', ''))
        os.environ['PKG_CONFIG_PATH'] = os.pathsep.join(self.pkgconfig_dir)
        call_pkg_config(['--exists'], LIB_NAME)

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
            f'-DCMAKE_C_FLAGS={"-fPIC" if SECP256K1_BUILD != "SHARED" and SYSTEM != "Windows" else ""}',
            f'-DSECP256K1_DISABLE_SHARED={"OFF" if SECP256K1_BUILD == "SHARED" else "ON"}',
            '-DSECP256K1_BUILD_BENCHMARK=OFF',
            '-DSECP256K1_BUILD_TESTS=OFF',
            '-DSECP256K1_BUILD_CTIME_TESTS=OFF',
            '-DSECP256K1_BUILD_EXHAUSTIVE_TESTS=OFF',
            '-DSECP256K1_BUILD_EXAMPLES=OFF',
            '-DSECP256K1_ENABLE_MODULE_ECDH=ON',
            '-DSECP256K1_ENABLE_MODULE_RECOVERY=ON',
            '-DSECP256K1_ENABLE_MODULE_SCHNORRSIG=ON',
            '-DSECP256K1_ENABLE_MODULE_EXTRAKEYS=ON',
        ]

        # Windows (more complex)
        if SYSTEM == 'Windows':
            vswhere = shutil.which('vswhere')
            cmd = [vswhere, '-latest', '-find', 'MSBuild\\**\\Bin\\MSBuild.exe']
            msvc = subprocess.check_output(cmd).strip().decode('utf-8')  # noqa S603

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
                cmake_args.append(f'-DCMAKE_OSX_ARCHITECTURES={MACHINE}')  # Native
            else:
                logging.info(f'Cross-compiling on {SYSTEM}:{MACHINE} for {X_HOST}')
                if X_HOST in ['armv7', 'armv7s', 'arm64', 'arm64e']:
                    cmake_args.append(f'-DCMAKE_OSX_ARCHITECTURES={X_HOST}')
        elif X_HOST is not None:
            if X_HOST not in [
                'arm-linux-gnueabihf',
                'x86_64-w64-mingw32',
            ]:
                raise NotImplementedError(f'Unsupported architecture: {X_HOST}')

            logging.info(f'Cross-compiling on {SYSTEM}:{MACHINE} for {X_HOST}')
            cmake_args.append(f'-DCMAKE_TOOLCHAIN_FILE=../cmake/{X_HOST}.toolchain.cmake')

        logging.info('    Configure CMake')
        subprocess.check_call(['cmake', '-S', lib_src, '-B', build_temp, *cmake_args])  # noqa S603

    @staticmethod
    def bc_build_command():
        logging.info('    Install with CMake')
        return ['cmake', '--build', '.', '--target', 'install', '--config', 'Release', '--clean-first']
