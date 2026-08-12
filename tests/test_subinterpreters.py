from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

interpreters: ModuleType | None
legacy_interpreters: ModuleType | None
low_level_interpreters: ModuleType | None

try:
    interpreters = importlib.import_module("concurrent.interpreters")
except ModuleNotFoundError:
    interpreters = None
    try:
        legacy_interpreters = importlib.import_module("_xxsubinterpreters")
    except ModuleNotFoundError:
        legacy_interpreters = None
        low_level_interpreters = pytest.importorskip("_interpreters")
    else:
        low_level_interpreters = None
else:
    legacy_interpreters = None
    low_level_interpreters = None


def test_repeated_subinterpreter_import_and_teardown() -> None:
    script = "from coincurve import PrivateKey; key = PrivateKey(bytes.fromhex('00' * 31 + '01')); assert key.public_key.verify(key.sign(b'x'), b'x')"
    for _ in range(5):
        if interpreters is not None:
            interpreter = interpreters.create()
            try:
                interpreter.exec(script)
            finally:
                interpreter.close()
        elif legacy_interpreters is not None:
            interpreter = legacy_interpreters.create()
            try:
                legacy_interpreters.run_string(interpreter, script)
            finally:
                legacy_interpreters.destroy(interpreter)
        else:
            assert low_level_interpreters is not None
            interpreter = low_level_interpreters.create()
            try:
                low_level_interpreters.exec(interpreter, script)
            finally:
                low_level_interpreters.destroy(interpreter)
