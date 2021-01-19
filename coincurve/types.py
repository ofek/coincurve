import sys
from typing import Optional

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable


Hasher = Optional[Callable[[bytes], bytes]]
