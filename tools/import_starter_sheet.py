"""Import the starter / early-family design sheets (Florabot, Aquabit, Pyrodrive, Voltling,
Glacibit, Qubit -- front and back views) into the game's sprite set.

These six families are absent from the two design collections; their sheets live in
source_art/scimon_collections/starter_sheets/ on a solid black backdrop with baked-in text
labels ("BACK VIEWS", column headers, family names).  The importer keys the black backdrop
with the shared pipeline, drops the text components by position (top band / left gutter),
hands every remaining component to the 3x3 cell its centroid falls in, then trims and
downscales exactly like the collection importer.

Stage mapping (the sheets draw baby -> middle -> final left to right):
    Florabot / Aquabit / Pyrodrive  baby->base, middle->-mid, final->-final  (3 game stages)
    Voltling / Glacibit / Qubit     middle->base, final->-final              (2 game stages;
    the baby design has no game species and is skipped, like unused babies in the collections)

Fronts land in <sid>-front.png, backs in <sid>-back.png.  The evolved starter stages gain
real back views for the first time; assets.back_path() serves them automatically.  Re-run:

    python tools/import_starter_sheet.py            # imports every sheet found
    python tools/import_starter_sheet.py --qa DIR   # also write a QA sheet

Needs pillow + numpy + scipy and the game's species table.
"""
import argparse
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "source_art", "scimon_collections", "starter_sheets")

# sheet file -> one row of target species ids per grid row (None = design has no game species)
SHEETS = {
    "front_starters.png": [["florabot", "florabot-mid", "florabot-final"],
                           ["aquabit", "aquabit-mid", "aquabit-final"],
                           ["pyrodrive", "pyrodrive-mid", "pyrodrive-final"]],
    "front_early.png": [["voltling-baby", "voltling", "voltling-final"],
                        ["glacibit-baby", "glacibit", "glacibit-final"],
                        ["qubit-baby", "qubit", "qubit-final"]],
    "backs_starters.png": [["florabot", "florabot-mid", "florabot-final"],
                           ["aquabit", "aquabit-mid", "aquabit-final"],
                           ["pyrodrive", "pyrodrive-mid", "pyrodrive-final"]],
    "backs_early.png": [["voltling-baby", "voltling", "voltling-final"],
                        ["glacibit-baby", "glacibit", "glacibit-final"],
                        ["qubit-baby", "qubit", "qubit-final"]],
}
COL_EDGES = (0, 420, 865, 1374)                # measured sprite columns (baby / middle / final)
ROW_EDGES = (0, 475, 805, 1145)                # measured sprite rows (families top to bottom)
TEXT_TOP = 130                                 # title + column headers live above this line
TEXT_LEFT = 240                                # family labels live left of this line


def cell_of(centroid):
    cy, cx = centroid
    col = next((i for i in range(3) if COL_EDGES[i] <= cx < COL_EDGES[i + 1]), None)
    row = next((i for i in range(3) if ROW_EDGES[i] <= cy < ROW_EDGES[i + 1]), None)
    return None if (row is None or col is None) else (row, col)


