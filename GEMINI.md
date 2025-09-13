# Gemini Code Assistant Context

## Project Overview

This project is a Python-based tool for applying a Traditional Chinese localization patch to the game "Hollow Knight: Silksong". The tool is designed to be user-friendly, providing a simple command-line interface to patch the game files and restore backups.

The core logic is implemented in `sk_cht.py`, which uses the `UnityPy` library to inspect and modify Unity game assets. The localization data, including fonts, textures, and text, is stored in the `CHT` directory.

The project is set up to be built into a standalone executable using `PyInstaller`, with platform-specific configurations for Windows, macOS, and Linux.

## Building and Running

The tool is intended to be run as a standalone executable. The `pyinstaller` command can be used to build the executable from the main script `sk_cht.py`.

To run the tool, execute the generated file in the root directory of the game. The tool provides a menu with the following options:

1.  **Apply Traditional Chinese Patch:** Modifies the game files to apply the localization.
2.  **Restore Backup:** Reverts the changes from a backup.
3.  **About:** Displays information about the tool.
4.  **Exit:** Exits the tool.

## Development Conventions

*   **Main Script:** The main entry point and core logic are in `sk_cht.py`.
*   **Localization Data:** All localization assets are stored in the `CHT` directory, organized into `Font`, `Png`, and `Text` subdirectories.
*   **Dependencies:** Project dependencies are listed in `requirements.txt`.
*   **Platform Support:** The script includes logic to handle different file paths for Windows, macOS, and Linux.
*   **Backup:** The tool automatically creates a backup of the original game files in a `Backup` directory before applying any changes.
*   **Temporary Files:** A `temp_workspace` directory is used for intermediate file operations and is cleaned up afterward.
