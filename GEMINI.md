# Gemini Code Assistant Context

## Project Overview

This project is a Python-based tool for applying a Traditional Chinese localization patch to the game "Hollow Knight: Silksong". The tool is designed to be user-friendly, providing a simple command-line interface to patch the game files and restore backups.

The core logic is implemented in `sk_cht.py`, which uses the `UnityPy` library to inspect and modify Unity game assets. The localization data, including fonts, textures, and text, is stored in the `CHT` directory.

The project is set up to be built into a standalone executable using `PyInstaller`, with platform-specific configurations for Windows, macOS, and Linux.

## Building and Running

The tool is intended to be run as a standalone executable from the game's root directory. The `pyinstaller` command, configured in `.github/workflows/Bulid.yml`, is used to build the executable from the main script `sk_cht.py`.

To run the tool, the user executes the generated file. The tool provides a menu with the following options:

1.  **Apply Traditional Chinese Patch:** Modifies the game files to apply the localization.
2.  **Restore Backup:** Reverts the changes from a backup.
3.  **About:** Displays information about the tool.
4.  **Exit:** Exits the tool.

## Development Conventions

*   **Main Script:** The main entry point and core logic are in `sk_cht.py`.
*   **Localization Data:** All localization assets are stored in the `CHT` directory, organized into `Font`, `Png`, and `Text` subdirectories.
*   **Dependencies:** Project dependencies are listed in `requirements.txt`.
*   **Platform Support:** The script includes logic to automatically detect the operating system (Windows, macOS, Linux) and adjust file paths accordingly. It contains a specific workaround for macOS to correctly load the `TypeTreeGenerator` from the game's `Managed` folder.
*   **Backup:** The tool automatically creates a backup of the original game files in a `Backup` directory before applying any changes.
*   **Temporary Files:** A `temp_workspace` directory is used for intermediate file operations and is cleaned up afterward.
*   **Core Logic (`sk_cht.py`):**
    *   **BC7 Patch:** Applies a monkey-patch to `UnityPy`'s `Texture2DConverter` at startup to correctly handle BC7 texture compression using the `etcpak` library.
    *   **File Modification:** The script targets and modifies three main game files:
        1.  `fonts_assets_chinese.bundle`: For font, material, and texture assets.
        2.  `resources.assets`: For all localization text files (`TextAsset`).
        3.  `title.spriteatlas.bundle`: For the main menu title logo (`Texture2D`).
    *   **Asset Processing:**
        *   `process_bundle`: Handles the complex modification of fonts (`MonoBehaviour`), materials (`Material`), and font atlas textures (`Texture2D`). It correctly processes both embedded textures and textures stored in external `.resS` files.
        *   `process_text_assets`: Iterates through `TextAsset` objects and replaces their content with the corresponding files from the `CHT/Text` directory.
        *   `process_title_bundle`: Specifically targets and replaces the game's title logo texture.