# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec untuk FH2 PC Installer.

Dijalankan dari root proyek:  pyinstaller build/fh2_installer.spec --noconfirm
Hasil:
  Windows  -> dist/FH2PCInstaller.exe  (satu file; DLL runtime ikut terbundel)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent  # noqa: F821 - disediakan PyInstaller
ICON = str(PROJECT_ROOT / "assets" / "icon.ico") if sys.platform == "win32" else None

a = Analysis(
    [str(PROJECT_ROOT / "src" / "fh2_installer" / "__main__.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[(str(PROJECT_ROOT / "assets" / "icon.png"), "assets")],
    hiddenimports=["cpuinfo"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FH2PCInstaller",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
