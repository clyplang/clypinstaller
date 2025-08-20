# ClypInstaller

ClypInstaller is a utility designed to simplify the installation and uninstallation of the `clyp` Python package, especially for use with package managers like WinGet that require an executable installer. This project provides scripts to build a standalone executable from the `install.py` script using Nuitka, making it easy to distribute and install `clyp` on Windows, Linux, and macOS.

## Features
- Interactive or silent installation of the `clyp` Python package
- Option to specify Python interpreter and `clyp` version
- Uninstall support
- Cross-platform build scripts (Windows PowerShell and Unix shell)
- Designed for packaging with WinGet and similar tools

## Requirements

- Python 3.4 - 3.13
- [Nuitka](https://nuitka.net/) (for building the executable)
- [inquirer](https://pypi.org/project/inquirer/) Python package (for interactive prompts)

## Building the Executable

### Windows

1. Install Nuitka:

   ```powershell
   pip install nuitka
   ```

2. Run the build script:
   ```powershell
   ./build.ps1
   ```
   This will generate an executable from `install.py`.

### Linux/macOS
1. Install Nuitka:
   ```sh
   pip install nuitka
   ```
2. Run the build script:
   ```sh
   ./build.sh
   ```

## Usage

After building, distribute the generated executable. Users can run it to install or uninstall `clyp`:

- **Install latest version:**
  ```sh
  ./install.exe
  ```
- **Specify Python or version:**
  ```sh
  ./install.exe --python C:\Path\To\Python.exe --version 1.2.3
  ```
- **Uninstall:**
  ```sh
  ./install.exe --uninstall
  ```
- **Silent install:**
  ```sh
  ./install.exe --silent
  ```

## For Package Managers (e.g., WinGet)
- Use the built executable as the installer in your WinGet manifest.
- The script ensures all dependencies are handled and provides a user-friendly installation experience.

## License
MIT License
