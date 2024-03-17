import os
import sys

from setuptools.command import build_ext

from setup import LIB_NAME
from setup_tools.linkers import SharedLinker, StaticLinker
from setup_tools.support import build_flags, has_system_lib, subprocess_run


class BuildExtensionFromCFFI(build_ext.build_ext):
    from setup import SECP256K1_BUILD

    static_lib = True if SECP256K1_BUILD == 'STATIC' else False

    def update_link_args(self, libraries, libraries_dirs, extra_link_args):
        if self.static_lib:
            StaticLinker.update_link_args(self.compiler, libraries, libraries_dirs, extra_link_args)
        else:
            SharedLinker.update_link_args(self.compiler, libraries, libraries_dirs, extra_link_args)

    def create_c_files(self, ext):
        # Construct C-file from CFFI
        build_script = os.path.join('_cffi_build', 'build.py')
        for i, c_file in enumerate(ext.sources):
            os.makedirs(self.build_temp, exist_ok=True)
            c_file = os.path.join(self.build_temp, os.path.basename(c_file))
            # This puts c-file a temp location (and not in the coincurve src directory)
            ext.sources[i] = c_file
            cmd = [sys.executable, build_script, c_file, '1' if self.static_lib else '0']
            subprocess_run(cmd)

    def build_extension(self, ext):
        # Construct C-file from CFFI
        self.create_c_files(ext)

        # Enforce API interface
        ext.py_limited_api = False

        # Find pkgconfig file for locally built library
        pkg_dirs = self.get_finalized_command('build_clib').pkgconfig_dir  # type: ignore
        c_lib_pkg = next((d for d in pkg_dirs if os.path.isfile(os.path.join(d, f'{LIB_NAME}.pc'))), None)

        if not has_system_lib() and not c_lib_pkg:
            raise RuntimeError(
                f'pkgconfig file not found: {LIB_NAME}.pc in : {pkg_dirs}.'
                f'\nSystem lib is {has_system_lib() = }. '
                'Please check that the library was properly built.'
            )

        # PKG_CONFIG_PATH is updated by build_clib if built locally,
        # however, it would not work for a step-by-step build, thus we specify the lib path
        ext.extra_compile_args.extend([f'-I{build_flags(LIB_NAME, "I", c_lib_pkg)[0]}'])
        ext.library_dirs.extend(build_flags(LIB_NAME, 'L', c_lib_pkg))

        libraries = build_flags(LIB_NAME, 'l', c_lib_pkg)

        # We do not set ext.libraries, this would add the default link instruction
        # Instead, we use extra_link_args to customize the link command
        self.update_link_args(libraries, ext.library_dirs, ext.extra_link_args)

        super().build_extension(ext)
