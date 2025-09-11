import os
import sys
import ctypes
import traceback
import json
import shutil
import time
import collections.abc

# UnityPy and related imports
import UnityPy
import UnityPy.config
from UnityPy.files import BundleFile, SerializedFile
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from UnityPy.export import Texture2DConverter
from UnityPy.streams import EndianBinaryReader
from UnityPy.enums import ClassIDType, TextureFormat
import etcpak

# Standard library imports
from io import BytesIO
from PIL import Image

# ==============================================================================
# --- Monkey-Patch for BC7 Compression ---
# ==============================================================================
print("[資訊] 應用 BC7 壓縮修正補丁...")
# 儲存原始的壓縮函式
original_compress_etcpak = Texture2DConverter.compress_etcpak

# 定義我們自己的、修正過的壓縮函式
def patched_compress_etcpak(data: bytes, width: int, height: int, target_texture_format: TextureFormat) -> bytes:
    """
    這是一個修正函式，用於解決 UnityPy 依賴的 etcpak 庫
    在新版本中對 BC7 壓縮 API 的變更。
    """
    if target_texture_format == TextureFormat.BC7:
        # 對於 BC7 格式，我們需要手動創建並傳入一個 BC7CompressBlockParams 物件
        params = etcpak.BC7CompressBlockParams()
        return etcpak.compress_bc7(data, width, height, params)
    else:
        # 對於所有其他格式，我們仍然使用原始的函式
        return original_compress_etcpak(data, width, height, target_texture_format)

# 用我們修正過的函式替換掉 UnityPy 中的原始函式
Texture2DConverter.compress_etcpak = patched_compress_etcpak
print("[資訊] 補丁應用成功。")

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
# --- FileWrapper 輔助類別 ---
# ==============================================================================
class FileWrapper:
    """一個輔助類別，用於包裝修改後的資料流，同時保留原始檔案的元數據。"""
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
        return self._stream.read()

    def __getattr__(self, name):
        return getattr(self._original, name)
        
# ==============================================================================
# --- 1. 全域路徑與設定 ---
# ==============================================================================
GAME_ROOT_PATH = os.getcwd()
PLATFORM_NAME = "未知"
BUNDLE_FILE_PATH = None
TEXT_ASSETS_FILE_PATH = None
TITLE_BUNDLE_PATH = None

if sys.platform == "win32":
    PLATFORM_NAME = "Windows"
    SILKSONG_DATA_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong_Data")
    STREAMING_ASSETS_PLATFORM_PATH = os.path.join(SILKSONG_DATA_PATH, "StreamingAssets", "aa", "StandaloneWindows64")
    BUNDLE_FILE_PATH = os.path.join(STREAMING_ASSETS_PLATFORM_PATH, "fonts_assets_chinese.bundle")
    TITLE_BUNDLE_PATH = os.path.join(STREAMING_ASSETS_PLATFORM_PATH, "atlases_assets_assets", "sprites", "_atlases", "title.spriteatlas.bundle")
    TEXT_ASSETS_FILE_PATH = os.path.join(SILKSONG_DATA_PATH, "resources.assets")

elif sys.platform == "darwin":
    PLATFORM_NAME = "macOS"
    SILKSONG_DATA_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong.app", "Contents", "Resources", "Data")
    STREAMING_ASSETS_PLATFORM_PATH = os.path.join(SILKSONG_DATA_PATH, "StreamingAssets", "aa", "StandaloneOSX")
    BUNDLE_FILE_PATH = os.path.join(STREAMING_ASSETS_PLATFORM_PATH, "fonts_assets_chinese.bundle")
    TITLE_BUNDLE_PATH = os.path.join(STREAMING_ASSETS_PLATFORM_PATH, "atlases_assets_assets", "sprites", "_atlases", "title.spriteatlas.bundle")
    TEXT_ASSETS_FILE_PATH = os.path.join(SILKSONG_DATA_PATH, "resources.assets")

