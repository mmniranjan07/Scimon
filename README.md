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
| H (overworld) | the help guide: TYPES / GEAR / CONTROLS (Tab cycles pages) |
| Pack: Tab, Q/E, T, N, U/J, Del | switch tab, category, take held item, nickname, reorder party, discard |
| B (hold) / Shift | run (the Running Shoes) |
| B (press, Cycle Rig held) | hop on / off the folding cycle - outdoors only, twice the speed |
| F (overworld) | Aerolift: fast-travel to a visited rest point |
| G (overworld) | Excavator: burrow out of a cave to its mouth |
| Confirm facing water (rod held) | cast the fishing line |
| M | mute SFX | F3 | collision/hitbox overlay | F11 | fullscreen |
**Phones / tablets:** an on-screen D-pad plus **A** (confirm), **B** (back) and **PACK** buttons appear automatically; every menu can also be tapped. See *Mobile / touch* below.
Mouse works on every menu (hover, click). The window is resizable; the game renders at 960x640 and scales.

## One-way ledges
Tile `l` is a ledge you can hop **down** but never climb: walking south into it from the tile above makes the player hop over it
onto the tile below (small arc + shadow); from the sides or from below it is a normal wall. Stacked `l` tiles form a vertical wall.
It is drawn procedurally (`townview._draw_ledges`), the rule lives in `TileMap.ledge_landing`, the hop in `Player.begin_jump`, and
`routes.validate()` understands the hop, so it also fails the build if a ledge could trap the player with no way back to the exit.

## Field abilities & fishing (the FireRed HM model)
Six field abilities replace FireRed's HMs, each unlocked at the same kind of milestone FireRed uses, tracked durably in the save
(`state.abilities` + the module key item; `abilities.sync_from_items` re-derives one from the other, so old saves migrate):

| Ability | FireRed analogue | Unlocked by |
|---|---|---|
| **Lumen** | HM05 Flash (Oak's aide, 10-dex gate) | Prof. Venn, once the Sci-Dex holds 10 species |
| **Aerolift** | HM02 Fly (a route gate) | Leader Fern, with the Green Stamp (press **F** to fast-travel to visited rest points) |
| **Aquaboard** | HM03 Surf (a story milestone) | The boss-victory aftermath - walk onto water tiles with a Hydro Scimon; open water has its own encounter pool |
| **Excavator** | HM04 Strength (a fetch sidequest) | The Route 4 supply chest (press **G** in a cave to tunnel back to its mouth) |
| **Hydroclimb** | HM07 Waterfall (an item ball in a postgame place) | The item ball on the Ascent Road - the falls it opens are a shortcut into a sealed pocket with its own chest |
| **Probe/Field/Deep Rod** | FireRed's rod tiers | Fisher Ora (Epidimy), a fisherman on Route 12, a fisherman on Route 20 |

Every ability also needs a party Sci-Mon of its required type (Hydro boards water, Radiant lights caves, ...), like needing a
mon that can learn the HM. **Fishing** is active: face any water tile and press confirm to cast (bobber, short wait, ~70% bite);
the rod's tier decides the level range, and fishing needs only a rod - never the Aquaboard. Cave places (Mt. Crescent, Hollowgate,
the Ascent) sit in darkness; Lumen widens the light around the player (FireRed's Flash, without blocking progress).
`routes.validate()` carries a second reachability pass that treats the falls as walkable, so the pocket behind them can never
soft-lock, and the chest rule now allows one town, one route and one wild place to hide a chest.

## IVs and EVs (Gen 3 rules, this build)
Every Scimon is born with an **Individual Value (IV, 0-31)** in each of the seven stats - the born
talent that makes two members of a species differ, rolled at creation and never re-rolled. Defeated
Scimons grant **Effort Values (EVs)**: 1 / 2 / 3 points in their highest base stat by stage (first /
middle / final), to the active Scimon and any healthy **Exp Coupler** holder, silently like Gen 3.
Effort is capped at **255 per stat and 510 in total**; captures grant nothing. Both feed Gen 3's
level-scaled stat formula:
    stat = (2*base + IV + EV/4) * level / 100 + 5      (HP: ... + level + 10; energy: base*level/50 + 15 + level)
With zero IVs and zero effort this collapses to the original V34 formula, and old saves keep their
stats until the load migration rolls their IVs and folds the retired flat vitamin bonus into effort
(2 EV per bonus point, serum-capped). The **vitamin serums** now grant 10 effort each but only train a
stat up to 100 - FireRed's "vitamins stop at 100 EVs" rule - while wild battles can push a stat past
100 up to 255. The read-out lives in the Pack's Sci-Mon panel and the Sci-Database preview (Effort
lists trained stats only; IVs show all seven). Test: `python tests/eviv.py`.

