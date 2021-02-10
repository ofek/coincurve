# Installation

-----

`coincurve` is available on PyPI and can be installed with [pip](https://pip.pypa.io):

```
pip install coincurve
```

## Wheel

Binary wheels are available for most platforms and require at least version `19.3` of pip to install.

| | | | | | | |
| --- | --- | --- | --- | --- | --- | --- |
| | 3.6 | 3.7 | 3.8 | 3.9 | PyPy3.6 7.3.3 | PyPy3.7 7.3.3 |
| Linux (x86_64) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Linux (AArch64) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Linux (x86) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Windows (x86_64) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | | |
| Windows (x86) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | | |
| macOS (x86_64) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | | |

## Source

If you are on a platform without support for pre-compiled wheels, you will need certain system packages in order to build from source.

A few environment variables influence the build:

- `COINCURVE_UPSTREAM_REF` - This is the Git reference of [libsecp256k1][] to use rather than the (frequently updated) default.
- `COINCURVE_IGNORE_SYSTEM_LIB` - The presence of this will force fetching of [libsecp256k1][] even if it's already detected at the system level.

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
