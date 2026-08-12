from __future__ import annotations

import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor

import pytest

from coincurve import PrivateKey

PRIVATE_KEY = PrivateKey(bytes.fromhex("00" * 31 + "01"))


def sign_and_verify(seed: int) -> bool:
    message = f"message-{seed}".encode()
    signature = PRIVATE_KEY.sign(message)
    return PRIVATE_KEY.public_key.verify(signature, message)


def test_import_does_not_enable_gil():
    if not sysconfig.get_config_var("Py_GIL_DISABLED"):
        pytest.skip("requires free-threaded CPython")
    assert not sys._is_gil_enabled()  # noqa: SLF001


def test_concurrent_operations_with_shared_key_and_context():
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert all(executor.map(sign_and_verify, range(1, 129)))
