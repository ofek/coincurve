from __future__ import annotations

import argparse
import logging
import os
from typing import NamedTuple

from cffi import FFI

logging.basicConfig(level=logging.INFO)

here = os.path.dirname(os.path.abspath(__file__))


class Source(NamedTuple):
    h: str
    include: str


def gather_sources_from_directory(directory: str) -> list[Source]:
    """
    Gather source files from a given directory.

    :param directory: The directory where source files are located.
    :return: A list of Source namedtuples.
    """
    sources = []
    for filename in os.listdir(directory):
        if filename.endswith(".h"):
            include_line = f"#include <{filename}>"
            sources.append(Source(filename, include_line))
    return sorted(sources)


define_static_lib = """
#if defined(_WIN32) || defined(_WIN32) || defined(__WIN32__) || defined(__NT__)
#   define SECP256K1_STATIC 1
#endif
"""


def mk_ffi(
    directory: str,
    sources: list[Source],
    static_lib: bool = False,  # noqa: FBT001, FBT002
    name: str = "_libsecp256k1",
) -> FFI:
    """
    Create an FFI object.

    :param sources: A list of Source namedtuples.
    :param static_lib: Whether to generate a static lib in Windows.
    :param name: The name of the FFI object.
    :return: An FFI object.
    """
    _ffi = FFI()
    code = [define_static_lib] if static_lib else []

    logging.info("   Static %s...", static_lib)
    for source in sources:
        with open(os.path.join(directory, source.h), encoding="utf-8") as h:
            logging.info("   Including %s...", source.h)
            c_header = h.read()
            _ffi.cdef(c_header)

        code.append(source.include)

    code.append("#define PY_USE_BUNDLED")
    _ffi.set_source(name, "\n".join(code))

    return _ffi


if __name__ == "__main__":
    logging.info("Starting CFFI build process...")
    parser = argparse.ArgumentParser(description="Generate C code using CFFI.")
    parser.add_argument("headers_dir", help="Path to the header files.", type=str)
    parser.add_argument("c_file", help="Generated C code filename.", type=str)
    parser.add_argument("static_lib", help="Generate static lib in Windows.", default="0N", type=str)
    args = parser.parse_args()

    modules = gather_sources_from_directory(args.headers_dir)
    ffi = mk_ffi(args.headers_dir, modules, args.static_lib == "ON")
    ffi.emit_c_code(args.c_file)

    vendor_cffi = os.environ.get("COINCURVE_VENDOR_CFFI", "1") == "1"
    if vendor_cffi:
        with open(args.c_file, encoding="utf-8") as f:
            source = f.read()

        expected_text = 'PyImport_ImportModule("_cffi_backend")'
        if expected_text not in source:
            msg = f"{expected_text} not found in {args.c_file}"
            raise ValueError(msg)

        new_source = source.replace(expected_text, 'PyImport_ImportModule("coincurve._cffi_backend")')
        with open(args.c_file, "w", encoding="utf-8") as f:
            f.write(new_source)

    logging.info("   Generated C code: %s", args.c_file)
