"""Generate PortaRun PWA icons — pure stdlib (zlib), no image libraries.

Full-bleed opaque teal square with a white "P" monogram. iOS/Android apply
their own rounded mask to home-screen icons, so the art is edge-to-edge with no
transparency or corner rounding of its own. Run:  python web/make_icons.py
"""

import pathlib
import struct
import zlib

TEAL = (13, 122, 104)   # --restroom brand color
WHITE = (255, 255, 255)
OUT = pathlib.Path(__file__).parent / "icons"
SS = 4  # supersampling factor for anti-aliasing


def in_p(x, y):
    """True if normalized point (0..1) is inside the white 'P' glyph."""
    # Stem: the vertical spine on the left, from cap height to baseline.
    if 0.33 <= x <= 0.43 and 0.26 <= y <= 0.76:
        return True
    # Bowl: the right-bulging loop off the top of the stem. A ring, kept only
    # to the right of the stem centre so it reads as a P (not a balloon).
    dx, dy = x - 0.43, y - 0.40
    d = (dx * dx + dy * dy) ** 0.5
    if 0.085 <= d <= 0.175 and x >= 0.40:
        return True
    return False


def pixel(x, y):
    return WHITE if in_p(x, y) else TEAL


def render(size):
    """Return raw RGB bytes (size*size*3), supersampled for smooth edges."""
    rows = bytearray()
    inv = 1.0 / (size * SS)
    sub = [(i + 0.5) for i in range(SS)]
    for py in range(size):
        row = bytearray()
        for px in range(size):
            r = g = b = 0
            for sy in sub:
                ny = (py * SS + sy) * inv
                for sx in sub:
                    nx = (px * SS + sx) * inv
                    c = pixel(nx, ny)
                    r += c[0]; g += c[1]; b += c[2]
            n = SS * SS
            row += bytes((r // n, g // n, b // n))
        rows += b"\x00" + bytes(row)  # filter byte 0 per scanline
    return bytes(rows)


def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, size):
    raw = render(size)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    path.write_bytes(png)
    print(f"  wrote {path.name} ({size}x{size}, {len(png)} bytes)")


def main():
    OUT.mkdir(exist_ok=True)
    for size in (512, 192, 180, 32):
        write_png(OUT / f"icon-{size}.png", size)


if __name__ == "__main__":
    main()
