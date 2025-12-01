import collections.abc
import ctypes
import json
import os
import shutil
import sys
import time
import traceback

import uuid
import argparse
import etcpak

import UnityPy
import UnityPy.config
from io import BytesIO
from PIL import Image
from UnityPy.files import BundleFile, SerializedFile
from UnityPy.files.SerializedFile import FileIdentifier
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from UnityPy.export import Texture2DConverter
from UnityPy.streams import EndianBinaryReader
from UnityPy.enums import ClassIDType, TextureFormat


# ==============================================================================
# --- Monkey-Patch for BC7 Compression ---
# ==============================================================================
print("[資訊] 應用 BC7 壓縮修正補丁...")
original_compress_etcpak = Texture2DConverter.compress_etcpak


def patched_compress_etcpak(
    data: bytes, width: int, height: int, target_texture_format: TextureFormat
) -> bytes:
    if target_texture_format == TextureFormat.BC7:
        params = etcpak.BC7CompressBlockParams()
        return etcpak.compress_bc7(data, width, height, params)
    else:
        return original_compress_etcpak(data, width, height, target_texture_format)


Texture2DConverter.compress_etcpak = patched_compress_etcpak
print("[資訊] 補丁應用成功。")

# ==============================================================================
# --- 0. 執行環境與權限檢查 ---
# ==============================================================================


def get_base_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


# ==============================================================================
# --- FileWrapper 輔助類別 ---
# ==============================================================================
class FileWrapper:
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
class Config:
    PLATFORM_NAME: str = "Unknown"
    GAME_ROOT_PATH: str = os.getcwd()

    # --- 為所有路徑屬性提供初始值 ---
    SILKSONG_DATA_PATH: str = ""
    STREAMING_ASSETS_PLATFORM_PATH: str = ""
    BUNDLE_FILE_PATH: str = ""
    TITLE_BUNDLE_PATH: str = ""
    TEXT_ASSETS_FILE_PATH: str = ""
    MAP_FONT_BUNDLE_PATH: str = ""

    UNITY_VERSION: str = "6000.0.50f1"
    BACKUP_FOLDER: str = ""
    BUNDLED_DATA_PATH: str = ""
    CHT_FOLDER_PATH: str = ""
    
    # 資源路徑設定
    CURRENT_ASSET_FOLDER: str = "" 
    LOGO_SOURCE_FOLDER: str = ""  # 新增：獨立的 logo 資料夾路徑
    TEXT_SOURCE_FOLDER: str = ""
    TEMP_WORKSPACE_FOLDER: str = ""


