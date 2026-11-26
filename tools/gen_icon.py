"""Generate assets/icon.png dan assets/icon.ico (murni stdlib, tanpa PIL).

Ikon: huruf blok "FH2" emas di latar gelap, dengan motif jalan balap —
dua garis putih yang menyatu ke arah cakrawala dan garis tengah putus-putus.
Desain orisinal — tidak memakai art resmi Microsoft / Turn 10 / Playground.
ICO berisi PNG yang sama (format ICO modern membolehkan gambar PNG).
"""

import math
import struct
import zlib
from pathlib import Path

SIZE = 256


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk = struct.pack(">I", len(data)) + chunk_type + data
    chunk += struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return chunk


def _set(buf, x, y, color):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        i = (y * SIZE + x) * 4
        buf[i:i + 4] = bytes(color)


def _disc(buf, cx, cy, radius, color):
    for y in range(max(0, cy - radius), min(SIZE, cy + radius)):
        for x in range(max(0, cx - radius), min(SIZE, cx + radius)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                _set(buf, x, y, color)


def _rect(buf, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(SIZE, y1)):
        for x in range(max(0, x0), min(SIZE, x1)):
            _set(buf, x, y, color)


def _line(buf, x0, y0, x1, y1, radius, color):
    """Garis tebal: capai titik-titik di sepanjang ruas dengan disc."""
    length = max(abs(x1 - x0), abs(y1 - y0), 1)
    steps = int(length) + 1
    for i in range(steps + 1):
        t = i / steps
        _disc(buf, int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), radius, color)


def _block_letter(buf, x0, y0, scale, strokes, color):
    """Gambar huruf blok dari daftar ruas (x, y, w, h) relatif ke grid 5x7."""
    for (gx, gy, gw, gh) in strokes:
        _rect(
            buf,
            x0 + gx * scale, y0 + gy * scale,
            x0 + (gx + gw) * scale, y0 + (gy + gh) * scale,
            color,
        )


# Huruf blok pada grid 5 kolom x 7 baris (satuan sel).
LETTER_F = [(0, 0, 5, 1), (0, 0, 1, 7), (0, 3, 4, 1)]
LETTER_H = [(0, 0, 1, 7), (4, 0, 1, 7), (0, 3, 5, 1)]
LETTER_2 = [
    (0, 0, 5, 1), (4, 0, 1, 4), (0, 3, 5, 1),
    (0, 3, 1, 4), (0, 6, 5, 1),
]


def make_icon_png() -> bytes:
    buf = bytearray(SIZE * SIZE * 4)
    # latar: gradien vertikal gelap (abu arang ke hitam)
    for y in range(SIZE):
        t = y / SIZE
        r = int(14 + (6 - 14) * t)
        g = int(16 + (8 - 16) * t)
        b = int(20 + (10 - 20) * t)
        for x in range(SIZE):
            i = (y * SIZE + x) * 4
            buf[i:i + 4] = bytes((r, g, b, 255))

    gold = (212, 175, 55, 255)       # emas
    white = (235, 235, 235, 255)     # putih jalan
    grey = (140, 140, 140, 255)      # abu garis jalan

    # Motif jalan balap di bagian bawah: dua tepi jalan menyatu ke cakrawala.
    horizon_y = 176
    _line(buf, 8, 250, 108, horizon_y, 4, grey)
    _line(buf, 248, 250, 148, horizon_y, 4, grey)
    # garis tengah putus-putus (perspektif: makin pendek ke atas)
    for i, (y0, y1) in enumerate(((238, 222), (214, 202), (196, 188), (184, 179))):
        _line(buf, 128, y0, 128, y1, 3, white)

    # Huruf blok "FH2" emas di atas jalan.
    scale = 9
    _block_letter(buf, 28, 52, scale, LETTER_F, gold)
    _block_letter(buf, 88, 52, scale, LETTER_H, gold)
    _block_letter(buf, 148, 52, scale, LETTER_2, gold)
    # garis bawah emas pemisah huruf dan jalan
    _rect(buf, 24, 128, 232, 134, gold)

    raw = b""
    for y in range(SIZE):
        raw += b"\x00" + bytes(buf[y * SIZE * 4:(y + 1) * SIZE * 4])
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    return png


def make_icon_ico(png: bytes) -> bytes:
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 6 + 16)
    return header + entry + png


def main():
    assets = Path(__file__).resolve().parents[1] / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    png = make_icon_png()
    ico = make_icon_ico(png)
    (assets / "icon.png").write_bytes(png)
    (assets / "icon.ico").write_bytes(ico)
    print(f"icon.png: {len(png)} byte")
    print(f"icon.ico: {len(ico)} byte")


if __name__ == "__main__":
    main()
