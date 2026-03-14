#!/usr/bin/env python3
"""Build standalone DJOrganizer app with PyInstaller.

Usage: python3 build_standalone.py
Output: dist/DJOrganizer/ (folder with everything bundled)

The output folder can be zipped and distributed — no Python installation needed.
"""
import subprocess
import sys
import platform
from pathlib import Path

HERE = Path(__file__).parent

def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "DJOrganizer",
        "--noconfirm",
        "--clean",
        # Include Flask templates and static files
        "--add-data", f"templates{':' if platform.system() != 'Windows' else ';'}templates",
        "--add-data", f"static{':' if platform.system() != 'Windows' else ';'}static",
        # Include engine module
        "--add-data", f"engine{':' if platform.system() != 'Windows' else ';'}engine",
        # Hidden imports that PyInstaller might miss
        "--hidden-import", "flask",
        "--hidden-import", "tinytag",
        "--hidden-import", "engine.classifier",
        "--hidden-import", "engine.tagger",
        "--hidden-import", "engine.config",
        "--hidden-import", "engine.genres",
        "--hidden-import", "engine.keywords",
        # One-folder mode (easier to distribute than one-file)
        "--onedir",
        # Entry point
        "app.py",
    ]

    print(f"Building DJOrganizer for {platform.system()}...")
    result = subprocess.run(cmd, cwd=str(HERE))
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)

    dist_path = HERE / "dist" / "DJOrganizer"
    print(f"\nBuild complete: {dist_path}")
    print(f"To distribute: zip the '{dist_path}' folder")

    # Create a simple launcher script inside the dist folder
    if platform.system() == "Darwin":
        launcher = dist_path / "Launch DJOrganizer.command"
        launcher.write_text(
            '#!/bin/bash\n'
            'cd "$(dirname "$0")"\n'
            'open http://127.0.0.1:5555 &\n'
            './DJOrganizer\n'
        )
        launcher.chmod(0o755)
        print(f"Mac launcher: {launcher}")
    elif platform.system() == "Windows":
        launcher = dist_path / "Launch DJOrganizer.bat"
        launcher.write_text(
            '@echo off\r\n'
            'cd /d "%~dp0"\r\n'
            'start http://127.0.0.1:5555\r\n'
            'DJOrganizer.exe\r\n'
        )
        print(f"Windows launcher: {launcher}")

if __name__ == "__main__":
    build()
