from coincurve import PrivateKey, PublicKey, verify_signature


def test_verify_signature_util(benchmark, samples):
    signature = samples['SIGNATURE']
    message = samples['MESSAGE']
    public_key = samples['PUBLIC_KEY_COMPRESSED']
    benchmark(verify_signature, signature, message, public_key)


def test_private_key_new(benchmark):
    benchmark(PrivateKey)


def test_private_key_load(benchmark, samples):
    benchmark(PrivateKey, samples['PRIVATE_KEY_BYTES'])


def test_private_key_sign(benchmark, samples):
    private_key = PrivateKey(samples['PRIVATE_KEY_BYTES'])
    benchmark(private_key.sign, samples['MESSAGE'])


def test_private_key_sign_recoverable(benchmark, samples):
    private_key = PrivateKey(samples['PRIVATE_KEY_BYTES'])
    benchmark(private_key.sign_recoverable, samples['MESSAGE'])


def test_private_key_ecdh(benchmark, samples):
    private_key = PrivateKey(samples['PRIVATE_KEY_BYTES'])
    benchmark(private_key.ecdh, samples['PUBLIC_KEY_COMPRESSED'])


def test_public_key_load(benchmark, samples):
    benchmark(PublicKey, samples['PUBLIC_KEY_COMPRESSED'])


def test_public_key_load_from_valid_secret(benchmark, samples):
    benchmark(PublicKey.from_valid_secret, samples['PRIVATE_KEY_BYTES'])


def test_public_key_format(benchmark, samples):
    public_key = PublicKey(samples['PUBLIC_KEY_COMPRESSED'])
    benchmark(public_key.format)


def test_public_key_point(benchmark, samples):
    public_key = PublicKey(samples['PUBLIC_KEY_COMPRESSED'])
    benchmark(public_key.point)


def test_public_key_verify(benchmark, samples):
    public_key = PublicKey(samples['PUBLIC_KEY_COMPRESSED'])
    benchmark(public_key.verify, samples['SIGNATURE'], samples['MESSAGE'])


if __name__ == '__main__':
    import pytest

    pytest.main(['-s', __file__])
