import os
import sys
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
SOX_DIR = PROJECT_DIR / "tools" / "sox"


def install_python_dependencies():
    print("Installing Python dependencies...")

    requirements = PROJECT_DIR / "requirements.txt"

    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(requirements)
    ])


def check_sox():
    sox_exe = SOX_DIR / "sox.exe"

    if sox_exe.exists():
        print("SoX found.")
        return True

    print("SoX was not found.")
    return False


def main():
    print("=" * 50)
    print("KineTex Installer")
    print("=" * 50)

    print(f"Python: {sys.executable}")
    print()

    install_python_dependencies()

    print()

    if not check_sox():
        print("WARNING: SoX is missing.")
        print("Please install SoX or place sox.exe in:")
        print(SOX_DIR)

    print()
    print("=" * 50)
    print("Installation complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()