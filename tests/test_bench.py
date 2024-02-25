from coincurve import PrivateKey, PublicKey, verify_signature


def test_verify_signature_util(benchmark, samples):
    signature = samples.get('SIGNATURE')
    message = samples.get('MESSAGE')
    public_key = samples.get('PUBLIC_KEY_COMPRESSED')
    benchmark(verify_signature, signature, message, public_key)


def test_private_key_new(benchmark):
    benchmark(PrivateKey)


def test_private_key_load(benchmark, samples):
    benchmark(PrivateKey, samples.get('PRIVATE_KEY_BYTES'))


def test_private_key_sign(benchmark, samples):
    private_key = PrivateKey(samples.get('PRIVATE_KEY_BYTES'))
    benchmark(private_key.sign, samples.get('MESSAGE'))


def test_private_key_sign_recoverable(benchmark, samples):
    private_key = PrivateKey(samples.get('PRIVATE_KEY_BYTES'))
    benchmark(private_key.sign_recoverable, samples.get('MESSAGE'))


def test_private_key_ecdh(benchmark, samples):
    private_key = PrivateKey(samples.get('PRIVATE_KEY_BYTES'))
    benchmark(private_key.ecdh, samples.get('PUBLIC_KEY_COMPRESSED'))


def test_public_key_load(benchmark, samples):
    benchmark(PublicKey, samples.get('PUBLIC_KEY_COMPRESSED'))


def test_public_key_load_from_valid_secret(benchmark, samples):
    benchmark(PublicKey.from_valid_secret, samples.get('PRIVATE_KEY_BYTES'))


def test_public_key_format(benchmark, samples):
    public_key = PublicKey(samples.get('PUBLIC_KEY_COMPRESSED'))
    benchmark(public_key.format)


def test_public_key_point(benchmark, samples):
    public_key = PublicKey(samples.get('PUBLIC_KEY_COMPRESSED'))
    benchmark(public_key.point)


def test_public_key_verify(benchmark, samples):
    public_key = PublicKey(samples.get('PUBLIC_KEY_COMPRESSED'))
    benchmark(public_key.verify, samples.get('SIGNATURE'), samples.get('MESSAGE'))


if __name__ == '__main__':
    import pytest

    pytest.main(['-s', __file__])