def detect_environment(*, game_build: str = "Unknown"):

    if game_build in ["Windows", "Linux", "macOS"]:
        Config.PLATFORM_NAME = game_build
    else:
        if sys.platform == "win32":
            Config.PLATFORM_NAME = "Windows"
        elif sys.platform == "darwin":
            Config.PLATFORM_NAME = "macOS"
        elif sys.platform.startswith("linux"):
            Config.PLATFORM_NAME = "Linux"
        else:
            Config.PLATFORM_NAME = "Unknown"

    if Config.PLATFORM_NAME == "Windows":
        Config.SILKSONG_DATA_PATH = os.path.join(
            Config.GAME_ROOT_PATH, "Hollow Knight Silksong_Data"
        )
        Config.STREAMING_ASSETS_PLATFORM_PATH = os.path.join(
            Config.SILKSONG_DATA_PATH, "StreamingAssets", "aa", "StandaloneWindows64"
        )
    elif Config.PLATFORM_NAME == "macOS":
        Config.SILKSONG_DATA_PATH = os.path.join(
            Config.GAME_ROOT_PATH,
            "Hollow Knight Silksong.app",
            "Contents",
            "Resources",
            "Data",
        )
        Config.STREAMING_ASSETS_PLATFORM_PATH = os.path.join(
            Config.SILKSONG_DATA_PATH, "StreamingAssets", "aa", "StandaloneOSX"
        )
    elif Config.PLATFORM_NAME == "Linux":
        Config.SILKSONG_DATA_PATH = os.path.join(
            Config.GAME_ROOT_PATH, "Hollow Knight Silksong_Data"
        )
        Config.STREAMING_ASSETS_PLATFORM_PATH = os.path.join(
            Config.SILKSONG_DATA_PATH, "StreamingAssets", "aa", "StandaloneLinux64"
        )
    
    # 共用路徑定義
    if Config.PLATFORM_NAME in ["Windows", "macOS", "Linux"]:
        Config.BUNDLE_FILE_PATH = os.path.join(
            Config.STREAMING_ASSETS_PLATFORM_PATH, "fonts_assets_chinese.bundle"
        )
        Config.MAP_FONT_BUNDLE_PATH = os.path.join(
            Config.STREAMING_ASSETS_PLATFORM_PATH, "maps_assets_all.bundle"
        )
        Config.TITLE_BUNDLE_PATH = os.path.join(
            Config.STREAMING_ASSETS_PLATFORM_PATH,
            "atlases_assets_assets",
            "sprites",
            "_atlases",
            "title.spriteatlas.bundle",
        )
        Config.TEXT_ASSETS_FILE_PATH = os.path.join(
            Config.SILKSONG_DATA_PATH, "resources.assets"
        )

    Config.BUNDLED_DATA_PATH = get_base_path()
    Config.BACKUP_FOLDER = os.path.join(Config.GAME_ROOT_PATH, "Backup")
    Config.CHT_FOLDER_PATH = os.path.join(Config.BUNDLED_DATA_PATH, "CHT")
    
    # 修改：獨立定義 Logo 資料夾
    Config.LOGO_SOURCE_FOLDER = os.path.join(Config.CHT_FOLDER_PATH, "logo")
    
    Config.TEXT_SOURCE_FOLDER = os.path.join(Config.CHT_FOLDER_PATH, "Text")
    Config.TEMP_WORKSPACE_FOLDER = os.path.join(Config.GAME_ROOT_PATH, "temp_workspace")


# ==============================================================================
# --- 輔助函數 ---
# ==============================================================================
def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in " .-_()").replace(" ", "_")


def find_cab_name_in_bundle(env):
    """
    遞迴地在 Bundle 環境中查找主要的 SerializedFile，並返回其名稱 (CAB-)。
    """
    def search(container):
        for f in container.files.values():
            if isinstance(f, SerializedFile):
                return f.name 
        for f in container.files.values():
            if isinstance(f, BundleFile):
                found_name = search(f)
                if found_name:
                    return found_name
        return None
    return search(env)


