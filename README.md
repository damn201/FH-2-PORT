# FH2 PC Installer

Installer/launcher Windows untuk memainkan **Forza Horizon 2 (Xbox 360)
secara native di PC** — **BUKAN emulator**.

Aplikasi ini memasang port native open-source **Lavender Shift**
([arcanite24/lavender-shift](https://github.com/arcanite24/lavender-shift),
v0.2.0, lisensi BSD-3-Clause), lalu membantumu memeriksa PC, memilih file
game, dan memainkan gamenya dengan satu klik.

**v1.1.0 — tampilan baru, satu layar saja.** Tidak ada lagi 5 tab yang
membingungkan: pilih file game, tekan **▶ MAIN**, langsung main. Semua
langkah (cek sistem, unduh port, validasi file game, buka launcher)
berjalan otomatis saat MAIN ditekan, dan bisa dilanjutkan — langkah yang
sudah selesai dilewati bila kamu menekan MAIN lagi.

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

Aplikasi ini hanya memeriksa syarat di atas dan menampilkannya sebagai
info di log — **tidak ada satu pun yang memblokir tombol MAIN**.
README port tidak menetapkan batas RAM minimum, jadi RAM hanya dilaporkan.

## File game yang dibutuhkan

Aplikasi ini **TIDAK menyertakan file game apa pun**. Kamu wajib memakai
file berikut **milikmu sendiri**:

- Disc image Forza Horizon 2 **USA** (`.iso`)
- **Title update v2**

Hanya versi USA + title update v2 yang didukung port ini.

**Title update yang belum ada BUKAN penghalang.** Bila kamu belum punya
file title update v2, aplikasi hanya memberi peringatan jelas di log —
tombol MAIN tetap jalan dan membuka launcher, karena launcher itu sendiri
yang meminta disc image + title update di GUI-nya saat Set up. Disc
`.iso` juga tidak memblokir MAIN: bila belum dipilih, kamu akan diberi
peringatan dan tetap bisa melihat sendiri apa yang diminta launcher.

## Unduhan port (otomatis saat MAIN ditekan)

- Unduhan memakai **URL langsung** (bukan GitHub API), jadi tidak kena
  rate-limit GitHub.
- Bila koneksi gagal/terputus, unduhan **dicoba ulang sampai 3 kali**.
- File hasil unduhan diverifikasi **ukurannya** (66.945.128 byte) dan,
  bila bisa diambil, **SHA-256**-nya dari file `.sha256` rilis.
- Bila `LavenderShiftLauncher.exe` sudah ada di folder install, unduhan
  **dilewati** — tekan MAIN lagi untuk melanjutkan dari langkah terakhir
  yang berhasil.

## Cara pakai

1. Jalankan `FH2PCInstaller.exe`.
2. **1. File Game** — pilih disc `.iso` dan title update v2 milikmu
   (boleh kosong dulu; lihat catatan di atas).
3. **2. Folder Install** — biarkan bawaan (`C:\Games\LavenderShift`)
   atau pilih folder lain.
4. Tekan **▶ MAIN**. Aplikasi otomatis: memeriksa PC (info saja),
   mengunduh + mengekstrak port (63,8 MB, dilewati bila sudah ada),
   memeriksa file game (peringatan saja), lalu membuka
   `LavenderShiftLauncher.exe`.
5. Di dalam launcher: pilih disc image + title update, tekan **Set up**,
   lalu tunggu **build pertama 15 menit–1 jam**. Bila build berhenti di
   tengah jalan, tekan Set up lagi — build melanjutkan dari tempat
   berhenti. Setelah selesai, tekan **Play** di launcher.

Bila ada langkah yang gagal, log akan menulis errornya beserta "yang
harus dilakukan" dalam Bahasa Indonesia sederhana. Tekan MAIN lagi untuk
melanjutkan dari langkah terakhir yang berhasil. Tombol **Salin Log**
menyalin seluruh log ke clipboard — tempelkan bila kamu perlu mengirim
lognya saat meminta bantuan.

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

Tes ini memeriksa: rilis port di GitHub bisa dijangkau (kegagalan API —
mis. rate-limit 403 — dilaporkan sebagai "tidak dapat diperiksa", BUKAN
gagal, karena alur normal tidak memakai API), validasi file game pada
file tiruan, dan cek sistem tidak crash. Unit test:

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