elif sys.platform.startswith("linux"):
    PLATFORM_NAME = "Linux"
    SILKSONG_DATA_PATH = os.path.join(GAME_ROOT_PATH, "Hollow Knight Silksong_Data")
    STREAMING_ASSETS_PLATFORM_PATH = os.path.join(SILKSONG_DATA_PATH, "StreamingAssets", "aa", "StandaloneLinux64")
    BUNDLE_FILE_PATH = os.path.join(STREAMING_ASSETS_PLATFORM_PATH, "fonts_assets_chinese.bundle")
    TITLE_BUNDLE_PATH = os.path.join(STREAMING_ASSETS_PLATFORM_PATH, "atlases_assets_assets", "sprites", "_atlases", "title.spriteatlas.bundle")
    TEXT_ASSETS_FILE_PATH = os.path.join(SILKSONG_DATA_PATH, "resources.assets")

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
    print("\n[開始執行修改流程]")
    paths_to_check = [BUNDLE_FILE_PATH, TEXT_ASSETS_FILE_PATH, TITLE_BUNDLE_PATH, CHT_FOLDER_PATH]
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
        if os.path.exists(BACKUP_FOLDER):
            print("\n[步驟 1/4] 偵測到舊的備份資料夾，正在移除...")
            shutil.rmtree(BACKUP_FOLDER)
            print("舊備份已移除。")

        print("\n[步驟 1/4] 正在建立新的原始檔案備份...")
        backup_bundle_target = os.path.join(BACKUP_FOLDER, os.path.relpath(BUNDLE_FILE_PATH, GAME_ROOT_PATH))
        backup_assets_target = os.path.join(BACKUP_FOLDER, os.path.relpath(TEXT_ASSETS_FILE_PATH, GAME_ROOT_PATH))
        backup_title_target = os.path.join(BACKUP_FOLDER, os.path.relpath(TITLE_BUNDLE_PATH, GAME_ROOT_PATH))
        os.makedirs(os.path.dirname(backup_bundle_target), exist_ok=True)
        os.makedirs(os.path.dirname(backup_assets_target), exist_ok=True)
        os.makedirs(os.path.dirname(backup_title_target), exist_ok=True)
        shutil.copy2(BUNDLE_FILE_PATH, backup_bundle_target)
        shutil.copy2(TEXT_ASSETS_FILE_PATH, backup_assets_target)
        shutil.copy2(TITLE_BUNDLE_PATH, backup_title_target)
        print("新備份已建立至 'Backup' 資料夾。")

        print("\n[步驟 2/4] 正在載入資源並應用修改...")
        if os.path.exists(TEMP_WORKSPACE_FOLDER): shutil.rmtree(TEMP_WORKSPACE_FOLDER)
        os.makedirs(TEMP_WORKSPACE_FOLDER, exist_ok=True)
        if UNITY_VERSION: UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION
        generator = TypeTreeGenerator(UNITY_VERSION)
        generator.load_local_game(GAME_ROOT_PATH)
        bundle_env = UnityPy.load(BUNDLE_FILE_PATH)
        bundle_env.typetree_generator = generator
        text_env = UnityPy.load(TEXT_ASSETS_FILE_PATH)
        title_env = UnityPy.load(TITLE_BUNDLE_PATH)
        title_env.typetree_generator = generator

        process_bundle(bundle_env)
        process_text_assets(text_env)
        process_title_bundle(title_env)
        print("資源修改完成。")

        print("\n[步驟 3/4] 正在重新打包修改後的檔案...")
        modified_bundle_path = os.path.join(TEMP_WORKSPACE_FOLDER, os.path.basename(BUNDLE_FILE_PATH))
        modified_text_assets_path = os.path.join(TEMP_WORKSPACE_FOLDER, os.path.basename(TEXT_ASSETS_FILE_PATH))
        modified_title_bundle_path = os.path.join(TEMP_WORKSPACE_FOLDER, os.path.basename(TITLE_BUNDLE_PATH))
        with open(modified_bundle_path, "wb") as f: f.write(bundle_env.file.save())
        with open(modified_text_assets_path, "wb") as f: f.write(text_env.file.save())
        with open(modified_title_bundle_path, "wb") as f: f.write(title_env.file.save())
        print("打包完成。")

        print("\n[步驟 4/4] 正在用新檔案覆蓋遊戲檔案...")
        shutil.move(modified_bundle_path, BUNDLE_FILE_PATH)
        shutil.move(modified_text_assets_path, TEXT_ASSETS_FILE_PATH)
        shutil.move(modified_title_bundle_path, TITLE_BUNDLE_PATH)
        print("覆蓋完成！")
        print("\n== 所有操作已成功完成！==")

    except Exception as e:
        print(f"\n[嚴重錯誤] 操作過程中發生錯誤: {e}")
        traceback.print_exc()
    finally:
        if os.path.exists(TEMP_WORKSPACE_FOLDER): shutil.rmtree(TEMP_WORKSPACE_FOLDER)

def restore_backup():
    print("\n[開始執行還原備份流程]")
    if not os.path.exists(BACKUP_FOLDER):
        print("[錯誤] 找不到 'Backup' 資料夾，無法還原。")
        return
    try:
        backup_bundle = os.path.join(BACKUP_FOLDER, os.path.relpath(BUNDLE_FILE_PATH, GAME_ROOT_PATH))
        backup_assets = os.path.join(BACKUP_FOLDER, os.path.relpath(TEXT_ASSETS_FILE_PATH, GAME_ROOT_PATH))
        backup_title = os.path.join(BACKUP_FOLDER, os.path.relpath(TITLE_BUNDLE_PATH, GAME_ROOT_PATH))
        if not os.path.exists(backup_bundle) or not os.path.exists(backup_assets) or not os.path.exists(backup_title):
            print("[錯誤] 備份資料夾中檔案不完整，無法還原。")
            return
        print("正在從 'Backup' 資料夾還原原始檔案...")
        shutil.copy2(backup_bundle, BUNDLE_FILE_PATH)
        shutil.copy2(backup_assets, TEXT_ASSETS_FILE_PATH)
        shutil.copy2(backup_title, TITLE_BUNDLE_PATH)
        print("\n== 檔案已成功還原！==")
    except Exception as e:
        print(f"\n[嚴重錯誤] 還原過程中發生錯誤: {e}")
        traceback.print_exc()

def show_about():
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

def process_title_bundle(env):
    """處理 title.spriteatlas.bundle，替換主選單 Logo。"""
    print("[資訊] 開始處理 Title Bundle...")
    TARGET_ASSET_NAME = "sactx-0-1024x1024-BC7-Title-228dda81"
    SOURCE_PNG_NAME = "logo.png"
    source_png_path = os.path.join(PNG_SOURCE_FOLDER, SOURCE_PNG_NAME)

    if not os.path.exists(source_png_path):
        print(f"  - [警告] 找不到源文件 '{SOURCE_PNG_NAME}'，跳過 Title Logo 替換。")
        return

    for obj in env.objects:
        if obj.type.name == "Texture2D":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == TARGET_ASSET_NAME:
                    print(f"  - [紋理] 找到目標 Title Logo: '{data.m_Name}'")
                    
                    if not (data.m_StreamData and data.m_StreamData.path):
                        print("  - [警告] Title Logo 不是 .resS 格式，暫不支援此種替換。")
                        break

                    with Image.open(source_png_path) as img:
                        image_binary, new_format = Texture2DConverter.image_to_texture2d(img, data.m_TextureFormat, data.assets_file.target_platform)

                    resS_path = os.path.basename(data.m_StreamData.path)
                    bundle_file = data.assets_file.parent
                    resS_file = bundle_file.files[resS_path]
                    
                    new_ress_stream = BytesIO(image_binary)
                    wrapper = FileWrapper(resS_file, new_ress_stream)
                    bundle_file.files[resS_path] = wrapper
                    print(f"    - [資訊] 已為 '{resS_path}' 創建新的數據流。")

                    data.m_StreamData.offset = 0
                    data.m_StreamData.size = len(image_binary)
                    data.m_Width = img.width
                    data.m_Height = img.height
                    data.m_TextureFormat = new_format
                    data.m_CompleteImageSize = len(image_binary)
                    if hasattr(data, 'image_data'): data.image_data = b""
                    data.save()
                    print(f"    - [紋理] 已成功更新 '{data.m_Name}' 的元數據。")
                    
                    break
            except Exception as e:
                print(f"  - [嚴重警告] 處理 Title Logo 時發生錯誤: {e}")
                traceback.print_exc()
                break

