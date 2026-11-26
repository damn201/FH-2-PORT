"""FH2 PC Installer — mainkan Forza Horizon 2 (Xbox 360) secara native
di Windows.

Ini BUKAN emulator. Aplikasi ini adalah installer/launcher untuk port
native open-source Lavender Shift (arcanite24/lavender-shift, BSD-3-Clause),
yang merupakan port dari versi Xbox 360 "Forza Horizon 2" lewat static
recompilation (ShiftGlue — teknologi yang sama dengan Pinyon Shift untuk
Forza Horizon 1).

Penjelasan jujur: kode game Xbox 360 tidak bisa jalan native di PC begitu
saja — Xbox 360 memakai CPU PowerPC (Xenon) yang arsitekturnya berbeda
total dari PC x86-64. Yang dilakukan port ini adalah mengompilasi ulang
(static recompilation) kode game tersebut menjadi program Windows native,
sehingga game berjalan langsung di prosesor PC tanpa lapisan emulasi.
Port ini membutuhkan disc image Forza Horizon 2 USA + title update v2
milik pengguna sendiri.

Aplikasi ini TIDAK menyertakan file game apa pun. Pengguna wajib memakai
disc image FH2 USA (.iso) + title update v2 miliknya sendiri.
"""

__version__ = "1.1.0"
__app_name__ = "FH2 PC Installer"
