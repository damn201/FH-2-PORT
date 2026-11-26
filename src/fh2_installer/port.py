"""Manajemen port Lavender Shift (Forza Horizon 2 Xbox 360): unduh, pasang,
verifikasi, dan validasi file game.

Port yang dipakai: arcanite24/lavender-shift v0.2.0 (BSD-3-Clause).
Aset: LavenderShift-0.2.0-windows-x64.zip (63,8 MB), berisi launcher
LavenderShiftLauncher.exe.
Cara pakai portnya (dari README port): ekstrak zip ke folder dengan path
pendek (mis. C:\\Games\\LavenderShift), buka LavenderShiftLauncher.exe,
pilih disc image + title update, tekan Set up, tunggu build pertama
15 menit–1 jam (bila berhenti, tekan Set up lagi), lalu tekan Play.
Game hasil build: source\\out\\build\\win-amd64-release\\lavender_shift.exe.
Save tersimpan di folder `user` di samping launcher.

Modul ini TIDAK menyertakan file game apa pun — pengguna wajib memakai
disc image Forza Horizon 2 USA (.iso) + title update v2 miliknya sendiri.
"""

import hashlib
import json
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .config import (
    BUILT_GAME_PARTS,
    LAUNCHER_EXE,
    MAX_DOWNLOAD_ATTEMPTS,
    PORT_ASSET,
    PORT_ASSET_SIZE,
    PORT_RELEASE_API,
    PORT_SHA256_URL,
    PORT_TAG,
    PORT_URL,
    USER_AGENT,
    downloads_dir,
    load_settings,
    save_settings,
)


class GitHubRateLimitError(RuntimeError):
    """GitHub API menolak (HTTP 403) — biasanya rate-limit tanpa login.

    Alur normal aplikasi TIDAK PERNAH memakai API GitHub (unduhan memakai
    URL hardcoded di config), jadi error ini hanya relevan untuk
    --self-test, dan di sana dilaporkan sebagai "tidak dapat diperiksa",
    bukan kegagalan.
    """