def process_font(obj_reader):
    try:
        data = obj_reader.read()
        asset_name = data.m_Name
        source_asset_name = "chinese_body_bold" if asset_name == "do_not_use_chinese_body_bold" else asset_name
        source_json_path = os.path.join(FONT_SOURCE_FOLDER, f"{source_asset_name}.json")
        if os.path.exists(source_json_path):
            original_tree = obj_reader.read_typetree()
            with open(source_json_path, "r", encoding="utf-8") as f: source_dict = json.load(f)
            if "m_fontInfo" in source_dict: original_tree["m_fontInfo"] = source_dict["m_fontInfo"]
            if "m_glyphInfoList" in source_dict: original_tree["m_glyphInfoList"] = source_dict["m_glyphInfoList"]
            obj_reader.save_typetree(original_tree)
            print(f"  - [字型] 已從 JSON 完整替換 '{asset_name}' 的數據")
    except Exception as e:
        print(f"  - [警告] 處理字型 '{getattr(obj_reader, 'm_Name', '未知')}' 時出錯: {e}")

def process_material(obj_reader):
    try:
        data = obj_reader.read()
        asset_name = data.m_Name
        source_asset_name = "chinese_body_bold Material" if asset_name == "do_not_use_chinese_body_bold Material" else asset_name
        safe_name = sanitize_filename(source_asset_name)
        source_json_path = os.path.join(MATERIAL_SOURCE_FOLDER, f"{safe_name}.json")
        if os.path.exists(source_json_path):
            original_tree = obj_reader.read_typetree()
            with open(source_json_path, "r", encoding="utf-8") as f: source_dict = json.load(f)
            updated_tree = deep_update(original_tree, source_dict)
            obj_reader.save_typetree(updated_tree)
            print(f"  - [材質] 已從 JSON 更新 '{asset_name}'")
    except Exception as e:
        print(f"  - [警告] 處理材質 '{getattr(obj_reader, 'm_Name', '未知')}' 時出錯: {e}")

def process_embedded_texture(data):
    try:
        asset_name = data.m_Name
        source_asset_name = "chinese_body_bold Atlas" if asset_name == "do_not_use_chinese_body_bold Atlas" else asset_name
        safe_name = sanitize_filename(source_asset_name)
        source_png_path = os.path.join(PNG_SOURCE_FOLDER, f"{safe_name}.png")
        if os.path.exists(source_png_path):
            with Image.open(source_png_path) as img:
                data.image = img
                data.m_Width = img.width
                data.m_Height = img.height
                data.save()
                print(f"  - [紋理] 已成功替換 (內嵌模式) '{asset_name}'")
    except Exception as e:
        print(f"  - [警告] 處理內嵌紋理 '{data.m_Name}' 時出錯: {e}")

def process_ress_texture_group(texture_group):
    if not texture_group: return
    first_texture = texture_group[0]
    resS_path = os.path.basename(first_texture.m_StreamData.path)
    bundle_file = first_texture.assets_file.parent
    print(f"  - [紋理組] 開始處理共享 '{resS_path}' 的 {len(texture_group)} 個紋理...")
    try:
        new_datas = []
        for tex_data in texture_group:
            asset_name = tex_data.m_Name
            source_asset_name = "chinese_body_bold Atlas" if asset_name == "do_not_use_chinese_body_bold Atlas" else asset_name
            safe_name = sanitize_filename(source_asset_name)
            source_png_path = os.path.join(PNG_SOURCE_FOLDER, f"{safe_name}.png")
            if os.path.exists(source_png_path):
                with Image.open(source_png_path) as img:
                    image_binary, new_format = Texture2DConverter.image_to_texture2d(img, tex_data.m_TextureFormat, tex_data.assets_file.target_platform)
                    new_datas.append({ "original_obj": tex_data, "image_binary": image_binary, "new_format": new_format, "img": img.copy() })

        new_ress_stream = BytesIO()
        current_offset = 0
        for data_dict in new_datas:
            data_dict["new_offset"] = current_offset
            new_ress_stream.write(data_dict["image_binary"])
            current_offset += len(data_dict["image_binary"])
        
        resS_file = bundle_file.files[resS_path]
        original_obj = resS_file._original if isinstance(resS_file, FileWrapper) else resS_file
        wrapper = FileWrapper(original_obj, new_ress_stream)
        bundle_file.files[resS_path] = wrapper
        print(f"    - [資訊] 已成功重建 '{resS_path}'，新總大小: {current_offset} bytes")

        for data_dict in new_datas:
            tex_data = data_dict["original_obj"]
            img = data_dict["img"]
            tex_data.m_StreamData.offset = data_dict["new_offset"]
            tex_data.m_StreamData.size = len(data_dict["image_binary"])
            tex_data.m_Width = img.width
            tex_data.m_Height = img.height
            tex_data.m_TextureFormat = data_dict["new_format"]
            tex_data.m_CompleteImageSize = len(data_dict["image_binary"])
            if hasattr(tex_data, 'image_data'): tex_data.image_data = b""
            tex_data.save()
            print(f"    - [紋理] 已更新 '{tex_data.m_Name}' 元數據 (新 offset: {data_dict['new_offset']})")
    except Exception as e:
        print(f"  - [嚴重警告] 處理紋理組 '{resS_path}' 時發生錯誤: {e}")
        traceback.print_exc()

