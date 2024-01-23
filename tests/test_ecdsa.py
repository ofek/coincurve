import os
import sys

from coincurve.ecdsa import cdata_to_der, der_to_cdata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.samples import SIGNATURE  # noqa: E402


def test_der():
    assert cdata_to_der(der_to_cdata(SIGNATURE)) == SIGNATURE
