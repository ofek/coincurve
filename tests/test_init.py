import os
from importlib import import_module
from unittest import mock

import pytest

import coincurve


def test_secp256k1_library_info_exists():
    # Check if the _secp256k1_library_info.py file exists in the installed package
    file_path = os.path.join(os.path.dirname(coincurve.__file__), '_secp256k1_library_info.py')

    if os.path.exists(file_path):
        # This test is run on the installed package, so the file may exist
        # Verify that the information is as expected: Only EXTERNAL and a dynamic library
        _secp256k1_library_info = import_module('coincurve._secp256k1_library_info')

        # import logging
        # logging.warning(f'info: {_secp256k1_library_info.SECP256K1_LIBRARY_NAME}')

        assert 'secp256k1' in _secp256k1_library_info.SECP256K1_LIBRARY_NAME
        assert any(ext in _secp256k1_library_info.SECP256K1_LIBRARY_NAME for ext in ('dll', 'so', 'dylib'))
        assert _secp256k1_library_info.SECP256K1_LIBRARY_TYPE == 'EXTERNAL'

    else:
        # If the file does not exist, test the load_secp256k1_conda_library function
        with mock.patch('importlib.import_module') as mock_import_module:
            mock_import_module.side_effect = ImportError

            # Verify that the function does not raise an exception
            try:
                coincurve.load_secp256k1_conda_library()
            except Exception:
                pytest.fail('load_secp256k1_conda_library() raised an exception')

            # Verify that the import was called
            mock_import_module.assert_called_once_with('coincurve._secp256k1_library_info')
