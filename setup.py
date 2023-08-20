import errno
import os
import os.path
import pathlib
import platform
import shutil
import subprocess
import sys
import tarfile
from distutils import log
from distutils.command.build_clib import build_clib as _build_clib
from distutils.command.build_ext import build_ext as _build_ext
from distutils.errors import DistutilsError
from io import BytesIO

from setuptools import Distribution as _Distribution, setup, find_packages, __version__ as setuptools_version
from setuptools.command.develop import develop as _develop
from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.sdist import sdist as _sdist

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from setup_support import build_flags, detect_dll, has_system_lib, find_conda_executable  # noqa: E402


BUILDING_FOR_WINDOWS = detect_dll()

MAKE = 'gmake' if platform.system() in ['FreeBSD', 'OpenBSD'] else 'make'

# IMPORTANT: keep in sync with .github/workflows/build.yml
#
# Version of libsecp256k1 to download if none exists in the `libsecp256k1` directory
UPSTREAM_REF = os.getenv('COINCURVE_UPSTREAM_REF') or 'ddf2b2910eb19032f8dd657c66735115ae24bfba'
LIB_NAME = 'libsecp256k1'
LIB_TARBALL_URL = f'https://github.com/bitcoin-core/secp256k1/archive/{UPSTREAM_REF}.tar.gz'


# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.', 2)[:2]] < [3, 3]:
    raise SystemExit(
        'Your setuptools version ({}) is too old to correctly install this '
        'package. Please upgrade to a newer version (>= 3.3).'.format(setuptools_version)
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
        download_library(self)

        _egg_info.run(self)


class sdist(_sdist):
    def run(self):
        download_library(self, force=True)
        _sdist.run(self)


if _bdist_wheel:

    class bdist_wheel(_bdist_wheel):
        def run(self):
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
        download_library(self)

        return [
            os.path.join(root, filename)
            for root, _, filenames in os.walk(LIB_NAME)
            for filename in filenames
        ]

    def build_libraries(self, libraries):
        raise NotImplementedError('build_libraries')

    def check_library_list(self, libraries):
        raise NotImplementedError('check_library_list')

    def get_library_names(self):
        return build_flags(LIB_NAME, 'l', os.path.join(os.path.abspath(self.build_clib), 'lib', 'pkgconfig'))

    def run(self):
        cwd = pathlib.Path().absolute()

        if has_system_lib():
            log.info('Using system library')
            return

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
        bash = find_conda_executable('bash') or find_conda_executable('sh') or 'bash'
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

if BUILDING_FOR_WINDOWS:

    class Distribution(_Distribution):
        def is_pure(self):
            return False

    package_data['coincurve'].append(f'{LIB_NAME}.dll')
    setup_kwargs = dict()
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
    version='18.0.0',

    description=f'Cross-platform Python CFFI bindings for {LIB_NAME}',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author_email='Ofek Lev <oss@ofek.dev>',
    license='MIT OR Apache-2.0',

    python_requires='>=3.7',
    install_requires=['asn1crypto', 'cffi>=1.3.0'],

    packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', LIB_NAME, 'tests')),
    package_data=package_data,

    distclass=Distribution,
    zip_safe=False,

    project_urls={
        'Documentation': 'https://ofek.dev/coincurve/',
        'Issues': 'https://github.com/ofek/coincurve/issues',
        'Source': 'https://github.com/ofek/coincurve',
    },
    keywords=[
        'secp256k1',
        'crypto',
        'elliptic curves',
        'bitcoin',
        'ethereum',
        'cryptocurrency',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries',
        'Topic :: Security :: Cryptography',
    ],
    **setup_kwargs
)
