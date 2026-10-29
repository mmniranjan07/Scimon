# Import the individually separated Scimon sprites and names

This pack contains 327 named forms across 109 three-form evolution families, with one front and one back PNG per form (654 PNGs total). No sprite image contains a full evolution sheet or a baked-in text label.

## Files

- `sprites/front/<Name>.png` — individual front view.
- `sprites/back/<Name>.png` — corresponding individual rear view.
- `sprite_manifest.json` — stable species ID, new name, prior name, stage, evolution links/level, dex, types, image size, source bounding box, anchor, source reference and checksums.
- `species_name_patch.json` — game-facing names and front/back paths keyed by stable species ID.
- `legacy_filename_map.json` — old ID-based filenames mapped to the new named sprite files. This is a mapping, not another duplicate set of PNGs.
- `evolution_lines.json` and `NAMES_AND_EVOLUTIONS.md` — every named evolution family.
- `index.html` — optional visual catalog. Images in the catalog remain separate files.

## Apply names in the actual game

1. Load the name patch and apply its `display_name` to the game's species definition (`Species.name` in the supplied Python project). Retain the existing species ID: IDs ending in `-baby`, `-mid` or `-final` may remain internal compatibility keys, but do not display those suffixes or stage placeholders as creature names.
2. The first form now uses the family's familiar name; the next two forms use their unique evolution names. For example: Florabot → Floravine → Floratitan, Voltling → Voltrix → Teslarch, Qubit → Qubiton → Quantarch. Look up stages using `chain_ids`/the manifest, not by assuming that the unsuffixed species ID is the first form. In many original families the unsuffixed ID is the second form.
3. Keep all existing IDs, dex values, evolution thresholds, stats, moves, inventory, captures, habitats and save references intact. This pack changes names and sprite lookups; it must not reset encounter policy or overwrite newer gameplay changes. The 327-form art roster includes 59 added first-form concepts beyond the original 268 registered forms. If the live game has not registered them yet, use the earlier complete database handoff to register them rather than aliasing them onto a different stage. Do not create a fourth stage in a family.
4. Use the canonical name in battles, party/storage, capture messages, evolution announcements, starter selection, Sci-Dex, trainer team labels and tooltips. Evolution announcements should say, for example, “Florabot evolved into Floravine!”
5. Preserve player nicknames. For an old save that stored the default species name on a creature instance, update it ONLY when it equals that species ID's previous canonical name. When in doubt preserve the nickname. Do not run global string replacement on IDs or save files. Source descriptions mentioning earlier generic names may need a targeted copy update.

## Image import and rendering

Use the `front` and `back` file paths from the manifest. If the engine requires `<species-id>-front.png` and `-back.png`, use `legacy_filename_map.json` to copy them at import time or configure an asset alias. Do not rename stable species IDs to match these human-readable PNG filenames.

PNG files are transparent RGBA cutouts at their extracted source resolution with 8 pixels of padding. No per-form resize was baked into these master images. Preserve aspect ratio, use nearest-neighbor rendering for pixel art, and apply the game's stage/family size configuration at runtime. Do not make every trimmed PNG the same apparent battle size. Ground-anchor metadata is supplied as a starting point; flying and floating creatures may need a family-specific hover anchor.

Back views are the generated rear designs, not mirrored front sprites. Pixel separation does not redraw or add animation. These exports preserve the generated concepts; inspect edge effects and battle anchors in the final renderer before shipping.

## Verification

Run `python validate_pack.py` after extraction. It checks the count, image decoding, alpha, unique names, all manifests, front/back pairs, aliases and evolution links. Validate the actual game's names and old-save behavior separately after importing. The validation report in this pack does not claim that the live game was changed.
