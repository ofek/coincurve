import os
import pathlib
import subprocess
import sys

from setuptools._distutils import log
from setuptools.command.build_ext import build_ext as _build_ext


def _update_extension_for_msvc(extension, compiler):
    log.info(f'compiler: {compiler}')
    [log.info(f'extra_link_args[{i}]: {v}') for i, v in enumerate(extension.__dict__.get('extra_link_args'))]

    # MSVCCompiler for VisualC on Windows
    if compiler == 'UnixCCompiler':
        return

    path_to_lib = ''
    for i, v in enumerate(extension.__dict__.get('extra_link_args')):

        # Replace -L with /LIBPATH: for MSVC
        if v.startswith('-L'):
            path_to_lib = v[2:]
            extension.__dict__['extra_link_args'][i] = f'/LIBPATH:{path_to_lib}'

        # Replace -l with the library filename for MSVC
        if v.startswith('-l'):
            v = v.replace('-l', 'lib')

            if os.path.isfile(path_to_lib + v + '.lib'):
                extension.__dict__['extra_link_args'][i] = f'{v}.lib'

            if os.path.isfile(path_to_lib + v + '.a'):
                extension.__dict__['extra_link_args'][i] = f'{v}.a'


def _update_extension_for_c_library(extension, c_lib_path=None, c_flags=None):
    from setup.setup_config import PKGCONFIG

    if c_lib_path:
        extension.__dict__.get('include_dirs').append(os.path.join(c_lib_path, 'include'))
        extension.__dict__.get('include_dirs').extend(c_flags['include_dirs'])

        extension.__dict__.get('library_dirs').insert(0, os.path.join(c_lib_path, 'lib'))
        extension.__dict__.get('library_dirs').extend(c_flags['library_dirs'])

        extension.__dict__['define'] = c_flags['define']
        return

    try:
        extension.__dict__.get('extra_compile_args').append(
            subprocess.check_output([PKGCONFIG, '--cflags-only-I', 'libsecp256k1']).strip().decode('utf-8')  # noqa S603
        )
        extension.__dict__.get('extra_link_args').append(
            subprocess.check_output([PKGCONFIG, '--libs-only-L', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
        )
        extension.__dict__.get('extra_link_args').append(
            subprocess.check_output([PKGCONFIG, '--libs-only-l', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
        )
    except subprocess.CalledProcessError as e:
        log.error(f'Error: {e}')
        raise e


class BuildCFFISetuptools(_build_ext):
    def build_extensions(self):
        if self.distribution.has_c_libraries():
            log.info('build_extensions: Locally built C-lib')
            _build_clib = self.get_finalized_command('build_clib')
            _update_extension_for_c_library(self.extensions[0], str(_build_clib.build_clib), _build_clib.build_flags)

        super().build_extensions()

    def run(self):
        log.info('run build_ext')
        super().run()


class _BuildCFFILib(BuildCFFISetuptools):
    lib_type = '0'

    def build_extensions(self):
        from setup.setup_support import absolute

        log.info(
            f'Cmdline CFFI build:'
            f'\n         OS:{os.name}'
            f'\n   Platform:{sys.platform}'
            f'\n   Compiler:{self.compiler.__class__.__name__}'
            f'\n        CWD: {pathlib.Path().absolute()}'
            f'\n     Source: {absolute(self.extensions[0].sources[0])}'
        )
        build_script = absolute(os.path.join('../_cffi_build', 'build_from_cmdline.py'))

        c_file = self.extensions[0].sources[0]
        subprocess.run([sys.executable, build_script, c_file, self.lib_type], shell=False, check=True)  # noqa S603
        log.info('CFFI build complete')

        log.info(f'{self.extensions}')
        _update_extension_for_msvc(self.extensions[0], self.compiler.__class__.__name__)

        super().build_extensions()


class BuildCFFIForSharedLib(_BuildCFFILib):
    def build_extensions(self):
        log.info('Building dynamic library')
        self.lib_type = '0'
        super().build_extensions()


class BuildCFFIForStaticLib(_BuildCFFILib):
    def build_extensions(self):
        log.info('Building static library')
        self.lib_type = '1'
        super().build_extensions()
