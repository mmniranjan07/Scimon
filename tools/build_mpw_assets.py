"""Builds assets/mpw/ from the raw packs in source_art/ (Buildings.png, Trees.png, MPWSP01/).

    pip install pillow numpy scipy ; python tools/build_mpw_assets.py

Outputs (all PNG, native resolution; the game scales them with nearest neighbour):
  assets/mpw/buildings/<role>.png   individual buildings cut from Buildings.png (baked shadows removed)
  assets/mpw/trees/tree_*.png       green trees only, bush_*.png green bushes (Trees.png)
  assets/mpw/buildings/gym_green.png the Green Gym from MPWSP01/tileset
  assets/mpw/mon/<n>_{front,back,idle,attack,menu}.png, fx/, bg/, ow/, ui/   from MPWSP01
"""
import os
import shutil

import numpy as np
import scipy.ndimage as ndi
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "source_art")
OUT = os.path.join(HERE, "assets", "mpw")
MPW = os.path.join(SRC, "MPWSP01")

BUILDING_BOXES = {   # role: (x, y, w, h) in Buildings.png
    "house_a": (739, 537, 26, 32), "house_b": (570, 476, 31, 37), "house_c": (294, 480, 29, 33),
    "house_d": (677, 536, 27, 33), "house_e": (294, 535, 29, 33), "house_f": (400, 482, 32, 31),
    "house_g": (474, 478, 26, 34), "house_h": (664, 473, 34, 40), "house_i": (331, 480, 35, 33),
    "house_j": (770, 537, 26, 32), "house_k": (210, 479, 29, 34),
    "cush": (377, 696, 41, 45), "center": (150, 693, 58, 48), "mart": (433, 697, 47, 44),
    "mart_epi": (499, 697, 50, 44), "lab": (5, 794, 64, 64), "hall": (727, 772, 69, 73),
    "library": (598, 773, 37, 72), "farm": (286, 593, 45, 37),
}
GREEN_TREES = {      # name: (band y0, y1, column) -- 64 px columns of Trees.png
    "tree_a1": (452, 543, 1), "tree_a2": (452, 543, 2), "tree_a4": (452, 543, 4), "tree_a5": (452, 543, 5),
    "tree_a7": (452, 543, 7), "tree_a8": (452, 543, 8), "tree_a9": (452, 543, 9),
    "tree_b3": (572, 672, 3), "tree_b7": (572, 672, 7), "tree_c0": (706, 800, 0), "tree_c4": (706, 800, 4),
    "tree_c8": (706, 800, 8),
}
GYM_BOX = (480, 0, 112, 112)       # green gym (first of the three) in MPWSP01/tileset/tileset.png
MON_FOR = range(1, 17)


def save(img, *parts):
    p = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p)


def trim(img):
    """Keep only the largest blob (drops slivers of neighbouring sprites), then crop to it."""
    a = np.array(img)
    lab, n = ndi.label(ndi.binary_dilation(a[:, :, 3] > 0, iterations=2))
    if n > 1:
        keep = int(np.bincount(lab.ravel())[1:].argmax()) + 1
        a[lab != keep] = 0
    img = Image.fromarray(a, "RGBA")
    box = img.getbbox()
    return img.crop(box) if box else img


def buildings():
    im = Image.open(os.path.join(SRC, "Buildings.png")).convert("RGBA")
    A = np.array(im)
    body = A[:, :, 3] >= 200
    lab, _ = ndi.label(ndi.binary_dilation(body, iterations=1))
    for role, (x, y, w, h) in BUILDING_BOXES.items():
        sub = lab[y:y + h, x:x + w]
        ids = np.bincount(sub[body[y:y + h, x:x + w]].ravel())
        best = int(ids.argmax())
        crop = A[y:y + h, x:x + w].copy()
        m = (sub == best) & body[y:y + h, x:x + w]
        crop[~m] = 0
        crop[m, 3] = 255
        save(trim(Image.fromarray(crop)), "buildings", role + ".png")
    gym = Image.open(os.path.join(MPW, "tileset", "tileset.png")).convert("RGBA")
    x, y, w, h = GYM_BOX
    save(trim(gym.crop((x, y, x + w, y + h))), "buildings", "gym_green.png")


