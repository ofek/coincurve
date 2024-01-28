import errno
import logging
import os
import pathlib
import shutil
import subprocess

from setuptools._distutils import log
from setuptools.command.build_clib import build_clib as _build_clib

from setup.setup_support import absolute, download_library, has_system_lib


class BuildClibWithMake(_build_clib):
    def __init__(self, dist):
        super().__init__(dist)
        self.build_flags = None
        self.pkgconfig_dir = None

    def initialize_options(self: _build_clib):
        _build_clib.initialize_options(self)
        self.build_flags = None

    def finalize_options(self: _build_clib):
        _build_clib.finalize_options(self)
        if self.build_flags is None:
            self.build_flags = {
                'define': [],
            }

    def get_source_files(self):
        from setup.setup_config import LIB_NAME

        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        return [f for root, _, fns in os.walk(absolute(LIB_NAME)) for f in fns]

    def build_libraries(self, libraries):
        raise NotImplementedError('build_libraries')

    def check_library_list(self, libraries):
        raise NotImplementedError('check_library_list')

    def get_library_names(self):
        return None

    def run(self):
        from setup.setup_config import LIB_NAME, MAKE, COMPILER, EXTRA_COMPILE_ARGS

        cwd = pathlib.Path().absolute()

        log.info(f'{LIB_NAME} C library build:')
        log.info(f'   - compiler: {COMPILER}')
        log.info(f'   - extra compile args: {EXTRA_COMPILE_ARGS}')

        if has_system_lib():
            log.info('Using system library')
            return

        build_external_library = os.path.join(cwd, 'build_external_library')
        built_lib_dir = os.path.join(build_external_library, LIB_NAME)
        installed_lib_dir = os.path.abspath(self.build_clib)

        try:
            os.makedirs(build_external_library)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        download_library(self, libdir=built_lib_dir)

        autoreconf = 'autoreconf -if --warnings=all'
        bash = shutil.which('bash')

        self.announce('   autoreconf', level=log.INFO)
        args = [bash, '-c', autoreconf]
        with open('_build_clib_autoreconf.log', 'w') as outfile:
            subprocess.check_call(args, cwd=built_lib_dir, stdout=outfile, stderr=outfile)  # noqa S603

        for filename in [
            os.path.join(built_lib_dir, 'configure'),
            os.path.join(built_lib_dir, 'build-aux', 'compile'),
            os.path.join(built_lib_dir, 'build-aux', 'config.guess'),
            os.path.join(built_lib_dir, 'build-aux', 'config.sub'),
            os.path.join(built_lib_dir, 'build-aux', 'depcomp'),
            os.path.join(built_lib_dir, 'build-aux', 'install-sh'),
            os.path.join(built_lib_dir, 'build-aux', 'missing'),
            os.path.join(built_lib_dir, 'build-aux', 'test-driver'),
        ]:
            try:
                os.chmod(filename, 0o700)
            except OSError as e:
                # some of these files might not exist depending on autoconf version
                if e.errno != errno.ENOENT:
                    # If the error isn't 'No such file or directory' something
                    # else is wrong, and we want to know about it
                    raise

        cmd = [
            'configure',
            '--disable-shared',
            '--enable-static',
            '--disable-dependency-tracking',
            '--with-pic',
            '--enable-module-extrakeys',
            '--enable-module-recovery',
            '--enable-module-schnorrsig',
            '--prefix',
            installed_lib_dir.replace('\\', '/'),
            '--enable-experimental',
            '--enable-module-ecdh',
            '--enable-benchmark=no',
            '--enable-tests=no',
            '--enable-exhaustive-tests=no',
        ]

        if os.name == 'nt':
            cmd.append('CC=cl.exe')

        if 'COINCURVE_CROSS_HOST' in os.environ:
            cmd.append(f"--host={os.environ['COINCURVE_CROSS_HOST']}")

        # Prepend the working directory to the PATH
        os.environ['PATH'] = built_lib_dir + os.pathsep + os.environ['PATH']

        self.announce('   configure', level=log.INFO)
        with open('_build_clib_configure.log', 'w') as outfile:
            try:
                subprocess.check_call([bash, '-c', ' '.join(cmd)], cwd=built_lib_dir, stdout=outfile)  # noqa S603
            except subprocess.CalledProcessError as e:
                logging.error(f'An error occurred during the configure step: {e}')
                with open('_build_clib_configure.log', 'r') as infile:
                    log_contents = infile.read()
                    logging.error(f'Configure log:\n{log_contents}')
                raise e

        self.announce('   make', level=log.INFO)
        with open('_build_clib_make.log', 'w') as outfile:
            subprocess.check_call([MAKE], cwd=built_lib_dir, stdout=outfile)  # noqa S603

        self.announce('   make install', level=log.INFO)
        with open('_build_clib_install.log', 'w') as outfile:
            subprocess.check_call([MAKE, 'install'], cwd=built_lib_dir, stdout=outfile)  # noqa S603

        self.pkgconfig_dir = os.path.join(installed_lib_dir, 'lib', 'pkgconfig')

        if not has_system_lib():
            self.build_flags['define'].append(('CFFI_ENABLE_RECOVERY', None))

        self.announce('build_clib Done', level=log.INFO)
