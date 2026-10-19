"""Convert the 16x24 "RPG DB" character GIF into the game's native character sheets.

    python tools/import_rpgdb_sheet.py [path/to/16x24rpgdb.gif]
    (default: assets/sprites/characters/16x24rpgdb.gif)  ->  assets/characters/rpgdb0_0.png ... rpgdb11_0.png

The GIF's last frame is the full sheet: 12 characters across (0-3 "old style", 4-11 "new style"), 6 rows of 16x24 poses
per character:  down stand, down step, right stand, right step, up stand, up step.  There is no left row (left = right
mirrored) and only one step pose per direction, so:
    * each 16x24 pose is bottom-aligned in the game's 16x32 frame,
    * idle = the stand pose; walk = a 6-frame cycle stand, step, step, stand, step', step'
      (step' = the step mirrored for up/down, so the other foot leads; side views reuse the single step pose),
    * output uses the same layout as every other character sheet (settings.SHEET_LAYOUT: 24 columns x 7 rows,
      right/up/left/down starting at columns 0/6/12/18, idle on row 1, walk on row 2).
The sheet's green backdrop (109,170,44) is keyed out.  Needs Pillow (see requirements-dev.txt)."""
import os
import sys

from PIL import Image, ImageOps, ImageSequence

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SRC = os.path.join(ROOT, "assets", "sprites", "characters", "16x24rpgdb.gif")
OUT = os.path.join(ROOT, "assets", "characters")

SRC_W, SRC_H, COLS, ROWS = 16, 24, 12, 6
DST_W, DST_H = 16, 32
KEY = (109, 170, 44)
DIR_COL = {"right": 0, "up": 6, "left": 12, "down": 18}
POSE_ROWS = {"down": (0, 1), "right": (2, 3), "up": (4, 5)}      # (stand row, step row) in the source


def load_sheet(path):
    with Image.open(path) as im:
        last = None
        for frame in ImageSequence.Iterator(im):
            last = frame.convert("RGBA").copy()
    px = last.load()
    for y in range(last.height):
        for x in range(last.width):
            if px[x, y][:3] == KEY:
                px[x, y] = (0, 0, 0, 0)
    return last


def pose(sheet, col, row):
    return sheet.crop((col * SRC_W, row * SRC_H, (col + 1) * SRC_W, (row + 1) * SRC_H))


def convert(sheet, col):
    out = Image.new("RGBA", (24 * DST_W, 7 * DST_H), (0, 0, 0, 0))

    def put(img, frame_col, row):
        out.paste(img, (frame_col * DST_W, row * DST_H + (DST_H - SRC_H)))      # bottom-aligned

    poses = {}
    for facing, (r_stand, r_step) in POSE_ROWS.items():
        stand, step = pose(sheet, col, r_stand), pose(sheet, col, r_step)
        other = ImageOps.mirror(step) if facing in ("down", "up") else step
        poses[facing] = (stand, [stand, step, step, stand, other, other])
    stand, walk = poses["right"]
    poses["left"] = (ImageOps.mirror(stand), [ImageOps.mirror(f) for f in walk])
    for facing, (stand, walk) in poses.items():
        for i in range(6):
            put(stand, DIR_COL[facing] + i, 1)                # idle row
            put(walk[i], DIR_COL[facing] + i, 2)              # walk row
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else SRC
    sheet = load_sheet(path)
    os.makedirs(OUT, exist_ok=True)
    for c in range(COLS):
        convert(sheet, c).save(os.path.join(OUT, f"rpgdb{c}_0.png"))
    print(f"wrote {COLS} character sheets to {os.path.normpath(OUT)} (rpgdb0_0.png .. rpgdb{COLS - 1}_0.png)")


if __name__ == "__main__":
    main()
