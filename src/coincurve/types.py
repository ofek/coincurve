from __future__ import annotations

from collections.abc import Callable

Hasher = Callable[[bytes], bytes]
