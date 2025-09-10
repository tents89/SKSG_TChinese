import os
import sys
import ctypes
import traceback
import json
import shutil
import time
import collections.abc
import UnityPy
import UnityPy.config
from io import BytesIO
from UnityPy.files import BundleFile, SerializedFile
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from PIL import Image

# ==============================================================================
# --- 0. 執行環境與權限檢查 ---
# ==============================================================================
def is_admin():
    """檢查當前是否以管理員權限執行 (僅限 Windows)"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理員權限重新執行腳本 (僅限 Windows)"""
    if sys.platform == 'win32':
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

def get_base_path():
    """ 獲取資源檔案的基礎路徑，兼容開發環境與 PyInstaller 打包環境 """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# --- 1. 全域路徑與設定 (跨平台自動偵測) ---
# ==============================================================================
GAME_ROOT_PATH = os.getcwd()
PLATFORM_NAME = "未知"
BUNDLE_FILE_PATH = None
TEXT_ASSETS_FILE_PATH = None

# 根據偵測到的作業系統，設定對應的遊戲檔案路徑
if sys.platform == "win32":
    PLATFORM_NAME = "Windows"
    BUNDLE_FILE_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong_Data", "StreamingAssets", "aa", "StandaloneWindows64", "fonts_assets_chinese.bundle")
    TEXT_ASSETS_FILE_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong_Data", "resources.assets")
elif sys.platform == "darwin": # macOS
    PLATFORM_NAME = "macOS"
    BUNDLE_FILE_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong.app", "Contents", "Resources", "Data", "StreamingAssets", "aa", "StandaloneOSX", "fonts_assets_chinese.bundle")
    TEXT_ASSETS_FILE_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong.app", "Contents", "Resources", "Data", "resources.assets")
elif sys.platform.startswith("linux"):
    PLATFORM_NAME = "Linux"
    BUNDLE_FILE_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong_Data", "StreamingAssets", "aa", "StandaloneLinux64", "fonts_assets_chinese.bundle")
    TEXT_ASSETS_FILE_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong_Data", "resources.assets")

UNITY_VERSION = "6000.0.50f1"
BACKUP_FOLDER = os.path.join(GAME_ROOT_PATH, "Backup")

BUNDLED_DATA_PATH = get_base_path()
CHT_FOLDER_PATH = os.path.join(BUNDLED_DATA_PATH, "CHT")
FONT_SOURCE_FOLDER = os.path.join(CHT_FOLDER_PATH, "Font")
PNG_SOURCE_FOLDER = os.path.join(CHT_FOLDER_PATH, "Png")
TEXT_SOURCE_FOLDER = os.path.join(CHT_FOLDER_PATH, "Text")
MATERIAL_SOURCE_FOLDER = os.path.join(CHT_FOLDER_PATH, "Font")

TEMP_WORKSPACE_FOLDER = os.path.join(GAME_ROOT_PATH, "temp_workspace")

# ==============================================================================
# --- 輔助函數 ---
# ==============================================================================
def deep_update(original, new_data):
    """
    遞迴地用 new_data 中的值更新 original 字典 (用於材質等)。
    """
    for key, value in new_data.items():
        if isinstance(value, collections.abc.Mapping) and key in original and isinstance(original[key], collections.abc.Mapping):
            original[key] = deep_update(original.get(key, {}), value)
        else:
            original[key] = value
    return original

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in " .-_()").replace(" ", "_")

# ==============================================================================
# --- 選單功能 ---
# ==============================================================================

