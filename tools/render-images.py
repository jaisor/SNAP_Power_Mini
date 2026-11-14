# SPDX-License-Identifier: MIT
# Renders the top and bottom board views for the README and draws the board's width and height
# on them. Run with KiCad's Python (it has pcbnew and Pillow):
#   "C:/Program Files/KiCad/10.0/bin/python.exe" tools/render-images.py
# kicad-cli's render has no dimension layer and surrounds the board with a soft shadow, so the
# board is cut out of the render (fully opaque pixels only) and put on a transparent canvas with
# room for the dimension lines. The sizes come from the board's Edge.Cuts outline.
import os
import subprocess
import sys
import tempfile

import pcbnew
from PIL import Image, ImageDraw, ImageFont

NAME = "SNAP_Power_Mini"
KICAD_CLI = "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
FONT = "C:/Windows/Fonts/arialbd.ttf"
OUT = "docs/images"
INK = (128, 136, 146, 255)  # mid grey: readable on GitHub's light and dark pages
PAD, ROOM = 30, 120  # canvas margin, and the extra room on the dimensioned sides, px
GAP, TICK, ARROW, LINE, TEXT = 55, 18, 20, 4, 44  # dimension line geometry, px


def board_size(path):
    """Width and height of the Edge.Cuts outline in mm, measured on the lines' centres."""
    board = pcbnew.LoadBoard(path)
    xs, ys = [], []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            for p in (d.GetStart(), d.GetEnd()):
                xs.append(p.x)
                ys.append(p.y)
    return pcbnew.ToMM(max(xs) - min(xs)), pcbnew.ToMM(max(ys) - min(ys))


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") + " mm"


def arrow(draw, tip, dx, dy):
    """Filled arrowhead with its point at tip, pointing along (dx, dy)."""
    x, y = tip
    bx, by = x - dx * ARROW, y - dy * ARROW
    half = ARROW * 0.4
    draw.polygon([(x, y), (bx - dy * half, by + dx * half), (bx + dy * half, by - dx * half)], fill=INK)


def annotate(src, dst, width_mm, height_mm):
    im = Image.open(src).convert("RGBA")
    solid = im.getchannel("A").point(lambda a: 255 if a >= 250 else 0)
    box = solid.getbbox()
    board = im.crop(box)
    board.putalpha(solid.crop(box))
    bw, bh = board.size
    # The render is orthographic, so both axes must give the same scale.
    assert abs(bw / width_mm - bh / height_mm) < 0.5, (bw, bh, width_mm, height_mm)

    x0, y0 = PAD + ROOM, PAD
    x1, y1 = x0 + bw, y0 + bh
    canvas = Image.new("RGBA", (x1 + PAD, y1 + ROOM + PAD), (0, 0, 0, 0))
    canvas.paste(board, (x0, y0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, TEXT)

    # Width, below the board
    y = y1 + GAP
    for x in (x0, x1 - 1):
        draw.line([(x, y1 + 12), (x, y + TICK)], fill=INK, width=LINE)
    draw.line([(x0 + ARROW, y), (x1 - 1 - ARROW, y)], fill=INK, width=LINE)
    arrow(draw, (x0, y), -1, 0)
    arrow(draw, (x1 - 1, y), 1, 0)
    draw.text(((x0 + x1) / 2, y + 12), fmt(width_mm), font=font, fill=INK, anchor="ma")

    # Height, left of the board
    x = x0 - GAP
    for yy in (y0, y1 - 1):
        draw.line([(x0 - 12, yy), (x - TICK, yy)], fill=INK, width=LINE)
    draw.line([(x, y0 + ARROW), (x, y1 - 1 - ARROW)], fill=INK, width=LINE)
    arrow(draw, (x, y0), 0, -1)
    arrow(draw, (x, y1 - 1), 0, 1)
    label = fmt(height_mm)
    l, t, r, b = font.getbbox(label)
    tile = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((2 - l, 2 - t), label, font=font, fill=INK)
    tile = tile.rotate(90, expand=True)
    canvas.alpha_composite(tile, (x - 12 - tile.width, (y0 + y1 - tile.height) // 2))

    canvas.save(dst, optimize=True)
    print(f"{dst}: {canvas.width} x {canvas.height} px, {fmt(width_mm)} x {fmt(height_mm)}, {bw / width_mm:.1f} px/mm")


def main():
    pcb = f"{NAME}.kicad_pcb"
    width_mm, height_mm = board_size(pcb)
    with tempfile.TemporaryDirectory() as tmp:
        for side in ("top", "bottom"):
            raw = os.path.join(tmp, f"{side}.png")
            subprocess.run([KICAD_CLI, "pcb", "render", "--side", side, "--quality", "high",
                            "-w", "1600", "-h", "1000", "-o", raw, pcb], check=True, stdout=subprocess.DEVNULL)
            annotate(raw, f"{OUT}/pcb-{side}.png", width_mm, height_mm)


if __name__ == "__main__":
    sys.exit(main())