def clean_trees():
    A = np.array(Image.open(os.path.join(SRC, "Trees.png")).convert("RGBA")).astype(int)
    rgb, alpha = A[:, :, :3], A[:, :, 3] > 0
    drop = np.zeros(alpha.shape, bool)
    for col in ((112, 200, 160), (64, 176, 136), (24, 160, 104)):      # placeholder background and ground rings
        drop |= (np.abs(rgb - np.array(col)).sum(axis=2) == 0) & alpha
    A[drop, 3] = 0
    return A.astype("uint8")


def trees():
    A = clean_trees()
    for name, (y0, y1, c) in GREEN_TREES.items():
        sub = A[y0:y1, c * 64:c * 64 + 64]
        save(trim(Image.fromarray(sub, "RGBA")), "trees", name + ".png")
    save(trim(Image.fromarray(A[83:172, 97:190], "RGBA")), "trees", "tree_big.png")
    # plain green bushes (flowering and autumn bushes are left out)
    region = A[1088:1152, 0:192]
    for k, x0 in enumerate((0, 96)):
        save(trim(Image.fromarray(region[:, x0:x0 + 96].copy(), "RGBA")), "trees", f"bush_{k}.png")


def mpw_pack():
    for n in MON_FOR:
        sheet = Image.open(os.path.join(MPW, "sprites", f"sprite{n}.png")).convert("RGBA")
        save(sheet.crop((0, 0, 96, 96)), "mon", f"{n}_front.png")
        save(sheet.crop((96, 0, 192, 96)), "mon", f"{n}_back.png")
        for kind in ("idle", "attack"):
            shutil.copy(os.path.join(MPW, "sprites", f"sprite{n}_{kind}.png"), os.path.join(OUT, "mon", f"{n}_{kind}.png"))
        shutil.copy(os.path.join(MPW, "menu sprites", f"menusprite{n}.png"), os.path.join(OUT, "mon", f"{n}_menu.png"))
    for n in range(1, 8):
        save(Image.open(os.path.join(MPW, "attack effects", f"attack{n}.png")), "fx", f"attack{n}.png")
    for n in range(1, 4):                                   # 640x360 -> top 640x320 (the pack's native 2:1 stage)
        save(Image.open(os.path.join(MPW, "backgrounds", f"background{n}.png")).convert("RGBA").crop((0, 0, 640, 320)), "bg", f"bg{n}.png")
    for n in range(1, 11):
        shutil.copy(os.path.join(MPW, "character overworld", f"ow{n}.png"), os.path.join(OUT, "ow", f"ow{n}.png")) if os.path.isdir(os.path.join(OUT, "ow")) else (os.makedirs(os.path.join(OUT, "ow")), shutil.copy(os.path.join(MPW, "character overworld", f"ow{n}.png"), os.path.join(OUT, "ow", f"ow{n}.png")))
    os.makedirs(os.path.join(OUT, "ui"), exist_ok=True)
    for f in sorted(os.listdir(os.path.join(MPW, "UI"))):
        shutil.copy(os.path.join(MPW, "UI", f), os.path.join(OUT, "ui", f))


def write_sizes():
    """mpw_sizes.py: native pixel size of every building, so the (pygame-free) map modules can trim footprints."""
    d = os.path.join(OUT, "buildings")
    rows = [f'    "mpw/buildings/{f}": {Image.open(os.path.join(d, f)).size},' for f in sorted(os.listdir(d))]
    with open(os.path.join(HERE, "mpw_sizes.py"), "w") as fh:
        fh.write('"""Generated by tools/build_mpw_assets.py -- native (w, h) of each MPW building sprite."""\nSIZES = {\n' + "\n".join(rows) + "\n}\n")


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "mon"), exist_ok=True)
    buildings(); trees(); mpw_pack(); write_sizes()
    print("done:", sum(len(f) for _, _, f in os.walk(OUT)), "files")
