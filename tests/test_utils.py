from coincurve import verify_signature
from coincurve.utils import chunk_data, der_to_pem, pem_to_der


def test_der_conversion(samples):
    assert pem_to_der(der_to_pem(samples["PRIVATE_KEY_DER"])) == samples["PRIVATE_KEY_DER"]


def test_verify_signature(samples):
    assert verify_signature(samples["SIGNATURE"], samples["MESSAGE"], samples["PUBLIC_KEY_COMPRESSED"])
    assert verify_signature(samples["SIGNATURE"], samples["MESSAGE"], samples["PUBLIC_KEY_UNCOMPRESSED"])


def test_chunk_data():
    assert list(chunk_data("4fadd1977328c11efc1c1d8a781aa6b9677984d3e0b", 2)) == [
        "4f",
        "ad",
        "d1",
        "97",
        "73",
        "28",
        "c1",
        "1e",
        "fc",
        "1c",
        "1d",
        "8a",
        "78",
        "1a",
        "a6",
        "b9",
        "67",
        "79",
        "84",
        "d3",
        "e0",
        "b",
    ]
