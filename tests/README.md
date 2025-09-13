# 測試說明

這個測試套件為 SKSG Traditional Chinese 專案提供全面的測試覆蓋。

## 測試結構

```
tests/
├── conftest.py              # 共用測試配置和 fixtures
├── unit/                    # 單元測試
│   ├── test_file_wrapper.py        # FileWrapper 類別測試
│   ├── test_utility_functions.py   # 工具函數測試
│   ├── test_text_processing.py     # 文字處理測試
│   ├── test_font_processing.py     # 字型處理測試
│   ├── test_texture_processing.py  # 紋理處理測試
│   └── test_material_processing.py # 材質處理測試
├── integration/             # 整合測試
│   ├── test_modding_workflow.py    # 完整工作流程測試
│   └── test_cli_interface.py       # CLI 介面測試
└── README.md               # 本文件
```

## 執行測試

### 使用 uv (推薦)

```bash
# 執行所有測試
uv run pytest tests/

# 只執行單元測試
uv run pytest tests/unit/

# 只執行整合測試  
uv run pytest tests/integration/

# 執行測試並產生覆蓋率報告
uv run pytest tests/ --cov=src --cov-report=html

# 執行特定測試檔案
uv run pytest tests/unit/test_file_wrapper.py

# 執行特定測試函數
uv run pytest tests/unit/test_file_wrapper.py::test_file_wrapper_basic_properties
```

### 使用傳統 pip

```bash
# 執行所有測試
python -m pytest tests/

# 其他指令類似，只需將 uv run 替換為 python -m
```

## 測試標記

- `@pytest.mark.unit`: 單元測試
- `@pytest.mark.integration`: 整合測試  
- `@pytest.mark.slow`: 較慢的測試
- `@pytest.mark.skipif`: 條件性跳過的測試

### 執行特定標記的測試

```bash
# 只執行單元測試
uv run pytest -m unit

# 跳過慢速測試
uv run pytest -m "not slow"

# 只執行整合測試
uv run pytest -m integration
```

## Fixtures

### 通用 Fixtures

- `temp_dir`: 提供臨時測試目錄
- `mock_game_structure`: 模擬遊戲目錄結構
- `mock_cht_data`: 模擬 CHT 資料夾結構
- `mock_unity_env`: 模擬 UnityPy 環境
- `mock_file_wrapper`: 模擬 FileWrapper 類別

## 重構需求

目前大部分測試使用 `pytest.skip()` 標記為跳過，因為需要先重構 `sk_cht.py` 為模組化結構。

### 重構建議

1. **分離核心邏輯**: 將 `sk_cht.py` 中的函數分離到獨立模組
2. **建立類別結構**: 為主要功能建立類別
3. **依賴注入**: 使用依賴注入提高可測試性
4. **配置管理**: 將硬編碼的配置移到配置檔案

### 重構後的測試結構建議

```python
# src/sksg_tchinese/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── file_wrapper.py      # FileWrapper 類別
│   ├── texture_processor.py # 紋理處理
│   ├── font_processor.py    # 字型處理
│   ├── material_processor.py # 材質處理
│   └── text_processor.py    # 文字處理
├── utils/
│   ├── __init__.py
│   ├── file_utils.py        # 檔案工具
│   ├── platform_utils.py    # 平台工具
│   └── backup_utils.py      # 備份工具
├── cli/
│   ├── __init__.py
│   └── interface.py         # CLI 介面
└── config/
    ├── __init__.py
    └── settings.py          # 設定管理
```

## 貢獻測試

1. 新增測試時請遵循現有的命名規範
2. 為每個新功能添加對應的單元測試
3. 複雜的工作流程需要整合測試
4. 使用適當的測試標記
5. 確保測試具有良好的文檔字串

## 持續整合

測試應該在以下情況自動執行：
- Pull Request 建立時
- 程式碼推送到主分支時
- 發布新版本時

建議的 CI 配置應該包含：
- 多平台測試 (Windows, macOS, Linux)
- 多 Python 版本測試 (3.8+)
- 程式碼覆蓋率檢查
- 程式碼品質檢查 (black, isort, flake8)