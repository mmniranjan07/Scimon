"""Import the "Scimon All Individual Named Sprites" pack into the game's sprite set.

The pack (source_art/Scimon_All_Individual_Named_Sprites/) ships 327 named forms across 109
three-form families as one front + one back PNG per form (654 PNGs): transparent RGBA cutouts at
their extracted source resolution with 8px of padding, no baked-in text label, no baked-in resize.
This importer:

1. validates the pack with its own validate_pack.py (counts, checksums, alpha, front/back pairs,
   alias table and evolution links),
2. copies every PNG to assets/scimon/<species-id>-front.png / -back.png using the pack's
   legacy_filename_map.json -- the engine's canonical asset names; stable species IDs are never
   renamed to match the human-readable PNG filenames,
3. keeps the images at their source resolution on purpose: battle_sizing.py derives each form's
   apparent battle size from its body at runtime (stage/family configuration), so no per-form
   resize may be baked into the assets,
4. refreshes the game's contact sheet from the art now on disk (dex order, 12 per row).

Run any time (idempotent -- it rewrites the same 654 filenames):

    python tools/import_named_sprites.py

Display names are applied separately by tools/apply_name_patch.py (same pack).  Needs pillow
and reads the game's species table.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACK_DIR = os.path.join(ROOT, "source_art", "Scimon_All_Individual_Named_Sprites")
CANONICAL = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-(?:front|back)\.png$")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=PACK_DIR, help="extracted pack directory")
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "scimon"))
    args = ap.parse_args()

    sys.path.insert(0, ROOT)
    from data import SPECIES

    # ---- 1) validate the pack with its own checks (counts, sha256, alpha, pairs, evolution links)
    sys.path.insert(0, args.src)
    try:
        import validate_pack
    except ImportError:
        sys.exit(f"validate_pack.py not found in {args.src}")
    from pathlib import Path
    report = validate_pack.validate(Path(args.src))
    print("pack validation:", json.dumps(report))

    # ---- 2) copy every PNG under the engine's canonical <species-id>-<view>.png names
    with open(os.path.join(args.src, "legacy_filename_map.json"), encoding="utf-8") as f:
        amap = json.load(f)
    if len(amap) != 654 or len(set(amap.values())) != 654:
        sys.exit(f"unexpected alias table: {len(amap)} entries")
    os.makedirs(args.out, exist_ok=True)
    written = 0
    for dst, rel in sorted(amap.items()):
        if not CANONICAL.match(dst):
            sys.exit(f"alias target is not a canonical asset name: {dst!r}")
        sid = dst.rsplit("-", 1)[0]
        if sid not in SPECIES or dst not in (SPECIES[sid].front, SPECIES[sid].back):
            sys.exit(f"alias target {dst} does not belong to a registered species asset path")
        src = os.path.join(args.src, rel)
        if not os.path.isfile(src):
            sys.exit(f"pack file missing: {rel}")
        with open(src, "rb") as a, open(os.path.join(args.out, dst), "wb") as b:
            b.write(a.read())
        written += 1
    print(f"wrote {written} sprites -> {args.out}")

    # ---- 3) every registered form must now have its art on disk
    missing = [sid for sid, sp in sorted(SPECIES.items())
               if not os.path.isfile(os.path.join(args.out, sp.front))
               or (sp.back and not os.path.isfile(os.path.join(args.out, sp.back)))]
    if missing:
        sys.exit(f"forms without art after import: {missing[:8]}")

    # ---- 4) refresh the contact sheet from the art now on disk (dex order, 12 per row)
    from PIL import Image
    tile, per_row = 84, 12
    ids = [sid for sid, sp in sorted(SPECIES.items(), key=lambda kv: kv[1].dex)
           if os.path.isfile(os.path.join(args.out, SPECIES[sid].front))]
    board = Image.new("RGBA", (per_row * tile, ((len(ids) + per_row - 1) // per_row) * tile), (24, 26, 30, 255))
    for i, sid in enumerate(ids):
        img = Image.open(os.path.join(args.out, SPECIES[sid].front))
        img.thumbnail((tile - 6, tile - 6), Image.LANCZOS)
        board.alpha_composite(img, ((i % per_row) * tile + (tile - img.width) // 2,
                                    (i // per_row) * tile + (tile - img.height) // 2))
    board.save(os.path.join(args.out, "_contact_sheet.png"))
    print(f"contact sheet -> {os.path.relpath(os.path.join(args.out, '_contact_sheet.png'), ROOT)}")


if __name__ == "__main__":
    main()