# ==============================================================================
# --- 選單功能 ---
# ==============================================================================
def run_modding(text_folder_name: str, font_mode: str):
    """
    font_mode: "new" (修改字體) 或 "old" (原版字體)
    """
    # 設定資源路徑 (影響字體與紋理)
    if font_mode == "new":
        Config.CURRENT_ASSET_FOLDER = os.path.join(Config.CHT_FOLDER_PATH, "font_new")
        print(f"\n[模式] 使用修改版字體 (資源路徑: font_new)")
    else:
        Config.CURRENT_ASSET_FOLDER = os.path.join(Config.CHT_FOLDER_PATH, "font_old")
        print(f"\n[模式] 使用原版字體 (資源路徑: font_old)")

    print(f"[開始執行修改流程]")
    
    # 1. 檔案檢查
    paths_to_check = [
        Config.BUNDLE_FILE_PATH,
        Config.TEXT_ASSETS_FILE_PATH,
        Config.TITLE_BUNDLE_PATH,
        Config.MAP_FONT_BUNDLE_PATH,
        Config.CHT_FOLDER_PATH,
        Config.CURRENT_ASSET_FOLDER,
        Config.LOGO_SOURCE_FOLDER # 檢查 Logo 資料夾是否存在
    ]
    for path in paths_to_check:
        if not path or not os.path.exists(path):
            print(f"\n[錯誤] 關鍵路徑或檔案不存在: {path}")
            print(f"請確保此程式位於遊戲根目錄下，且資源檔案完整。")
            return

    print("\n[警告] 此操作將直接修改遊戲檔案。")
    confirm = input("您是否要繼續執行？ (輸入 'y' 確認): ").strip().lower()
    if confirm != "y":
        print("操作已取消。")
        return

    try:
        # 2. 備份
        if os.path.exists(Config.BACKUP_FOLDER):
            shutil.rmtree(Config.BACKUP_FOLDER)
        print("\n[步驟 1/4] 正在建立新的原始檔案備份...")
        backup_files = [
            Config.BUNDLE_FILE_PATH,
            Config.TEXT_ASSETS_FILE_PATH,
            Config.TITLE_BUNDLE_PATH,
            Config.MAP_FONT_BUNDLE_PATH
        ]
        
        for file_path in backup_files:
            backup_target = os.path.join(
                Config.BACKUP_FOLDER,
                os.path.relpath(file_path, Config.GAME_ROOT_PATH),
            )
            os.makedirs(os.path.dirname(backup_target), exist_ok=True)
            shutil.copy2(file_path, backup_target)
            
        print("新備份已建立至 'Backup' 資料夾。")

        # 3. 載入與修改
        print("\n[步驟 2/4] 正在載入資源並應用修改...")
        if os.path.exists(Config.TEMP_WORKSPACE_FOLDER):
            shutil.rmtree(Config.TEMP_WORKSPACE_FOLDER)
        os.makedirs(Config.TEMP_WORKSPACE_FOLDER, exist_ok=True)
        if Config.UNITY_VERSION:
            UnityPy.config.FALLBACK_UNITY_VERSION = Config.UNITY_VERSION

        generator = TypeTreeGenerator(Config.UNITY_VERSION)
        if sys.platform == "darwin":
            managed_folder_path = os.path.join(Config.SILKSONG_DATA_PATH, "Managed")
            generator.load_local_dll_folder(managed_folder_path)
        else:
            generator.load_local_game(Config.GAME_ROOT_PATH)

        bundle_env = UnityPy.load(Config.BUNDLE_FILE_PATH)
        bundle_env.typetree_generator = generator
        text_env = UnityPy.load(Config.TEXT_ASSETS_FILE_PATH)
        title_env = UnityPy.load(Config.TITLE_BUNDLE_PATH)
        title_env.typetree_generator = generator
        map_font_env = UnityPy.load(Config.MAP_FONT_BUNDLE_PATH)  
        map_font_env.typetree_generator = generator  

        # 執行修改
        process_bundle(bundle_env, skip_bold_atlas=(font_mode == "old"))
        process_text_assets(text_env, text_folder_name)
        process_title_bundle(title_env)

        # 只有在選擇 "修改字體 (new)" 時，才處理地圖字體引用
        if font_mode == "new":
            target_font_path_id = find_target_font_path_id(bundle_env)
            process_map_font_bundle(map_font_env, bundle_env, target_font_path_id)
        else:
            print("[資訊] 選擇原版字體模式，跳過地圖字體引用修改 (Map Font Bundle)。")

        print("資源修改完成。")

        # 4. 重新打包
        print("\n[步驟 3/4] 正在重新打包修改後的檔案...")
        modified_bundle_path = os.path.join(
            Config.TEMP_WORKSPACE_FOLDER, os.path.basename(Config.BUNDLE_FILE_PATH)
        )
        modified_text_assets_path = os.path.join(
            Config.TEMP_WORKSPACE_FOLDER, os.path.basename(Config.TEXT_ASSETS_FILE_PATH)
        )
        modified_title_bundle_path = os.path.join(
            Config.TEMP_WORKSPACE_FOLDER, os.path.basename(Config.TITLE_BUNDLE_PATH)
        )
        modified_map_font_path = os.path.join(
            Config.TEMP_WORKSPACE_FOLDER, os.path.basename(Config.MAP_FONT_BUNDLE_PATH)
        )  
        
        with open(modified_bundle_path, "wb") as f:
            f.write(bundle_env.file.save())
        with open(modified_text_assets_path, "wb") as f:
            f.write(text_env.file.save())
        with open(modified_title_bundle_path, "wb") as f:
            f.write(title_env.file.save())
        with open(modified_map_font_path, "wb") as f:
            f.write(map_font_env.file.save())  
        print("打包完成。")

        # 5. 覆蓋檔案
        print("\n[步驟 4/4] 正在用新檔案覆蓋遊戲檔案...")
        shutil.move(modified_bundle_path, Config.BUNDLE_FILE_PATH)
        shutil.move(modified_text_assets_path, Config.TEXT_ASSETS_FILE_PATH)
        shutil.move(modified_title_bundle_path, Config.TITLE_BUNDLE_PATH)
        shutil.move(modified_map_font_path, Config.MAP_FONT_BUNDLE_PATH)  
        print("覆蓋完成！")
        print("\n== 所有操作已成功完成！==")

    except Exception as e:
        print(f"\n[嚴重錯誤] 操作過程中發生錯誤: {e}")
        traceback.print_exc()
    finally:
        if os.path.exists(Config.TEMP_WORKSPACE_FOLDER):
            shutil.rmtree(Config.TEMP_WORKSPACE_FOLDER)


