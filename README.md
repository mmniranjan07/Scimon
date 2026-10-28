# SCI-MON - Python / Pygame edition

The `scimon_py` look (transparent, game-ready sprites and building art) merged with everything in
`SCIMON VERSION - 34` (interiors, Sci-Database, held items, key items, pack, full story flow),
now running on the audited **scimon_database.json** catalog: 109 families / 327 forms (every family
first → middle → final), explicit habitat zones per map patch (F3 highlights the active zone), phased
wild-stage unlocks (100/0/0 → 85/15/0 → 80/17/3 as stamps and story flags land) and the 0.1% global
migration branch — see `encounters.py` and the Sci-Dex catalog (D in the Sci-Database terminal).

    pip install -r requirements.txt     # pygame >= 2.5 (pygame-ce also works)
    python main.py


## MPW art overhaul (this build)
> **Sprite revert (py19 + py18 art).** Buildings use the original py18 art again; everything else in this
> section (foliage, characters, battle backgrounds / effects, UI icons) is unchanged.  Scimon creatures were
> since redrawn from the design collections -- see *Scimon art redesign* below.
> * Buildings: `assets/town/bld_*.png` (lab, hall, cush, library, mart, farm, house_0/1/2), including Epidimy's houses, Scimon Center
>   and Supply Mart, plus the chimney smoke and lab beacon that belong to those sprites.  Only the Epidimy Green Gym keeps its MPW sprite
>   (py18 had no gym); to use the old library sprite instead, set its sprite to `"town/bld_library.png"` in `epidimy.py`.
> * Scimon: `assets/scimon/<species>-front|back.png` through `assets.mon_image`; they are single stills, so `assets.mon_anim` returns one
>   frame and the sprite breathes / lunges in code.  The MPW monster sheets are no longer loaded.
> * Characters are smaller: `settings.CHAR_PX = 2` (was 3), so a 32x32 frame is drawn at 64x64.  Set it to 3 for the previous size.
>   The battle trainer is rescaled to stay the same size.
> * `worldmap.native_size()` measures `town/` building PNGs so footprint trimming works for them.

