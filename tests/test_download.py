"""Unit test retry unduhan + verifikasi SHA-256 (mock, tanpa internet)."""

import hashlib
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fh2_installer import port as port_module  # noqa: E402
from fh2_installer.port import (  # noqa: E402
    _sha256_of,
    download_port,
    fetch_expected_sha256,
)

FAKE_DATA = b"isi-zip-palsu-untuk-test" * 100


class _FakeResponse:
    """Respon urlopen tiruan: context manager + read() + headers."""

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk, self._pos = self._data[self._pos:], len(self._data)
            return chunk
        chunk = self._data[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk


def _urlopen_ok(*args, **kwargs):
    return _FakeResponse(FAKE_DATA)


def _urlopen_fail_twice_then_ok():
    calls = {"n": 0}

    def _impl(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise urllib.error.URLError("koneksi putus (tiruan)")
        return _FakeResponse(FAKE_DATA)

    _impl.calls = calls
    return _impl


class TestDownloadRetry(unittest.TestCase):
    def test_gagal_dua_kali_lalu_berhasil(self):
        """Koneksi putus 2x lalu berhasil — unduhan selesai."""
        impl = _urlopen_fail_twice_then_ok()
        logs = []
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch.object(
                port_module.urllib.request, "urlopen", side_effect=impl
            ):
                hasil = download_port(
                    dest=dest,
                    expected_size=len(FAKE_DATA),
                    verify_sha256=False,
                    log_cb=logs.append,
                )
            self.assertEqual(hasil, dest)
            self.assertEqual(dest.read_bytes(), FAKE_DATA)
            self.assertEqual(impl.calls["n"], 3)
            self.assertTrue(any("Mencoba lagi" in m for m in logs))

    def test_gagal_terus_mencoba_tiga_kali(self):
        """Koneksi selalu gagal — mencoba tepat 3 kali lalu menyerah."""
        calls = {"n": 0}

        def _always_fail(*args, **kwargs):
            calls["n"] += 1
            raise urllib.error.URLError("tidak ada internet (tiruan)")

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch.object(
                port_module.urllib.request, "urlopen", side_effect=_always_fail
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    download_port(
                        dest=dest,
                        expected_size=len(FAKE_DATA),
                        verify_sha256=False,
                    )
        self.assertEqual(calls["n"], 3)
        self.assertIn("3 percobaan", str(ctx.exception))
        self.assertFalse(dest.exists())

    def test_ukuran_tidak_cocok_dicoba_ulang(self):
        """File hasil unduhan ukurannya salah — dihapus dan dicoba ulang."""
        calls = {"n": 0}

        def _impl(*args, **kwargs):
            calls["n"] += 1
            return _FakeResponse(b"terlalu-pendek")

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch.object(
                port_module.urllib.request, "urlopen", side_effect=_impl
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    download_port(
                        dest=dest,
                        expected_size=len(FAKE_DATA),
                        verify_sha256=False,
                    )
        self.assertEqual(calls["n"], 3)
        self.assertIn("Ukuran file tidak cocok", str(ctx.exception))
        self.assertFalse(dest.exists())


class TestSha256(unittest.TestCase):
    def test_sha256_of(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.bin"
            path.write_bytes(FAKE_DATA)
            self.assertEqual(
                _sha256_of(path), hashlib.sha256(FAKE_DATA).hexdigest()
            )

    def test_fetch_expected_sha256_format_hash_spasi_nama(self):
        expected = hashlib.sha256(FAKE_DATA).hexdigest()
        body = f"{expected}  LavenderShift-0.2.0-windows-x64.zip\n".encode()
        with mock.patch.object(
            port_module.urllib.request, "urlopen",
            return_value=_FakeResponse(body),
        ):
            self.assertEqual(fetch_expected_sha256(), expected)

    def test_fetch_expected_sha256_gagal_kembali_none(self):
        """File .sha256 tidak bisa diambil — kembali None (lanjut ukuran saja)."""
        with mock.patch.object(
            port_module.urllib.request, "urlopen",
            side_effect=urllib.error.URLError("tidak ada internet (tiruan)"),
        ):
            self.assertIsNone(fetch_expected_sha256())

    def test_fetch_expected_sha256_isi_bukan_hash_kembali_none(self):
        with mock.patch.object(
            port_module.urllib.request, "urlopen",
            return_value=_FakeResponse(b"bukan-hash\n"),
        ):
            self.assertIsNone(fetch_expected_sha256())

    def test_download_verifikasi_sha256_cocok(self):
        expected = hashlib.sha256(FAKE_DATA).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch.object(
                port_module.urllib.request, "urlopen", side_effect=_urlopen_ok
            ), mock.patch.object(
                port_module, "fetch_expected_sha256", return_value=expected
            ):
                hasil = download_port(
                    dest=dest, expected_size=len(FAKE_DATA)
                )
            self.assertEqual(hasil, dest)

    def test_download_verifikasi_sha256_tidak_cocok_dicoba_ulang(self):
        """SHA-256 salah — file dihapus, dicoba ulang 3x, lalu menyerah."""
        wrong = "0" * 64
        calls = {"n": 0}

        def _impl(*args, **kwargs):
            calls["n"] += 1
            return _FakeResponse(FAKE_DATA)

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch.object(
                port_module.urllib.request, "urlopen", side_effect=_impl
            ), mock.patch.object(
                port_module, "fetch_expected_sha256", return_value=wrong
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    download_port(
                        dest=dest, expected_size=len(FAKE_DATA)
                    )
        self.assertEqual(calls["n"], 3)
        self.assertIn("SHA-256", str(ctx.exception))
        self.assertFalse(dest.exists())

    def test_download_tanpa_hash_rilis_tetap_lanjut(self):
        """Hash rilis tidak bisa diambil — unduhan tetap lanjut (ukuran saja)."""
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch.object(
                port_module.urllib.request, "urlopen", side_effect=_urlopen_ok
            ), mock.patch.object(
                port_module, "fetch_expected_sha256", return_value=None
            ):
                hasil = download_port(
                    dest=dest, expected_size=len(FAKE_DATA)
                )
            self.assertEqual(hasil, dest)
            self.assertEqual(dest.read_bytes(), FAKE_DATA)


if __name__ == "__main__":
    unittest.main()
