from __future__ import annotations

from base64 import b64decode, b64encode
from hashlib import sha256 as _sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import NoReturn

MSG_HASH_SIZE = 32
PEM_HEADER = b"-----BEGIN PRIVATE KEY-----\n"
PEM_FOOTER = b"-----END PRIVATE KEY-----\n"


def sha256(bytestr: bytes) -> bytes:
    return _sha256(bytestr).digest()


def _raise_buffer_type_error(name: str) -> NoReturn:
    msg = f"{name} must be a one-dimensional C-contiguous readable buffer"
    raise TypeError(msg) from None


def _as_bytes(data: bytes | bytearray | memoryview, name: str) -> bytes:
    try:
        view = memoryview(data)
    except TypeError:
        _raise_buffer_type_error(name)
    if view.ndim != 1 or not view.c_contiguous:
        _raise_buffer_type_error(name)
    return data if type(data) is bytes else bytes(view)


def int_to_bytes(num: int) -> bytes:
    return num.to_bytes((num.bit_length() + 7) // 8 or 1, "big")


def chunk_data(data: bytes, size: int) -> Generator[bytes, None, None]:
    return (data[i : i + size] for i in range(0, len(data), size))


def der_to_pem(der: bytes) -> bytes:
    return b"".join([PEM_HEADER, b"\n".join(chunk_data(b64encode(der), 64)), b"\n", PEM_FOOTER])


def pem_to_der(pem: bytes | bytearray | memoryview) -> bytes:
    lines = _as_bytes(pem, "PEM data").strip().splitlines()
    if len(lines) < 3 or lines[0] != PEM_HEADER.strip() or lines[-1] != PEM_FOOTER.strip():  # noqa: PLR2004
        msg = "Invalid PEM: expected a PKCS#8 private key"
        raise ValueError(msg)
    try:
        return b64decode(b"".join(lines[1:-1]), validate=True)
    except ValueError:
        msg = "Invalid PEM: private key data is not valid base64"
        raise ValueError(msg) from None
