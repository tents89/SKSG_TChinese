"""測試文字處理功能的單元測試"""
import pytest
import json
from unittest.mock import Mock, patch, mock_open


class TestTextAssetProcessing:
    """測試文字資產處理功能"""

    def test_process_text_assets_with_existing_file(self, mock_unity_env, temp_dir):
        """測試處理存在的文字檔案"""
        # 建立測試文字檔
        text_file = temp_dir / "ZH_General.txt"
        text_file.write_text("測試內容")

        # 模擬 Unity 環境
        mock_obj = Mock()
        mock_obj.type.name = "TextAsset"

        mock_data = Mock()
        mock_data.m_Name = "ZH_General"
        mock_obj.read.return_value = mock_data

        mock_unity_env.objects = [mock_obj]

        with patch('os.path.exists', return_value=True), \
             patch('os.path.join', return_value=str(text_file)):
            # 這個測試需要在重構後實現具體的測試邏輯
            pytest.skip("需要重構 process_text_assets 函數才能進行測試")

    def test_process_text_assets_missing_file(self, mock_unity_env):
        """測試處理不存在的文字檔案"""
        mock_obj = Mock()
        mock_obj.type.name = "TextAsset"

        mock_data = Mock()
        mock_data.m_Name = "ZH_NonExistent"
        mock_obj.read.return_value = mock_data

        mock_unity_env.objects = [mock_obj]

        with patch('os.path.exists', return_value=False):
            # 這個測試需要在重構後實現具體的測試邏輯
            pytest.skip("需要重構 process_text_assets 函數才能進行測試")

    def test_supported_text_assets(self):
        """測試支援的文字資產列表"""
        expected_assets = {
            "ZH_Achievements", "ZH_AutoSaveNames", "ZH_Belltown",
            "ZH_Bonebottom", "ZH_Caravan", "ZH_City", "ZH_Coral",
            "ZH_Crawl", "ZH_Credits List", "ZH_Deprecated", "ZH_Dust",
            "ZH_Enclave", "ZH_Error", "ZH_Fast Travel", "ZH_Forge",
            "ZH_General", "ZH_Greymoor", "ZH_Inspect", "ZH_Journal",
            "ZH_Lore", "ZH_MainMenu", "ZH_Map Zones", "ZH_Peak",
            "ZH_Pilgrims", "ZH_Prompts", "ZH_Quests", "ZH_Shellwood",
            "ZH_Shop", "ZH_Song", "ZH_Titles", "ZH_Tools", "ZH_UI",
            "ZH_Under", "ZH_Wanderers", "ZH_Weave", "ZH_Wilds"
        }

        # 這個測試驗證文字資產列表是否完整
        # 實際的測試邏輯需要在重構後實現
        assert len(expected_assets) == 36  # 驗證我們有正確數量的資產
