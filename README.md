# FH2 PC Installer

Installer/launcher Windows untuk memainkan **Forza Horizon 2 (Xbox 360)
secara native di PC** — **BUKAN emulator**.

Aplikasi ini memasang port native open-source **Lavender Shift**
([arcanite24/lavender-shift](https://github.com/arcanite24/lavender-shift),
v0.2.0, lisensi BSD-3-Clause), lalu membantumu memeriksa PC, memilih file
game, dan memainkan gamenya dengan satu klik.

## Penjelasan jujur: kenapa ini bisa native?

Kode game **Xbox 360 tidak bisa jalan native di PC begitu saja**. Xbox 360
memakai CPU PowerPC (Xenon) yang arsitekturnya berbeda total dari PC
x86-64, sehingga game Xbox 360 biasanya hanya bisa dimainkan lewat emulator
(mis. Xenia).

Yang dilakukan port ini adalah **static recompilation** (ShiftGlue —
teknologi yang sama dengan Pinyon Shift untuk Forza Horizon 1): kode game
Xbox 360 dikompilasi ulang menjadi program Windows native, sehingga game
berjalan langsung di prosesor PC tanpa lapisan emulasi. Port inilah yang
diunduh dan dipasang oleh aplikasi ini. Jadi yang kamu mainkan adalah
Forza Horizon 2 versi Xbox 360 yang berjalan native di Windows.

## Syarat PC

(Dari README port.)

- Windows 10 atau Windows 11 64-bit
- CPU 2013 atau lebih baru dengan **AVX2**
  (Intel Haswell, AMD Ryzen/Zen atau lebih baru)
- GPU yang mendukung **Vulkan**
- Ruang disk kosong minimal **20 GB** (port 64 MB + game ~20 GB)

Aplikasi ini punya tab **Cek Sistem** yang memeriksa semua syarat di atas
dan memberi tahu mana yang lolos, gagal, atau tidak dapat diperiksa.
README port tidak menetapkan batas RAM minimum, jadi RAM hanya dilaporkan.

## File game yang dibutuhkan

Aplikasi ini **TIDAK menyertakan file game apa pun**. Kamu wajib memakai
file berikut **milikmu sendiri**:

- Disc image Forza Horizon 2 **USA** (`.iso`)
- **Title update v2**

Hanya versi USA + title update v2 yang didukung port ini.

Tab **Game** di aplikasi akan memvalidasi kedua file yang kamu pilih dan
menampilkan masalah bila ada.

## Cara pakai

1. Jalankan `FH2PCInstaller.exe`.
2. **Cek Sistem** — tekan "Jalankan Cek Sistem", pastikan semuanya lolos.
3. **Unduh Port** — pilih folder install dengan path pendek
   (mis. `C:\Games\LavenderShift`), tekan "Unduh Port" (63,8 MB),
   lalu "Verifikasi" untuk memastikan `LavenderShiftLauncher.exe` ada.
4. **Game** — pilih file disc `.iso` dan file title update v2 milikmu,
   tekan "Validasi File Game", lalu "Simpan".
5. **Main** — tekan **BUKA LAUNCHER**. Di dalam launcher: pilih disc
   image + title update, tekan **Set up**, lalu tunggu **build pertama
   15 menit–1 jam**. Bila build berhenti di tengah jalan, tekan Set up
   lagi — build melanjutkan dari tempat berhenti. Setelah selesai, tekan
   **Play** di launcher. Berikutnya, tombol **MAIN LANGSUNG** di aplikasi
   ini bisa dipakai untuk menjalankan game hasil build secara langsung.

Catatan di dalam game:

- Tekan **F6** untuk settings.
- Save tersimpan di folder `user` di samping launcher.

Cara pakai portnya secara manual (tanpa installer ini) juga sama:
ekstrak `LavenderShift-0.2.0-windows-x64.zip` ke folder ber-path pendek,
jalankan `LavenderShiftLauncher.exe`, pilih disc image + title update,
tekan Set up, tunggu build pertama, lalu tekan Play.

## Port alternatif

Selain port utama (Lavender Shift v0.2.0 untuk versi Xbox 360), ada
alternatif lain:

- **Azimuth** (Almost There Games, itch.io) — wrapper untuk versi
  **Xbox One** Forza Horizon 2 build 1.0.0.64, bukan versi Xbox 360.

Installer ini hanya memakai Lavender Shift; Azimuth dicantumkan di sini
sebagai alternatif untuk dicoba sendiri bila kamu punya versi Xbox One.

## Build sendiri

### Windows (hasil: `dist\FH2PCInstaller.exe`)

```bat
build\build-windows.bat
```

Syarat: Python 3.12 terpasang dan ada di PATH. Semua DLL runtime (Tk/Tcl)
terbundel di dalam exe.

### GitHub Actions

Push tag `v*` (mis. `v1.0.0`) atau jalankan manual via tab Actions.
Runner `windows-latest` membangun exe dan mengunggah artifact bernama
**FH2PCInstaller-Windows**.

### Tes mandiri (tanpa GUI)

```sh
PYTHONPATH=src python -m fh2_installer --self-test
```

Tes ini memeriksa: rilis port di GitHub bisa dijangkau, validasi file game
pada file tiruan, dan cek sistem tidak crash. Unit test:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Lisensi

- **FH2 PC Installer** (aplikasi ini): kode installer/launcher di sini
  bebas dipakai untuk keperluan pribadi.
- **Port Lavender Shift** (arcanite24/lavender-shift): BSD-3-Clause.
- **Forza Horizon 2 dan aset game** adalah milik Microsoft / Turn 10 /
  Playground Games. Aplikasi ini tidak menyertakan, mendistribusikan,
  atau menyediakan file game, key, atau konten berhak cipta apa pun —
  gunakan hanya disc image + title update milikmu sendiri.
