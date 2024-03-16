import os
import subprocess
import sys

from setuptools.command import build_ext


class BuildExt(build_ext.build_ext):
    def run(self):
        if self.distribution.has_c_libraries():
            _build_clib = self.get_finalized_command('build_clib')
            self.include_dirs.append(os.path.join(_build_clib.build_clib, 'include'))
            self.include_dirs.extend(_build_clib.build_flags['include_dirs'])

            self.library_dirs.insert(0, os.path.join(_build_clib.build_clib, 'lib'))
            self.library_dirs.extend(_build_clib.build_flags['library_dirs'])

            self.define = _build_clib.build_flags['define']

        return super().run()


class BuildCFFIForSharedLib(build_ext.build_ext):
    def build_extensions(self):
        build_script = os.path.join('_cffi_build', 'build_shared.py')
        c_file = self.extensions[0].sources[0]
        subprocess.run([sys.executable, build_script, c_file, '0'], shell=False, check=True)  # noqa S603
        super().build_extensions()
