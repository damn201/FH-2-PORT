"""Antarmuka grafis FH2 PC Installer v1.1.0 — SATU LAYAR (Tkinter, Bahasa
Indonesia).

Tidak ada tab lagi. Pengguna cukup: pilih file game, tekan MAIN, langsung
main. Semua langkah berjalan otomatis saat MAIN ditekan, dan bisa
dilanjutkan (resumable): langkah yang sudah selesai dilewati.

Alur MAIN:
  1. Cek sistem — hanya info/peringatan, TIDAK PERNAH memblokir MAIN.
  2. Unduh + ekstrak port Lavender Shift v0.2.0 — dilewati bila
     LavenderShiftLauncher.exe sudah ada (retry 3x + verifikasi ukuran
     + SHA-256 bila bisa).
  3. Validasi file game — hanya peringatan, TIDAK PERNAH memblokir MAIN
     (title update yang hilang hanya peringatan; launcher sendiri yang
     meminta kedua file itu di GUI-nya).
  4. Jalankan LavenderShiftLauncher.exe.

Operasi panjang berjalan di thread terpisah agar jendela tidak membeku;
progres dilaporkan lewat queue + after(). Bila ada langkah gagal, error
ditulis ke log beserta "yang harus dilakukan", dan pengguna cukup menekan
MAIN lagi untuk melanjutkan dari langkah terakhir yang berhasil.
"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .config import (
    LAUNCHER_EXE,
    PORT_ASSET,
    PORT_TAG,
    default_install_dir,
    load_settings,
    save_settings,
)
from .port import (
    download_port,
    extract_port,
    find_launcher,
    launch_launcher,
    open_folder,
    validate_game_files,
)
from .syscheck import FAIL, run_checks


def _asset_path(name: str) -> Path | None:
    """Cari file aset (berfungsi saat dijalankan dari source maupun frozen)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
    else:
        base = Path(__file__).resolve().parents[2]
    candidate = base / "assets" / name
    return candidate if candidate.is_file() else None


