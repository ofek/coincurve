from setuptools import setup, find_packages


setup(
    name="coincurve",
    version="0.1.0",

    description='Cross-platform Python CFFI bindings for libsecp256k1',
    long_description=open('README.md', 'r').read(),
    author='Ofek Lev',
    author_email='ofekmeister@gmail.com',
    maintainer='Ofek Lev',
    maintainer_email='ofekmeister@gmail.com',
    url='https://github.com/ofek/coincurve',
    download_url='https://github.com/ofek/coincurve',
    license='MIT',

    setup_requires=['cffi>=1.3.0'],
    install_requires=['cffi>=1.3.0'],
    tests_require=['pytest'],

    packages=find_packages(exclude=('_cffi_build', '_cffi_build.*', 'libsecp256k1')),
    cffi_modules=[
        "_cffi_build/build.py:ffi"
    ],
    zip_safe=False,

    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries",
        "Topic :: Security :: Cryptography"
    ]
)
