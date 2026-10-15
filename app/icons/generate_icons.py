#!/usr/bin/env python3
"""Generate the Focus Flow PWA icons from original, license-clean artwork.

The artwork is defined procedurally here (the same design that ships as
``icon.svg``) and rasterised to PNG using only the Python standard library, so
the icons can be regenerated on any machine without ImageMagick, Cairo, PIL or
any other third-party dependency.

Usage::

    python3 app/icons/generate_icons.py

The script writes ``icon-192.png``, ``icon-512.png`` and
``icon-maskable-512.png`` next to itself.
"""

import math
import os
import struct
import zlib

# Design palette, matching the app's light-theme accent colours.
BG_TOP = (29, 78, 216)  # #1d4ed8
BG_BOTTOM = (22, 63, 179)  # #163fb3
PROGRESS = (169, 194, 255)  # #a9c2ff
WHITE = (255, 255, 255)

SUPERSAMPLE = 4


def _lerp(a, b, t):
    return a + (b - a) * t


def _blend(fg, bg, alpha):
    return tuple(int(round(_lerp(bg[i], fg[i], alpha))) for i in range(4))


def _inside_rounded_rect(nx, ny, half, radius):
    ax = abs(nx)
    ay = abs(ny)
    if ax > half or ay > half:
        return False
    corner = half - radius
    if ax > corner and ay > corner:
        dx = ax - corner
        dy = ay - corner
        return dx * dx + dy * dy <= radius * radius
    return True


def _on_hand(nx, ny, direction, length, half_width):
    ux, uy = direction
    along = nx * ux + ny * uy
    perp = abs(nx * -uy + ny * ux)
    return 0.0 <= along <= length and perp <= half_width


def _sample(nx, ny, canvas_y, maskable):
    """Return an (r, g, b, a) tuple for a design-space point.

    ``nx``/``ny`` are centred design coordinates in roughly [-0.5, 0.5];
    ``canvas_y`` (0..1) selects the vertical gradient stop.
    """

    g = _lerp(BG_TOP[0], BG_BOTTOM[0], canvas_y)
    b = _lerp(BG_TOP[1], BG_BOTTOM[1], canvas_y)
    b2 = _lerp(BG_TOP[2], BG_BOTTOM[2], canvas_y)
    background = (int(round(g)), int(round(b)), int(round(b2)), 255)

    if maskable:
        alpha = 255
    else:
        alpha = 255 if _inside_rounded_rect(nx, ny, 0.5, 0.24) else 0

    if alpha == 0:
        return (0, 0, 0, 0)

    dist = math.hypot(nx, ny)
    outer = 0.37
    inner = 0.29

    color = background

    if inner <= dist <= outer:
        angle = math.atan2(ny, nx)
        # Normalised angle starting at the top (12 o'clock) going clockwise.
        t = ((angle + math.pi / 2) % (2 * math.pi)) / (2 * math.pi)
        if t <= 0.72:
            ring = PROGRESS
        else:
            ring = WHITE
        color = (ring[0], ring[1], ring[2], 255)

    if _on_hand(nx, ny, (0.0, -1.0), 0.20, 0.030):
        color = (WHITE[0], WHITE[1], WHITE[2], 255)
    if _on_hand(nx, ny, (0.5, -0.8660254), 0.14, 0.034):
        color = (WHITE[0], WHITE[1], WHITE[2], 255)
    if dist <= 0.058:
        color = (WHITE[0], WHITE[1], WHITE[2], 255)

    return (color[0], color[1], color[2], alpha)


def render(size, maskable=False):
    content_scale = 0.78 if maskable else 1.0
    step = 1.0 / (size * SUPERSAMPLE)
    rows = []
    for py in range(size):
        row = []
        canvas_y = (py + 0.5) / size
        for px in range(size):
            acc_r = acc_g = acc_b = acc_a = 0.0
            for sy in range(SUPERSAMPLE):
                y = (py * SUPERSAMPLE + sy + 0.5) / (size * SUPERSAMPLE)
                ny = (y - 0.5) / content_scale
                for sx in range(SUPERSAMPLE):
                    x = (px * SUPERSAMPLE + sx + 0.5) / (size * SUPERSAMPLE)
                    nx = (x - 0.5) / content_scale
                    r, g, b, a = _sample(nx, ny, canvas_y, maskable)
                    af = a / 255.0
                    acc_r += r * af
                    acc_g += g * af
                    acc_b += b * af
                    acc_a += af
            samples = SUPERSAMPLE * SUPERSAMPLE
            if acc_a == 0:
                row.append((0, 0, 0, 0))
            else:
                row.append(
                    (
                        int(round(acc_r / acc_a)),
                        int(round(acc_g / acc_a)),
                        int(round(acc_b / acc_a)),
                        int(round(255 * acc_a / samples)),
                    )
                )
        rows.append(row)
    return rows


def _chunk(tag, data):
    payload = tag + data
    return (
        struct.pack(">I", len(data))
        + payload
        + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
    )


def encode_png(rows):
    height = len(rows)
    width = len(rows[0])
    raw = bytearray()
    for row in rows:
        raw.append(0)  # filter type 0 (None)
        for r, g, b, a in row:
            raw += bytes((r, g, b, a))
    compressed = zlib.compress(bytes(raw), 9)
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        signature
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", compressed)
        + _chunk(b"IEND", b"")
    )


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    targets = [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-512.png", 512, True),
    ]
    for name, size, maskable in targets:
        data = encode_png(render(size, maskable=maskable))
        path = os.path.join(here, name)
        with open(path, "wb") as handle:
            handle.write(data)
        print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