def _short_name(path: str) -> str:
    """Nama file saja (untuk label), atau '' bila kosong."""
    return Path(path).name if path.strip() else ""


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"FH2 PC Installer v{__version__}")
        self.geometry("720x640")
        self.minsize(640, 560)
        icon = _asset_path("icon.png")
        if icon is not None:
            try:
                self._icon_photo = tk.PhotoImage(file=str(icon))
                self.iconphoto(True, self._icon_photo)
            except tk.TclError:
                pass

        self.settings = load_settings()
        self.queue: queue.Queue = queue.Queue()
        self._running = False
        self.disc_var = tk.StringVar(value=self.settings.get("disc_iso") or "")
        self.update_var = tk.StringVar(value=self.settings.get("title_update") or "")

        style = ttk.Style()
        style.configure("Big.TButton", font=("TkDefaultFont", 14, "bold"))

        self._build_widgets()
        self._refresh_labels()
        self.log(
            "Siap. Pilih file game di atas (boleh kosong dulu), lalu tekan MAIN."
        )
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Layout — satu layar
    # ------------------------------------------------------------------

    def _build_widgets(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main, text="FH2 PC Installer",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            main,
            text="Port native Forza Horizon 2 (Xbox 360) untuk Windows — "
                 "BUKAN emulator. Butuh disc USA (.iso) + title update v2 "
                 "milikmu sendiri.",
            wraplength=680,
        ).pack(anchor="w", pady=(2, 10))

        # --- 1. File Game ---
        game = ttk.LabelFrame(main, text="1. File Game", padding=10)
        game.pack(fill="x", pady=(0, 8))

        row = ttk.Frame(game)
        row.pack(fill="x", pady=(0, 4))
        ttk.Button(
            row, text="Pilih Disc (.iso)", command=self._pick_disc,
        ).pack(side="left")
        self.disc_label = ttk.Label(row, text="", wraplength=480)
        self.disc_label.pack(side="left", padx=(8, 0))

        row2 = ttk.Frame(game)
        row2.pack(fill="x")
        ttk.Button(
            row2, text="Pilih Title Update v2", command=self._pick_update,
        ).pack(side="left")
        self.update_label = ttk.Label(row2, text="", wraplength=480)
        self.update_label.pack(side="left", padx=(8, 0))

        # --- 2. Folder Install ---
        folder = ttk.LabelFrame(main, text="2. Folder Install", padding=10)
        folder.pack(fill="x", pady=(0, 8))
        row3 = ttk.Frame(folder)
        row3.pack(fill="x")
        self.install_entry = ttk.Entry(row3)
        self.install_entry.pack(side="left", fill="x", expand=True)
        self.install_entry.insert(
            0, self.settings.get("install_dir") or default_install_dir()
        )
        ttk.Button(row3, text="Browse...", command=self._pick_install_dir).pack(
            side="left", padx=(6, 0)
        )

        # --- Tombol MAIN ---
        self.main_btn = ttk.Button(
            main, text="▶  MAIN", style="Big.TButton",
            command=self._start_main,
        )
        self.main_btn.pack(fill="x", pady=(4, 6))

        self.progress = ttk.Progressbar(main, length=400, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 2))
        self.status_var = tk.StringVar(value="Siap.")
        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", pady=(0, 6))

        # --- Log ---
        ttk.Label(main, text="Log:").pack(anchor="w")
        log_frame = ttk.Frame(main)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Tombol bawah ---
        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Salin Log", command=self._copy_log).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            bottom, text="Buka Folder Install",
            command=self._open_install_folder,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Log & queue
    # ------------------------------------------------------------------

    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "progress":
                    downloaded, total = payload
                    if total:
                        self.progress.configure(mode="determinate")
                        self.progress["value"] = downloaded / total * 100
                        self.status_var.set(
                            f"Mengunduh... {downloaded / 1024 / 1024:.1f} / "
                            f"{total / 1024 / 1024:.1f} MB"
                        )
                elif kind == "progress_mode":
                    self.progress.configure(mode=payload)
                    if payload == "indeterminate":
                        self.progress.start(15)
                    else:
                        self.progress.stop()
                        self.progress["value"] = 0
                elif kind == "main_done":
                    self._running = False
                    self.main_btn.configure(state="normal")
                    self.progress.configure(mode="determinate")
                    self.progress.stop()
                    self.progress["value"] = 100 if payload else 0
                    self.status_var.set(
                        "Selesai." if payload
                        else "Berhenti karena ada error — tekan MAIN lagi "
                             "untuk melanjutkan."
                    )
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Pilihan file
    # ------------------------------------------------------------------

    def _refresh_labels(self):
        disc = self.disc_var.get()
        update = self.update_var.get()
        self.disc_label.configure(
            text=_short_name(disc) if disc
            else "Belum dipilih — launcher akan memintanya nanti."
        )
        self.update_label.configure(
            text=_short_name(update) if update
            else "Belum dipilih — launcher akan memintanya nanti."
        )

    def _pick_disc(self):
        path = filedialog.askopenfilename(
            title="Pilih disc image Forza Horizon 2 USA (.iso)",
            filetypes=[("Disc image", "*.iso"), ("Semua file", "*.*")],
        )
        if path:
            self.disc_var.set(path)
            self._refresh_labels()
            self._save_settings()

    def _pick_update(self):
        path = filedialog.askopenfilename(
            title="Pilih file title update v2",
            filetypes=[("Arsip ZIP", "*.zip"), ("Semua file", "*.*")],
        )
        if path:
            self.update_var.set(path)
            self._refresh_labels()
            self._save_settings()

    def _pick_install_dir(self):
        folder = filedialog.askdirectory(title="Pilih folder install port")
        if folder:
            self.install_entry.delete(0, "end")
            self.install_entry.insert(0, folder)
            self._save_settings()

    def _save_settings(self):
        self.settings["install_dir"] = self.install_entry.get().strip()
        self.settings["disc_iso"] = self.disc_var.get()
        self.settings["title_update"] = self.update_var.get()
        save_settings(self.settings)

    def _copy_log(self):
        text = self.log_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set(
            "Log disalin ke clipboard — tempelkan bila diminta."
        )

    def _open_install_folder(self):
        install_dir = self.install_entry.get().strip()
        if not install_dir:
            messagebox.showwarning(
                "Folder install", "Pilih folder install dulu."
            )
            return
        ok, message = open_folder(install_dir)
        if not ok:
            messagebox.showwarning("Buka folder", message)
        self.log(message)

    # ------------------------------------------------------------------
    # Alur MAIN (otomatis, resumable)
    # ------------------------------------------------------------------

    def _start_main(self):
        if self._running:
            return
        install_dir = self.install_entry.get().strip()
        if not install_dir:
            messagebox.showwarning(
                "Folder install", "Pilih folder install dulu."
            )
            return
        self._running = True
        self.main_btn.configure(state="disabled")
        self.progress["value"] = 0
        self._save_settings()
        self.log("=" * 60)
        self.log("MAIN ditekan — memulai...")
        threading.Thread(
            target=self._main_worker,
            args=(
                install_dir,
                self.disc_var.get(),
                self.update_var.get(),
            ),
            daemon=True,
        ).start()

    def _q(self, kind: str, payload):
        self.queue.put((kind, payload))

    def _main_worker(self, install_dir: str, disc: str, update: str):
        try:
            # 1. Cek sistem — hanya info/peringatan, TIDAK PERNAH memblokir.
            self._q("log", "1. Memeriksa PC kamu...")
            try:
                checks = run_checks(install_dir or None)
                for check in checks:
                    mark = {"ok": "✓", "gagal": "⚠",
                            "tidak diketahui": "?"}[check["status"]]
                    line = f"   {mark} {check['name']}: {check['detail']}"
                    if check["status"] == FAIL and check["tip"]:
                        line += f" ({check['tip']})"
                    self._q("log", line)
                self._q(
                    "log",
                    "   Cek sistem selesai — ini hanya info. "
                    "Tidak ada yang memblokir MAIN.",
                )
            except Exception as exc:  # noqa: BLE001 - cek sistem tidak boleh menggagalkan MAIN
                self._q("log", f"   Cek sistem tidak bisa jalan ({exc}) — lanjut.")

            # 2. Unduh + ekstrak port — lewati bila launcher sudah ada.
            exe = find_launcher(install_dir)
            if exe is not None:
                self._q(
                    "log",
                    f"2. Port sudah terpasang ({exe}) — lewati unduhan.",
                )
            else:
                self._q(
                    "log",
                    f"2. Mengunduh port Lavender Shift {PORT_TAG} "
                    f"({PORT_ASSET}, 63,8 MB)...",
                )
                self._q("status", "Mengunduh port...")
                zip_path = download_port(
                    progress_cb=lambda d, t: self._q("progress", (d, t)),
                    log_cb=lambda m: self._q("log", f"   {m}"),
                )
                self._q("log", "   Unduhan selesai. Mengekstrak...")
                self._q("progress_mode", "indeterminate")
                self._q("status", "Mengekstrak port...")
                extract_port(zip_path, Path(install_dir))
                self._q("progress_mode", "determinate")
                exe = find_launcher(install_dir)
                if exe is None:
                    raise RuntimeError(
                        "Port berhasil diunduh dan diekstrak, tetapi "
                        f"{LAUNCHER_EXE} tidak ditemukan di folder install. "
                        "Coba hapus folder install lalu tekan MAIN lagi."
                    )
                self._q("log", f"   Port terpasang: {exe}")
                settings = load_settings()
                settings["install_dir"] = install_dir
                settings["port_version"] = PORT_TAG
                settings["port_exe"] = str(exe)
                save_settings(settings)

            # 3. Validasi file game — hanya peringatan, TIDAK PERNAH memblokir.
            self._q("log", "3. Memeriksa file game...")
            result = validate_game_files(disc, update)
            for issue in result["issues"]:
                self._q("log", f"   ⚠ {issue}")
            for warning in result["warnings"]:
                self._q("log", f"   ⚠ {warning}")
            if not result["issues"] and not result["warnings"]:
                self._q("log", "   File game OK.")
            else:
                self._q(
                    "log",
                    "   Tenang — ini hanya peringatan. Launcher sendiri "
                    "yang akan meminta file disc + title update di GUI-nya.",
                )

            # 4. Jalankan launcher.
            self._q("log", "4. Membuka launcher...")
            self._q("status", "Membuka launcher...")
            ok, message = launch_launcher(install_dir)
            if not ok:
                raise RuntimeError(message)
            self._q("log", f"   {message}")
            self._q(
                "log",
                "Selesai. Di dalam launcher: pilih disc image + title "
                "update, tekan Set up, tunggu build pertama "
                "(15 menit–1 jam), lalu tekan Play. Tekan F6 di dalam "
                "game untuk settings.",
            )
            self._q("main_done", True)
        except Exception as exc:  # noqa: BLE001 - semua kegagalan MAIN berakhir di sini
            self._q("log", f"GAGAL: {exc}")
            self._q(
                "log",
                "Yang harus dilakukan: periksa pesan di atas, lalu tekan "
                "MAIN lagi — aplikasi melanjutkan dari langkah terakhir "
                "yang berhasil. Bila terus gagal, tekan 'Salin Log' dan "
                "kirim lognya.",
            )
            self._q("main_done", False)


def run():
    app = App()
    app.mainloop()