def restore_backup():
    print("\n[開始執行還原備份流程]")
    if not os.path.exists(Config.BACKUP_FOLDER):
        print("[錯誤] 找不到 'Backup' 資料夾，無法還原。")
        return
    try:
        # 定義需要還原的檔案列表
        files_to_restore = [
            (Config.BUNDLE_FILE_PATH, "fonts_assets_chinese.bundle"),
            (Config.TEXT_ASSETS_FILE_PATH, "resources.assets"),
            (Config.TITLE_BUNDLE_PATH, "title.spriteatlas.bundle"),
            (Config.MAP_FONT_BUNDLE_PATH, "maps_assets_all.bundle"),
        ]

        print("正在從 'Backup' 資料夾還原原始檔案...")
        for original_path, filename in files_to_restore:
            backup_path = os.path.join(
                Config.BACKUP_FOLDER,
                os.path.relpath(original_path, Config.GAME_ROOT_PATH),
            )
            
            if os.path.exists(backup_path):
                # 確保目標資料夾存在
                os.makedirs(os.path.dirname(original_path), exist_ok=True)
                shutil.copy2(backup_path, original_path)
                print(f"  - 已還原: {filename}")
            else:
                print(f"  - [警告] 備份中找不到 {filename}，跳過。")

        print("\n== 檔案還原程序結束！==")
    except Exception as e:
        print(f"\n[嚴重錯誤] 還原過程中發生錯誤: {e}")
        traceback.print_exc()


def show_about():
    print("\n" + "=" * 60)
    print("== 關於此工具 ==")
    print("\n本工具全程使用AI完成。")
    print("\n核心: Python")
    print("  - 資源庫: UnityPy")
    print("  - 自動化腳本: Gemini大神")
    print("\n不提供相關技術支援。")
    print("=" * 60)


# ==============================================================================
# --- 腳本核心邏輯 (處理 Unity 資源) ---
# ==============================================================================
def find_target_font_path_id(font_bundle_env):
    """在 fonts_assets_chinese.bundle 中查找目標字體的 PathID"""
    print("[資訊] 正在查找目標字體 PathID...")
    target_names = {"chinese_body_bold", "do_not_use_chinese_body_bold"}
    for obj in font_bundle_env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name in target_names:
                    print(
                        f"  - [資訊] 找到目標字體 '{data.m_Name}'，PathID: {obj.path_id}"
                    )
                    return obj.path_id
            except Exception:
                continue
    print(
        "  - [警告] 未在 fonts_assets_chinese.bundle 中找到目標字體。"
    )
    return None


