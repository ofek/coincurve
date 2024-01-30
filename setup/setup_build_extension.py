import logging
import os
import pathlib
import subprocess
import sys

from setuptools._distutils import log
from setuptools.command.build_ext import build_ext as _build_ext

from setup.setup_support import exact_library_name


class BuildCFFISetuptools(_build_ext):
    static = False

    def build_extensions(self):
        from setup.setup_config import LIB_NAME, COMPILER, EXTRA_COMPILE_ARGS
        from setup.setup_support import build_flags

        pkg_dir = None

        compiler = self.compiler.__class__.__name__

        logging.info(f'build_extensions: {vars(self.compiler)}')
        # Ok, let's go the easy way
        # self.compiler.set_executable('compiler', 'gcc')
        # self.compiler.set_executable('linker_exe', 'gcc')

        log.info('Building Extension (coincurve._libsecp256k1):')
        log.info(f'   - extension compiler: {compiler}')
        log.info(f'   - system compiler: {COMPILER}')
        log.info(f'   - extra compile args: {EXTRA_COMPILE_ARGS}')

        if self.distribution.has_c_libraries():
            log.info('build_extensions: Locally built C-lib')
            _build_clib = self.get_finalized_command('build_clib')
            pkg_dir = _build_clib.pkgconfig_dir

        self.extensions[0].include_dirs.extend(build_flags(LIB_NAME, 'I', pkg_dir))
        self.define = _build_clib.build_flags['define']

        lib_dir = build_flags(LIB_NAME, 'L', pkg_dir)[0]
        link_args_msvc = ['/LIBPATH:' + lib_dir.replace('/', '\\')]

        for _l in build_flags(LIB_NAME, 'l', pkg_dir):
            lib_file, lib_fp = exact_library_name(_l, lib_dir)

            if compiler == 'MSVCCompiler':
                # if lib_file.endswith('.a'):
                #     _a = lib_file
                #     # lib_file = lib_file.replace('.a', '.lib')
                #     os.rename(os.path.join(lib_dir, _a), os.path.join(lib_dir, lib_file))
                self.spawn(['lib', '/DEF:' + lib_fp, '/OUT:' + lib_file])
                self.spawn(['nm', '-g', f'{lib_dir}/{lib_file}'])  # using a msys2 command with unix path
                # args = ['nm', '-g', f'{lib_dir}/{lib_file}']
                # log.info(subprocess.check_output(['nm', '-g', f'{lib_dir}/{lib_file}'], shell=True, check=True))  # S603
                # self.spawn(['dumpbin.exe', '/ALL', f'{lib_dir}/{lib_file}'.replace('/', '\\\\')])
                link_args_msvc.append(lib_file)
            else:
                self.extensions[0].extra_link_args.append(lib_fp)

        if compiler == 'MSVCCompiler':
            self.extensions[0].extra_compile_args.append('/MT')
            # https://cibuildwheel.readthedocs.io/en/1.x/faq/#importerror-dll-load-failed-the-specific-module-could-not-be-found-error-on-windows
            self.extensions[0].extra_compile_args.append('/d2FH4-') if sys.platform == 'win32' else None

            self.extensions[0].extra_link_args.append('/VERBOSE:LIB')
            self.extensions[0].extra_link_args.extend(link_args_msvc)

            log.info(f'build_extensions: MSVCCompiler: {link_args_msvc}')

        super().build_extensions()


class _BuildCFFILib(BuildCFFISetuptools):
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
        args = [sys.executable, build_script, c_file, '1' if self.static else '0']
        subprocess.run(args, shell=False, check=True)  # noqa S603
        log.info('CFFI build completed')

        super().build_extensions()


class BuildCFFIForSharedLib(_BuildCFFILib):
    def build_extensions(self):
        log.info('Building dynamic library')
        self.static = False
        super().build_extensions()


class BuildCFFIForStaticLib(_BuildCFFILib):
    def build_extensions(self):
        log.info('Building static library')
        self.static = True
        super().build_extensions()