def run_modding():
    """執行主要的 Modding 流程"""
    print("\n[開始執行修改流程]")
    paths_to_check = [BUNDLE_FILE_PATH, TEXT_ASSETS_FILE_PATH, CHT_FOLDER_PATH]
    for path in paths_to_check:
        if not path or not os.path.exists(path):
            print(f"\n[錯誤] 關鍵路徑或檔案不存在: {path}")
            print(f"請確保此程式位於遊戲根目錄下，且 {PLATFORM_NAME} 版本的遊戲檔案完整。")
            return
            
    print("\n[警告] 此操作將直接修改遊戲檔案。")
    confirm = input("您是否要繼續執行？ (輸入 'y' 確認): ").strip().lower()
    if confirm != 'y':
        print("操作已取消。")
        return

    try:
        # 建立備份
        if os.path.exists(BACKUP_FOLDER):
            print("\n[步驟 1/4] 偵測到舊的備份資料夾，正在移除...")
            shutil.rmtree(BACKUP_FOLDER)
            print("舊備份已移除。")

        print("\n[步驟 1/4] 正在建立新的原始檔案備份...")
        # 確保備份路徑中的所有資料夾都存在
        backup_bundle_target = os.path.join(BACKUP_FOLDER, os.path.relpath(BUNDLE_FILE_PATH, GAME_ROOT_PATH))
        backup_assets_target = os.path.join(BACKUP_FOLDER, os.path.relpath(TEXT_ASSETS_FILE_PATH, GAME_ROOT_PATH))
        os.makedirs(os.path.dirname(backup_bundle_target), exist_ok=True)
        os.makedirs(os.path.dirname(backup_assets_target), exist_ok=True)
        
        shutil.copy2(BUNDLE_FILE_PATH, backup_bundle_target)
        shutil.copy2(TEXT_ASSETS_FILE_PATH, backup_assets_target)
        print("新備份已建立至 'Backup' 資料夾。")

        # 載入與修改資源
        print("\n[步驟 2/4] 正在載入資源並應用修改...")
        if os.path.exists(TEMP_WORKSPACE_FOLDER): shutil.rmtree(TEMP_WORKSPACE_FOLDER)
        os.makedirs(TEMP_WORKSPACE_FOLDER, exist_ok=True)
        if UNITY_VERSION: UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION
        
        generator = TypeTreeGenerator(UNITY_VERSION)
        generator.load_local_game(GAME_ROOT_PATH)
        
        bundle_env = UnityPy.load(BUNDLE_FILE_PATH)
        bundle_env.typetree_generator = generator
        
        text_env = UnityPy.load(TEXT_ASSETS_FILE_PATH)
        
        process_bundle(bundle_env)
        process_text_assets(text_env)
        print("資源修改完成。")

        # 重新打包
        print("\n[步驟 3/4] 正在重新打包修改後的檔案...")
        modified_bundle_path = os.path.join(TEMP_WORKSPACE_FOLDER, os.path.basename(BUNDLE_FILE_PATH))
        modified_text_assets_path = os.path.join(TEMP_WORKSPACE_FOLDER, os.path.basename(TEXT_ASSETS_FILE_PATH))
        with open(modified_bundle_path, "wb") as f: f.write(bundle_env.file.save())
        with open(modified_text_assets_path, "wb") as f: f.write(text_env.file.save())
        print("打包完成。")

        # 覆蓋檔案
        print("\n[步驟 4/4] 正在用新檔案覆蓋遊戲檔案...")
        shutil.move(modified_bundle_path, BUNDLE_FILE_PATH)
        shutil.move(modified_text_assets_path, TEXT_ASSETS_FILE_PATH)
        print("覆蓋完成！")
        print("\n== 所有操作已成功完成！==")

    except Exception as e:
        print(f"\n[嚴重錯誤] 操作過程中發生錯誤: {e}")
        traceback.print_exc()
    finally:
        if os.path.exists(TEMP_WORKSPACE_FOLDER): shutil.rmtree(TEMP_WORKSPACE_FOLDER)