def process_map_font_bundle(map_font_env, font_bundle_env, target_font_path_id):
    """修改 maps_assets_all.bundle，增加對 defaultFont 的檢查"""
    if not target_font_path_id:
        return

    print("[資訊] 開始處理 Map Font Bundle...")

    def find_main_asset_file(container):
        for f in container.files.values():
            if isinstance(f, SerializedFile):
                return f
        for f in container.files.values():
            if isinstance(f, BundleFile):
                found = find_main_asset_file(f)
                if found:
                    return found
        return None

    main_asset_file = find_main_asset_file(map_font_env)
    if not main_asset_file:
        print("  - [錯誤] 在 maps_assets_all.bundle 中找不到主要的 asset 檔案。")
        return

    target_bundle_internal_name = find_cab_name_in_bundle(font_bundle_env)
    if not target_bundle_internal_name:
        print(f"  - [錯誤] 無法在 '{Config.BUNDLE_FILE_PATH}' 中確定內部 CAB 名称。")
        return
    
    # 查找或創建 FileID
    font_bundle_file_id = -1
    for i, external in enumerate(main_asset_file.externals):
        if (
            os.path.basename(external.path.replace("\\", "/"))
            == target_bundle_internal_name
        ):
            font_bundle_file_id = i + 1
            break
            
    if font_bundle_file_id == -1:
        print(f"  - [資訊] 正在添加對 '{target_bundle_internal_name}' 的外部引用...")
        new_external = FileIdentifier.__new__(FileIdentifier)
        new_external.path = (
            f"archive:/{target_bundle_internal_name}/{target_bundle_internal_name}"
        )
        if main_asset_file.header.version >= 5:
            new_external.guid = uuid.uuid4().bytes
            new_external.type = 2
        if main_asset_file.header.version >= 6:
            new_external.temp_empty = ""
        main_asset_file.externals.append(new_external)
        font_bundle_file_id = len(main_asset_file.externals)

    # 修改物件引用
    modified_count = 0
    for obj in main_asset_file.objects.values():
        if obj.type.name == "MonoBehaviour":
            try:
                tree = obj.read_typetree()
                if "fontZH" in tree and isinstance(tree["fontZH"], dict):
                    tree["fontZH"]["m_FileID"] = font_bundle_file_id
                    tree["fontZH"]["m_PathID"] = target_font_path_id
                    obj.save_typetree(tree)
                    modified_count += 1
            except Exception:
                continue

    if modified_count > 0:
        print(f"  - [成功] 已成功修改 {modified_count} 個地圖文本物件的字體引用。")
    else:
        print("  - [警告] 未找到任何需要修改的目標地圖文本物件。")


def process_title_bundle(env):
    print("[資訊] 開始處理 Title Bundle...")
    TARGET_ASSET_NAME_PREFIX = "sactx-0-1024x1024-BC7-Title-"
    SOURCE_PNG_NAME = "logo.png"
    
    # 修改：強制使用獨立的 LOGO_SOURCE_FOLDER (CHT/logo)，不論字體選擇為何
    source_png_path = os.path.join(Config.LOGO_SOURCE_FOLDER, SOURCE_PNG_NAME)
    
    if not os.path.exists(source_png_path):
        print(f"  - [資訊] 找不到 '{source_png_path}'，跳過 Title Logo 替換。")
        return
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name.startswith(
                    TARGET_ASSET_NAME_PREFIX
                ):
                    print(f"  - [紋理] 找到目標 Title Logo: '{data.m_Name}'")
                    if not (data.m_StreamData and data.m_StreamData.path):
                        print("  - [警告] Title Logo 不是 .resS 格式，暫不支援。")
                        break
                    with Image.open(source_png_path) as img:
                        image_binary, new_format = (
                            Texture2DConverter.image_to_texture2d(
                                img,
                                data.m_TextureFormat,
                                data.assets_file.target_platform,
                            )
                        )
                    resS_path = os.path.basename(data.m_StreamData.path)
                    bundle_file = data.assets_file.parent
                    resS_file = bundle_file.files[resS_path]
                    new_ress_stream = BytesIO(image_binary)
                    wrapper = FileWrapper(resS_file, new_ress_stream)
                    bundle_file.files[resS_path] = wrapper
                    
                    data.m_StreamData.offset = 0
                    data.m_StreamData.size = len(image_binary)
                    data.m_Width = img.width
                    data.m_Height = img.height
                    data.m_TextureFormat = new_format
                    data.m_CompleteImageSize = len(image_binary)
                    if hasattr(data, "image_data"):
                        data.image_data = b""
                    data.save()
                    print(f"    - [紋理] 已更新 Title Logo。")
                    break
            except Exception as e:
                print(f"  - [嚴重警告] Title Logo 處理錯誤: {e}")


