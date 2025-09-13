# 開發者指南 - SKSG Traditional Chinese Tool

本文件提供 SKSG Traditional Chinese 專案的開發環境設定與架構說明。

## 📋 目錄

- [環境需求](#-環境需求)
- [快速開始](#-快速開始)
- [專案架構](#-專案架構)
- [開發工作流程](#-開發工作流程)
- [測試](#-測試)
- [建構](#-建構)
- [貢獻指南](#-貢獻指南)

## 🛠️ 環境需求

- **Python**: 3.8+ (推薦 3.12+)
- **uv**: 現代的 Python 套件管理器 (推薦)
- **Git**: 版本控制

## 🚀 快速開始

### 1. 複製專案

```bash
git clone https://github.com/tents89/SKSO_TChinese.git
cd SKSO_TChinese
```

### 2. 安裝 uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 3. 設定開發環境

```bash
# 安裝依賴
uv sync

# 執行測試驗證環境
uv run python sk_cht.py
uv run pytest tests/
```

## 🏗️ 專案架構

```
SKSG_TChinese/
├── sk_cht.py              # 主程式檔案
├── pyproject.toml         # 專案配置與依賴管理
├── requirements.txt       # pip 依賴清單
├── CHT/                   # 繁體中文本地化資源
│   ├── Font/             # 字型檔案和配置
│   ├── Png/              # 圖片資源
│   └── Text/             # 文字翻譯檔案
├── tests/                # 測試套件
│   ├── unit/            # 單元測試
│   └── integration/     # 整合測試
└── build_assets/        # 建構相關檔案
```

### 核心功能模組

1. **檔案包裝器 (FileWrapper)**: 處理 Unity 檔案的記憶體操作
2. **字型處理**: 處理繁體中文字型和字符映射
3. **紋理處理**: 處理遊戲紋理和圖片資源
4. **文字處理**: 處理遊戲內文字翻譯

## ⚙️ 開發工作流程

```bash
# 執行主程式
uv run python sk_cht.py

# 執行測試
uv run pytest tests/ -v

# 執行特定測試
uv run pytest tests/unit/test_file_wrapper.py -v
```

## 🧪 測試

### 測試結構

- **單元測試** (`tests/unit/`): 測試個別功能模組
- **整合測試** (`tests/integration/`): 測試完整工作流程

### 測試覆蓋率

```bash
# 產生覆蓋率報告
uv run pytest tests/ --cov=. --cov-report=html
```

## 📦 建構

### 開發建構

```bash
uv run python sk_cht.py
```

### 生產建構

使用 PyInstaller 建構跨平台可執行檔：

```bash
# Windows
uv run pyinstaller --onefile --icon=sk.ico --add-data "CHT;CHT" \
  --collect-all UnityPy --collect-all TypeTreeGeneratorAPI \
  --collect-all archspec --name="SilkSong_CHT_win" sk_cht.py

# macOS
uv run pyinstaller --onefile --icon=sk.icns --add-data "CHT:CHT" \
  --collect-all UnityPy --collect-all TypeTreeGeneratorAPI \
  --collect-all archspec --name="SilkSong_CHT_mac" sk_cht.py

# Linux
uv run pyinstaller --onefile --icon=sk.png --add-data "CHT:CHT" \
  --collect-all UnityPy --collect-all TypeTreeGeneratorAPI \
  --collect-all archspec --name="SilkSong_CHT_linux" sk_cht.py
```

## 🤝 貢獻指南

### 開發流程

1. Fork 專案並建立功能分支
2. 開發並確保測試通過
3. 提交變更並建立 Pull Request

### 程式碼規範

- 遵循 PEP 8 風格指南
- 為新功能撰寫測試
- 撰寫清楚的提交訊息

### 提交訊息格式

```
類型: 簡短描述

詳細說明 (如果需要)
```

類型範例：`feat`, `fix`, `docs`, `test`, `refactor`

## 📞 支援

- **Issues**: [GitHub Issues](https://github.com/tents89/SKSO_TChinese/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tents89/SKSO_TChinese/discussions)

---

感謝你對 SKSG Traditional Chinese 專案的貢獻！ 🎮✨
