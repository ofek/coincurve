import pytest

from coincurve.ecdsa import cdata_to_der, der_to_cdata


def test_der(samples):
    assert cdata_to_der(der_to_cdata(samples["SIGNATURE"])) == samples["SIGNATURE"]


if __name__ == "__main__":
    pytest.main(["-s", __file__])