def process_font(obj_reader):
    try:
        data = obj_reader.read()
        asset_name = data.m_Name
        source_asset_name = (
            "chinese_body_bold"
            if asset_name == "do_not_use_chinese_body_bold"
            else asset_name
        )
        source_json_path = os.path.join(
            Config.CURRENT_ASSET_FOLDER, f"{source_asset_name}.json"
        )
        if os.path.exists(source_json_path):
            original_tree = obj_reader.read_typetree()
            with open(source_json_path, "r", encoding="utf-8") as f:
                source_dict = json.load(f)

            if "m_fontInfo" in source_dict:
                original_tree["m_fontInfo"] = source_dict["m_fontInfo"]
            if "m_glyphInfoList" in source_dict:
                original_tree["m_glyphInfoList"] = source_dict["m_glyphInfoList"]

            obj_reader.save_typetree(original_tree)
            print(f"  - [字型] 已更新 '{asset_name}' 的數據")
    except Exception as e:
        print(f"  - [警告] 處理字型 '{getattr(data, 'm_Name', '未知')}' 時出錯: {e}")


def process_material(obj_reader):
    try:
        tree = obj_reader.read_typetree()
        asset_name = tree.get("m_Name", "未知材質")

        if "m_SavedProperties" in tree and "m_Floats" in tree["m_SavedProperties"]:
            new_floats = []
            height_modified = False
            width_modified = False

            for key, value in tree["m_SavedProperties"]["m_Floats"]:
                if key == "_TextureHeight":
                    new_floats.append([key, 4096.0])
                    height_modified = True
                elif key == "_TextureWidth":
                    new_floats.append([key, 4096.0])
                    width_modified = True
                else:
                    new_floats.append([key, value])

            if not height_modified:
                new_floats.append(["_TextureHeight", 4096.0])
            if not width_modified:
                new_floats.append(["_TextureWidth", 4096.0])

            tree["m_SavedProperties"]["m_Floats"] = new_floats
            obj_reader.save_typetree(tree)
            print(f"  - [材質] 已更新 '{asset_name}' 的紋理尺寸屬性")

    except Exception as e:
        print(f"  - [警告] 處理材質 '{getattr(obj_reader, 'm_Name', '未知')}' 時出錯: {e}")


def process_embedded_texture(data):
    try:
        asset_name = data.m_Name
        source_asset_name = (
            "chinese_body_bold Atlas"
            if asset_name == "do_not_use_chinese_body_bold Atlas"
            else asset_name
        )
        safe_name = sanitize_filename(source_asset_name)
        source_png_path = os.path.join(Config.CURRENT_ASSET_FOLDER, f"{safe_name}.png")
        if os.path.exists(source_png_path):
            with Image.open(source_png_path) as img:
                data.image = img
                data.m_Width = img.width
                data.m_Height = img.height
                data.save()
                print(f"  - [紋理] 已替換 (內嵌) '{asset_name}'")
    except Exception as e:
        print(f"  - [警告] 處理內嵌紋理 '{data.m_Name}' 時出錯: {e}")


def process_ress_texture_group(texture_group):
    if not texture_group:
        return
    first_texture = texture_group[0]
    resS_path = os.path.basename(first_texture.m_StreamData.path)
    bundle_file = first_texture.assets_file.parent
    print(f"  - [紋理組] 正在處理 '{resS_path}' 中的 {len(texture_group)} 個紋理...")
    try:
        new_datas = []
        for tex_data in texture_group:
            asset_name = tex_data.m_Name
            source_asset_name = (
                "chinese_body_bold Atlas"
                if asset_name == "do_not_use_chinese_body_bold Atlas"
                else asset_name
            )
            safe_name = sanitize_filename(source_asset_name)
            source_png_path = os.path.join(Config.CURRENT_ASSET_FOLDER, f"{safe_name}.png")
            if os.path.exists(source_png_path):
                with Image.open(source_png_path) as img:
                    image_binary, new_format = Texture2DConverter.image_to_texture2d(
                        img,
                        tex_data.m_TextureFormat,
                        tex_data.assets_file.target_platform,
                    )
                    new_datas.append(
                        {
                            "original_obj": tex_data,
                            "image_binary": image_binary,
                            "new_format": new_format,
                            "img": img.copy(),
                        }
                    )

        if not new_datas:
            return

        new_ress_stream = BytesIO()
        current_offset = 0
        for data_dict in new_datas:
            data_dict["new_offset"] = current_offset
            new_ress_stream.write(data_dict["image_binary"])
            current_offset += len(data_dict["image_binary"])

        resS_file = bundle_file.files[resS_path]
        original_obj = (
            resS_file._original if isinstance(resS_file, FileWrapper) else resS_file
        )
        wrapper = FileWrapper(original_obj, new_ress_stream)
        bundle_file.files[resS_path] = wrapper
        print(f"    - [資訊] 已重建 '{resS_path}'，新大小: {current_offset} bytes")

        for data_dict in new_datas:
            tex_data = data_dict["original_obj"]
            img = data_dict["img"]
            tex_data.m_StreamData.offset = data_dict["new_offset"]
            tex_data.m_StreamData.size = len(data_dict["image_binary"])
            tex_data.m_Width = img.width
            tex_data.m_Height = img.height
            tex_data.m_TextureFormat = data_dict["new_format"]
            tex_data.m_CompleteImageSize = len(data_dict["image_binary"])
            if hasattr(tex_data, "image_data"):
                tex_data.image_data = b""
            tex_data.save()
            print(f"    - [紋理] 已更新 '{tex_data.m_Name}' 元數據")
    except Exception as e:
        print(f"  - [嚴重警告] 處理紋理組 '{resS_path}' 時發生錯誤: {e}")
        traceback.print_exc()