## Scimon art redesign (collections 01 + 02)
All 103 wild Scimon families (the classic Route 1 cast + 97 of the wider region's species) were redrawn from the
`Scimon_Collection_01/02_Front_and_Back` design atlases: proper **front views and rear three-quarter back views**
for every stage (baby / middle / final).  The atlases live in `source_art/scimon_collections/` and are imported with

    python tools/import_scimon_collections.py          # -> assets/scimon/<species>-front|back.png

The tool keys out the atlases' painted gradient backdrop (region grow + pocket keying), hands every creature to its
atlas cell (splitting designs that overlap their neighbours by watershed), trims, normalises the alpha and downscales
onto the game's ~256 px canvas.  The three starter families and the earlier glacibit / qubit / voltling lines are not
part of the collections and keep their original art.  Battles pick the back views up automatically
(`assets.back_path`), and the Sci-Database preview (F) flips to them too.

All art that people see in play now comes from three packs; run `python tools/build_mpw_assets.py` (needs `pillow numpy scipy`) to
rebuild `assets/mpw/` and `mpw_sizes.py` from `source_art/`.
* **Buildings**: cut from `Buildings.png` (`assets/mpw/buildings/`, drawn 3x). Every building's footprint is trimmed to its sprite
  (`worldmap.trim_footprints`), so nothing invisible blocks you. Chimney smoke and the lab beacon belonged to the old sprites and are gone.
* **Foliage**: only the green trees and green bushes of `Trees.png` (`assets/mpw/trees/`, `townview.GREEN_TREES`), native size with a soft ground shadow.
* **Green Gym**: the green gym from `MPWSP01/tileset` replaces the Epidimy Library (`epi-gym`, footprint 7x7, Hall interior, Leader Fern). It is the only gym in the game.
* **Characters**: the ten `MPWSP01` overworld sheets (`sprites.MPW_CAST`; unlisted NPCs get a stable sheet from their id), 4-frame walk, 4 facings.
* **Monsters**: species map to MPW monsters in `assets.MPW_MON`; battle uses front idle / attack frames, back view, 32x32 menu icons in lists, the HUD and the overworld.
* **Battle**: MPW backgrounds (`battle.BG_FOR_AREA`: Riven grass, Route 1 beach, Epidimy snow), MPW attack effects per technique type (`sprites.FX_FOR_TYPE`), lunge animation.
* **UI**: MPW icons on the battle menu (sword / shield / swap / fist, highlighted twins when selected) and the HP / STB / EXP bars. The pack has no panel art, so panels and fonts stay procedural.

## Controls
| Key | Action |
|---|---|
| Arrows / WASD | move, navigate menus |
| Enter / Space / Z | confirm, talk, advance dialogue (first press finishes the typing) |
| Esc / X | back / close |
| I / Tab / Esc (overworld) | open the Pack |
| Pack: Tab, Q/E, T, U/J, Del | switch tab, category, take held item, reorder party, discard |
| M | mute SFX | F3 | collision/hitbox overlay | F11 | fullscreen |
**Phones / tablets:** an on-screen D-pad plus **A** (confirm), **B** (back) and **PACK** buttons appear automatically; every menu can also be tapped. See *Mobile / touch* below.
Mouse works on every menu (hover, click). The window is resizable; the game renders at 960x640 and scales.

## One-way ledges
Tile `l` is a ledge you can hop **down** but never climb: walking south into it from the tile above makes the player hop over it
onto the tile below (small arc + shadow); from the sides or from below it is a normal wall. Stacked `l` tiles form a vertical wall.
It is drawn procedurally (`townview._draw_ledges`), the rule lives in `TileMap.ledge_landing`, the hop in `Player.begin_jump`, and
`routes.validate()` understands the hop, so it also fails the build if a ledge could trap the player with no way back to the exit.

## Mobile / touch
On a touch device (browser reports a coarse pointer) the engine opens a larger canvas and places the 960x640 game inside it,
so the controls never hide anything: **landscape phones** get the D-pad on the left and A/B/PACK on the right; **portrait phones**
get the game on top and controls underneath; **tablets / squarish screens** get translucent controls over the corners. The layout
follows rotation. Buttons become normal key events (A=Enter, B=X, PACK=I), the D-pad also auto-repeats in menus, and taps on the
game area behave like mouse clicks. The landing page switches to a full-viewport play mode on phones (also on iOS, which lacks
element fullscreen) and tries to lock landscape.

Test on a desktop (any window size string, e.g. portrait `390x844`):

    SCIMON_TOUCH=1 SCIMON_TOUCH_SIZE=844x390 python main.py

Click the pads with the mouse is not simulated - use the browser's device emulation on the pygbag build for real multi-touch.

## Saving
Progress autosaves every few seconds (party, Sci-Database, bag, credits, Sci-Dex, chests, story flags). In the browser it lives in
localStorage; on desktop in `~/.scimon/save.json`. The title screen offers CONTINUE / NEW GAME when a save exists. Code: `savegame.py`.

## Architecture
| File | Role |
|---|---|
| `main.py` | entry point |
| `engine.py` | `Scene` base class, `StateId` enum, scene stack (state machine), fade transitions, main loop with delta time |
| `state.py` | `GameState` singleton: party, Sci-Database, bag, credits, Sci-Dex + every inventory/shop/held-item operation |
| `data.py` | types, techniques, species, items, catalogue (merged V34 + scimon_py) |
| `monsters.py` | `Scimon` model, damage/capture/XP formulas, enemy AI |
| `battle.py` | turn engine (`plan_turn` -> events) and `BattleScene` UI |
| `map.py` | `TileMap` (Rect collision, pre-rendered world), `Camera`, terrain/interior art |
| `worldmap.py` | Riven Town layout, buildings, NPCs, interior grids |
| `routes.py` | outdoor areas + the link graph (Route 1 + merged towns/kanto), healers, chests, network validation |
| `towns.py` | the styled towns of the wider region (Stonreach ... Astrion Plateau, Ost's Cabin): grids, buildings, outfits |
| `kanto.py` | Routes 2-25 and the wild places between them: seeded maps, signs, travelers, the edge list |
| `species_expanded.py` | the wider region's 100 wild Scimons: curated tables, archetype stats, type learnset pools |
| `sprites.py` | `Player`, `NPC` (sheet-based, hitbox-anchored), `ScimonSprite`, `TrainerSprite`, `ImpactBurst` |
| `interiors.py` | the eight interior rooms as sprite props with footprints; generates each room's collision grid |
| `overworld.py` | exploration scene: movement, doors, talk, encounters, HUD |
| `scenes.py` | title, dialogue, wake-up, professor's lab briefing, starter select, rival encounter, game flow |
| `menus.py` | Pack, Shop, Sci-Database, repair service menu |
| `ui.py` | glass panels, pixel text, typewriter dialogue box, bars, chips, button grid, toast |
| `touch.py` | mobile support: layouts, on-screen D-pad / A / B / PACK, multi-touch finger tracking |
| `assets.py` / `audio.py` | cached image/font loader; synthesized SFX (no audio files) |

Design rules: nothing blocks - dialogue, battles, shops and transitions are all scene states advanced by
`update(dt)`. All movement, animation, typing speed and bar easing use `dt`, so behaviour is frame-rate
independent (the fuzz test mixes 7 ms and 50 ms frames). Collision is grid based: a step is allowed only if
the destination tile's `Rect` misses every solid-tile Rect and NPC Rect (`Rect.collidelist`).

## Assets
* Buildings and Scimon sprites: `scimon_py` (transparent, trimmed).
* **Interiors** are built from furniture sprites (`assets/interiors/`). Each prop has a footprint; the footprints *are* the collision
  grid, so F3 shows exactly what blocks you. Tall furniture only blocks its base row and is depth-sorted against characters.
* **Characters** are 16x32-px sheets (`assets/characters/<body>_<hue>.png`: Adam / Alex / Amelia / Bob, with hue variants baked so the
  whole cast looks distinct). The hitbox is the 48x48 tile at the feet; the 48x96 sprite is anchored to its bottom edge
  (F3 draws the art box in blue and the hitbox in cyan/magenta). Walk and idle animations are rows 2 and 1 of the sheet.
* **All furniture, wall/floor patches, characters and beach pieces are original art** generated by `python tools/generate_original_art.py`
  (pure Pillow, seeded, no input files; `pip install -r requirements-dev.txt` first; names and pixel sizes are fixed so layouts never change). `python tools/preview_rooms.py`
  renders every room (and its hitbox view) to PNG.
* Fonts: Press Start 2P and VT323, both SIL OFL.

## Town revamp (exterior, buildings, interiors)
Everything people see in Riven Town was redrawn; characters, dialogue, door positions, shops and every building's purpose are unchanged.
* **Beach dressing**: the sand and ocean tiles still use the original tile code; the beach (rows 17-20) additionally gets palm trees and sprouts,
  rock lumps, small and rock-ringed tide pools and sand flowers (`assets/town/beach_*.png`, built by `tools/generate_original_art.py`). Map chars: `Q` palm, `i` sprout,
  `j` rock, `v` tide pool (2x2 / 3x3), all solid; `z` sand flowers, walkable. The sea-gate lane (columns 20-22) and Sella's tile stay clear and
  `validate()` checks the whole beach stays reachable. Everything outside the beach renders pixel-identically to before.
* `worldmap.py`: new town layout (central plaza, pond park, fenced crop field with scarecrow, hedged gardens and
  fenced house yards, lamp-lit streets). Tall-grass encounter patches, NPC tiles, doors and the player start are kept; `validate()` now also
  checks that every door, NPC and tall-grass tile is reachable on foot.
* `townview.py`: new overworld renderer (autotiled cobbles + kerbs, hedges, fences, pond coping; trees/lamps/benches/stalls are depth-sorted
  props so characters walk behind canopies). Animated: pond + fountain, lamp glow, chimney smoke, lab beacon, road studs, name tags that fade in
  near a building.
* `assets/town/`: original pixel art generated by `tools/town_terrain.py`, `town_props.py`, `town_buildings.py` (9 building sprites in use).
* `interiors.py`: all eight rooms re-furnished for their purpose (server racks, specimen tank and holo-table in the lab; tool wall and parts
  shelf at Cush's; flags and podium in the hall; reading desks in the library; seed bins, troughs and hydroponic trays on the farms) with baked
  window light, lamp glow and edge shading. New props are `assets/interiors/x_*.png` from `tools/town_interior_props.py`.
* Rebuild all art: `cd tools && python3 generate_original_art.py && python3 town_terrain.py && python3 town_props.py && python3 town_buildings.py && python3 town_interior_props.py`.

* Plaza signpost is interactive (face it + confirm: Up / Down / Left / Right directions, text in `worldmap.SIGN_LINES`). Lamp posts no longer block
  a tile (you can walk past/behind them); the pondside bench and the two south market stalls were removed.
* **Walk behind the Hall, Lab, Library and Mart**: rows 1-3 of those footprints are open back yard (`e`), reachable from the lawn strips beside
  each building; the top map row, the facade rows and the door stay solid (`worldmap.BACK_ACCESS` / `BACK_ROWS`). Those four buildings are
  depth-sorted props now, so you are hidden behind them, and they turn see-through while you stand in their back yard.
* **Farms**: the south greenhouse ("Grow") is gone; its plot is now one big fenced crop field (merged with the old one beside it) with two scarecrows,
  a gate on the south side and a walkable lane through the middle. Farmer Wren's dialogue now says "field".

## Epidimy Town (north of Route 1)
Route 1's north road (row 0, x 6..9) leads to **Epidimy Town**, laid out after a reference screenshot: terraced plateau with the field
station and a cottage, a cave mouth in the rock band (sealed, read its sign), a fountain pond, west lake, south-east and north-east
ponds, seven cottages, the Library, the Scimon Center (free healing) and a supply mart. Peaceful: no tall grass.
* `epidimy.py` - grid, buildings, NPCs, signs, `validate()` (everything reachable, NPCs never cut a road).
* Drawn by `TileMap._render_styled` with **Riven Town's own renderer** (`townview.py`): same lawns, cobbled roads + kerbs, stone walls,
  coping-rimmed animated ponds (only the middle one has the fountain jet), trees, lamps, benches, name tags and glowing road studs.
* Buildings are Riven's sprites (`town/bld_house_0..2`, `bld_library`, `bld_cush`, `bld_mart`).
* Doors are per area (`Building.area`, `routes.building_at`). Interiors reuse the house / library / cush / mart rooms.
* New in the network: Epidimy's north lane (x 6..7) gates to Route 2 and its west forest road (rows 20..21) gates to Route 22.
* Test: `python tests/epidimy.py [screenshot_dir]`. Note: `tests/play.py` was already failing before this change.
  Delete `~/.scimon/save.json` before running `tests/smoke.py` (it expects a fresh game).

## The wider region (the town network)
Every road on the reference map is its own walkable area, wired into one graph by `routes.LINKS` -- 42 areas in all:
Riven Town, Epidimy Town, 8 styled towns, 5 wild places and 25 numbered routes.
* **Towns** (`towns.py`, drawn like Epidimy with Riven's renderer + the landmark sprites): **Stonreach Town** (quarry, moon
  crystals), **Tidebrook Town** (river with plank bridges), **Aurum City** (the golden crossroads), **Emberport City**
  (harbour, pier, lighthouse), **Verdance City** (hedges and garden arches), **Dusklight Town** (monuments under the rim),
  **Vespera City** (hedge walks), **Cinderfall Island** (volcanic ground, lava pools, two sea piers), the **Astrion Plateau**
  (the League's grand hall) and **Ost's Cabin** (windmill at the end of Route 25). Each has Cush's Repair Nook (free
  healing, pass-free) and a Supply Mart; every town's `validate()` runs at import.
* **Places** (`kanto.py`): Mossmere Wood, Mt. Crescent (glowing crystals), Hollowgate Tunnel (a lit corridor), Ascent Road
  and Seaglass Isles (sand and sea glass). Routes 2-25 are generated from seeds (winding roads, tall grass, signs,
  travelers); sea routes 19-21 are plank walkways over the ocean, and Riven Town gains a fishing pier (rows 21-23, x 10-11)
  linking to Route 21.
* `routes.validate()` now checks the whole network at import: every open tile reachable, ledges never soft-lock, NPCs
  never cut a road, signs readable, one-way graph connectivity from the town, healer warp tiles sane.
* Battle backgrounds per area: styled towns on the grass field, routes/places on the beach field (`battle.BG_FOR_AREA`).
* Test: `python tests/network.py [screenshot_dir]` - validates + renders all 42 maps, walks
  Riven -> Epidimy -> Mossmere -> Stonreach -> Mt. Crescent -> Tidebrook, opens both hidden chests and checks the
  far-wipe healer fallback.

## The wider region's Scimons (100 new species + biome encounters)
The dex grows from 9 to **109 species**: 100 originals in `species_expanded.py` (stats/learnsets derive from
archetype + a per-type technique pool; 49 new techniques cover all 18 types), with original art generated by
`tools/build_scimon_art.py` (seeded, part-based pixel-art in the established style; re-run any time, add
`--sheet` for a contact sheet at `assets/scimon/_contact_sheet.png`).
* **Habitat rules** (species_expanded.WILD_HOME, enforced by routes.validate()): Botanic/Bio/Atmospheric/Chemical/
  Mechanical/Radiant live in the grass biomes (meadow + Mossmere forest); Hydro on the sea routes' tide-grass beds;
  Cryo above the snow line of the Epidimy climb (routes 22, Ascent Road); Thermal on Cinderfall's volcanic shores
  (routes 20-21); Geologic and Metallic in the caves (Mt. Crescent, route 3/10) and Hollowgate's glow-moss chambers;
  Electric on Aurum's grid routes and the tunnel lantern line; Plasma/Quantum/Nano/Digital on the big-city roads
  (routes 5-8); Cosmic and Shadow by Dusklight's monuments (routes 8/10/12/13) and off the deep sea lanes.
  The classic Route 1 cast (Sporelet, Dewbit, Cindermite, Sparkit, Pebblon, Nanolyte) stays on Route 1 only.
* `routes.AREA_ENCOUNTERS` gives every grass-bearing area its own table; levels scale with distance from Riven
  (near 2-6, mid 6-12, far 12-18), common > uncommon > rare weights. Sea routes, Seaglass Isles, Hollowgate
  Tunnel and the Ascent Road gained encounter patches (tide-grass / glow-moss).
* Test: `python tests/specimens.py` - data integrity, sprite loading, biome rules, all 30 tables, battle smoke.

## FRLG landmarks (the reference-map build)
Every town and route follows its FireRed/LeafGreen counterpart's building placement, adapted to the region.
**All 25 routes and 5 wild places are hand-authored to their FRLG shapes** (`kanto.py` `*_ROWS` grids): Route 2's
forest corridors and hop-down ledges, Route 3's ledge tiers, Route 4's descent with the sealed chest clearing,
Route 5's Day-Care, Route 12/13's coastal water strips, Route 17's fence-railed cycling road with one-way slope
cuts, Route 19-21's sea boardwalks and islets, Route 23's checkpoint climb with its water bridge, Route 24's
Nugget Bridge at the Tidebrook exit, Mossmere's two-gate forest, Hollowgate's two-mouth tunnel, the Ascent Road's
ledge climb and Seaglass Isles' sand islets. Pass `rows=` to `kanto.Route` to hand-draw a map -- gate positions
are derived from the drawn rims and written back into each entry's `ends`, so geography and the link graph can
never disagree.
* **New landmark buildings** (`tools/town_network_art.py`): `bld_tower` (Dusklight's Monument Tower, Aurum's
  Spire), `bld_museum` (Stonreach's Museum of Science), `bld_deptstore` (Verdance's Grand Mart - extended stock),
  `bld_gatehouse` (route guard huts), `bld_mansion` (Cinderfall's Old Mansion), plus the Research Lab (Astrion
  lab sprite). Interiors reuse the shared room set with themed NPCs (Tower Keeper, Curator, wardens, scientists).
* **Towns**: Pewter-style Stonreach (museum east, gym lot north-centre), Cerulean-style Tidebrook (gym lot
  south-centre, Wheelworks west), Saffron-style Aurum (Spire on the plaza), Vermilion-style Emberport (fan club
  east, gym lot west), Celadon-style Verdance (Grand Mart north-west, Hedge Corner south-east), Lavender-style
  Dusklight (tower north-east), Fuchsia-style Vespera (Safari Gate north-east - "closed for survey"), Cinnabar-
  style Cinderfall (lab west, mansion north-west), Indigo-style Astrion Plateau (nook + mart either side of the
  road). Each town carries a fenced, signposted **gym lot** - the League runs one gym per region, so the lots
  wait for a second season (7 empty stamp slots).
* **Routes**: gate huts on 2, 2N, 5, 6, 11, 12, 15, 16, 22 and the League checkpoint on 23 (all enterable, guards
  inside); the **Day-Care** on Route 5; **Cush's nook mid-Route 10** (a real healer on the road); Route 24's
  **long plank bridge** over the river band (the Nugget Bridge); Route 17's **one-way descent** (slope ledges,
  like the cycling road); Route 25's sea cove. `routes.validate()` now also proves every route door reachable.
* Test: the network walk covers the reworked roads; `python tests/network.py [dir]`.

## Evolutions (every Sci-Mon evolves)
All 268 species evolve: the three starters climb three-stage lines (Florabot -> Floravine Lv16 -> Floratitan
Lv32; Pyrodrive -> Pyroblaze -> Pyrodrake; Aquabit -> Aquafin -> Aquarex -- dex 4-9), and every wild line runs
two stages (base -> "Rex/Prime/Nova..." final) or three (a "ling" baby -> base -> final; a seeded ~40/60 split,
159 stage species in all).  Levels trigger the change automatically after a battle: level-ups in the fight carry
over, and the overworld announces each evolution ("Florabot is evolving! ...").  Stage stats derive from the
line's archetype (babies 62%, finals ~145% with rarer catch rates and richer learnsets), stages inherit the
family's habitat so the biome rule holds per family, and babies/finals appear in the wild pools: babies common at
the low end of a route's band, finals rare at the top.  Starters and the classic Route 1 cast are never wild
outside Route 1 (enforced by routes.validate()).
* Mechanics: `data.EVOLUTIONS` / `data.CHAIN_OF` (pure data, built in data.py), `monsters.evolve` /
  `check_evolutions`, `overworld._evolution_lines`.
* Sprites: `tools/build_scimon_art.py` renders any species missing a PNG; babies are drawn smaller with a big
  visor, finals gain a golden crest and aura motes.

## Hidden chests
Two supply chests are tucked away off the beaten path (tile `X`, solid, interacted with like interior chests):
* **Epidimy Town**: the nook behind the west lake's north bank - Hydro Cell x1 + Nano Repair x2.
* **Route 4**: a tree-sealed clearing off the road - Bio Trellis x1 + Repair Cell x3.
Opening is remembered in `opened_chests` (savegame) and restored by `OverworldScene` via `map.sync_state` on travel,
restore and blackout. `routes.CHESTS` holds the registry; `routes.validate()` enforces the house rule: at most one
town and one route may hide a chest, each on an `X` tile with a reachable approach.

## New region art and character outfits
* `tools/town_network_art.py` (pure Pillow, seeded, same style as the other town generators) builds
  `assets/town/`: bridges, pier planks, mooring posts, volcanic ground, lava pools, cinder rocks, the Dusklight
  monument, moon crystals, tunnel beams, sea glass, the garden arch and the landmark buildings
  (`bld_lighthouse`, `bld_windmill`, `bld_plateau`). Re-run with `python3 tools/town_network_art.py`.
* New map letters: walkable `R` bridge, `I` pier, `V` volcanic ground, `U` sea glass; solid props `n` cinder rock,
  `o` lava (with glow), `Z` monument, `C` crystal (glow), `t` tunnel beam (glow), `K` arch, `d` mooring post,
  `J` lighthouse (2x2), `X` chest. Wired through `townview.draw_ground` / `build_props` / `Fx` glows.
* **Area outfits**: NPCs of every new town dress for their town (`towns.OUTFITS` + `towns.area_look` - sailors in
  Emberport cobalt, gardeners in Verdance leaf, league staff in royal on the Plateau...). Route travelers wear shared
  ranger / sailor / hiker palettes (`kanto.RANGER_LOOK` etc.); the Cush franchises keep Cush's own look everywhere.
  `worldmap._npc` / `_trainer` accept an explicit `look=` code (the formula behind `sprites.make_look`).

## Parity notes and deliberate differences
* Ported 1:1 from V34: type chart, techniques, species, stat/damage/capture/XP formulas, held items,
  key items, categories, shop prices/sell-back, repair, Sci-Database, interiors and their collision grids,
  NPC dialogue, rival counter-pick rule, no capture/run vs. the rival.
* Tall-grass patches are written straight into the town map (same areas as before, minus the tiles now under the plaza/crop field).
* Two tiny fixes to V34's planner: Overclock and status moves also update the simulated copy, so a status
  applied this turn ticks at end of that turn (as in scimon_py).
* Not in V34 either: save/load. Wild wins pay no credits (scimon_py's addition was not carried over).

## Publishing on GitHub

**1. Push the repo**

    git init -b main
    git add .
    git commit -m "SCI-MON Pygame edition"
    git remote add origin https://github.com/<you>/<repo>.git
    git push -u origin main

**2. Play in the browser (GitHub Pages)** -- `.github/workflows/pages.yml` builds the game to WebAssembly with
[pygbag](https://github.com/pygame-web/pygbag) on every push to `main`. One-time setup: *Settings -> Pages -> Source: GitHub Actions*.
The game is then live at `https://<you>.github.io/<repo>/` (click once on the page to start audio).
Local web test: `pip install pygbag && python -m pygbag .` then open http://localhost:8000.
`main.py` is async (`await asyncio.sleep(0)` per frame), which is a no-op on desktop, so `python main.py` works as before.

**3. Licensing.** The code and the generated art (`assets/interiors`, `assets/characters`, `assets/town`) are original, so you can choose any
licence for them. Fonts (Press Start 2P, VT323) are SIL OFL. Before making the repo public, confirm you made `assets/tiles`, `assets/buildings`
and `assets/scimon` (monster sprites) yourself or have the right to share them.

## Tests (headless)
    python tests/smoke.py   # title -> wake -> professor briefing -> starter -> rival battle
    python tests/play.py    # battle, collision, doors, shop, pack, database, capture
    python tests/specimens.py # 109 species: data, art, biome rules, per-area encounter tables
    python tests/network.py # the 42-area network: render + walk-through + hidden chests + healer fallback
    python tests/fuzz.py 1  # random input + teleports, asserts invariants
    python tests/touch.py   # touch layouts, D-pad / button events, tap routing