def _github_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def release_info(timeout: int = 30) -> dict:
    """Ambil info rilis port dari GitHub API.

    Hanya dipakai --self-test — alur normal TIDAK PERNAH memanggil ini.
    Mengembalikan {"tag", "asset_name", "asset_url", "asset_size"}.
    Melempar GitHubRateLimitError bila API menolak dengan HTTP 403
    (rate-limit GitHub tanpa login).
    """
    try:
        data = _github_json(PORT_RELEASE_API, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise GitHubRateLimitError(
                "GitHub API menolak (HTTP 403) — kemungkinan rate-limit "
                "tanpa login. Ini tidak memengaruhi unduhan port, karena "
                "unduhan memakai URL langsung, bukan API."
            ) from exc
        raise
    assets = [
        {
            "name": a["name"],
            "url": a["browser_download_url"],
            "size": a.get("size", 0),
        }
        for a in data.get("assets", [])
    ]
    for asset in assets:
        if asset["name"] == PORT_ASSET:
            return {
                "tag": data.get("tag_name", ""),
                "asset_name": asset["name"],
                "asset_url": asset["url"],
                "asset_size": asset["size"],
            }
    raise RuntimeError(
        f"Aset {PORT_ASSET} tidak ditemukan di rilis {data.get('tag_name', '?')}."
    )


def fetch_expected_sha256(url: str = PORT_SHA256_URL, timeout: int = 30) -> str | None:
    """Ambil hash SHA-256 yang diharapkan dari file .sha256 rilis.

    Format file .sha256 umumnya "<hash>  <nama-file>" atau hanya "<hash>".
    Mengembalikan hash huruf kecil, atau None bila file tidak bisa diambil
    atau isinya bukan hash SHA-256 yang valid (unduhan tetap lanjut dengan
    verifikasi ukuran saja).
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace").strip()
    except Exception:  # noqa: BLE001 - tidak ada internet / file tidak ada
        return None
    parts = text.split()
    if not parts:
        return None
    candidate = parts[0].lower()
    if len(candidate) == 64 and all(c in "0123456789abcdef" for c in candidate):
        return candidate
    return None


def _sha256_of(path: Path) -> str:
    """Hitung SHA-256 sebuah file (dibaca per 1 MB)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_once(
    url: str,
    dest: Path,
    progress_cb=None,
    timeout: int = 900,
) -> Path:
    """Satu kali percobaan unduh (tanpa retry). Mengembalikan path tujuan."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)
    return dest


def download_port(
    url: str = PORT_URL,
    dest: Path | None = None,
    progress_cb=None,
    expected_size: int = PORT_ASSET_SIZE,
    timeout: int = 900,
    attempts: int = MAX_DOWNLOAD_ATTEMPTS,
    verify_sha256: bool = True,
    log_cb=None,
) -> Path:
    """Unduh zip port dengan laporan progres (downloaded_bytes, total_bytes).

    - Mencoba ulang sampai `attempts` kali bila koneksi gagal/terputus.
    - Memverifikasi ukuran file hasil unduhan bila expected_size diberikan.
    - Bila verify_sha256 True, mengambil hash dari file .sha256 rilis dan
      memverifikasi SHA-256 file; bila hash tidak bisa diambil, unduhan
      tetap lanjut dengan verifikasi ukuran saja (tidak gagal).
    - File yang gagal/rusak dihapus sebelum percobaan berikutnya.
    - log_cb (bila diberikan) dipanggil dengan pesan Bahasa Indonesia
      sederhana untuk setiap percobaan.
    """
    dest = dest or (downloads_dir() / PORT_ASSET)
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        if log_cb and attempts > 1:
            log_cb(f"Mengunduh port (percobaan {attempt}/{attempts})...")
        try:
            _download_once(url, dest, progress_cb=progress_cb, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - koneksi gagal/terputus
            last_error = exc
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                pass
            if log_cb:
                if attempt < attempts:
                    log_cb(
                        f"Unduhan terputus ({exc}). Mencoba lagi "
                        f"({attempt + 1}/{attempts})..."
                    )
            continue
        # Ukuran file harus cocok — bila tidak, anggap rusak, coba lagi.
        if expected_size and dest.stat().st_size != expected_size:
            last_error = RuntimeError(
                f"Ukuran file tidak cocok: {dest.stat().st_size} byte, "
                f"diharapkan {expected_size} byte. File mungkin rusak."
            )
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                pass
            if log_cb and attempt < attempts:
                log_cb(
                    f"File hasil unduhan rusak (ukuran tidak cocok). "
                    f"Mencoba lagi ({attempt + 1}/{attempts})..."
                )
            continue
        # Verifikasi SHA-256 bila hash rilis bisa diambil.
        if verify_sha256:
            expected = fetch_expected_sha256()
            if expected is not None:
                actual = _sha256_of(dest)
                if actual != expected:
                    last_error = RuntimeError(
                        "SHA-256 file tidak cocok dengan yang diterbitkan "
                        "di GitHub. File mungkin rusak atau tertukar."
                    )
                    try:
                        dest.unlink(missing_ok=True)
                    except OSError:
                        pass
                    if log_cb and attempt < attempts:
                        log_cb(
                            "Verifikasi SHA-256 gagal. "
                            f"Mencoba lagi ({attempt + 1}/{attempts})..."
                        )
                    continue
                if log_cb:
                    log_cb("Verifikasi SHA-256 cocok.")
            elif log_cb:
                log_cb(
                    "Hash SHA-256 rilis tidak bisa diambil — lanjut dengan "
                    "verifikasi ukuran saja."
                )
        return dest
    raise RuntimeError(
        f"Unduhan gagal setelah {attempts} percobaan. "
        f"Periksa koneksi internetmu, lalu tekan MAIN lagi. "
        f"Error terakhir: {last_error}"
    )


def extract_port(zip_path: Path, install_dir: Path) -> Path:
    """Ekstrak zip port ke folder install. Mengembalikan folder install."""
    zip_path = Path(zip_path)
    install_dir = Path(install_dir)
    if not zip_path.is_file():
        raise RuntimeError(f"File zip tidak ditemukan: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(f"File bukan zip yang valid: {zip_path}")
    install_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(path=install_dir)
    return install_dir


def find_launcher(install_dir: Path | str) -> Path | None:
    """Cari LavenderShiftLauncher.exe di folder install (termasuk subfolder).

    Perbandingan nama tidak membedakan huruf besar/kecil.
    """
    root = Path(install_dir)
    if not root.is_dir():
        return None
    target = LAUNCHER_EXE.lower()
    direct = root / LAUNCHER_EXE
    if direct.is_file():
        return direct
    for candidate in root.rglob("*"):
        if candidate.is_file() and candidate.name.lower() == target:
            return candidate
    return None


def verify_port(install_dir: Path | str) -> Path | None:
    """Path bila port sudah terpasang (LavenderShiftLauncher.exe ditemukan)."""
    return find_launcher(install_dir)


def install_port(
    install_dir: Path | str,
    progress_cb=None,
    log_cb=None,
) -> Path:
    """Unduh (retry 3x + verifikasi ukuran + SHA-256) + ekstrak port ke
    folder install. Mengembalikan path launcher.

    Menyimpan install_dir dan versi port ke settings.
    """
    install_dir = Path(install_dir)
    zip_path = download_port(progress_cb=progress_cb, log_cb=log_cb)
    extract_port(zip_path, install_dir)
    exe = find_launcher(install_dir)
    if exe is None:
        raise RuntimeError(
            "Port berhasil diunduh dan diekstrak, tetapi "
            f"{LAUNCHER_EXE} tidak ditemukan di folder install."
        )
    settings = load_settings()
    settings["install_dir"] = str(install_dir)
    settings["port_version"] = PORT_TAG
    settings["port_exe"] = str(exe)
    save_settings(settings)
    return exe


def validate_game_files(disc_iso: Path | str, title_update: Path | str) -> dict:
    """Validasi file game: disc image FH2 USA (.iso) + title update v2.

    Aturan v1.1.0 (longgar — tidak ada yang memblokir MAIN):
    - Disc .iso tetap divalidasi keberadaannya (harus ada dan berakhiran
      .iso) — masalahnya masuk "issues".
    - Title update v2 yang hilang / tidak ditemukan HANYA menjadi
      peringatan ("warnings"), BUKAN penghalang: launcher itu sendiri yang
      meminta kedua file itu di GUI-nya, jadi pengguna tetap bisa lanjut
      dan memilihnya di sana.

    Mengembalikan:
      {"valid": bool (False hanya bila ada masalah disc),
       "issues": [masalah disc],
       "warnings": [peringatan, tidak membuat tidak valid],
       "detail": str}
    """
    issues: list[str] = []
    warnings: list[str] = []

    disc = Path(disc_iso) if disc_iso else Path("")
    update = Path(title_update) if title_update else Path("")

    if not str(disc_iso).strip():
        issues.append(
            "File disc .iso belum dipilih. Launcher butuh disc image "
            "Forza Horizon 2 USA (.iso) — siapkan filenya, lalu pilih di "
            "launcher saat Set up."
        )
    elif not disc.is_file():
        issues.append(
            f"File disc tidak ditemukan: {disc}. Periksa lagi lokasi "
            "file disc image Forza Horizon 2 USA (.iso) milikmu."
        )
    elif disc.suffix.lower() != ".iso":
        issues.append(
            f"File disc harus berakhiran .iso (file ini: {disc.name}). "
            "Pilih disc image Forza Horizon 2 USA berformat .iso."
        )

    if not str(title_update).strip():
        warnings.append(
            "File title update v2 belum dipilih. Launcher butuh title "
            "update v2 — siapkan filenya, lalu pilih di launcher saat "
            "Set up."
        )
    elif not update.is_file():
        warnings.append(
            f"File title update tidak ditemukan: {update}. Launcher butuh "
            "title update v2 — siapkan filenya, lalu pilih di launcher "
            "saat Set up."
        )
    elif update.suffix.lower() != ".zip":
        warnings.append(
            f"File title update biasanya berformat .zip (file ini: "
            f"{update.name}). Pastikan ini memang file title update v2."
        )

    valid = not issues
    if valid and not warnings:
        detail = (
            "File game valid: disc image FH2 USA (.iso) dan title update v2 "
            "ditemukan."
        )
    elif valid:
        detail = "File game OK, dengan catatan: " + " ".join(warnings)
    else:
        detail = "File game bermasalah — " + " ".join(issues)
    return {
        "valid": valid,
        "issues": issues,
        "warnings": warnings,
        "detail": detail,
    }


def find_built_game(install_dir: Path | str) -> Path | None:
    """Cari game hasil build pertama (lavender_shift.exe).

    Game ini baru ada setelah pengguna menekan Set up di launcher dan
    build pertama selesai (15 menit–1 jam).
    """
    root = Path(install_dir)
    if not root.is_dir():
        return None
    candidate = root.joinpath(*BUILT_GAME_PARTS)
    if candidate.is_file():
        return candidate
    target = BUILT_GAME_PARTS[-1].lower()
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() == target:
            return path
    return None


def launch_launcher(install_dir: Path | str) -> tuple[bool, str]:
    """Jalankan LavenderShiftLauncher.exe dari folder install."""
    exe = find_launcher(install_dir)
    if exe is None:
        return False, (
            "Port belum terpasang. Tekan MAIN lagi untuk mengunduhnya."
        )
    try:
        subprocess.Popen(
            [str(exe)],
            cwd=str(Path(exe).parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, f"Tidak bisa menjalankan {LAUNCHER_EXE}: {exc}"
    return True, (
        f"{LAUNCHER_EXE} dibuka. Di dalam launcher: pilih disc image + "
        "title update, tekan Set up, tunggu build pertama (15 menit–1 jam), "
        "lalu tekan Play."
    )


def launch_game(install_dir: Path | str) -> tuple[bool, str]:
    """Jalankan game hasil build (lavender_shift.exe) bila sudah ada."""
    exe = find_built_game(install_dir)
    if exe is None:
        return False, (
            "Game hasil build belum ada. Buka launcher dulu "
            f"({LAUNCHER_EXE}), pilih disc image + title update, "
            "tekan Set up, dan tunggu build pertama selesai "
            "(15 menit–1 jam) sebelum menekan MAIN LANGSUNG."
        )
    try:
        subprocess.Popen(
            [str(exe)],
            cwd=str(Path(exe).parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, f"Tidak bisa menjalankan {exe.name}: {exc}"
    return True, (
        "Forza Horizon 2 dibuka. Tekan F6 di dalam game untuk settings. "
        "Save tersimpan di folder 'user' di samping launcher."
    )


def open_folder(path: Path | str) -> tuple[bool, str]:
    """Buka folder di File Explorer (Windows) / file manager lainnya."""
    import platform

    target = Path(path)
    if not target.is_dir():
        return False, f"Folder tidak ditemukan: {target}"
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["explorer", str(target)])
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError as exc:
        return False, f"Tidak bisa membuka folder: {exc}"
    return True, f"Membuka folder: {target}"
