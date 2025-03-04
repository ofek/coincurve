from __future__ import annotations

from collections.abc import Callable

from coincurve._libsecp256k1 import ffi

Hasher = Callable[[bytes], bytes] | None
Nonce = tuple[ffi.CData, ffi.CData]
