import os

from setuptools.command import build_py


class BuildLibInfo(build_py.build_py):
    """Create SECP256K1 library build info."""

    def run(self):
        import contextlib

        from setup_tools.support import subprocess_run, update_pkg_config_path, verify_system_lib

        update_pkg_config_path()

        with contextlib.suppress(Exception):
            cmd = (
                [
                    'pkg-config',
                    '--libs-only-L',
                    '--dont-define-prefix',
                    'libsecp256k1',
                ]
                if os.name == 'nt'
                else ['pkg-config', '--libs-only-L', 'libsecp256k1']
            )
            lib_dir = subprocess_run(cmd)
            os.makedirs(self.build_lib, exist_ok=True)
            verify_system_lib(lib_dir[2:].strip(), os.path.join('src', 'coincurve'))
        super().run()
