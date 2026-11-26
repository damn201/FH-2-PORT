"""Konstanta dan pengaturan FH2 PC Installer (stdlib saja)."""

import json
import os
import platform
from pathlib import Path

APP_DIR_NAME = "FH2PCInstaller"

# --- Port native yang dipakai (arcanite24/lavender-shift) ---
PORT_REPO = "arcanite24/lavender-shift"
PORT_TAG = "v0.2.0"
PORT_ASSET = "LavenderShift-0.2.0-windows-x64.zip"
PORT_URL = (
    f"https://github.com/{PORT_REPO}/releases/download/{PORT_TAG}/{PORT_ASSET}"
)
PORT_SHA256_URL = PORT_URL + ".sha256"
PORT_RELEASE_API = (
    f"https://api.github.com/repos/{PORT_REPO}/releases/tags/{PORT_TAG}"
)
PORT_LICENSE = "BSD-3-Clause"
LAUNCHER_EXE = "LavenderShiftLauncher.exe"
# Game hasil build pertama (relatif terhadap folder install port).
BUILT_GAME_PARTS = (
    "source", "out", "build", "win-amd64-release", "lavender_shift.exe"
)
BUILT_GAME_REL = "\\".join(BUILT_GAME_PARTS)

# Ukuran aset yang terverifikasi (26 Nov 2026): 66.945.128 byte = 63,8 MB.
PORT_ASSET_SIZE = 66945128

# Berapa kali unduhan port dicoba ulang bila koneksi gagal/terputus.
MAX_DOWNLOAD_ATTEMPTS = 3

# --- Syarat minimum PC (dari README port) ---
MIN_WINDOWS_BUILD = 18362  # Windows 10 versi 1903 (lantai wajar; README: Win 10/11)
MIN_DISK_GB = 20  # port 64 MB + game ~20 GB
# CPU wajib punya AVX2 (Intel Haswell 2013+ / AMD Ryzen/Zen+).
REQUIRED_CPU_FLAGS = ("avx2",)

USER_AGENT = "FH2PCInstaller/1.1 (+https://github.com/arcanite24/lavender-shift)"


def platform_id() -> str:
    """'windows' | 'macos' | 'linux' | 'unknown'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return "unknown"


def is_frozen() -> bool:
    """True saat berjalan sebagai binary hasil PyInstaller."""
    import sys

    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Folder data FH2 PC Installer milik pengguna (dibuat bila belum ada)."""
    pid = platform_id()
    if pid == "windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif pid == "macos":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    folder = base / APP_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def downloads_dir() -> Path:
    folder = app_dir() / "downloads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def settings_path() -> Path:
    return app_dir() / "settings.json"


def default_install_dir() -> str:
    """Folder install bawaan port: path pendek (disarankan README port)."""
    if platform_id() == "windows":
        return r"C:\Games\LavenderShift"
    return str(Path.home() / "LavenderShift")


def default_settings() -> dict:
    return {
        "install_dir": "",
        "disc_iso": "",
        "title_update": "",
        "game_validated": False,
        "port_version": "",
        "port_exe": "",
    }


def load_settings() -> dict:
    settings = default_settings()
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            settings.update(data)
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    settings_path().write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )
