# Gemini Code Assistant Context

## Project Overview

This project is a Python-based tool for applying a Traditional Chinese localization patch to the game "Hollow Knight: Silksong". The tool is designed to be user-friendly, providing a simple command-line interface to patch the game files and restore backups.

The core logic is implemented in `sk_cht.py`, which uses the `UnityPy` library to inspect and modify Unity game assets. The localization data, including fonts, textures, and text, is stored in the `CHT` directory.

## Building and Running

The tool is intended to be run as a standalone executable from the game's root directory. The `.github/workflows/Bulid.yml` file automates the build process using `PyInstaller`.

Example build command for Windows:
```bash
uv run pyinstaller --onefile --icon=sk.ico --add-data "CHT;CHT" --collect-all UnityPy --name="SilkSong_CHT_win" sk_cht.py
```

To run the tool, the user executes the generated file, which provides a menu with these options:
1.  **Apply Traditional Chinese Patch**
2.  **Restore Backup**
3.  **About**
4.  **Exit**

## Development Conventions

*   **Main Script:** `sk_cht.py` is the single entry point containing all logic.
*   **Key Technologies:**
    *   **UnityPy**: For reading/writing Unity asset files.
    *   **Pillow (PIL)**: For image processing.
    *   **etcpak**: For BC7 texture compression.
    *   **PyInstaller**: For creating standalone executables.
*   **Localization Data:** All assets are in the `CHT` directory (`Font`, `Png`, `Text`).
*   **Platform Support:** The script auto-detects Windows, macOS, and Linux to adjust file paths. It includes a specific workaround for macOS to correctly load the `TypeTreeGenerator`.
*   **Backup:** A `Backup` directory is automatically created for original game files.
*   **Temporary Files:** A `temp_workspace` directory is used for intermediate operations and is cleaned up afterward.

## Core Workflow

1.  **Startup:** A monkey-patch is applied to `UnityPy`'s `Texture2DConverter` to ensure correct BC7 texture compression via `etcpak`.
2.  **File Identification:** The tool targets three main game files for modification:
    *   `fonts_assets_chinese.bundle`: For font, material, and texture assets.
    *   `resources.assets`: For all localization text files (`TextAsset`).
    *   `title.spriteatlas.bundle`: For the main menu title logo (`Texture2D`).
3.  **Asset Processing:**
    *   **Fonts & Materials (`process_bundle`):** Modifies font assets (which are `MonoBehaviour` objects), `Material` properties, and font atlas textures (`Texture2D`). It correctly handles both embedded textures and those in external `.resS` files.
    *   **Game Text (`process_text_assets`):** Replaces the content of `TextAsset` objects with corresponding files from the `CHT/Text` directory.
    *   **Title Logo (`process_title_bundle`):** Specifically targets and replaces the game's title logo texture.
4.  **Repackaging:** The modified assets are saved into new files within the `temp_workspace`.
5.  **Finalization:** The newly created files overwrite the original game files, and the temporary workspace is removed.
