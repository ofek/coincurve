from typing import Callable, Optional

Hasher = Optional[Callable[[bytes], bytes]]
