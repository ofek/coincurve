from __future__ import annotations

import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor

import pytest

from coincurve import PrivateKey

pytestmark = pytest.mark.skipif(
    not sysconfig.get_config_var("Py_GIL_DISABLED"),
    reason="requires free-threaded CPython",
)


def sign_and_verify(seed: int) -> bool:
    private_key = PrivateKey(seed.to_bytes(32, "big"))
    message = f"message-{seed}".encode()
    signature = private_key.sign(message)
    return private_key.public_key.verify(signature, message)


def test_import_does_not_enable_gil():
    assert not sys._is_gil_enabled()  # noqa: SLF001


def test_concurrent_operations_with_shared_context():
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert all(executor.map(sign_and_verify, range(1, 129)))
