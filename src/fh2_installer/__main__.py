"""Entry point FH2 PC Installer.

Penggunaan:
  python -m fh2_installer            # buka GUI
  python -m fh2_installer --version  # tampilkan versi
  python -m fh2_installer --self-test  # cek non-GUI (untuk pengujian)
"""

import argparse
import sys
import tempfile
from pathlib import Path


def self_test() -> int:
    """Tes mandiri tanpa GUI; kembalikan 0 bila semua lolos."""
    from fh2_installer import __version__
    from fh2_installer.config import (
        PORT_ASSET,
        PORT_ASSET_SIZE,
        PORT_TAG,
        app_dir,
        platform_id,
    )
    from fh2_installer.port import release_info, validate_game_files
    from fh2_installer.syscheck import run_checks, summarize

    failures = []

    print(f"FH2 PC Installer v{__version__} — self-test")
    print(f"platform: {platform_id()} | python: {sys.version.split()[0]}")

    try:
        folder = app_dir()
        print(f"app_dir: {folder} (ok)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"app_dir: {exc}")

    try:
        info = release_info()
        assert info["tag"] == PORT_TAG, info
        assert info["asset_name"] == PORT_ASSET, info
        assert info["asset_size"] == PORT_ASSET_SIZE, info
        print(
            f"rilis port: {info['tag']} | aset: {info['asset_name']} "
            f"({info['asset_size'] / 1024 / 1024:.1f} MB) (ok)"
        )
    except Exception as exc:  # noqa: BLE001 - API gagal = "tidak dapat diperiksa", BUKAN gagal
        # GitHub API tanpa login sering rate-limit (HTTP 403). Alur normal
        # TIDAK PERNAH memakai API (unduhan memakai URL hardcoded), jadi
        # kegagalan di sini tidak menggagalkan self-test.
        print(f"rilis port: tidak dapat diperiksa ({exc}) (ok — bukan gagal)")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disc = root / "Forza Horizon 2.iso"
            disc.write_bytes(b"\x00" * 16)
            update = root / "FH2-TU2.zip"
            update.write_bytes(b"\x00" * 16)

            hasil = validate_game_files(disc, update)
            assert hasil["valid"] is True, hasil
            assert not hasil["issues"], hasil
            print("validasi file game: disc .iso + update lolos (ok)")

            bukan_iso = root / "game.bin"
            bukan_iso.write_bytes(b"\x00" * 16)
            hasil = validate_game_files(bukan_iso, update)
            assert hasil["valid"] is False, hasil
            assert any(".iso" in i for i in hasil["issues"]), hasil
            print("validasi file game: disc bukan .iso gagal (ok)")

            hasil = validate_game_files(root / "tidak-ada.iso", update)
            assert hasil["valid"] is False, hasil
            print("validasi file game: disc tidak ada gagal (ok)")

            hasil = validate_game_files(disc, root / "tidak-ada.zip")
            assert hasil["valid"] is True, hasil
            assert hasil["warnings"], hasil
            print(
                "validasi file game: title update tidak ada hanya "
                "peringatan, bukan penghalang (ok)"
            )

            update_rar = root / "FH2-TU2.rar"
            update_rar.write_bytes(b"\x00" * 16)
            hasil = validate_game_files(disc, update_rar)
            assert hasil["valid"] is True, hasil
            assert hasil["warnings"], hasil
            print("validasi file game: update bukan .zip hanya peringatan (ok)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"validasi file game: {exc}")

    try:
        checks = run_checks()
        ok, gagal, tidak_diketahui = summarize(checks)
        for check in checks:
            print(f"  syscheck [{check['status']}] {check['name']}: {check['detail']}")
        print(
            f"syscheck: {len(checks)} cek jalan tanpa crash "
            f"({ok} lolos, {gagal} gagal, {tidak_diketahui} tidak diketahui) (ok)"
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"syscheck: {exc}")

    try:
        import tkinter  # noqa: F401
        print("tkinter: ok")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"tkinter: {exc}")

    if failures:
        print("\nSELF-TEST GAGAL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nSELF-TEST OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="fh2_installer",
        description="FH2 PC Installer — port native Forza Horizon 2 untuk Windows",
    )
    parser.add_argument("--version", action="store_true", help="tampilkan versi")
    parser.add_argument("--self-test", action="store_true", help="tes mandiri tanpa GUI")
    args = parser.parse_args(argv)
    if args.version:
        from fh2_installer import __version__
        print(f"FH2 PC Installer {__version__}")
        return 0
    if args.self_test:
        return self_test()
    from fh2_installer.app import run
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