def restore_backup():
    """從 Backup 資料夾還原原始檔案"""
    print("\n[開始執行還原備份流程]")
    if not os.path.exists(BACKUP_FOLDER):
        print("[錯誤] 找不到 'Backup' 資料夾，無法還原。")
        return
    try:
        backup_bundle = os.path.join(BACKUP_FOLDER, os.path.relpath(BUNDLE_FILE_PATH, GAME_ROOT_PATH))
        backup_assets = os.path.join(BACKUP_FOLDER, os.path.relpath(TEXT_ASSETS_FILE_PATH, GAME_ROOT_PATH))

        if not os.path.exists(backup_bundle) or not os.path.exists(backup_assets):
            print("[錯誤] 備份資料夾中檔案不完整，無法還原。")
            return
            
        print("正在從 'Backup' 資料夾還原原始檔案...")
        shutil.copy2(backup_bundle, BUNDLE_FILE_PATH)
        shutil.copy2(backup_assets, TEXT_ASSETS_FILE_PATH)
        print("\n== 檔案已成功還原！==")
    except Exception as e:
        print(f"\n[嚴重錯誤] 還原過程中發生錯誤: {e}")
        traceback.print_exc()

def show_about():
    """顯示關於資訊"""
    print("\n" + "="*60)
    print("== 關於此工具 ==")
    print("\n本工具全程使用AI完成。")
    print("\n核心: Python")
    print("  - 資源庫: UnityPy")
    print("  - 自動化腳本: Gemini大神")
    print("\n不提供技術支援。")
    print("="*60)

# ==============================================================================
# --- 腳本核心邏輯 (處理 Unity 資源) ---
# ==============================================================================

def process_bundle(env):
    """遞迴處理 Bundle 中的所有資源檔案"""
    def find_and_process(container):
        files_to_process = []
        if hasattr(container, 'files') and container.files is not None:
            files_to_process = container.files.values()
        for asset_file in files_to_process:
            if isinstance(asset_file, SerializedFile):
                for obj in asset_file.objects.values():
                    apply_bundle_modifications(obj)
            elif isinstance(asset_file, BundleFile):
                find_and_process(asset_file)
    find_and_process(env)

def apply_bundle_modifications(obj):
    """根據物件類型，應用不同的修改邏輯"""
    data = None
    try:
        data = obj.read()
        if not (data and hasattr(data, 'm_Name') and data.m_Name): return
        asset_name = data.m_Name
        obj_type = obj.type.name

        # --- 處理字型 (MonoBehaviour)，採用完整替換邏輯 ---
        if obj_type == "MonoBehaviour" and asset_name in ["chinese_body", "chinese_body_bold", "do_not_use_chinese_body_bold"]:
            # 如果是新名稱，對應到舊名稱的JSON檔案
            source_asset_name = "chinese_body_bold" if asset_name == "do_not_use_chinese_body_bold" else asset_name
            source_json_path = os.path.join(FONT_SOURCE_FOLDER, f"{source_asset_name}.json")

            if os.path.exists(source_json_path):
                original_tree = obj.read_typetree()
                with open(source_json_path, "r", encoding="utf-8") as f:
                    source_dict = json.load(f)
                
                if "m_fontInfo" in source_dict:
                    original_tree["m_fontInfo"] = source_dict["m_fontInfo"]
                if "m_glyphInfoList" in source_dict:
                    original_tree["m_glyphInfoList"] = source_dict["m_glyphInfoList"]
                
                obj.save_typetree(original_tree)
                print(f"  - [字型] 已從 JSON 完整替換 '{asset_name}' 的數據")

        # --- 處理材質 (Material)，由 JSON 驅動 ---
        elif obj_type == "Material" and asset_name in ["simsun_tmpro Material", "chinese_body_bold Material", "do_not_use_chinese_body_bold Material"]:
            source_asset_name = "chinese_body_bold Material" if asset_name == "do_not_use_chinese_body_bold Material" else asset_name
            safe_name = sanitize_filename(source_asset_name)
            source_json_path = os.path.join(MATERIAL_SOURCE_FOLDER, f"{safe_name}.json")
            
            if os.path.exists(source_json_path):
                original_tree = obj.read_typetree()
                with open(source_json_path, "r", encoding="utf-8") as f:
                    source_dict = json.load(f)
                updated_tree = deep_update(original_tree, source_dict)
                obj.save_typetree(updated_tree)
                print(f"  - [材質] 已從 JSON 更新 '{asset_name}'")

        # --- 處理紋理 (Texture2D)，增強穩定性 ---
        elif obj_type == "Texture2D" and asset_name in ["chinese_body Atlas", "chinese_body_bold Atlas", "do_not_use_chinese_body_bold Atlas"]:
            source_asset_name = "chinese_body_bold Atlas" if asset_name == "do_not_use_chinese_body_bold Atlas" else asset_name
            safe_name = sanitize_filename(source_asset_name)
            source_png_path = os.path.join(PNG_SOURCE_FOLDER, f"{safe_name}.png")
            
            if os.path.exists(source_png_path):
                with Image.open(source_png_path) as img:
                    data.image = img
                    # 同步更新圖片的元數據
                    data.m_Width = img.width
                    data.m_Height = img.height
                    data.save()
                    print(f"  - [紋理] 已成功替換 '{asset_name}'")
    except Exception as e:
        print(f"  - [警告] 處理資源 '{asset_name}' 時發生錯誤: {e}")
        return

