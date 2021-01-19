from typing import Callable, Optional

# https://bugs.python.org/issue42965
Hasher = Optional[Callable[[bytes], bytes]]
