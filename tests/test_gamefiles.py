"""Unit test validasi file game (disc image FH2 USA + title update v2)."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fh2_installer.port import validate_game_files  # noqa: E402


def _make_files(root: Path, disc_name: str, update_name: str):
    disc = root / disc_name
    disc.write_bytes(b"\x00" * 16)
    update = root / update_name
    update.write_bytes(b"\x00" * 16)
    return disc, update


class TestValidateGameFiles(unittest.TestCase):
    def test_disc_iso_dan_update_lolos(self):
        with tempfile.TemporaryDirectory() as tmp:
            disc, update = _make_files(
                Path(tmp), "Forza Horizon 2.iso", "FH2-TU2.zip"
            )
            hasil = validate_game_files(disc, update)
            self.assertTrue(hasil["valid"])
            self.assertEqual(hasil["issues"], [])
            self.assertEqual(hasil["warnings"], [])

    def test_disc_bukan_iso_gagal(self):
        with tempfile.TemporaryDirectory() as tmp:
            disc, update = _make_files(Path(tmp), "game.bin", "FH2-TU2.zip")
            hasil = validate_game_files(disc, update)
            self.assertFalse(hasil["valid"])
            self.assertTrue(any(".iso" in i for i in hasil["issues"]))

    def test_disc_tidak_ada_gagal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            update = root / "FH2-TU2.zip"
            update.write_bytes(b"\x00" * 16)
            hasil = validate_game_files(root / "tidak-ada.iso", update)
            self.assertFalse(hasil["valid"])
            self.assertTrue(any("tidak ditemukan" in i for i in hasil["issues"]))

    def test_update_tidak_ada_hanya_peringatan(self):
        """v1.1.0: title update yang hilang HANYA peringatan, bukan penghalang."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disc = root / "Forza Horizon 2.iso"
            disc.write_bytes(b"\x00" * 16)
            hasil = validate_game_files(disc, root / "tidak-ada.zip")
            self.assertTrue(hasil["valid"])
            self.assertEqual(hasil["issues"], [])
            self.assertTrue(
                any("title update" in w.lower() for w in hasil["warnings"])
            )

    def test_update_belum_dipilih_hanya_peringatan(self):
        """v1.1.0: title update belum dipilih HANYA peringatan."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disc = root / "Forza Horizon 2.iso"
            disc.write_bytes(b"\x00" * 16)
            hasil = validate_game_files(disc, "")
            self.assertTrue(hasil["valid"])
            self.assertTrue(
                any("title update" in w.lower() for w in hasil["warnings"])
            )

    def test_update_bukan_zip_hanya_peringatan(self):
        """Title update yang bukan .zip tetap valid, hanya ada peringatan."""
        with tempfile.TemporaryDirectory() as tmp:
            disc, update = _make_files(
                Path(tmp), "Forza Horizon 2.iso", "FH2-TU2.rar"
            )
            hasil = validate_game_files(disc, update)
            self.assertTrue(hasil["valid"])
            self.assertEqual(hasil["issues"], [])
            self.assertTrue(hasil["warnings"])

    def test_kedua_file_kosong_gagal(self):
        """v1.1.0: disc yang hilang tetap masalah; title update hanya peringatan."""
        with tempfile.TemporaryDirectory() as tmp:
            hasil = validate_game_files("", "")
            self.assertFalse(hasil["valid"])
            self.assertEqual(len(hasil["issues"]), 1)
            self.assertTrue(
                any("title update" in w.lower() for w in hasil["warnings"])
            )


if __name__ == "__main__":
    unittest.main()
