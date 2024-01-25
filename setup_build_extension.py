import os
import pathlib
import subprocess
import sys
from typing import TYPE_CHECKING, cast

from setuptools._distutils import log
from setuptools.command.build_ext import build_ext as _build_ext


def _update_extension_for_msvc(extension, compiler):
    if compiler == 'gcc':
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

    return extension


def _update_extension_for_c_library(extension):
    from setup import PKGCONFIG

    extension.__dict__.get('extra_compile_args').append(
        subprocess.check_output([PKGCONFIG, '--cflags-only-I', 'libsecp256k1']).strip().decode('utf-8')  # noqa S603
    )
    extension.__dict__.get('extra_link_args').append(
        subprocess.check_output([PKGCONFIG, '--libs-only-L', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
    )
    extension.__dict__.get('extra_link_args').append(
        subprocess.check_output([PKGCONFIG, '--libs-only-l', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
    )

    return extension


class BuildCFFISetuptools(_build_ext):
    def run(self):
        if self.distribution.has_c_libraries():
            from setup_build_secp256k1_with_make import BuildClibWithMake

            log.info('   Locally built C-lib')
            _build_clib: BuildClibWithMake = cast(BuildClibWithMake, self.get_finalized_command('build_clib'))
            self.include_dirs.append(os.path.join(_build_clib.build_clib, 'include'))
            self.include_dirs.extend(_build_clib.build_flags['include_dirs'])

            self.library_dirs.insert(0, os.path.join(_build_clib.build_clib, 'lib'))
            self.library_dirs.extend(_build_clib.build_flags['library_dirs'])

            self.define = _build_clib.build_flags['define']

        return _build_ext.run(self)


class _BuildCFFILib(BuildCFFISetuptools):
    def build_extensions(self):
        from setup_support import absolute

        build_script = os.path.join('_cffi_build', 'build_from_cmdline.py')

        c_file = self.extensions[0].sources[0] = absolute(self.extensions[0].sources[0])

        subprocess.run([sys.executable, build_script, c_file, self.lib_type], shell=False, check=True)  # noqa S603

        _update_extension_for_c_library(self.extensions[0])
        _update_extension_for_msvc(self.extensions[0], self.compiler.compiler[0])

        super().build_extensions()


class BuildCFFIForSharedLib(_BuildCFFILib):
    def build_extensions(self):
        from setup_support import absolute

        log.info(
            f'Cmdline CFFI Shared for: '
            f'\n         OS:{os.name}'
            f'\n   Platform:{sys.platform}'
            f'\n   Compiler:{(self.compiler)}'
            f'\n        CWD: {pathlib.Path().absolute()}'
            f'\n     Source: {absolute(self.extensions[0].sources[0])}'
        )
        self.lib_type = '0'
        super().build_extensions()


class BuildCFFIForStaticLib(_BuildCFFILib):
    def build_extensions(self):
        from setup_support import absolute

        log.info(
            f'Cmdline CFFI Static for: '
            f'\n         OS:{os.name}'
            f'\n   Platform:{sys.platform}'
            f'\n   Compiler:{(self.compiler)}'
            f'\n        CWD: {pathlib.Path().absolute()}'
            f'\n     Source: {absolute(self.extensions[0].sources[0])}'
        )
        self.lib_type = '1'
        super().build_extensions()
