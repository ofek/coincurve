import argparse
import logging
import os
from collections import namedtuple
from typing import List

from cffi import FFI

logging.basicConfig(level=logging.INFO)

here = os.path.dirname(os.path.abspath(__file__))

Source = namedtuple('Source', ('h', 'include'))


def gather_sources_from_directory(directory: str) -> List[Source]:
    """
    Gather source files from a given directory.

    :param directory: The directory where source files are located.
    :return: A list of Source namedtuples.
    """
    sources = []
    for filename in os.listdir(directory):
        if filename.endswith('.h'):
            include_line = f'#include <{filename}>'
            sources.append(Source(filename, include_line))
    return sorted(sources)


define_static_lib = """
#if defined(_WIN32)
#   define SECP256K1_STATIC 1
#   define SECP256K1_API extern __declspec(dllexport)
#endif
"""

define_shared_lib = """
#if defined(_WIN32)
#   define SECP256K1_API extern __declspec(dllimport)
#endif
"""


def mk_ffi(sources: List[Source],
           static_lib: str = '0',
           name: str = '_libsecp256k1') -> FFI:
    """
    Create an FFI object.

    :param sources: A list of Source namedtuples.
    :param libraries: A list of libraries to link against.
    :param static_lib: Whether to generate a static lib in Windows.
    :param name: The name of the FFI object.
    :return: An FFI object.
    """
    _ffi = FFI()
    code = [define_static_lib] if static_lib == '1' else [define_shared_lib]

    for source in sources:
        with open(os.path.join(here, source.h)) as h:
            logging.info(f'   Including {source.h}...')
            c_header = h.read().replace('SECP256K1_API', '')
            _ffi.cdef(c_header)

        code.append(source.include)

    code.append('#define PY_USE_BUNDLED')
    _ffi.set_source(name, '\n'.join(code))

    return _ffi


if __name__ == '__main__':
    logging.info('Starting CFFI build process...')
    parser = argparse.ArgumentParser(description='Generate C code using CFFI.')
    parser.add_argument('c_file', help='Generated C code filename.')
    parser.add_argument('static_lib', help='Generate static lib in Windows.', default=False)
    args = parser.parse_args()

    modules = gather_sources_from_directory(here)
    ffi = mk_ffi(modules, args.static_lib)
    ffi.emit_c_code(args.c_file)
    logging.info(f'   Generated C code: {args.c_file}')
