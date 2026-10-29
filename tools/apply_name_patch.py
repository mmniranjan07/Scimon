"""Apply the named-sprite pack's display-name patch to the game's species database.

The pack (source_art/Scimon_All_Individual_Named_Sprites/) renames the 327 forms to their
canonical display names: the first form of every family now carries the family's familiar name
and the next two forms use their unique evolution names (Florabot -> Floravine -> Floratitan,
Voltling -> Voltrix -> Teslarch).  Species IDs, dex values, stats, techniques, evolution
thresholds, habitats and the encounter policy are NOT touched.

For every species record the tool:

1. verifies the live name still equals the pack's `previous_display_name` (a newer rename
   anywhere means the game has moved on and the patch must not clobber it),
2. writes the new display name and records the old one as `previous_name`, which data.py
   exposes as PREVIOUS_NAMES so savegame.load() can migrate stored default names while
   preserving real player nicknames,
3. refreshes database-level provenance and regenerates scimon_db_data.py (the browser-build
   mirror) via tools/gen_db_module.py.

Run after (or before) tools/import_named_sprites.py -- they are independent:

    python tools/apply_name_patch.py
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACK_DIR = os.path.join(ROOT, "source_art", "Scimon_All_Individual_Named_Sprites")
PLACEHOLDER_WORDS = {"baby", "middle", "final"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=PACK_DIR, help="extracted pack directory")
    ap.add_argument("--db", default=os.path.join(ROOT, "assets", "scimon_database.json"))
    args = ap.parse_args()

    with open(args.db, encoding="utf-8") as f:
        db = json.load(f)
    with open(os.path.join(args.src, "species_name_patch.json"), encoding="utf-8") as f:
        patch = json.load(f)
    if len(patch) != 327 or len({p["display_name"] for p in patch.values()}) != 327:
        sys.exit("name patch must carry 327 unique display names")

    records = {rec["id"]: rec for rec in db["species"]}
    if set(records) != set(patch):
        sys.exit("the game database and the name patch disagree about the species ID set")

    # ---- safety first: the live game must still carry the names the patch was built against
    drifted = {sid: (records[sid]["name"], p["previous_display_name"])
               for sid, p in patch.items() if records[sid]["name"] != p["previous_display_name"]}
    if drifted:
        for sid, (live, expected) in sorted(drifted.items())[:10]:
            print(f"drifted: {sid}: live {live!r} != patch baseline {expected!r}")
        sys.exit(f"{len(drifted)} live names no longer match the patch baseline; refusing to clobber")

    # ---- apply: rename + keep the previous canonical name for savegame migration
    renamed = 0
    for sid, p in sorted(patch.items()):
        rec, new = records[sid], p["display_name"]
        low = new.lower().split()
        if PLACEHOLDER_WORDS & set(low) or new.endswith(" Prime"):
            sys.exit(f"display name still carries a stage placeholder: {sid} -> {new!r}")
        if rec["name"] != new:
            rec["previous_name"] = rec["name"]
            rec["name"] = new
            renamed += 1
    db["display_name_patch"] = {
        "source": os.path.basename(os.path.normpath(args.src)),
        "applied": datetime.date.today().isoformat(),
        "renamed_forms": renamed,
        "note": ("Canonical display names from the individually named sprite pack: first form carries "
                 "the family's familiar name, mid and final forms use their unique evolution names. "
                 "IDs, dex values, stats, techniques, evolution thresholds and the encounter policy "
                 "are unchanged; previous_name supports nickname-safe save migration."),
    }

    with open(args.db, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"renamed {renamed} forms -> {os.path.relpath(args.db, ROOT)}")

    # regenerate the browser-build mirror from the patched database
    import subprocess
    subprocess.run([sys.executable, os.path.join(HERE, "gen_db_module.py")], check=True)


if __name__ == "__main__":
    main()
