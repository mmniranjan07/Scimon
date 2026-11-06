"""Headless field-ability test: grant gates, module unlocks, surf walking + water encounters, the active
fishing flow, Aerolift fast-travel, the Excavator cave exit, the Hydroclimb waterfall shortcut and the
save/load round trip of every unlock."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine
import abilities
import data
from data import SPECIES
from monsters import create_scimon
from state import GameState
from routes import AREAS, CAVE_PLACES, FALLS_TILE, ITEM_BALLS, LINKS, PLACE_AREAS
from encounters import select_encounter
import layered_room

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/opencode/shots"; os.makedirs(OUT, exist_ok=True)
random.seed(7)


def first_species(req_type):
    return next(sid for sid, sp in SPECIES.items() if req_type in sp.types)


# ---- 1. gates -------------------------------------------------------------------------------------
st = GameState()
assert abilities.gate_met(st, None)
assert not abilities.gate_met(st, "flag:boss_beaten"), "flag gate open too early"
st.story.add("boss_beaten")
assert abilities.gate_met(st, "flag:boss_beaten")
assert not abilities.gate_met(st, "dex:10"), "dex gate open too early"
for sid in list(SPECIES)[:10]:
    st.captured.add(sid)
assert abilities.gate_met(st, "dex:10")
assert abilities.gate_met(st, "dex:3") and not abilities.gate_met(st, "dex:99")
print("OK gates")

# ---- 2. module items unlock abilities (idempotent) ------------------------------------------------
st = GameState()
st.add_item("abl_lumen", 1)
st.add_item("abl_hydroclimb", 1)
assert set(abilities.sync_from_items(st)) == {"lumen", "hydroclimb"}
assert abilities.sync_from_items(st) == [], "sync not idempotent"
assert st.abilities == {"lumen", "hydroclimb"}
assert abilities.ABILITY_ITEM.keys() == abilities.ABILITIES.keys()
for item_id in abilities.ABILITY_ITEM.values():
    assert item_id in data.CATALOG, f"missing catalog item {item_id}"
    assert data.CATALOG[item_id].permanent
print("OK module sync")

# ---- 3. can_use = unlock + required party type ----------------------------------------------------
st = GameState()
st.abilities.add("aquaboard")
st.party = [create_scimon("florabot", 8)]                      # Botanic: no Hydro in the party
assert abilities.has_ability(st, "aquaboard") and not abilities.can_use(st, "aquaboard")
st.party = [create_scimon("aquabit", 8)]                       # the Hydro starter
assert abilities.can_use(st, "aquaboard")
print("OK can_use")

# ---- 4. surf: water walkable + water-zone encounters ------------------------------------------------
import map as map_mod
m = map_mod.TileMap.route("route21")                            # a sea route with real W tiles
w_tiles = [(x, y) for y in range(m.h) for x in range(m.w) if m.tile_at(x, y) == "W"]
assert w_tiles, "route21 has no water"
wx, wy = w_tiles[0]
assert m.is_solid(wx, wy), "water must be solid without the Aquaboard"
m.walkable_override.add("W")
assert not m.is_solid(wx, wy), "Aquaboard must open the water"
zone = abilities._water_zone("route21")
assert zone and zone["habitat_id"] in ("water", "sea")
rolled = {select_encounter(st, zone)[0] for _ in range(200)}
import routes as routes_mod
fams = {fid for fid, f in data.FAMILIES.items() if "water" in f["normal_habitats"] or "sea" in f["normal_habitats"]}
assert all(data.FAMILY_OF[sid] in fams for sid in rolled), "surf pool leaked a land family"
assert "epidimy" not in routes_mod.ENCOUNTER_ZONES              # styled towns stay peaceful
print("OK surf")

# ---- 5. fishing: rod tiers -----------------------------------------------------------------------
st = GameState()
st.stamps.add("green"); st.story.add("boss_beaten")             # phase 2: the widest caps apply
seen_ranges = {}
for rod, (lo, hi) in (("probe_rod", (2, 8)), ("field_rod", (10, 20)), ("deep_rod", (20, 35))):
    got = [abilities.fishing_encounter(st, "route21", rod) for _ in range(300)]
    got = [g for g in got if g]
    assert got, f"{rod} never bites"
    seen_ranges[rod] = (min(lv for _s, lv in got), max(lv for _s, lv in got))
    assert seen_ranges[rod][0] >= lo - 2 and seen_ranges[rod][1] <= hi, (rod, seen_ranges[rod])
assert not abilities.fishing_encounter(st, "route21", "no_such_rod")
# fishing works even where no water zone is registered (Epidimy's lake)
got = [abilities.fishing_encounter(st, "epidimy", "probe_rod") for _ in range(100)]
assert any(g for g in got), "Epidimy lake should still fish the plain water pool"
print("OK fishing tiers", seen_ranges)

# ---- 6. the item ball grants Hydroclimb -----------------------------------------------------------
assert "ascent" in ITEM_BALLS and ITEM_BALLS["ascent"]
ib_def = ITEM_BALLS["ascent"][0]
assert ib_def["loot"] == (("abl_hydroclimb", 1),)
ball = layered_room.item_ball(ib_def["tile"], ib_def["key"], ib_def["loot"])
st = GameState()
lines = ball.interact(st)
assert st.qty("abl_hydroclimb") == 1 and ball.taken
assert any("Hydroclimb" in ln for ln in lines)
assert ball.interact(st) and "scuffed" in ball.interact(st)[0]   # taken: no second loot
ball.sync(st); assert ball.taken
fresh = layered_room.item_ball(ib_def["tile"], ib_def["key"], ib_def["loot"])
fresh.sync(GameState()); assert not fresh.taken
print("OK item ball")

# ---- 7. the waterfall shortcut ---------------------------------------------------------------------
am = map_mod.TileMap.route("ascent")
falls = [(x, y) for y in range(am.h) for x in range(am.w) if am.tile_at(x, y) == FALLS_TILE]
assert len(falls) == 3, falls
fx, fy = falls[0]
assert am.is_solid(fx, fy), "falls must be solid without Hydroclimb"
am.walkable_override.add(FALLS_TILE)
assert not am.is_solid(fx, fy), "Hydroclimb must open the falls"
# the pocket behind the falls: gated without the ability, reachable with it
from routes import _reach, LINKS
solid = __import__("worldmap").OVERWORLD_SOLID
arrivals = {(tx, ty) for links in LINKS.values() for (tgt, (tx, ty), _f) in links.values() if tgt == "ascent"}
base = set().union(*(_reach(am.rows, am.w, am.h, s, solid) for s in arrivals))
with_ab = set().union(*(_reach(am.rows, am.w, am.h, s, solid - {FALLS_TILE}) for s in arrivals))
pocket = {(25, 6), (24, 6), (26, 6), (24, 7), (25, 7), (24, 8), (25, 8), (26, 8)}
assert not (pocket & base), "pocket leaked without Hydroclimb"
assert pocket <= with_ab, "pocket unreachable even with Hydroclimb"
assert {t for t, _ in (LINKS["ascent"].items())} is not None
exits = set(LINKS.get("ascent", {}))
for t in pocket:
    assert exits & _reach(am.rows, am.w, am.h, t, solid - {FALLS_TILE}), f"soft-lock in the pocket at {t}"
print("OK waterfall shortcut")

# ---- 8. excavator places ---------------------------------------------------------------------------
for area in CAVE_PLACES:
    assert area in AREAS, f"cave place {area} missing"
    arr = [(tx, ty) for links in LINKS.values() for (tgt, (tx, ty), _f) in links.values() if tgt == area]
    assert arr, f"{area} has no burrow exit"
print("OK cave places")

# ---- 9. save round trip ------------------------------------------------------------------------------
import savegame
st = GameState()
st.party = [create_scimon("aquabit", 10)]
st.add_item("abl_aquaboard", 1); st.add_item("abl_aerolift", 1)
abilities.sync_from_items(st)
st.captured.add("aquabit"); st.captured.add("florabot")
raw = savegame.serialize(st)
st2 = GameState()
savegame._read = lambda: raw                                   # feed the serialized blob back
assert savegame.load(st2)
assert st2.abilities == {"aquaboard", "aerolift"}
assert st2.qty("abl_aquaboard") == 1 and st2.qty("abl_aerolift") == 1
st3 = GameState(); st3.items = {"abl_lumen": 1}                # old save: item held, ability never unlocked
savegame._read = lambda: savegame.serialize(st3)
st3.party = [create_scimon("florabot", 5)]
assert savegame.load(st3) and "lumen" in st3.abilities, "migration did not re-derive the ability"
print("OK save round trip")

# ---- 10. engine-driven: cast, reel, fly, burrow ------------------------------------------------------
eng = Engine()
st = eng.state
st.intro_done = True
st.party = [create_scimon("aquabit", 12), create_scimon(first_species("Atmospheric"), 12),
            create_scimon(first_species("Geologic"), 12)]
st.captured |= {m.species_id for m in st.party}
from overworld import OverworldScene
ovs = OverworldScene()
eng.push(ovs)
for _ in range(30):
    eng.step(1 / 60)
ovs._sync_abilities()
assert "aquaboard" not in st.abilities
st.add_item("abl_aquaboard", 1)
ovs._sync_abilities()
assert "aquaboard" in st.abilities, "the overworld did not self-heal the unlock"

# fishing: find a pier/edge tile next to real water (W), face it, cast
import worldmap as wm
spot = next((x, y, d) for y in range(len(wm.MAP_ROWS)) for x in range(len(wm.MAP_ROWS[0]))
            for d, (dx, dy) in {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}.items()
            if 0 <= y + dy < len(wm.MAP_ROWS) and 0 <= x + dx < len(wm.MAP_ROWS[0])
            and wm.MAP_ROWS[y][x] not in wm.OVERWORLD_SOLID and wm.MAP_ROWS[y + dy][x + dx] == "W")
ovs.player.place(spot[0], spot[1], spot[2])
st.add_item("probe_rod", 1)
_real_random = random.random
random.random = lambda: 0.1                                      # guarantee the bite
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
assert ovs.fishing, "confirm facing water with a rod did not cast"
for _ in range(400):
    eng.step(1 / 60)
    if not ovs.fishing:
        break
random.random = _real_random
from engine import StateId
assert not ovs.fishing, "cast never resolved"
for _ in range(120):
    eng.step(1 / 60)
    if eng.find(StateId.BATTLE):
        break
assert eng.find(StateId.BATTLE), "a guaranteed bite must start a battle"


def battle_auto(max_steps=900):
    """Fight the hooked Scimon to the end with keyboard input only."""
    for _ in range(max_steps):
        eng.step(1 / 60)
        bt = eng.find(StateId.BATTLE)
        if not bt:
            return True
        if bt.end_timer is not None:
            continue
        ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
        if bt.menu == "message":
            eng.dispatch(ret)
        elif bt.menu in ("main", "fight"):
            eng.dispatch(ret)
        elif bt.menu == "switch":
            eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        else:
            eng.dispatch(ret)
    return False


assert battle_auto(), "the hooked battle never ended"
print("OK fishing (bit -> battle)")


def until_overworld(max_steps=400):
    """Advance (and confirm through) whatever the battle left on the stack -- evolutions, learn-move
    prompts, dialogue -- until the overworld is on top again."""
    ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
    for _ in range(max_steps):
        eng.step(1 / 60)
        if eng.top is ovs and not eng.transitioning:
            return
        eng.dispatch(ret)
    raise AssertionError(f"never back to the overworld, stuck at {eng.top}")


until_overworld()

# fly: K_f opens the Aerolift menu, picking a target warps there
ovs.map = ovs._get_map(None, "route1"); ovs.building = None
ovs.player.place(11, 25, "down")
st.visited_areas |= {"epidimy", "stonreach"}                    # the menu lists visited rest points
st.add_item("abl_aerolift", 1); ovs._sync_abilities()
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f, mod=0, unicode=""))
from abilities import FlyMenu
assert isinstance(eng.top, FlyMenu), f"fly menu did not open: {eng.top}"
targets = eng.top.targets
assert {a for _n, a, _t in targets} >= {"epidimy", "stonreach"}, targets
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
for _ in range(90):
    eng.step(1 / 60)
assert st.location.get("area"), "fly did not warp"
print("OK aerolift ->", st.location.get("area"), st.location.get("tile"))

# burrow: K_g inside a cave place returns to the mouth
st.abilities.add("excavator")
ovs.map = ovs._get_map(None, "mt_crescent"); ovs.building = None; ovs._load_npcs()
deep = (9, 4)
ovs.player.place(*deep, "down")
st.location = {"area": "mt_crescent", "tile": list(deep), "facing": "down"}
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g, mod=0, unicode=""))
for _ in range(90):
    eng.step(1 / 60)
entries = sorted({(tx, ty) for links in LINKS.values() for (tgt, (tx, ty), _f) in links.values() if tgt == "mt_crescent"})
assert tuple(st.location["tile"]) in entries, (st.location, entries)
print("OK excavator ->", st.location["tile"])

# K_g outside the caves politely declines
ovs.map = ovs._get_map(None, "route1"); ovs.building = None; ovs._load_npcs()
st.location = {"area": "route1", "tile": [11, 25], "facing": "down"}
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g, mod=0, unicode=""))
for _ in range(30):
    eng.step(1 / 60)
assert st.location["area"] == "route1" and st.location["tile"] == [11, 25], "burrowed outside a cave!"
print("OK excavator refuses outside caves")

print("ALL OK")
