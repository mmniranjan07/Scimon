"""Headless Safari Reserve test: the session (fee, modules, step budget, PA warnings, time-up escort)
and FireRed's verbatim battle math -- catch factors from the 0-200 catch_rate scale, bait/rock counter
rules, the Safari Ball shake roll, the escape roll, and the reserve's encounter zones."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))
import random as _rnd
_rnd.seed(29)

import routes
import safari
from data import SPECIES
from monsters import create_scimon
from settings import SAFARI_BALLS, SAFARI_COST, SAFARI_STEPS
from state import GameState

st = GameState()
st.credits = 1000

# ---- 1. the session --------------------------------------------------------------------------------
safari.enter(st)
assert st.safari == {"balls": SAFARI_BALLS, "steps": SAFARI_STEPS}, st.safari
for _ in range(199):
    assert safari.on_step(st) is None
pa = safari.on_step(st)                                # 200 left: the halfway PA
assert pa and "Half" in pa, pa
for _ in range(99):
    safari.on_step(st)
pa = safari.on_step(st)                                # 100 left: the warning PA
assert pa and "hundred" in pa, pa
for _ in range(89):
    safari.on_step(st)
pa = safari.on_step(st)                                # 10 left: the last call
assert pa and "Ten" in pa, pa
for _ in range(9):
    assert safari.on_step(st) is None
assert safari.on_step(st) == "time_up"                 # 0 steps left: the escort
safari.end(st)
assert st.safari is None

# ---- 2. species factors (FireRed's init formula on the rescaled catch rate) -------------------------
class Fake:
    def __init__(self, cr):
        self.catch_rate = cr

assert safari.catch_factor(Fake(200)) == 20            # 200 -> 255 FRLG -> 255*100//1275 = 20
assert safari.catch_factor(Fake(45)) == 4              # 45*255//200 = 57 -> 57*100//1275 = 4
assert safari.catch_factor(Fake(3)) == max(1, 3 * 255 // 200 * 100 // 1275)
assert safari.escape_factor(Fake(200)) == 2            # commons barely skittish (FireRed's minimum)
assert safari.escape_factor(Fake(45)) >= 4             # rares are jumpier
assert safari.escape_factor(Fake(3)) >= safari.escape_factor(Fake(45))

# ---- 3. bait / rock / watch counters, verbatim from battle_main.c ------------------------------------
f = safari.SafariField.for_species(Fake(45))
base = f.catch_factor
safari.throw_rock(f)
assert f.catch_factor == min(20, base * 2) and f.rock_counter in range(2, 7) and f.bait_counter == 0
safari.throw_bait(f)
assert f.catch_factor == max(3, (min(20, base * 2)) // 2), "bait halves the (rock-boosted) factor"
assert f.bait_counter in range(2, 7) and f.rock_counter == 0
for _ in range(10):
    safari.watch(f, Fake(45))
assert f.bait_counter == 0 and f.rock_counter == 0 and f.catch_factor == base, "counters must decay to base"

# ---- 4. the Safari Ball roll (battle_script_commands.c, Safari Ball bonus 15, full HP) ---------------
mon = create_scimon("florabot", 10)
f = safari.SafariField.for_species(Fake(200))          # catch factor 20 -> restored rate 255
wins = sum(safari.roll_catch(f, mon)[0] for _ in range(4000))
assert 25 <= wins / 40 <= 75, f"max-factor catch rate way off band: {wins/40}%"
f = safari.SafariField.for_species(Fake(3))            # factor 1: rares are hard
wins = sum(safari.roll_catch(f, mon)[0] for _ in range(4000))
assert wins / 40 < 20, f"min-factor catch rate too generous: {wins/40}%"
caught, shakes = safari.roll_catch(safari.SafariField.for_species(Fake(200)), mon)
assert 0 <= shakes <= 3

# ---- 5. the escape roll (battle_ai_script_commands.c) ------------------------------------------------
f = safari.SafariField.for_species(Fake(45))           # escape factor 6 -> 30% base
base = sum(safari.roll_flee(f) for _ in range(4000)) / 40
safari.throw_rock(f)
angry = sum(safari.roll_flee(f) for _ in range(4000)) / 40
safari.throw_bait(f)
eating = sum(safari.roll_flee(f) for _ in range(4000)) / 40
assert 15 <= base <= 45, base
assert angry >= base, "angry mons must flee at least as often"
assert eating < base, "eating mons must flee less"

# ---- 6. the reserve map: zones, links, arrival -------------------------------------------------------
rows = routes.AREAS["safari"].rows
assert len(rows) == routes.SAFARI_H and all(len(r) == routes.SAFARI_W for r in rows)
assert routes.zone_at("safari", *routes.SAFARI_ARRIVAL) is None, "the arrival road must be safe ground"
g_tiles = [routes.zone_at("safari", x, y) for y in range(routes.SAFARI_H) for x in range(routes.SAFARI_W)]
habitats = {z["zone_id"] for z in g_tiles if z}
assert len(habitats) == 4, habitats                    # meadow, water, forest, highland all reachable
assert set(routes.LINKS["safari"]) == {(17, 29), (18, 29)}
assert all(dst == "vespera" for dst, _t, _f in routes.LINKS["safari"].values())
ball = routes.ITEM_BALLS["safari"][0]
assert rows[ball["tile"][1]][ball["tile"][0]] == "*"
for z in routes.ENCOUNTER_ZONES["safari"]:
    lo, hi = z["band"]
    assert z["gym_id"] == 6 and z["gym_ceiling"] == 33
    assert 1 <= lo <= hi <= 33

# ---- 7. wild encounters fire in the reserve's zones --------------------------------------------------
import encounters
random.seed(5)
st.stamps = {"green"}
z = routes.zone_at("safari", *next((x, y) for y in range(10, 25) for x in range(11, 25)
                                   if rows[y][x] == "g"))
seen = {encounters.select_encounter(st, z)[0] for _ in range(300) if encounters.select_encounter(st, z)}
assert seen, "the reserve's meadow zone produced no encounters"

print("OK safari: session, FRLG factor math, ball/escape rolls, reserve zones, links, encounters")
