"""共用測試設定和 fixtures"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def temp_dir():
    """建立臨時測試目錄"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_game_structure(temp_dir):
    """建立模擬的遊戲目錄結構"""
    game_root = temp_dir / "game"
    game_root.mkdir()

    # Windows 結構
    data_path = game_root / "Hollow Knight Silksong_Data"
    data_path.mkdir()

    streaming_assets = data_path / "StreamingAssets" / "aa" / "StandaloneWindows64"
    streaming_assets.mkdir(parents=True)

    # 建立假的 bundle 檔案
    bundle_file = streaming_assets / "fonts_assets_chinese.bundle"
    bundle_file.write_bytes(b"fake bundle data")

    # 建立假的 title bundle
    title_path = streaming_assets / "atlases_assets_assets" / "sprites" / "_atlases"
    title_path.mkdir(parents=True)
    title_bundle = title_path / "title.spriteatlas.bundle"
    title_bundle.write_bytes(b"fake title bundle")

    # 建立假的 resources.assets
    resources = data_path / "resources.assets"
    resources.write_bytes(b"fake resources data")

    return {
        "game_root": game_root,
        "data_path": data_path,
        "bundle_file": bundle_file,
        "title_bundle": title_bundle,
        "resources": resources
    }


@pytest.fixture
def mock_cht_data(temp_dir):
    """建立模擬的 CHT 資料夾結構"""
    cht_root = temp_dir / "CHT"
    cht_root.mkdir()

    # Font 資料夾
    font_path = cht_root / "Font"
    font_path.mkdir()
    font_json = font_path / "chinese_body.json"
    font_json.write_text('{"m_fontInfo": {"Name": "test"}, "m_glyphInfoList": []}')

    # Png 資料夾
    png_path = cht_root / "Png"
    png_path.mkdir()

    # Text 資料夾
    text_path = cht_root / "Text"
    text_path.mkdir()
    text_file = text_path / "ZH_General.txt"
    text_file.write_text("測試文字內容")

    return {
        "cht_root": cht_root,
        "font_path": font_path,
        "png_path": png_path,
        "text_path": text_path
    }


@pytest.fixture
def mock_unity_env():
    """建立模擬的 UnityPy 環境"""
    env = Mock()
    env.file = Mock()
    env.file.save.return_value = b"saved unity data"

    # 模擬物件
    mock_obj = Mock()
    mock_obj.type.name = "MonoBehaviour"

    mock_data = Mock()
    mock_data.m_Name = "chinese_body"
    mock_obj.read.return_value = mock_data

    env.objects = [mock_obj]

    return env


@pytest.fixture
def mock_file_wrapper():
    """建立模擬的 FileWrapper"""
    from io import BytesIO

    class MockFileWrapper:
        def __init__(self, original_file, new_data_stream):
            self._original = original_file
            self._stream = new_data_stream

        @property
        def Length(self):
            return len(self._stream.getbuffer())

        @property
        def Position(self):
            return self._stream.tell()

        @Position.setter
        def Position(self, value):
            self._stream.seek(value)

        def read_bytes(self, length):
            return self._stream.read(length)

        def save(self):
            self.Position = 0
            data = self._stream.read()
            self.Position = 0  # 讀取後重設位置
            return data

    return MockFileWrapper
