"""Extract FireRed building exteriors from the pokefirered decomp into SCI-MON assets.

    python tools/extract_frlg_buildings.py [--check]

Renders the source maps from the FRLG decomp (metatile-accurate: 8-tile metatiles with
bottom+top layers, global BG palette table as loaded by src/fieldmap.c), crops the three
buildings SCI-MON borrows, and writes transparent PNGs into assets/town/:

    bld_safarigate.png   Fuchsia City Safari Zone entrance   (6x6 metatiles)
    bld_daycare.png      Route 5 Pokemon Day-Care            (6x5 metatiles)
    bld_casino.png       Celadon City Game Corner            (7x5 metatiles)

FRLG metatiles are 16x16 px and SCI-MON draws buildings at 3x (48 px per tile), so the
native sizes line up with Scimon's Building footprint convention automatically.
"""
import json
import os
import struct

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.normpath(os.path.join(HERE, "..", "assets", "town"))
ROOT = os.environ.get("FRLG_ROOT", "/home/mmniranjan07/pokefirered")
NUM_TILES_IN_PRIMARY = 640
NUM_PALS_IN_PRIMARY = 7
NUM_PALS_TOTAL = 13

# (out name, layout id, metatile rect x0, y0, x1, y1 inclusive)
BUILDINGS = [
    ("bld_safarigate", "LAYOUT_FUCHSIA_CITY", 22, 0, 26, 5),
    ("bld_daycare", "LAYOUT_ROUTE5", 21, 21, 26, 25),
    ("bld_casino", "LAYOUT_CELADON_CITY", 31, 17, 37, 21),
]


def trim_void(im, thresh=0.8):
    """Cut border rows/cols that are mostly pure-black void blocks (FRLG map voids), then alpha-trim."""
    px = im.load()
    w, h = im.size

    def black_fracRow(y):
        n = sum(1 for x in range(w) if px[x, y][:3] == (0, 0, 0))
        return n / w

    def black_fracCol(x):
        n = sum(1 for y in range(h) if px[x, y][:3] == (0, 0, 0))
        return n / h

    top = 0
    while top < h and black_fracRow(top) > thresh:
        top += 1
    bot = h
    while bot > top and black_fracRow(bot - 1) > thresh:
        bot -= 1
    left = 0
    while left < w and black_fracCol(left) > thresh:
        left += 1
    right = w
    while right > left and black_fracCol(right - 1) > thresh:
        right -= 1
    return im.crop((left, top, right, bot))


def read_gbapal(path):
    data = open(path, "rb").read()
    pal = []
    for j in range(16):
        v = struct.unpack_from("<H", data, j * 2)[0]
        pal.append((min((v & 31) * 8, 255), min(((v >> 5) & 31) * 8, 255), min(((v >> 10) & 31) * 8, 255)))
    return pal


def camel(name):
    folder = name.replace("gTileset_", "")
    out = folder[0].lower()
    for ch in folder[1:]:
        out += ("_" + ch.lower()) if ch.isupper() else ch
    return out


class Tileset:
    def __init__(self, kind, name):
        self.dir = os.path.join(ROOT, "data", "tilesets", kind, camel(name))
        self.tiles = Image.open(os.path.join(self.dir, "tiles.png")).convert("P")
        data = open(os.path.join(self.dir, "metatiles.bin"), "rb").read()
        self.metatiles = [data[i:i + 16] for i in range(0, len(data), 16)]


