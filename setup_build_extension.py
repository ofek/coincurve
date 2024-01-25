import os
import pathlib
import subprocess
import sys
from typing import TYPE_CHECKING, cast

from setuptools._distutils import log
from setuptools.command.build_ext import build_ext as _build_ext

if TYPE_CHECKING:
    from setup_build_secp256k1_with_make import BuildClibWithMake


def _update_extensions_for_msvc(extension, compiler):
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


class BuildCFFIForSharedLib(_build_ext):
    def build_extensions(self):
        from setup_support import absolute

        log.info(f'Cmdline CFFI Shared for: {os.name}:{sys.platform}:{(self.compiler.compiler[0])}')
        build_script = os.path.join('_cffi_build', 'build_from_cmdline.py')

        _update_extensions_for_msvc(self.extensions[0], self.compiler.compiler[0])
        c_file = self.extensions[0].sources[0] = absolute(self.extensions[0].sources[0])

        subprocess.run([sys.executable, build_script, c_file, '0'], shell=False, check=True)  # noqa S603
        super().build_extensions()


class BuildCFFIForStaticLib(_build_ext):
    def build_extensions(self):
        from setup_support import absolute

        log.info(
            f'Cmdline CFFI Static for: '
            f'\n         OS:{os.name}'
            f'\n   Platform:{sys.platform}'
            f'\n   Compiler:{(self.compiler.compiler[0])}'
            f'\n        CWD: {pathlib.Path().absolute()}'
            f'\n     Source: {absolute(self.extensions[0].sources[0])}'
        )
        build_script = os.path.join('_cffi_build', 'build_from_cmdline.py')

        _update_extensions_for_msvc(self.extensions[0], self.compiler.compiler[0])
        c_file = self.extensions[0].sources[0] = absolute(self.extensions[0].sources[0])

        log.info(
            f'\n     C-file: {c_file}'
        )
        subprocess.run([sys.executable, build_script, c_file, '1'], shell=False, check=True)  # noqa S603
        super().build_extensions()


class BuildCFFISetuptools(_build_ext):
    def run(self):
        log.info(f'Setuptools CFFI static for: {os.name}:{sys.platform}:{(self.compiler.compiler[0])}')
        if self.distribution.has_c_libraries():
            log.info('   Locally built C-lib')
            _build_clib: BuildClibWithMake = cast(self.get_finalized_command('build_clib'), BuildClibWithMake)
            self.include_dirs.append(os.path.join(_build_clib.build_clib, 'include'))
            self.include_dirs.extend(_build_clib.build_flags['include_dirs'])

            self.library_dirs.insert(0, os.path.join(_build_clib.build_clib, 'lib'))
            self.library_dirs.extend(_build_clib.build_flags['library_dirs'])

            self.define = _build_clib.build_flags['define']

        return _build_ext.run(self)
