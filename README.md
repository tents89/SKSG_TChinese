# 絲綢之歌-繁體中文化一鍵處理工具

這是一個專為《Hollow Knight: Silksong》設計的全自動繁體中文化工具。只需簡單操作，即可將遊戲內的文本、字型替換為繁體中文版本。

遊戲更新後，請嘗試重新執行一次此工具。

![image](https://github.com/tents89/SKSG_TChinese/blob/main/Tool.png)
> **本工具的核心邏輯與程式碼均由 AI 構建，並使用 Python 與 UnityPy 技術實現。**

---

## 🚀 如何使用

### 下載

請前往 **[Releases 頁面](https://github.com/tents89/SKSG_TChinese/releases)** 下載對應你作業系統的最新版本壓縮包。

### 步驟

1.  **解壓縮檔案**：
    * 將下載的 `.zip` 檔案解壓縮後會得到一個執行檔。

2.  **位置**：
    * **非常重要**：請將解壓縮後的執行檔**移動到你的《Hollow Knight: Silksong》遊戲根目錄下，或是透過 `--root` 引數手動指定。**
    * **Windows**:
        * **Steam**: 通常是 `.../steamapps/common/Hollow Knight Silksong/`
        * **Game Pass**: 通常類似 `.../XboxGames/Hollow Knight Silksong/Content/` (需放在遊戲安裝目錄下的 `Content` 資料夾內)

    * **macOS**: 通常是 `.../steamapps/common/Hollow Knight Silksong/` (執行檔需放在 `Hollow Knight Silksong.app` 旁邊)
    * **Linux**: 通常是 `.../steamapps/common/Hollow Knight Silksong/`

3.  **執行工具**：
    * **Windows**: 直接雙擊 `SilkSong_CHT_win.exe` 執行。
    * **macOS / Linux**: 開啟終端機 (Terminal)，並切換到遊戲根目錄。
        * 首先，賦予檔案執行權限 (此步驟只需操作一次)：
            ```bash
            chmod +x ./SilkSong_CHT_mac
            ```
            *(若是 Linux 系統，請將指令中的 `SilkSong_CHT_mac` 改為 `SilkSong_CHT_linux`)*

        * 然後，執行程式：
            ```bash
            ./SilkSong_CHT_mac
            ```
            *(同樣，Linux 用戶請執行 `./SilkSong_CHT_linux`)*
    * 手動指定遊戲根目錄和平台
      #### 如果你下載的遊戲與當前作業系統不批配，可輸入 `T` 切換平台，或是手動指定根目錄與遊戲平台 (e.g. 在 SteamDeck 或 Linux/macOS 運行 Windows 版的遊戲) ####
        ```bash
        ./SilkSong_CHT_win --root <遊戲根目錄> --build <平台>

        # 範例
        ./SilkSong_CHT_win --root ".../steamapps/common/Hollow Knight Silksong/" --build "Windows"
        ```
      #### (將 `./SilkSong_CHT_win` 替換為對應名稱)
      
4.  **依照選單操作**：
    * 執行後會出現功能選單，輸入 `1`或`2`或`3` 即可開始繁體中文化處理。

---

## ⚠️ 注意

* 本工具內含三種文本來源，[修車組](https://www.bilibili.com/video/BV19epDzrEut)、[本專案的社群翻譯](https://paratranz.cn/projects/16176)與官方中文。
* 若修車組不願意被集成到本工具，請與我聯絡。
* 不保證遊戲每次更新都可以使用，但相容性理應極高。
* 本工具會直接修改遊戲檔案，雖然內建備份功能，但如果失效請對遊戲重新驗證檔案完整性。
* 本工具為粉絲製作，與 Team Cherry 和 Unity Technologies 皆無關聯。請自行承擔使用風險。
---

## 🔧 使用技術

* **主要語言**: Python 3.8+ (推薦 3.12+)
* **核心函式庫**: [UnityPy](https://github.com/K0lb3/UnityPy) (用於處理 Unity 遊戲資產)
* **套件管理**: uv / pip
* **測試框架**: pytest
* **打包工具**: PyInstaller
* **程式碼品質**: black, isort, flake8, mypy

---

## 👨‍💻 For Devs

對於想要參與開發或了解技術細節的開發者，請參閱：

📖 **[開發者指南 (README-DEV.md)](README-DEV.md)**
