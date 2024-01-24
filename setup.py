import errno
import os
import os.path
import pathlib
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

LIB_NAME = 'libsecp256k1'
LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'

# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.', 2)[:2]] < [3, 3]:
    raise SystemExit(
        f'Your setuptools version ({setuptools_version}) is too old to correctly install this package. Please upgrade '
        f'to a newer version (>= 3.3).'
    )


def download_library(command, libdir=LIB_NAME, force=False):
    if command.dry_run:
        return

    if force:
        shutil.rmtree(libdir, ignore_errors=True)

    if os.path.exists(os.path.join(libdir, 'autogen.sh')):
        # Library already downloaded
        return

    # Ensure the path exists
    os.makedirs(libdir, exist_ok=True)

    # _download will use shutil.move, thus remove the directory
    os.rmdir(libdir)

    command.announce(f'Downloading {LIB_NAME} source code', level=log.INFO)
    from requests.exceptions import RequestException
    try:
        _download_library(libdir)
    except RequestException as e:
        raise SystemExit(f'Unable to download {LIB_NAME} library: {e!s}', ) from e


def _download_library(libdir):
    import requests
    r = requests.get(LIB_TARBALL_URL, stream=True, timeout=10)
    status_code = r.status_code
    if status_code != 200:
        raise SystemExit(f'Unable to download {LIB_NAME} library: HTTP-Status: {status_code}')
    content = BytesIO(r.raw.read())
    content.seek(0)
    with tarfile.open(fileobj=content) as tf:
        dirname = tf.getnames()[0].partition('/')[0]
        tf.extractall()
    shutil.move(dirname, libdir)


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
            download_library(self, force=True)

        _dist_info.run(self)


class sdist(_sdist):
    def run(self):
        if not has_system_lib():
            download_library(self, force=True)
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
        return build_flags(LIB_NAME, 'l', os.path.join(os.path.abspath(self.build_clib), 'lib', 'pkgconfig'))

    def run(self):
        cwd = pathlib.Path().absolute()

        log.info('SECP256K1 build options:')
        if has_system_lib():
            log.info('Using system library')
            return

        build_temp = os.path.abspath(self.build_temp)
        build_external_library = os.path.join(cwd, 'build_external_library')
        built_lib_dir = os.path.join(build_external_library, LIB_NAME)
        installed_lib_dir = os.path.abspath(self.build_clib)

        try:
            os.makedirs(build_external_library)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        download_library(self, libdir=built_lib_dir)

        autoreconf = 'autoreconf -if --warnings=all'
        bash = shutil.which('bash')
        subprocess.check_call([bash, '-c', autoreconf], cwd=built_lib_dir)  # noqa S603

        for filename in [
            os.path.join(built_lib_dir, 'configure'),
            os.path.join(built_lib_dir, 'build-aux', 'compile'),
            os.path.join(built_lib_dir, 'build-aux', 'config.guess'),
            os.path.join(built_lib_dir, 'build-aux', 'config.sub'),
            os.path.join(built_lib_dir, 'build-aux', 'depcomp'),
            os.path.join(built_lib_dir, 'build-aux', 'install-sh'),
            os.path.join(built_lib_dir, 'build-aux', 'missing'),
            os.path.join(built_lib_dir, 'build-aux', 'test-driver'),
        ]:
            try:
                os.chmod(filename, 0o700)
            except OSError as e:
                # some of these files might not exist depending on autoconf version
                if e.errno != errno.ENOENT:
                    # If the error isn't 'No such file or directory' something
                    # else is wrong and we want to know about it
                    raise

        cmd = [
            'configure',
            '--disable-shared',
            '--enable-static',
            '--disable-dependency-tracking',
            '--with-pic',
            '--enable-module-extrakeys',
            '--enable-module-recovery',
            '--enable-module-schnorrsig',
            '--prefix',
            installed_lib_dir.replace('\\', '/'),
            '--enable-experimental',
            '--enable-module-ecdh',
            '--enable-benchmark=no',
            '--enable-tests=no',
            '--enable-exhaustive-tests=no',
        ]
        if 'COINCURVE_CROSS_HOST' in os.environ:
            cmd.append(f"--host={os.environ['COINCURVE_CROSS_HOST']}")

        log.debug(f"Running configure: {' '.join(cmd)}")
        # Prepend the working directory to the PATH
        os.environ['PATH'] = built_lib_dir + os.pathsep + os.environ['PATH']
        subprocess.check_call([bash, '-c', ' '.join(cmd)], cwd=built_lib_dir)  # noqa S603

        subprocess.check_call([MAKE], cwd=built_lib_dir)  # noqa S603
        subprocess.check_call([MAKE, 'install'], cwd=built_lib_dir)  # noqa S603

        self.build_flags['include_dirs'].extend(build_flags(LIB_NAME,
                                                            'I',
                                                            os.path.join(installed_lib_dir, 'lib', 'pkgconfig')))
        self.build_flags['library_dirs'].extend(build_flags(LIB_NAME,
                                                            'L',
                                                            os.path.join(installed_lib_dir, 'lib', 'pkgconfig')))
        if not has_system_lib():
            self.build_flags['define'].append(('CFFI_ENABLE_RECOVERY', None))
        self.announce('build_clib Done', level=log.INFO)


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
                f'bundled {LIB_NAME}. See README for details.'
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
    install_requires=['asn1crypto', 'cffi>=1.3.0'],

    packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', LIB_NAME, 'tests')),
    package_data=package_data,

    distclass=Distribution,
    zip_safe=False,
    **setup_kwargs
)
