"""測試 FileWrapper 類別的功能"""
import pytest
from io import BytesIO
from unittest.mock import Mock


def test_file_wrapper_basic_properties(mock_file_wrapper):
    """測試 FileWrapper 的基本屬性"""
    original_file = Mock()
    test_data = b"test data"
    stream = BytesIO(test_data)

    wrapper = mock_file_wrapper(original_file, stream)

    assert wrapper.Length == len(test_data)
    assert wrapper.Position == 0


def test_file_wrapper_position_manipulation(mock_file_wrapper):
    """測試 FileWrapper 的位置操作"""
    original_file = Mock()
    test_data = b"test data for position testing"
    stream = BytesIO(test_data)

    wrapper = mock_file_wrapper(original_file, stream)

    # 測試設定位置
    wrapper.Position = 5
    assert wrapper.Position == 5

    # 測試讀取
    read_data = wrapper.read_bytes(4)
    assert read_data == b"data"
    assert wrapper.Position == 9


def test_file_wrapper_save(mock_file_wrapper):
    """測試 FileWrapper 的儲存功能"""
    original_file = Mock()
    test_data = b"data to save"
    stream = BytesIO(test_data)

    wrapper = mock_file_wrapper(original_file, stream)

    # 移動位置然後儲存
    wrapper.Position = 5
    saved_data = wrapper.save()

    assert saved_data == test_data
    assert wrapper.Position == 0  # save 後位置應該重設為 0
