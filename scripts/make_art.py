"""One-off: turn the background-removed profile picture into a 0/1 grid.

Writes scripts/art.json: a list of rows, each row a list of [char, level]
where char is "0", "1" or " " and level (0-7) is the brightness bucket.

    uv run --with pillow python scripts/make_art.py
"""
import json
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

HERE = Path(__file__).parent
ROWS = 52
CELL_W, CELL_H = 5.72, 11.0  # monospace advance at 9.5px font, line height
CROP = (84, 50, 318, 300)  # left, top, right, bottom in the 400x400 pfp
LEVELS = 8

img = Image.open(HERE / "pfp_cut.png").convert("RGBA").crop(CROP)
w, h = img.size
cols = round(ROWS * (CELL_H / CELL_W) * (w / h))

alpha = img.getchannel("A")
gray = ImageOps.grayscale(img.convert("RGB"))
# equalise contrast using only the subject's pixels
mask = alpha.point(lambda a: 255 if a > 128 else 0)
gray = ImageOps.equalize(gray, mask=mask)
edges = gray.filter(ImageFilter.FIND_EDGES)

small = gray.resize((cols, ROWS), Image.LANCZOS)
small_a = alpha.resize((cols, ROWS), Image.LANCZOS)
small_e = edges.resize((cols, ROWS), Image.LANCZOS)

rows = []
for y in range(ROWS):
    row = []
    for x in range(cols):
        a = small_a.getpixel((x, y))
        if a < 110:
            row.append([" ", 0])
            continue
        v = small.getpixel((x, y)) / 255
        e = small_e.getpixel((x, y)) / 255
        v = min(1.0, v + 0.2 * e)  # lift shadows a bit, emphasise outlines
        level = min(LEVELS - 1, int(v * LEVELS))
        # '0' carries more ink than '1', so brighter cells get zeros
        ch = "0" if v > 0.5 else "1"
        row.append([ch, level])
    rows.append(row)

(HERE / "art.json").write_text(json.dumps(rows, separators=(",", ":")))
print(f"{cols}x{ROWS}")
for r in rows:
    print("".join(c for c, _ in r))