def process_bundle(env, skip_bold_atlas=False):
    """
    skip_bold_atlas: 如果為 True，則在處理紋理時會強制忽略 chinese_body_bold Atlas
    """
    print("[資訊] 正在分析與分類資源...")
    all_objects = []

    def find_all_objects(container):
        if hasattr(container, "files") and container.files is not None:
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
                if not (hasattr(data, "m_Name") and data.m_Name):
                    continue
                asset_name = data.m_Name

                # Font Logic
                if obj.type.name == "MonoBehaviour" and asset_name in [
                    "chinese_body",
                    "chinese_body_bold",
                    "do_not_use_chinese_body_bold",
                ]:
                    fonts_to_process.append(data)
                
                # Material Logic
                elif obj.type.name == "Material" and asset_name in [
                    "simsun_tmpro Material",
                    "chinese_body_bold Material",
                    "do_not_use_chinese_body_bold Material",
                ]:
                    materials_to_process.append(data)
                
                # Texture Logic
                elif obj.type.name == "Texture2D" and asset_name in [
                    "chinese_body Atlas",
                    "chinese_body_bold Atlas",
                    "do_not_use_chinese_body_bold Atlas",
                ]:
                    # 關鍵修改：如果是原版字體模式 (skip_bold_atlas=True)，且當前是 bold atlas，則跳過
                    if skip_bold_atlas and asset_name == "chinese_body_bold Atlas":
                        print("  - [略過] 原版字體模式：跳過 'chinese_body_bold Atlas'")
                        continue
                    
                    if data.m_StreamData and data.m_StreamData.path:
                        resS_path = os.path.basename(data.m_StreamData.path)
                        if resS_path not in textures_by_ress:
                            textures_by_ress[resS_path] = []
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


def process_text_assets(env, text_folder_name: str):
    """處理 resources.assets 中的文本替換"""
    current_text_source_folder = os.path.join(Config.CHT_FOLDER_PATH, text_folder_name)
    print(f"[文字] 來源資料夾: {text_folder_name}")

    text_target_assets = {
        "ZH_Achievements", "ZH_AutoSaveNames", "ZH_Belltown", "ZH_Bonebottom",
        "ZH_Caravan", "ZH_City", "ZH_Coral", "ZH_Crawl", "ZH_Credits List",
        "ZH_Deprecated", "ZH_Dust", "ZH_Enclave", "ZH_Error", "ZH_Fast Travel",
        "ZH_Forge", "ZH_General", "ZH_Greymoor", "ZH_Inspect", "ZH_Journal",
        "ZH_Lore", "ZH_MainMenu", "ZH_Map Zones", "ZH_Peak", "ZH_Pilgrims",
        "ZH_Prompts", "ZH_Quests", "ZH_Shellwood", "ZH_Shop", "ZH_Song",
        "ZH_Titles", "ZH_Tools", "ZH_UI", "ZH_Under", "ZH_Wanderers",
        "ZH_Weave", "ZH_Wilds",
    }

    count = 0
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data and data.m_Name in text_target_assets:
                source_txt_path = os.path.join(
                    current_text_source_folder, f"{data.m_Name}.txt"
                )
                if os.path.exists(source_txt_path):
                    with open(source_txt_path, "rb") as f:
                        local_bytes = f.read()
                    data.m_Script = local_bytes.decode("utf-8", "surrogateescape")
                    data.save()
                    count += 1
    print(f"  - [文字] 已替換 {count} 個文本檔案。")