def process_bundle(env):
    print("[資訊] 正在分析與分類所有資源...")
    all_objects = []
    def find_all_objects(container):
        if hasattr(container, 'files') and container.files is not None:
            for asset_file in list(container.files.values()):
                if isinstance(asset_file, SerializedFile):
                    all_objects.extend(asset_file.objects.values())
                elif isinstance(asset_file, BundleFile):
                    find_all_objects(asset_file)
    find_all_objects(env)

    materials_to_process, fonts_to_process, textures_by_ress = [], [], {}
    embedded_textures = []

    for obj in all_objects:
        try:
            if obj.type.name in ["MonoBehaviour", "Material", "Texture2D"]:
                data = obj.read()
                if not (hasattr(data, 'm_Name') and data.m_Name): continue
                asset_name = data.m_Name

                if obj.type.name == "MonoBehaviour" and asset_name in ["chinese_body", "chinese_body_bold", "do_not_use_chinese_body_bold"]:
                    fonts_to_process.append(data)
                elif obj.type.name == "Material" and asset_name in ["simsun_tmpro Material", "chinese_body_bold Material", "do_not_use_chinese_body_bold Material"]:
                    materials_to_process.append(data)
                elif obj.type.name == "Texture2D" and asset_name in ["chinese_body Atlas", "chinese_body_bold Atlas", "do_not_use_chinese_body_bold Atlas"]:
                    if data.m_StreamData and data.m_StreamData.path:
                        resS_path = os.path.basename(data.m_StreamData.path)
                        if resS_path not in textures_by_ress: textures_by_ress[resS_path] = []
                        textures_by_ress[resS_path].append(data)
                    else:
                        embedded_textures.append(data)
        except Exception as e:
            print(f"  - [警告] 預處理資源時出錯: {e}")

    print("[資訊] 分類完成，開始按依賴順序應用修改...")
    for resS_path, texture_group in textures_by_ress.items():
        texture_group.sort(key=lambda x: int(x.m_StreamData.offset))
        process_ress_texture_group(texture_group)
    for tex_data in embedded_textures:
        process_embedded_texture(tex_data)
    for font_data in fonts_to_process:
        process_font(font_data.object_reader)
    for mat_data in materials_to_process:
        process_material(mat_data.object_reader)

def process_text_assets(env):
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
        if sys.platform == 'win32': os.system('cls')
        
        print("="*60)
        print("== 絲綢之歌繁體中文化工具 v1.0 ==")
        print("="*60)
        print(f"作業系統: {PLATFORM_NAME}")
        print(f"遊戲目錄: {GAME_ROOT_PATH}")
        
        if not BUNDLE_FILE_PATH:
            print(f"\n[錯誤] 不支援的作業系統 ({sys.platform})。")
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
    is_packaged = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
    if sys.platform == 'win32' and is_packaged and not is_admin():
        print("偵測到需要管理員權限，正在嘗試重新啟動...")
        run_as_admin()
        sys.exit(0)
    if sys.platform == 'win32' and not is_packaged and not is_admin():
        print("\n" + "="*60)
        print("== [開發者警告] ==")
        print("偵測到腳本未以管理員權限執行。")
        print("部分檔案操作 (如覆蓋遊戲檔案) 可能會失敗。")
        print("="*60 + "\n")
    main_menu()
