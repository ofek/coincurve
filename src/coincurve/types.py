from __future__ import annotations

import sys

from coincurve._libsecp256k1 import ffi

# https://bugs.python.org/issue42965
if sys.version_info >= (3, 9, 2):
    from collections.abc import Callable
else:
    from typing import Callable

Hasher = Callable[[bytes], bytes] | None
Nonce = tuple[ffi.CData, ffi.CData]
