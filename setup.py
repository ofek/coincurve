import errno
import os
import os.path
import platform
import shutil
import subprocess
import tarfile
from io import BytesIO
import sys

from setuptools import Distribution as _Distribution, setup, find_packages, __version__ as setuptools_version
from setuptools._distutils import log
from setuptools._distutils.errors import DistutilsError
from setuptools.command.build_clib import build_clib as _build_clib
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.extension import Extension
from setuptools.command.develop import develop as _develop
from setuptools.command.dist_info import dist_info as _dist_info
from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.sdist import sdist as _sdist

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from setup_support import absolute, build_flags, detect_dll, has_system_lib  # noqa: E402

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


def download_library(command):
    if command.dry_run:
        return
    libdir = 'libsecp256k1'
    if os.path.exists(os.path.join(libdir, 'autogen.sh')):
        # Library already downloaded
        return
    if not os.path.exists(libdir):
        command.announce('downloading libsecp256k1 source code', level=log.INFO)
        try:
            import requests
            try:
                r = requests.get(LIB_TARBALL_URL, stream=True, timeout=10)
                status_code = r.status_code
                if status_code == 200:
                    content = BytesIO(r.raw.read())
                    content.seek(0)
                    with tarfile.open(fileobj=content) as tf:
                        dirname = tf.getnames()[0].partition('/')[0]
                        tf.extractall()
                    shutil.move(dirname, libdir)
                else:
                    raise SystemExit('Unable to download secp256k1 library: HTTP-Status: %d', status_code)
            except requests.exceptions.RequestException as e:
                raise SystemExit('Unable to download secp256k1 library: %s', str(e))
        except ImportError as e:
            raise SystemExit('Unable to download secp256k1 library: %s', str(e))


class egg_info(_egg_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        _egg_info.run(self)


class dist_info(_dist_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        _dist_info.run(self)


class sdist(_sdist):
    def run(self):
        if not has_system_lib():
            download_library(self)
        _sdist.run(self)


if _bdist_wheel:

    class bdist_wheel(_bdist_wheel):
        def run(self):
            if not has_system_lib():
                download_library(self)
            _bdist_wheel.run(self)


else:
    bdist_wheel = None


class build_clib(_build_clib):
    def initialize_options(self):
        _build_clib.initialize_options(self)
        self.build_flags = None

    def finalize_options(self):
        _build_clib.finalize_options(self)
        if self.build_flags is None:
            self.build_flags = {'include_dirs': [], 'library_dirs': [], 'define': []}

    def get_source_files(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        if not has_system_lib():
            download_library(self)

        return [
            filename
            for root, _, filenames in os.walk(absolute('libsecp256k1'))
            for filename in filenames
        ]

    def build_libraries(self, libraries):
        raise Exception('build_libraries')

    def check_library_list(self, libraries):
        raise Exception('check_library_list')

    def get_library_names(self):
        return build_flags('libsecp256k1', 'l', os.path.abspath(self.build_temp))

    def run(self):
        if has_system_lib():
            log.info('Using system library')
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

        log.debug(f"Running configure: {' '.join(cmd)}")
        subprocess.check_call(cmd, cwd=build_temp)  # noqa S603

        subprocess.check_call([MAKE], cwd=build_temp)  # noqa S603
        subprocess.check_call([MAKE, 'check'], cwd=build_temp)  # noqa S603
        subprocess.check_call([MAKE, 'install'], cwd=build_temp)  # noqa S603

        self.build_flags['include_dirs'].extend(build_flags('libsecp256k1', 'I', build_temp))
        self.build_flags['library_dirs'].extend(build_flags('libsecp256k1', 'L', build_temp))
        if not has_system_lib():
            self.build_flags['define'].append(('CFFI_ENABLE_RECOVERY', None))


class build_ext(_build_ext):
    def run(self):
        if self.distribution.has_c_libraries():
            _build_clib = self.get_finalized_command('build_clib')
            self.include_dirs.append(os.path.join(_build_clib.build_clib, 'include'))
            self.include_dirs.extend(_build_clib.build_flags['include_dirs'])

            self.library_dirs.insert(0, os.path.join(_build_clib.build_clib, 'lib'))
            self.library_dirs.extend(_build_clib.build_flags['library_dirs'])

            self.define = _build_clib.build_flags['define']

        return _build_ext.run(self)


class develop(_develop):
    def run(self):
        if not has_system_lib():
            raise DistutilsError(
                "This library is not usable in 'develop' mode when using the "
                'bundled libsecp256k1. See README for details.'
            )
        _develop.run(self)


package_data = {'coincurve': ['py.typed']}


class BuildCFFIForSharedLib(_build_ext):
    def build_extensions(self):
        build_script = os.path.join('_cffi_build', 'build_shared.py')
        c_file = self.extensions[0].sources[0]
        subprocess.run([sys.executable, build_script, c_file, '0'], shell=False, check=True)  # noqa S603
        super().build_extensions()


if has_system_lib():

    class Distribution(_Distribution):
        def has_c_libraries(self):
            return not has_system_lib()

    # --- SECP256K1 package definitions ---
    secp256k1_package = 'libsecp256k1'

    extension = Extension(
        name='coincurve._libsecp256k1',
        sources=[os.path.join('coincurve', '_libsecp256k1.c')],
        # ABI?: py_limited_api=True,
    )

    extension.extra_compile_args = [
        subprocess.check_output(['pkg-config', '--cflags-only-I', 'libsecp256k1']).strip().decode('utf-8')  # noqa S603
    ]
    extension.extra_link_args = [
        subprocess.check_output(['pkg-config', '--libs-only-L', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
        subprocess.check_output(['pkg-config', '--libs-only-l', 'libsecp256k1']).strip().decode('utf-8'),  # noqa S603
    ]

    if os.name == 'nt' or sys.platform == 'win32':
        # Apparently, the linker on Windows interprets -lxxx as xxx.lib, not libxxx.lib
        for i, v in enumerate(extension.__dict__.get('extra_link_args')):
            extension.__dict__['extra_link_args'][i] = v.replace('-L', '/LIBPATH:')

            if v.startswith('-l'):
                v = v.replace('-l', 'lib')
                extension.__dict__['extra_link_args'][i] = f'{v}.lib'

    setup_kwargs = dict(
        setup_requires=['cffi>=1.3.0', 'requests'],
        ext_modules=[extension],
        cmdclass={
            'build_clib': build_clib,
            'build_ext': BuildCFFIForSharedLib,
            'develop': develop,
            'egg_info': egg_info,
            'sdist': sdist,
            'bdist_wheel': bdist_wheel,
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
            ext_package='coincurve',
            cffi_modules=['_cffi_build/build.py:ffi'],
            cmdclass={
                'build_clib': build_clib,
                'build_ext': build_ext,
                'develop': develop,
                'egg_info': egg_info,
                'sdist': sdist,
                'bdist_wheel': bdist_wheel,
            },
        )

setup(
    name='coincurve',
    version='19.0.0',

    packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', 'libsecp256k1', 'tests')),
    package_data=package_data,

    distclass=Distribution,
    zip_safe=False,
    **setup_kwargs
)
