import os
from importlib import import_module
from importlib.util import find_spec
from unittest.mock import patch

import pytest

import coincurve

# These tests will be run on the installed package. The module
# _secp256k1_library_info.py does not exist in the dist source code,
# but it may exist in the installed package and we need to test the
# behavior of the library loading in that case.

# This requires to have conditional statement in the tests


def test_secp256k1_library_info_exists():
    """Test _secp256k1_library_info.py file has correct information."""
    if find_spec('coincurve._secp256k1_library_info'):
        # This test is run on the installed package, so the file may exist
        # Verify that the information is as expected: Only EXTERNAL and a dynamic library
        _secp256k1_library_info = import_module('coincurve._secp256k1_library_info')

        assert 'secp256k1' in _secp256k1_library_info.SECP256K1_LIBRARY_NAME
        assert any(ext in _secp256k1_library_info.SECP256K1_LIBRARY_NAME for ext in ('dll', 'so', 'dylib'))
        assert _secp256k1_library_info.SECP256K1_LIBRARY_TYPE == 'EXTERNAL'


def test_secp256k1_library_info_does_not_exists():
    """Test _secp256k1_library_info.py file has correct information."""
    if not find_spec('coincurve._secp256k1_library_info'):
        with pytest.raises(ImportError):
            import coincurve

            coincurve.load_secp256k1_conda_library()


@patch('ctypes.CDLL')
@patch('ctypes.util.find_library', return_value=None)
def test_load_secp256k1_conda_library_internal(mock_find_library, mock_cdll):
    """Test loading the secp256k1 library."""
    if not find_spec('coincurve._secp256k1_library_info'):
        with pytest.raises(ImportError):
            coincurve.load_secp256k1_conda_library()
    else:
        with patch('coincurve._secp256k1_library_info.SECP256K1_LIBRARY_TYPE', 'INTERNAL'):
            coincurve.load_secp256k1_conda_library()
            mock_find_library.assert_not_called()
            mock_cdll.assert_not_called()


@patch('ctypes.CDLL')
@patch('ctypes.util.find_library', return_value=None)
def test_load_secp256k1_conda_library_external_nolib(mock_find_library, mock_cdll):
    """Test loading the secp256k1 library."""
    import coincurve

    if not find_spec('coincurve._secp256k1_library_info'):
        with pytest.raises(ImportError):
            coincurve.load_secp256k1_conda_library()
    else:
        with patch('coincurve._secp256k1_library_info.SECP256K1_LIBRARY_TYPE', 'EXTERNAL'):
            with patch('coincurve._secp256k1_library_info.SECP256K1_LIBRARY_NAME', 'libname.so'):
                with patch('os.getenv', return_value=None):
                    assert os.getenv('CONDA_PREFIX') is None
                    with pytest.raises(RuntimeError):
                        coincurve.load_secp256k1_conda_library()
                    mock_find_library.assert_called_once_with('libname.so')
                    mock_cdll.assert_not_called()


@patch('ctypes.CDLL')
@patch('ctypes.util.find_library', return_value=None)
def test_load_secp256k1_conda_library(mock_find_library, mock_cdll):
    """Test loading the secp256k1 library."""
    import coincurve

    if not find_spec('coincurve._secp256k1_library_info'):
        with pytest.raises(ImportError):
            coincurve.load_secp256k1_conda_library()
    else:
        with patch('coincurve._secp256k1_library_info.SECP256K1_LIBRARY_TYPE', 'EXTERNAL'):
            with patch('coincurve._secp256k1_library_info.SECP256K1_LIBRARY_NAME', 'libname.so'):
                with patch('os.getenv', return_value='/path/to/libname'):
                    assert os.getenv('CONDA_PREFIX') == '/path/to/libname'
                    coincurve.load_secp256k1_conda_library()
                    mock_find_library.assert_called_once_with('libname.so')
                    mock_cdll.assert_called_once()
                    assert '/path/to/libname' in mock_cdll.call_args[0][0]
                    assert 'libname.so' in mock_cdll.call_args[0][0]
