import errno
import logging
import os
import os.path
import platform
import subprocess
import sys

from setuptools import Distribution as _Distribution, setup, find_packages, __version__ as setuptools_version
from setuptools.command import build_clib, build_ext, develop, dist_info, egg_info, sdist
from setuptools.extension import Extension


try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from setup_support import absolute, build_flags, detect_dll, download_library, has_system_lib  # noqa: E402

BUILDING_FOR_WINDOWS = detect_dll()

MAKE = 'gmake' if platform.system() in ['FreeBSD', 'OpenBSD'] else 'make'

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_TAG') or '1ad5185cd42c0636104129fcc9f6a4bf9c67cc40'

LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'

# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.', 2)[:2]] < [3, 3]:
    raise SystemExit(
        f'Your setuptools version ({setuptools_version}) is too old to correctly install this package. Please upgrade '
        f'to a newer version (>= 3.3).'
    )


class EggInfo(egg_info.egg_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        super().run()


class DistInfo(dist_info.dist_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        super().run()


class Sdist(sdist.sdist):
    def run(self):
        if not has_system_lib():
            download_library(self)
        super().run()


class Develop(develop.develop):
    def run(self):
        if not has_system_lib():
            raise RuntimeError(
                "This library is not usable in 'develop' mode when using the "
                'bundled libsecp256k1. See README for details.'
            )
        super().run()


if _bdist_wheel:
    class BdistWheel(_bdist_wheel):
        def run(self):
            if not has_system_lib():
                download_library(self)
            super().run()


class BuildClib(build_clib.build_clib):
    def initialize_options(self):
        super().initialize_options()
        self.build_flags = None

    def finalize_options(self):
        super().finalize_options()
        if self.build_flags is None:
            self.build_flags = {'include_dirs': [], 'library_dirs': [], 'define': [], 'libraries': []}

    def get_source_files(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        return [
            absolute(os.path.join(root, filename))
            for root, _, filenames in os.walk(absolute('libsecp256k1'))
            for filename in filenames
        ]

    def build_libraries(self, libraries):
        raise Exception('build_libraries')

    def check_library_list(self, libraries):
        raise Exception('check_library_list')

    def run(self):
        if has_system_lib():
            logging.info('Using system library')
            return

        build_temp = os.path.abspath(self.build_temp)

        try:
            os.makedirs(build_temp)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        if not os.path.exists(absolute('libsecp256k1')):
            # library needs to be downloaded
            self.get_source_files()

        if not os.path.exists(absolute('libsecp256k1/configure')):
            # configure script hasn't been generated yet
            autogen = absolute('libsecp256k1/autogen.sh')
            os.chmod(absolute(autogen), 0o700)
            subprocess.check_call([autogen], cwd=absolute('libsecp256k1'))  # noqa S603

        for filename in [
            'libsecp256k1/configure',
            'libsecp256k1/build-aux/compile',
            'libsecp256k1/build-aux/config.guess',
            'libsecp256k1/build-aux/config.sub',
            'libsecp256k1/build-aux/depcomp',
            'libsecp256k1/build-aux/install-sh',
            'libsecp256k1/build-aux/missing',
            'libsecp256k1/build-aux/test-driver',
        ]:
            try:
                os.chmod(absolute(filename), 0o700)
            except OSError as e:
                # some of these files might not exist depending on autoconf version
                if e.errno != errno.ENOENT:
                    # If the error isn't 'No such file or directory' something
                    # else is wrong and we want to know about it
                    raise

        cmd = [
            absolute('libsecp256k1/configure'),
            '--disable-shared',
            '--enable-static',
            '--disable-dependency-tracking',
            '--with-pic',
            '--enable-module-extrakeys',
            '--enable-module-recovery',
            '--enable-module-schnorrsig',
            '--prefix',
            os.path.abspath(self.build_clib),
            '--enable-experimental',
            '--enable-module-ecdh',
            '--enable-benchmark=no',
            '--enable-tests=no',
            '--enable-exhaustive-tests=no',
        ]
        if 'COINCURVE_CROSS_HOST' in os.environ:
            cmd.append(f"--host={os.environ['COINCURVE_CROSS_HOST']}")

        logging.debug(f"Running configure: {' '.join(cmd)}")
        subprocess.check_call(cmd, cwd=build_temp)  # noqa S603

        subprocess.check_call([MAKE], cwd=build_temp)  # noqa S603
        subprocess.check_call([MAKE, 'check'], cwd=build_temp)  # noqa S603
        subprocess.check_call([MAKE, 'install'], cwd=build_temp)  # noqa S603

        self.build_flags['include_dirs'].extend(build_flags('libsecp256k1', 'I', build_temp))
        self.build_flags['library_dirs'].extend(build_flags('libsecp256k1', 'L', build_temp))
        self.build_flags['libraries'].extend(build_flags('libsecp256k1', 'l', build_temp))
        self.pkgconfig_dir = build_temp

        if not has_system_lib():
            self.build_flags['define'].append(('CFFI_ENABLE_RECOVERY', None))

        logging.info('build_clib: Done')


class _BuildExtensionFromCFFI(build_ext.build_ext):
    static_lib = None

    def update_link_args(self, libraries, libraries_dirs, extra_link_args, pkg_dir):
        raise NotImplementedError('update_link_args')

    def build_extension(self, ext):
        logging.info(
            f'Extension build:'
            f'\n         OS:{os.name}'
            f'\n   Platform:{sys.platform}'
            f'\n   Compiler:{self.compiler.__class__.__name__}'
            f'\n     Static:{self.static_lib}'
        )

        # Enforce API interface
        ext.py_limited_api = False

        if hasattr(b := self.get_finalized_command('build_clib'), 'pkgconfig_dir'):
            # Locally built C-lib
            pkg_dir = b.pkgconfig_dir

            ext.include_dirs.extend(build_flags('libsecp256k1', 'I', pkg_dir))
            ext.library_dirs.extend(build_flags('libsecp256k1', 'L', pkg_dir))

            libraries = build_flags('libsecp256k1', 'l', pkg_dir)
            logging.info(f'  Libraries:{libraries}')

            self.update_link_args(libraries, ext.library_dirs, ext.extra_link_args, pkg_dir)

        else:
            ext.include_dirs.extend(build_flags('libsecp256k1', 'I'))
            ext.library_dirs.extend(build_flags('libsecp256k1', 'L'))
            ext.libraries.extend(build_flags('libsecp256k1', 'l'))

        super().build_extension(ext)


class _BuildCFFI(_BuildExtensionFromCFFI):
    def build_extension(self, ext):
        logging.info(
            f'Cmdline CFFI build:'
            f'\n     Source: {absolute(ext.sources[0])}'
        )

        build_script = os.path.join('_cffi_build', 'build_shared.py')
        for c_file in ext.sources:
            cmd = [sys.executable, build_script, c_file, '1' if self.static_lib else '0']
            subprocess.run(cmd, shell=False, check=True)  # noqa S603

        super().build_extension(ext)


class BuildCFFIForSharedLib(_BuildCFFI):
    static_lib = False


class BuildCFFIForStaticLib(_BuildCFFI):
    static_lib = True

    def update_link_args(self, libraries, libraries_dirs, extra_link_args, pkg_dir):
        if self.compiler.__class__.__name__ == 'UnixCCompiler':
            # It is possible that the library was compiled without fPIC option
            for lib in libraries:
                # On MacOS the mix static/dynamic option is different
                # It requires a -force_load <full_lib_path> option for each library
                if sys.platform == 'darwin':
                    for lib_dir in libraries_dirs:
                        if os.path.exists(os.path.join(lib_dir, f'lib{lib}.a')):
                            extra_link_args.extend(
                                ['-Wl,-force_load', os.path.join(lib_dir, f'lib{lib}.a')]
                            )
                            break
                else:
                    extra_link_args.extend(['-Wl,-Bstatic', f'-l{lib}', '-Wl,-Bdynamic'])
        elif self.compiler.__class__.__name__ == 'MSVCCompiler':
            # This section is not used yet since we still cross-compile on Windows
            # TODO: write the windows native build here when finalized
            raise NotImplementedError(f'Unsupported compiler: {self.compiler.__class__.__name__}')
        else:
            raise NotImplementedError(f'Unsupported compiler: {self.compiler.__class__.__name__}')


package_data = {'coincurve': ['py.typed']}

extension = Extension(
    name='coincurve._libsecp256k1',
    sources=[os.path.join('coincurve', '_libsecp256k1.c')],
    py_limited_api=False,
)

if has_system_lib():

    class Distribution(_Distribution):
        def has_c_libraries(self):
            return not has_system_lib()


    # TODO: This has not been tested yet. has_system_lib() does not find conda install lib yet
    setup_kwargs = dict(
        setup_requires=['cffi>=1.3.0', 'requests'],
        ext_modules=[extension],
        cmdclass={
            'build_clib': BuildClib,
            'build_ext': BuildCFFIForSharedLib,
            'develop': Develop,
            'egg_info': EggInfo,
            'sdist': Sdist,
            'bdist_wheel': BdistWheel if _bdist_wheel else None,
        },
    )

else:
    if BUILDING_FOR_WINDOWS:

        class Distribution(_Distribution):
            def is_pure(self):
                return False


        package_data['coincurve'].append('libsecp256k1.dll')
        setup_kwargs = {}

    else:

        class Distribution(_Distribution):
            def has_c_libraries(self):
                return not has_system_lib()


        setup_kwargs = dict(
            setup_requires=['cffi>=1.3.0', 'requests'],
            ext_modules=[extension],
            cmdclass={
                'build_clib': BuildClib,
                'build_ext': BuildCFFIForStaticLib,
                'develop': Develop,
                'egg_info': EggInfo,
                'sdist': Sdist,
                'bdist_wheel': BdistWheel if _bdist_wheel else None,
            },
        )


def main():
    setup(
        name='coincurve',
        version='19.0.0',

        packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', 'libsecp256k1', 'tests')),
        package_data=package_data,

        distclass=Distribution,
        zip_safe=False,
        **setup_kwargs
    )


if __name__ == '__main__':
    main()
