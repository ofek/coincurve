import os
import pathlib
import subprocess
import sys

from setuptools._distutils import log
from setuptools.command.build_ext import build_ext as _build_ext

from setup.setup_support import exact_library_name


def _update_extension_for_msvc(extension, compiler):
    log.info(f'compiler: {compiler}')
    log.info(f'extension: {extension.__dict__}')
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
    from setup.setup_config import LIB_NAME
    from setup.setup_support import build_flags

    if c_lib_path:
        # Update include/lib for C-lib linking.
        extension.__dict__.get('include_dirs').append(os.path.join(c_lib_path, 'include'))
        extension.__dict__.get('include_dirs').extend(c_flags['include_dirs'])

        extension.__dict__.get('library_dirs').insert(0, os.path.join(c_lib_path, 'lib'))
        extension.__dict__.get('library_dirs').extend(c_flags['library_dirs'])

        # This class will call build_clib.get_library_names() to get the list of libraries to link
        # However, this would require the build_clib to know the linking compiler.
        # Instead, we simply use build_clib detection of the installed libraries and add them directly
        extension.__dict__.get('extra_link_args').extend(c_flags['library_fullnames'])

        extension.__dict__['define'] = c_flags['define']
        return

    try:
        # Update include/lib for C-lib linking. Append to the 'extra' args
        extension.__dict__.get('include_dirs').extend(build_flags(LIB_NAME, 'I'))

        # We need to decipher the name of the library from the pkg-config output
        for path in build_flags(LIB_NAME, 'L'):
            for lib in build_flags(LIB_NAME, 'l'):
                extension.__dict__.get('extra_link_args').append(exact_library_name(lib, path))
    except subprocess.CalledProcessError as e:
        log.error(f'Error: {e}')
        raise e


class BuildCFFISetuptools(_build_ext):
    static = False

    def build_extensions(self):
        from setup.setup_config import LIB_NAME, COMPILER, EXTRA_COMPILE_ARGS
        from setup.setup_support import build_flags

        pkg_dir = None
        compiler = self.compiler.__class__.__name__

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
        link_args_msvc = '/LIBPATH:' + lib_dir.replace('/', '\\')

        for _l in build_flags(LIB_NAME, 'l', pkg_dir):
            lib_file, lib_fp = exact_library_name(_l, lib_dir)

            if compiler == 'MSVCCompiler':
                if lib_file.endswith('.a'):
                    _a = lib_file
                    lib_file = lib_file.replace('.a', '.lib')
                    os.rename(os.path.join(lib_dir, _a), os.path.join(lib_dir, lib_file))
                link_args_msvc += f' {lib_file}'
            else:
                self.extensions[0].extra_link_args.append(lib_fp)

        if compiler == 'MSVCCompiler':
            # Reference:
            # https://cibuildwheel.readthedocs.io/en/1.x/faq/#importerror-dll-load-failed-the-specific-module-could-not-be-found-error-on-windows
            self.extensions[0].extra_compile_args.extend(['/MT', '/d2FH4-'])

            self.extensions[0].extra_link_args.append('/VERBOSE:LIB')
            self.extensions[0].extra_link_args.append(link_args_msvc)

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
