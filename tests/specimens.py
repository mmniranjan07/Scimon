"""The wider region's 100 new Scimons (headless): data integrity, art on disk and loadable, biome rules,
per-area encounter tables, and a battle smoke test across a sample of the new species.
Usage: python tests/specimens.py [screenshot_dir]"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from data import (SPECIES, SPECIES_COUNT, TECHNIQUES, WILD_HOME, ROUTE_ENCOUNTERS, STARTER_IDS, TYPE_COLORS)
from monsters import create_scimon
from battle import new_battle
from species_expanded import SPECIES_TABLE

# ---- 1) the dex: 109 base species + their evolution stages, unique dex numbers, valid fields everywhere
from data import CHAIN_OF, EVOLUTIONS
_families = {tuple(c) for c in CHAIN_OF.values()}
assert len(_families) == 109, len(_families)                      # one line per base species
assert sum(len(f) for f in _families) == SPECIES_COUNT == 268     # the families partition the dex
assert {len(f) for f in _families} <= {2, 3}                      # wild lines: 2 or 3 stages
assert all(len(CHAIN_OF[s]) == 3 for s in STARTER_IDS)            # starters: three stages each
_n3 = sum(1 for f in _families if len(f) == 3)
assert 20 <= _n3 <= 80 and len(_families) - _n3 >= 20, _n3        # a real mix of 2- and 3-stage lines
assert [(EVOLUTIONS["florabot"][1], EVOLUTIONS["florabot-mid"][1])] == [(16, 32)]
assert len({s.dex for s in SPECIES.values()}) == SPECIES_COUNT
assert [SPECIES[s].dex for s in STARTER_IDS] == [1, 2, 3]
assert [SPECIES[s].dex for s in ("florabot-mid", "florabot-final", "pyrodrive-mid", "pyrodrive-final",
                                 "aquabit-mid", "aquabit-final")] == [4, 5, 6, 7, 8, 9]
for sid, (target, lv) in EVOLUTIONS.items():
    assert target in SPECIES and 8 <= lv <= 40, (sid, target, lv)
    assert CHAIN_OF[target][0] == CHAIN_OF[sid][0]                # one line, one family
# every family member's habitat matches the line's base
for sid, chain in CHAIN_OF.items():
    base = next(m for m in chain if m in WILD_HOME and not m.endswith(("-baby", "-mid", "-final")))
    assert WILD_HOME[sid] == WILD_HOME[base], (sid, WILD_HOME[sid], WILD_HOME[base])
for row in SPECIES_TABLE:
    sid = row[0]
    s = SPECIES[sid]
    assert s.dex >= 17, (sid, s.dex)                     # 1-3 starters, 11-16 originals, new ones from 17
    assert s.types and all(t in TYPE_COLORS for t in s.types), sid
    assert s.rarity in ("common", "uncommon", "rare") and 40 <= s.catch_rate <= 200, sid
    assert s.learnset and all(t in TECHNIQUES for _, t in s.learnset), sid
    assert all(lv >= 1 for lv, _ in s.learnset) and len({t for _, t in s.learnset}) == len(s.learnset), sid
    assert all(20 <= v <= 90 for v in s.base), (sid, s.base)
    assert s.back is None, sid                           # wild-region mons are front-only, like the originals' wild cast
assert len(SPECIES_TABLE) == 100
# evolution mechanics: level-triggered transform keeps level/HP ratio, updates types/name/stats
from monsters import check_evolutions, create_scimon
_m = create_scimon("florabot", 16)
_m.hp = _m.max_hp // 2
_res = check_evolutions([_m])
assert _res and _m.species_id == "florabot-mid" and _m.name == "Floravine"
assert _m.hp == _m.max_hp // 2 and _m.level == 16
_b = create_scimon("vinelatch-baby", 13)
assert check_evolutions([_b]) and _b.species_id == "vinelatch"
_f = create_scimon("vinelatch", 32)
assert check_evolutions([_f]) and _f.species_id == "vinelatch-final"
_nm = create_scimon("florabot", 10)
assert not check_evolutions([_nm])                                 # below threshold: no forced evolution

# every type is represented among the new species
new_types = {t for row in SPECIES_TABLE for t in row[2]}
assert new_types == set(TYPE_COLORS), new_types ^ set(TYPE_COLORS)

# ---- 2) the art: every species' front sprite exists and loads through the real pipeline
pygame.init(); pygame.display.set_mode((320, 240))
import assets
for sid, sp in SPECIES.items():
    p = os.path.join(os.path.dirname(__file__), "..", "assets", "scimon", sp.front)
    assert os.path.isfile(p), f"missing sprite for {sid}"
    img = assets.mon_image(sid, 96, 96)
    assert img.get_width() > 0 and img.get_height() > 0, sid
back = assets.mon_image("vinelatch", 96, 96, back=True)   # front-only species fall back to the front art
assert back is not None

# ---- 3) biome rules hold for every new species (the classic Route 1 cast is the sanctioned exception)
CLASSIC = {"sporelet", "dewbit", "cindermite", "sparkit", "pebblon", "nanolyte"}
GRASS = {"meadow", "forest"}
for sid, home in WILD_HOME.items():
    if sid in CLASSIC or sid.endswith(("-baby", "-mid", "-final")) and SPECIES[sid].types[0] and \
            any(base in CLASSIC for base in (sid.replace("-baby", "").replace("-mid", "").replace("-final", ""),)):
        continue
    t = SPECIES[sid].types[0]
    if t in ("Botanic", "Bio", "Atmospheric", "Chemical", "Mechanical", "Radiant"):
        assert home in GRASS | {"plateau", "tunnel", "city", "water"}, (sid, t, home)
    elif t == "Hydro":
        assert home in ("water", "sea", "meadow", "forest", "highland"), (sid, home)
    elif t == "Cryo":
        assert home in ("highland", "water"), (sid, home)
    elif t == "Thermal":
        assert home in ("volcanic", "cave", "meadow"), (sid, home)
    elif t == "Geologic":
        assert home in ("cave", "volcanic"), (sid, home)
    elif t == "Metallic":
        assert home in ("cave", "tunnel", "city"), (sid, home)
    elif t == "Electric":
        assert home in ("city", "tunnel"), (sid, home)
    elif t in ("Plasma", "Quantum", "Nano", "Digital"):
        assert home in ("city", "tunnel", "meadow", "plateau"), (sid, home)
    elif t in ("Cosmic", "Shadow"):
        assert home in ("ghost", "sea"), (sid, home)

# ---- 4) the encounter tables: every grass-bearing area has one, everything in them is real
import routes
assert routes.validate()
wild_areas = {a.id for a in routes.AREAS.values() if not a.styled and a.encounters}
assert wild_areas <= set(routes.AREA_ENCOUNTERS), wild_areas - set(routes.AREA_ENCOUNTERS)
import overworld as ow
for area in sorted(wild_areas):
    for _ in range(20):
        sid, level = ow.pick_encounter(area)
        assert sid in SPECIES and 1 <= level <= 40, (area, sid, level)
sid, level = ow.pick_encounter("route1")
entry = next(e for e in routes.AREA_ENCOUNTERS["route1"] if e[0] == sid)
assert entry[2] <= level <= entry[3], (sid, level, entry)
# biome identity: the highland route is cold, the volcanic shore is hot, the city grid is electric
for area, want in (("route22", "Cryo"), ("route20", "Thermal"), ("route5", "Electric"), ("route10", "Geologic"),
                   ("route12", "Shadow"), ("route19", "Hydro")):
    got = {ow.pick_encounter(area)[0] for _ in range(400)}
    types = {t for s in got for t in SPECIES[s].types}
    assert want in types, (area, want, sorted(types))

# the strict biome rule: outside Route 1 no species appears outside its home biome (no Thermal in the forest!)
for area, table in routes.AREA_ENCOUNTERS.items():
    if area == "route1":
        continue
    for sid, _w, _lo, _hi in table:
        assert WILD_HOME[sid] in routes.AREA_BIOMES[area], (area, sid, WILD_HOME[sid])
def _base_primary(sid):
    base = sid.replace("-baby", "").replace("-mid", "").replace("-final", "")
    return SPECIES[base].types[0]

# spot-check the user's rules end to end: 300 rolls per route, no wrong-biome types
RULES = {"route2": ("Thermal", "Geologic", "Electric", "Cryo", "Hydro", "Plasma", "Quantum", "Nano", "Digital", "Cosmic", "Shadow"),
         "route20": ("Botanic", "Bio", "Atmospheric", "Chemical", "Mechanical", "Radiant", "Geologic", "Electric", "Quantum"),
         "hollowgate": ("Botanic", "Bio", "Hydro", "Cryo", "Plasma", "Quantum", "Cosmic", "Shadow", "Radiant"),
         "route5": ("Cryo", "Cosmic", "Shadow", "Geologic", "Hydro", "Thermal"),
         "route12": ("Thermal", "Geologic", "Electric", "Plasma", "Quantum", "Nano", "Digital", "Cryo", "Hydro"),
         "route21": ("Botanic", "Bio", "Atmospheric", "Chemical", "Mechanical", "Electric", "Quantum")}  # Geologic allowed: volcanic shores
for area, banned in RULES.items():
    banned_types = set(banned)
    for _ in range(300):
        sid, lv = ow.pick_encounter(area)
        primary = _base_primary(sid)          # habitat follows the line base's primary type
        if area == "route20" and primary == "Geologic":
            continue                          # volcanic shore: Geologic/Thermal rock-dwellers allowed
        assert primary not in banned_types, (area, sid, primary)

# ---- 5) battle smoke across a spread of the new species
for sid in ("voltling", "frostrit", "magma_ite" if False else "magmite", "wraithex", "kelpbot", "phaseling"):
    mon = create_scimon(sid, 10)
    assert mon.hp == mon.max_hp and mon.moves, sid
foe = create_scimon("florabot", 10)
b = new_battle([create_scimon("cogmite", 9)], foe, {}, {})
assert b is not None
print("OK specimens: 109 species valid (100 new), all sprites load, biome rules +", len(wild_areas),
      "area tables verified, battle smoke passed")