def import_sheet(path, named, out_dir, qa, max_side):
    """named: 3x3 target file names (None = design has no game species)."""
    im = Image.open(path).convert("RGBA")
    arr = np.asarray(im).astype(np.float32)
    rgb, alpha = arr[:, :, :3], arr[:, :, 3]
    rgb_u8 = np.asarray(im.convert("RGB"))
    sys.path.insert(0, HERE)
    import import_scimon_collections as imp

    bg = imp.background_mask(rgb, alpha, 14.0, 30.0)
    a = np.where(bg, 0, alpha)
    a = np.clip(a * (255.0 / max(float(a.max()), 1.0)), 0, 255).astype(np.uint8)
    labels, n = ndimage.label(a > 8, structure=imp.CONNECT8)
    written, skipped = 0, []
    cells = defaultdict(list)
    for lab in range(1, n + 1):
        m = labels == lab
        ys, xs = np.nonzero(m)
        if len(ys) < 40:
            continue                                  # dust
        # text filter: title / column headers sit in the top band; family name labels are wide,
        # thin strips in the left gutter (bubbles and sprites there are round or tall)
        w, h = int(xs.max() - xs.min()), int(ys.max() - ys.min())
        if ys.max() < TEXT_TOP:
            continue
        if xs.max() < TEXT_LEFT and h < 60 and w > 2.5 * h:
            continue
        cell = cell_of((float(ys.mean()), float(xs.mean())))
        if cell is None:
            continue
        sprite = np.zeros((*a.shape, 4), dtype=np.uint8)
        sprite[m] = np.concatenate([rgb_u8[m], a[m][:, None]], axis=1)
        cells[cell].append(sprite)
    for (row, col), sprites in sorted(cells.items()):
        name = named[row][col]
        if name is None:
            skipped.append(f"{os.path.basename(path)} ({row},{col}): baby design has no game species")
            continue
        canvas = np.zeros((*a.shape, 4), dtype=np.uint8)
        for sp in sprites:                            # disjoint components; max keeps soft edges
            canvas = np.maximum(canvas, sp)
        canvas = imp.clean_fragments(canvas)          # drop neighbour-design bleed
        target = imp.trim_scale(canvas, max_side)
        if target is None:
            skipped.append(f"{name}: empty cell")
            continue
        Image.fromarray(target, "RGBA").save(os.path.join(out_dir, name), optimize=True)
        written += 1
        qa.append((name[:-4], target))
    return written, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "scimon"))
    ap.add_argument("--qa", default=None)
    ap.add_argument("--max-side", type=int, default=256)
    args = ap.parse_args()

    sys.path.insert(0, ROOT)
    from data import SPECIES as ALL

    written, skipped, qa = 0, [], []
    for fn, rows in SHEETS.items():
        path = os.path.join(args.src, fn)
        if not os.path.isfile(path):
            print(f"sheet not found (skipping): {path}")
            continue
        view = "front" if fn.startswith("front") else "back"
        named = [[(s + f"-{view}.png") if s else None for s in row] for row in rows]
        w, sk = import_sheet(path, named, args.out, qa, args.max_side)
        written += w
        skipped += sk

    print(f"\nwrote {written} sprites -> {args.out}")
    for s in skipped:
        print("skipped:", s)

    if args.qa and qa:
        os.makedirs(args.qa, exist_ok=True)
        tile = 150
        board = Image.new("RGBA", (6 * tile, ((len(qa) + 5) // 6) * tile), (24, 26, 30, 255))
        for i, (sid, t) in enumerate(qa):
            img = Image.fromarray(t, "RGBA")
            img.thumbnail((tile - 6, tile - 6), Image.LANCZOS)
            board.alpha_composite(img, ((i % 6) * tile + (tile - img.width) // 2,
                                        (i // 6) * tile + (tile - img.height) // 2))
        board.save(os.path.join(args.qa, "qa_starter_sheets.png"))

    # refresh the game's contact sheet from the art now on disk
    t, per_row = 84, 12
    ids = [sid for sid, sp in sorted(ALL.items(), key=lambda kv: kv[1].dex)
           if os.path.isfile(os.path.join(args.out, ALL[sid].front))]
    board = Image.new("RGBA", (per_row * t, ((len(ids) + per_row - 1) // per_row) * t), (24, 26, 30, 255))
    for i, sid in enumerate(ids):
        img = Image.open(os.path.join(args.out, ALL[sid].front))
        img.thumbnail((t - 6, t - 6), Image.LANCZOS)
        board.alpha_composite(img, ((i % per_row) * t + (t - img.width) // 2,
                                    (i // per_row) * t + (t - img.height) // 2))
    board.save(os.path.join(args.out, "_contact_sheet.png"))
    print(f"contact sheet -> {os.path.relpath(os.path.join(args.out, '_contact_sheet.png'), ROOT)}")


if __name__ == "__main__":
    main()
