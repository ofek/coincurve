from __future__ import annotations

import os
import sys
import sysconfig


def main() -> None:
    version = sys.version_info
    if version[:2] != (3, 15):
        message = f"Expected Python 3.15, found {sys.version}"
        raise RuntimeError(message)

    expected_free_threaded = os.environ["EXPECTED_FREE_THREADED"] == "true"
    free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    if free_threaded != expected_free_threaded:
        message = f"Expected free-threaded={expected_free_threaded}, found free-threaded={free_threaded}"
        raise RuntimeError(message)

    print(sys.version)
    print(f"free-threaded={free_threaded}")


if __name__ == "__main__":
    main()
