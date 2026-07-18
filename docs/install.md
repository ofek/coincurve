# Installation

-----

`coincurve` is available on PyPI and can be installed with [pip](https://pip.pypa.io):

```
pip install coincurve
```

## Wheel

Binary wheels are available for most platforms. An up-to-date version of pip is recommended,
particularly when installing free-threaded wheels.

| | | | | |
| --- | --- | --- | --- | --- |
| | macOS | Windows | Linux (glibc) | Linux (musl) |
| CPython 3.9 | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> |
| CPython 3.10 | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> |
| CPython 3.11 | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> |
| CPython 3.12 | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> |
| CPython 3.13 | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> |
| CPython 3.14 | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> |
| CPython 3.14t (free-threaded) | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>ARM64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> | <ul><li>x86_64</li><li>i686</li><li>AArch64</li></ul> |

The x86-64 macOS wheels require macOS 10.15 or later. Python 3.15 prereleases, including
free-threaded builds, are supported through source installation; binary wheels will be added
after Python 3.15 reaches release candidate status.

## Source

If you are on a platform without support for pre-compiled wheels, you will need certain system packages in order to build from source.

A few environment variables influence the build:

- `COINCURVE_UPSTREAM_REF` - This is the Git reference of [libsecp256k1][] to use rather than the (frequently updated) default.
- `COINCURVE_IGNORE_SYSTEM_LIB` - Setting this to `ON` forces fetching of [libsecp256k1][] even if it is detected at the system level.
- `COINCURVE_SECP256K1_STATIC` - Setting this to `OFF` builds the vendored [libsecp256k1][] as a shared library.
- `COINCURVE_VENDOR_CFFI` - Setting this to anything other than `1` (the default) prevents vendoring of the `_cffi_backend` module and its license. Re-distributors must add `cffi` as a runtime dependency when disabling this.

!!! tip
    To avoid installing the binary wheels on compatible distributions, use the `--no-binary` option.

    ```
    pip install coincurve --no-binary coincurve
    ```

### Alpine

```
sudo apk add autoconf automake build-base libffi-dev libtool pkgconfig python3-dev
```

### Debian/Ubuntu

```
sudo apt-get install -y autoconf automake build-essential libffi-dev libtool pkg-config python3-dev
```

### RHEL/CentOS

```
sudo yum install -y autoconf automake gcc gcc-c++ libffi-devel libtool make pkgconfig python3-devel
```

### macOS

```
xcode-select --install
brew install autoconf automake libffi libtool pkg-config python
```
