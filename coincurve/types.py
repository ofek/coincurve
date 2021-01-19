import sys
from typing import Optional

# https://bugs.python.org/issue42965
if sys.version_info >= (3, 9, 2):
    from collections.abc import Callable
else:
    from typing import Callable

Hasher = Optional[Callable[[bytes], bytes]]