def render_map(layout_id):
    ls = json.load(open(os.path.join(ROOT, "data", "layouts", "layouts.json")))["layouts"]
    L = next(l for l in ls if l.get("id") == layout_id)
    prim = Tileset("primary", L["primary_tileset"])
    sec = Tileset("secondary", L["secondary_tileset"])
    pals = [[(0, 0, 0)] * 16 for _ in range(16)]
    for slot in range(NUM_PALS_IN_PRIMARY):
        pals[slot] = read_gbapal(os.path.join(prim.dir, "palettes", f"{slot:02d}.gbapal"))
    for slot in range(NUM_PALS_IN_PRIMARY, NUM_PALS_TOTAL):
        pals[slot] = read_gbapal(os.path.join(sec.dir, "palettes", f"{slot:02d}.gbapal"))
    w, h = L["width"], L["height"]
    blocks = open(os.path.join(ROOT, L["blockdata_filepath"]), "rb").read()
    im = Image.new("RGBA", (w * 16, h * 16))
    for by in range(h):
        for bx in range(w):
            mid = struct.unpack_from("<H", blocks, (by * w + bx) * 2)[0] & 0x3FF
            ts, mi = (sec, mid - NUM_TILES_IN_PRIMARY) if mid >= NUM_TILES_IN_PRIMARY else (prim, mid)
            raw = ts.metatiles[mi]
            for q in range(8):  # entries 0-3 bottom layer, 4-7 top layer (DrawMetatile, field_camera.c)
                e = struct.unpack_from("<H", raw, q * 2)[0]
                t, p = e & 0x3FF, (e >> 12) & 15
                sheet, ti = (prim.tiles, t) if t < NUM_TILES_IN_PRIMARY else (sec.tiles, t - NUM_TILES_IN_PRIMARY)
                px = sheet.load()
                sub = Image.new("RGBA", (8, 8))
                for y in range(8):
                    for x in range(8):
                        sub.putpixel((x, y), (*pals[p][px[(ti % 16) * 8 + x, (ti // 16) * 8 + y]], 255))
                if (e >> 10) & 1:
                    sub = sub.transpose(Image.FLIP_LEFT_RIGHT)
                if (e >> 11) & 1:
                    sub = sub.transpose(Image.FLIP_TOP_BOTTOM)
                im.alpha_composite(sub, (bx * 16 + (q % 2) * 8, by * 16 + ((q // 2) % 2) * 8))
    return im


def crop_building(map_im, rect):
    x0, y0, x1, y1 = rect
    return map_im.crop((x0 * 16, y0 * 16, (x1 + 1) * 16, (y1 + 1) * 16))


def key_grass(im):
    """Flood-fill the FRLG grass colours from the borders to transparency so the buildings
    sit on Scimon's own lawn colours without teal fringes."""
    GRASS = {(112, 200, 160), (64, 176, 136), (184, 248, 136)}
    w, h = im.size
    px = im.load()
    seen = set()
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        p = px[x, y]
        if p[3] != 0 and p[:3] not in GRASS:
            continue
        seen.add((x, y))
        px[x, y] = (0, 0, 0, 0)
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return im


def trim(im):
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def main():
    maps = {}
    for name, lid, x0, y0, x1, y1 in BUILDINGS:
        if lid not in maps:
            maps[lid] = render_map(lid)
            print("rendered", lid, maps[lid].size)
        spr = trim(key_grass(trim_void(crop_building(maps[lid], (x0, y0, x1, y1)))))
        out = os.path.join(OUTDIR, name + ".png")
        spr.save(out)
        print(f"{name}.png {spr.size[0]}x{spr.size[1]}  footprint {spr.size[0] // 16}x{spr.size[1] // 16}")
    # contact sheet for a quick eyeball
    sheet = Image.new("RGBA", (3 * 200, 220), (34, 40, 34, 255))
    for i, (name, *_r) in enumerate(BUILDINGS):
        spr = Image.open(os.path.join(OUTDIR, name + ".png"))
        sheet.alpha_composite(spr.resize((spr.width * 2, spr.height * 2), Image.NEAREST), (i * 200 + 4, 4))
    sheet.save(os.path.join(OUTDIR, "_frlg_buildings_preview.png"))
    print("preview -> assets/town/_frlg_buildings_preview.png")


if __name__ == "__main__":
    main()