# ==============================================================================
# --- 主程式入口 ---
# ==============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", help="Target: Windows, Linux, macOS", required=False)
    parser.add_argument("--root", help="Game root directory", required=False)
    args = parser.parse_args()

    if args.root:
        Config.GAME_ROOT_PATH = args.root

    initial_build_target = "Unknown"
    if args.build:
        build_arg_lower = args.build.lower()
        if build_arg_lower == "windows":
            initial_build_target = "Windows"
        elif build_arg_lower == "linux":
            initial_build_target = "Linux"
        elif build_arg_lower == "macos":
            initial_build_target = "macOS"

    detect_environment(game_build=initial_build_target)

    while True:
        if sys.platform == "win32":
            os.system("cls")
        else:
            os.system("clear")

        print("=" * 60)
        print("== 絲綢之歌繁體中文化工具 v1.20 ==")
        print("=" * 60)
        print(f"目前平台: {Config.PLATFORM_NAME} (輸入 'T' 可手動切換)")
        print(f"遊戲目錄: {Config.GAME_ROOT_PATH}")

        if not Config.BUNDLE_FILE_PATH or not os.path.exists(Config.BUNDLE_FILE_PATH):
            print(f"\n[警告] 找不到遊戲檔案。")

        print("\n請選擇要執行的操作：\n")
        print("  1. 執行繁體中文化 (進入詳細設定)")
        print("  2. 還原備份")
        print("  3. 關於")
        print("  4. 退出\n")

        choice = input(f"請輸入選項 [1-4] 或 T 切換平台: ").strip().lower()

        if choice == "1":
            # --- 子選單 1: 選擇翻譯版本 ---
            print("\n[翻譯版本選擇]")
            print("  1. 舊版官方簡中")
            print("  2. 繁體社群重譯")
            print("  3. 新版官方簡中 (修車組轉正)")
            trans_choice = input("請選擇翻譯版本 [1-3]: ").strip()
            
            folder_map = {
                "1": "Text",
                "2": "Text_Re",
                "3": "Text_Chs"
            }
            selected_text_folder = folder_map.get(trans_choice)
            
            if not selected_text_folder:
                print("無效的選擇，返回主選單。")
                time.sleep(1)
                continue

            # --- 子選單 2: 選擇字體版本 ---
            print("\n[字體版本選擇]")
            print("  1. 修改字體 (推薦)")
            print("  2. 原版字體 (不修改地圖字體")
            font_choice = input("請選擇字體版本 [1-2]: ").strip()

            font_mode = ""
            if font_choice == "1":
                font_mode = "new"
            elif font_choice == "2":
                font_mode = "old"
            else:
                print("無效的選擇，返回主選單。")
                time.sleep(1)
                continue
            
            # 執行 Modding
            run_modding(text_folder_name=selected_text_folder, font_mode=font_mode)

        elif choice == "2":
            restore_backup()
        elif choice == "3":
            show_about()
        elif choice == "4":
            print("程式即將退出。")
            time.sleep(1)
            break
        elif choice == "t":
            print("\n--- 手動切換平台 ---")
            print("  1. Windows")
            print("  2. Linux")
            print("  3. macOS")
            p_choice = input("請選擇新平台 [1-3]: ").strip()
            new_p = {"1": "Windows", "2": "Linux", "3": "macOS"}.get(p_choice)
            if new_p:
                detect_environment(game_build=new_p)
                print(f"平台已切換至: {Config.PLATFORM_NAME}")
                time.sleep(1)
            else:
                print("無效選項。")
                time.sleep(1)
        else:
            print("\n無效指令。")
            time.sleep(1)
            continue

        input("\n按下 Enter 鍵返回主選單...")


if __name__ == "__main__":
    main()