def process_text_assets(env):
    """處理 resources.assets 中的文本替換"""
    text_target_assets = {"ZH_Achievements", "ZH_AutoSaveNames", "ZH_Belltown", "ZH_Bonebottom", "ZH_Caravan", "ZH_City", "ZH_Coral", "ZH_Crawl", "ZH_Credits List", "ZH_Deprecated", "ZH_Dust", "ZH_Enclave", "ZH_Error", "ZH_Fast Travel", "ZH_Forge", "ZH_General", "ZH_Greymoor", "ZH_Inspect", "ZH_Journal", "ZH_Lore", "ZH_MainMenu", "ZH_Map Zones", "ZH_Peak", "ZH_Pilgrims", "ZH_Prompts", "ZH_Quests", "ZH_Shellwood", "ZH_Shop", "ZH_Song", "ZH_Titles", "ZH_Tools", "ZH_UI", "ZH_Under", "ZH_Wanderers", "ZH_Weave", "ZH_Wilds"}
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data and data.m_Name in text_target_assets:
                source_txt_path = os.path.join(TEXT_SOURCE_FOLDER, f"{data.m_Name}.txt")
                if os.path.exists(source_txt_path):
                    with open(source_txt_path, "rb") as f:
                        local_bytes = f.read()
                    data.m_Script = local_bytes.decode("utf-8", "surrogateescape")
                    data.save()

# ==============================================================================
# --- 主程式入口 ---
# ==============================================================================
def main_menu():
    while True:
        # 清除主控台畫面，增強使用者體驗
        if sys.platform == 'win32': os.system('cls')
        
        print("="*60)
        print("== 絲綢之歌繁體中文化工具1.0 ==")
        print("="*60)
        print(f"偵測到作業系統: {PLATFORM_NAME}")
        print(f"遊戲目錄: {GAME_ROOT_PATH}")
        
        if not BUNDLE_FILE_PATH:
            print(f"\n[錯誤] 不支援的作業系統 ({sys.platform})。")
            print("本工具支援 Windows, macOS(理論), 與 Linux(理論)。")
            input("\n按下 Enter 鍵退出...")
            return

        print("\n請選擇要執行的操作：\n")
        print("  1. 進行繁體中文化")
        print("  2. 還原備份")
        print("  3. 關於")
        print("  4. 退出\n")
        
        choice = input("請輸入選項 [1-4]: ").strip()
        
        if choice == '1': run_modding()
        elif choice == '2': restore_backup()
        elif choice == '3': show_about()
        elif choice == '4':
            print("程式即將退出。")
            time.sleep(1)
            break
        else:
            print("\n無效的指令，請重新輸入。")
            time.sleep(1)
            continue
            
        input("\n按下 Enter 鍵返回主選單...")

if __name__ == "__main__":
    # 在 Windows 平台，檢查並請求管理員權限
    if sys.platform == 'win32' and not is_admin():
        print("偵測到需要管理員權限，正在嘗試重新啟動...")
        run_as_admin()
        sys.exit(0)
        
    main_menu()