## FireRed QoL: the road, the bag and the bench (this build)
* **Running shoes + the Cycle Rig** (FireRed's B-to-run and Bicycle): hold **B / Shift** to run (x1.6);
  **Mechanic Wade** (Tidebrook Wheelworks, once you hold a gym stamp) hands over the **Cycle Rig** key
  item - press **B** outdoors to hop on (x2.1). The rig never fits through doors, so buildings always
  dismount you.
* **Repel Fields** (FireRed's Repel / Super Repel): used from the Pack with no Sci-Mon target; wild
  encounters are suppressed for 100 / 200 steps while the HUD counts them down. Fishing ignores the
  field, exactly like FireRed.
* **Vitamin serums + the Grow Cell** (FireRed's vitamins + Rare Candy): six serums (HP Patch, Power,
  Guard, Focus, Aegis, Turbo) each grant 10 effort in their stat - serum-training a stat up to 100
  (Gen 3's vitamin cap), with the 510 total cap honoured; HP Patch raises the cap without healing.
  The **Grow Cell** grants one level (respecting the region's level cap) and can push a Sci-Mon over
  its evolution level - the FireRed evolution cutscene plays right from the Pack. All stocked at every
  Supply Mart.
* **Overworld nanites** (FireRed's walking poison): every 4 steps a party Scimon afflicted with
  Nanite-Infected loses 1/16 of its max HP; a full blackout heals the team and warps to the last healer,
  exactly like a battle loss. A Stabilizer or any healer clears it.
* **The Vs. Scanner** (FireRed's Vs. Seeker): **Club Scout Pella** (Emberport) hands it over on first
  talk. It recharges over 100 walked steps (HUD chip); while charged, talking to any beaten trainer -
  **gym leaders and their coaches included** - offers a rematch. Route travelers scale to your strongest
  Scimon (+2..15, capped); gym rings come back +12 levels. Rematches never re-award a leader's signature
  disc or field module.
* **Nicknames** (FireRed's nickname prompt): the Pack's Sci-Mon detail panel gains a **Nickname (N)**
  button - type a name (empty restores the species' own), and evolutions preserve it.
* **Held battle gear** (FireRed's held-item shelf, stocked at the Verdance Grand Mart): the **Nutrient
  Loop** heals 1/16 each turn (Leftovers), the **Holdfast Band** may endure a knockout at 1 HP (Focus
  Band), the **Torque Band** and **Logic Clip** boost physical / special techniques by 50% but lock the
  holder into the first technique used until it switches (Choice Band, incl. the locked fight menu and
  the battle-end reset), the **Reticle Lens** doubles the critical chance (Scope Lens), the **Lucky
  Mote** adds 50% EXP - catch-EXP included (Lucky Egg) - and the **Exp Coupler** gives every healthy
  bench holder half of the active Scimon's EXP (Exp. Share).

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
| `touch.py` | mobile support: layouts, on-screen D-pad / A / B / PACK / AERO, multi-touch finger tracking |
| `abilities.py` | field abilities (FireRed's HMs), their unlock items + grant gates, the FlyMenu and the fishing rods/pools |
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
**Every route and wild place from Route 2 to the end of the region is now decoded metatile-for-metatile from the
pokefirered decomp** (`kanto.py` `*_ROWS` grids, generated from `data/layouts/<Map>/map.bin` with FRLG's own
collision bits): Route 2 (split at the forest between the Viridian-side run and the Route 2 North Pewter approach),
Mossmere = Viridian Forest's full 54x69 wood, Route 3 + Route 4's west mountain road merged into one composite
(FRLG connects them over Mt. Moon's ridge), Mt. Crescent = Mt. Moon 1F, Route 4's east ledge descent with the
hidden clearing, Route 5's fenced Day-Care gardens, Route 7/8's underground-path gate stations, Route 9's rock
terraces, Route 10's two-mouth tunnel hill, Route 12's full 24x120 boardwalk bridge run, Route 13's hedge maze
with its plank crossing, Route 14's tiered sand fields, Route 16-18's fence-railed cycling road (24x160 Route
17), Route 19-21's sea channels (FRLG's surf water becomes plank causeways and sand spits - the game has no
surf), Route 22's Viridian gate station, Route 23's full 24x160 badge-gate climb with its pillar mazes, water
channels and checkpoint buildings, Route 24's Nugget Bridge, Route 25's cape and Sea Cottage, Hollowgate = Rock
Tunnel 1F, the Ascent = Victory Road 1F and Seaglass = Seafoam Islands 1F. Where FireRed passes through a gate
building's interior or a surf channel, the game's border gates carve the road through (the checkpoint hut stands
beside it); where FireRed's one-way ledges would seal a pocket for good, small stair-gap connectors keep every
tile reachable. Pass `rows=` to `kanto.Route` to hand-draw a map -- gate positions are derived from the drawn
rims and written back into each entry's `ends`, so geography and the link graph can never disagree.
* **New landmark buildings** (`tools/town_network_art.py`): `bld_tower` (Dusklight's Monument Tower, Aurum's
  Spire), `bld_museum` (Stonreach's Museum of Science), `bld_deptstore` (Verdance's Grand Mart - extended stock),
  `bld_gatehouse` (route guard huts), `bld_mansion` (Cinderfall's Old Mansion), plus the Research Lab (Astrion
  lab sprite). Interiors reuse the shared room set with themed NPCs (Tower Keeper, Curator, wardens, scientists).
* **Towns**: Pewter-style Stonreach (museum east, **Gym** north-centre), Cerulean-style Tidebrook (**Gym** north-east,
   Wheelworks west), Saffron-style Aurum (Spire on the plaza, **Gym** west of it), Vermilion-style Emberport (fan club
   east, **Gym** west), Celadon-style Verdance (Grand Mart north-west, **Gym** west-centre), Lavender-style
   Dusklight (tower north-east), Fuchsia-style Vespera (Safari Gate north-east - "closed for survey", **Gym** centre-south),
   Cinnabar-style Cinderfall (lab west, **Gym** south, mansion north-west), Indigo-style Astrion Plateau (nook + mart either side of the
   road).

## The gyms (FireRed's badge run)
Seven badge gyms open the season, one per town, each keeping its FireRed counterpart's type: **Leader Bastian**
(Stonreach, Geologic), **Leader Nerissa** (Tidebrook, Hydro), **Lt. Volta** (Emberport, Electric), **Leader Sylva**
(Verdance, Botanic), **Warden Vexa** (Vespera, Chemical), **Leader Cerebra** (Aurum, Quantum) and **Prof. Calder**
(Cinderfall, Thermal). Fern's Green Gym (Epidimy) holds the founding slot, FireRed badge order: Green, Boulder,
Cascade, Thunder, Rainbow, Soul, Marsh, Volcano. Every gym uses the ring order - two type-themed coaches gate the
leader (`requires`/`aside`), the leader's team matches its FireRed ace level, and the first win hands over the
gym's **stamp** plus a signature **move disc** (the gym-TM analogue: Boulder Rush, Tidal Crash, Coil Driver,
Petal Tempest, Venom Wash, Mind Render, Pyroclast - each disc-only, teachable once to a compatible Sci-Mon).
Wild zones already scale to this ladder (`encounters.GYM_REFERENCE` ceilings), and **Route 23's checkpoint now
asks for all eight stamps** before its warden steps out of the Ascent road (a stamps-aware reachability pass in
`routes.validate()` keeps the gate honest).
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
over, and each evolution plays a FireRed-style cutscene (the old form pulses white faster and faster to rising
beeps, a shockwave of light fills the screen, and the new form lands in a sparkle shower) before the
"Congratulations!" dialogue.  Learning a technique with a full moveset prompts FireRed-style as well: the
battle pauses, the player picks which of the four techniques to forget (or gives up), and evolution back-fill
queues the same prompts after the cutscene (`scenes.LearnMoveScene`).  Stage stats derive from the
line's archetype (babies 62%, finals ~145% with rarer catch rates and richer learnsets), stages inherit the
family's habitat so the biome rule holds per family, and babies/finals appear in the wild pools: babies common at
the low end of a route's band, finals rare at the top.  Starters and the classic Route 1 cast are never wild
outside Route 1 (enforced by routes.validate()).
* Mechanics: `data.EVOLUTIONS` / `data.CHAIN_OF` (pure data, built in data.py), `monsters.evolve` /
  `check_evolutions`, `overworld._evolution_lines`, `scenes.EvolutionScene` (the cutscene; sounds in `audio.py`).
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

## Battle depth (the FireRed battle feel)
* **Catch-EXP**: a successful capture still teaches the team a little - the active Scimon banks a
  **quarter of the defeat gain** (the Lucky Mote boosts it; Exp. Coupler holders siphon half of that),
  announced after the containment line. Captures never grant effort (Gen 3 keeps EVs on faints only).
* **The energy system** (replaces move PP): every Scimon carries an energy reserve, a trained stat like
  HP -- it scales with the species' reserve organ (the seventh base stat), so it grows with level and
  jumps on evolution (`monsters.recalc_stats`). Each technique drains its **energy cost per use**,
  derived from its power (status 3, damage 3 + power/10 capped at 12; lock-down statuses cost 4) --
  stronger techniques cost more. The fight menu shows `TYPE n EN` per move,
  disables unaffordable techniques, and offers **Struggle** (35 power, 25% recoil, free) when nothing
  is affordable. Both info panels carry a gold **ENERGY** bar (below HP; the player's adds EXP under
  it). Energy refills whenever the Scimon is fully healed -- Cush's Repair Nook (and every healer), and
  the renamed **Energy Cell** (mart stock, ¢450, id unchanged) restores one Sci-Mon's reserves from the
  Pack or mid-battle. The **DEFEND** action braces (incoming damage halved) and recharges 25% of max
  energy; the **Deep Cycle** ability recharges 1/8 of max energy every turn.
* **Stat stages**: Power / Defense / Sp. Defense / Speed move on FireRed's -3..+3 ladder with the
  `(2+s)/2` multiplier. Overclock & friends raise Power; new techniques spread the other axes (Damper
  Field, Coolant Flush, Turbine Spool, Impedance Matrix, Feedback Loop, Weighted Net) and are threaded
  deterministically (~40%) into type-matched learnsets. Stage chips (`P+2`, `D-1`) render beside the
  level in the info panel; switching out resets stages.
* **New statuses**: **Suspended** (standby: skips 1-3 turns, then wakes and acts) and **Crystallized**
  (frozen: 20% thaw per attempt, a Thermal hit thaws instantly) join the six V34 faults. The Stabilizer
  (and the battle menu's item use) clears any of them; a status boosts capture odds as before.
  (The old Stability gauge was removed -- its energy cost, DEFEND recharge and Deep Cycle roles all
  moved to the energy reserve.)
* **Battle abilities**: all 18 ability names in the Sci-Mon database now do something (see
  `data.BATTLE_ABILITIES`) - Condensation/Heat Sink absorb Hydro/Thermal hits, Sturdy Plating endures one
  knockout, Swarm Logic/Overdrive/Night Optics/Gyro Balance tune damage and crits, Photosynthesis/
  Regenerative Weave/Deep Cycle regenerate, Ember Body/Static Charge/Spore Vent punish contact,
  Coolant Flow/Buoyant Core grant status immunities, Vacuum Seal drains double energy, Grid Tether blocks
  fleeing and Silent Run guarantees it. The ability name renders on each info panel.
* **Smarter enemy AI**: moves score power x effectiveness x STAB, but status moves are played tactically
  (buff early, inflict on a clean target, never on an immune or already-afflicted one) and trainer
  Scimon switch out of a beaten type matchup 30% of the time when a bench member resists and answers.
* Old saves migrate silently: the retired `power_stage` field folds into the new stage dict, pre-energy
  saves (with per-move `move_pp`) come back with full energy reserves, and Sturdy never leaks out of a battle.
* Tall-grass patches are written straight into the town map (same areas as before, minus the tiles now under the plaza/crop field).
* Two tiny fixes to V34's planner: Overclock and status moves also update the simulated copy, so a status
  applied this turn ticks at end of that turn (as in scimon_py).
* Not in V34 either: save/load. Wild wins pay no credits (scimon_py's addition was not carried over).

## FireRed features: the Day-Care, the Safari Reserve and the Game Corner (this build)
Three classic FireRed systems, ported from the pokefirered decomp (mechanics read straight out of
`src/daycare.c`, `src/safari_zone.c`, `src/battle_main.c` and `src/battle_script_commands.c`) and
scaled to SCI-MON's habitat-pairing, no-genders model.

**The Day-Care (Route 5, FRLG's breeding).** Keeper Sorrel's day-care building (FRLG building sprite
rendered by `tools/extract_frlg_buildings.py`) now takes two deposited Scimons, which bank every
overworld step as EXP (FireRed's steps==EXP rule; new learnset moves replace the first technique with
no prompt, the daycare rule).  Withdrawal costs 100 credits + 100 per level gained, applied
level-by-level.  While both slots are filled, every 100 steps rolls against the pair's compatibility:
same family 50%, shared habitat 20% (SCI-MON has no genders, so normal habitats stand in for egg
groups), first-stage babies are infertile (Gen 3's undiscovered group).  A winning roll leaves an egg
with Sorrel; accept it into your party and it hatches after walking (rarity x hatch cycles x 60
steps) into the family's first stage at level 5, inheriting 3 IVs and moves from its parents.
The Day-Care counter is a modal scene like the shop (`menus.DaycareScene`).

**The Safari Reserve (Vespera's Safari Gate, FRLG's Safari Zone).** Pay the warden 200 credits for 20
Safari Modules and 400 steps, and she warps you into the reserve: four fenced sub-zones (the entry
meadow, the north wetland, the west ridge, the east grove) with their own habitat tables and a
gym-6 level ceiling.  You never battle in there -- every encounter opens a safari battle with only
BALL / BAIT / ROCK / RUN.  The math is FireRed's, verbatim: bait halves the catch factor (floor 3)
and quarters the escape factor, rocks double the catch factor (cap 20) and double the escape factor,
counters tick down while the Scimon watches, and after every action it may flee (escape factor x 5%).
The catch roll is the Safari Ball's (bonus 15) shake test, with the species' 0-200 catch rate
rescaled to FRLG's 0-255 scale; the derived escape rate rises with rarity.  The PA warns you at half,
100 and 10 steps, escorts you out at zero, and walking out the gate hands any leftover modules back.
The session is saved (`st.safari`).

**The Game Corner (Verdance, FRLG's casino).** Attendant Coyn runs the three-reel slot machine and
Dealer Vera the five-card-draw data-poker table.  Coins are bought at the counter (10 credits each,
never sold back; `st.coins`, saved).  The slots use FireRed's skill stop -- SPIN sets all three reels
running, then you stop each in turn, and the symbol is wherever the strip actually is -- over a
15-cell strip tuned to return about 99.9 coins per 100 bet (triples 300/50/30/12/6, cherries 2/1).
The poker table is standard Jacks-or-better video poker (bet, deal, hold any cards, draw; Royal 250
down to a pair of Jacks x1).  Both are modal scenes (`casino.SlotScene` / `casino.PokerScene`) with
their own synth SFX (reel tick, win chime, jackpot fanfare in `audio.py`).

* Mechanics: `daycare.py` (breeding + step bank), `safari.py` (session + FRLG-verbatim math),
  `casino.py` (reels + paytables), `battle.SafariBattleScene`, `routes._safari_rows` + `ZONE_TABLE`
  / `BAND_OVERRIDES` (the reserve), `state.buy_coins`, the `service="daycare"/"casino"/"poker"/
  "safari"` NPC hooks in `overworld._after_talk`, the step tick in `overworld._on_step`.
* Sprites: `assets/town/bld_daycare.png`, `bld_safarigate.png`, `bld_casino.png` (extracted from the
  pokefirered tilesets by `tools/extract_frlg_buildings.py`).
* Test: `python tests/daycare.py` (compat, guards, costs, egg roll + hatch, save round-trip),
  `python tests/safari.py` (session, factor math, ball/escape rolls, reserve zones),
  `python tests/casino.py` (coin economy, slot balance, hand evaluator, scene flows).

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
    python tests/qol.py     # repels, cycle rig, exp coupler, vitamins, vs. scanner, nicknames, held gear
    python tests/eviv.py    # IVs, the Gen 3 stat formula, effort yields + caps, serum cap, migration
    python tests/daycare.py # the Day-Care: compat, deposit guards, costs, eggs + hatching, saves
    python tests/safari.py  # the Safari Reserve: session, FRLG battle math, zones + links
    python tests/casino.py  # the Game Corner: coins, slot balance, poker hands, scene flows
    python tests/fuzz.py 1  # random input + teleports, asserts invariants
    python tests/touch.py   # touch layouts, D-pad / button events, tap routing
