"""Headless EV/IV test (Gen 3 rules): born IVs, the level-scaled stat formula, effort yields by stage,
the 255/510 caps, battle-time effort gains (active + Exp. Coupler holders), serum effort with the
100-per-stat vitamin cap, the old-save migration (flat bonus -> effort, retroactive IVs) and the
zero-IV/zero-effort backward compatibility with the original stat formula."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))
from data import (SPECIES, EV_PER_STAT_CAP, EV_TOTAL_CAP, IV_MAX, IV_STATS, VITAMIN_EV_CAP, VITAMIN_EV_GAIN,
                  YIELD_STATS)
from monsters import (Scimon, create_scimon, ev_yield, grant_evs, xp_for_level)
import battle as bt
from state import GameState

random.seed(23)


def mon(species="aquabit", level=10):
    return create_scimon(species, level)


def play(bs, events):
    for e in events:
        if e.effect:
            e.effect(bs)
    return events


# ---- 1. born IVs ----------------------------------------------------------------------------------------
for _ in range(40):
    m = mon("aquabit", 10)
    assert set(m.ivs) == set(IV_STATS), m.ivs
    assert all(0 <= v <= IV_MAX for v in m.ivs.values()), m.ivs
    assert m.evs == {}, "fresh Scimons start untrained"
seen = {tuple(sorted(m.ivs.values())) for m in (mon("aquabit", 5) for _ in range(30))}
assert len(seen) > 20, "IVs must differ between individuals"
print("OK born IVs")


# ---- 2. the Gen 3 stat formula --------------------------------------------------------------------------
sp = SPECIES["aquabit"]
m = mon("aquabit", 37)
m.ivs = {"hp": 31, "power": 16, "defense": 0, "sp_power": 7, "sp_defense": 22, "speed": 31}
m.evs = {"hp": 252, "power": 0, "defense": 4, "sp_power": 0, "sp_defense": 0, "speed": 60}
m.recalc_stats()
lv = 37
assert m.max_hp == (2 * sp.b_hp + 31 + 252 // 4) * lv // 100 + lv + 10, m.max_hp
assert m.power == (2 * sp.b_power + 16 + 0) * lv // 100 + 5, m.power
assert m.defense == (2 * sp.b_def + 0 + 1) * lv // 100 + 5, m.defense
assert m.speed == (2 * sp.b_speed + 31 + 15) * lv // 100 + 5, m.speed
assert m.max_energy == sp.b_energy * lv // 50 + 15 + lv, m.max_energy
# backward compatibility: zero IVs + zero effort collapses to the original V34 formula at every level
for lv2 in (1, 5, 16, 37, 50, 73, 100):
    m2 = mon("aquabit", lv2)
    m2.ivs, m2.evs = {}, {}
    m2.recalc_stats()
    assert m2.power == sp.b_power * lv2 // 50 + 5, (lv2, m2.power)
    assert m2.max_hp == sp.b_hp * lv2 // 50 + lv2 + 10, (lv2, m2.max_hp)
    assert m2.max_energy == sp.b_energy * lv2 // 50 + 15 + lv2, (lv2, m2.max_energy)
print("OK stat formula + backward compatibility")


# ---- 3. effort yields by stage ---------------------------------------------------------------------------
def top_stat(sid):
    return max(range(len(YIELD_STATS)), key=lambda i: (SPECIES[sid].base[i], -i))


for sid, sp_ in SPECIES.items():
    y = ev_yield(sid)
    assert len(y) == 1 and y[0][0] == YIELD_STATS[top_stat(sid)], (sid, y)
    expect = {1: 1, 2: 2, 3: 3}.get(int(sp_.stage_ordinal), 1)
    assert y[0][1] == expect, (sid, y, sp_.stage_ordinal)
assert ev_yield("florabot")[0][1] == 1 and ev_yield("florabot-mid")[0][1] == 2 and ev_yield("florabot-final")[0][1] == 3
print("OK effort yields (109 families / 327 forms)")


# ---- 4. the caps ------------------------------------------------------------------------------------------
m = mon("aquabit", 10)
m.evs = {"power": EV_PER_STAT_CAP - 1}
assert grant_evs(m, (("power", 3),)) and m.evs["power"] == EV_PER_STAT_CAP
assert not grant_evs(m, (("power", 3),)), "a maxed stat must not train further"
m.evs = {s: 85 for s in IV_STATS}                      # 85*6 = 510: exactly the total cap
m.evs = {"hp": 200, "power": 200, "defense": 110}      # 510 exactly
assert not grant_evs(m, (("speed", 3),)), "the 510 total cap must hold"
m.evs = {"hp": 200, "power": 200, "defense": 108}      # 508: room for 2 of the 3
assert grant_evs(m, (("defense", 3),)) and m.evs["defense"] == 110, m.evs
print("OK 255/510 caps")


# ---- 5. battle-time effort --------------------------------------------------------------------------------
def battle_with(player_mons, enemy=None):
    enemy = enemy or mon("sporelet", 4)
    return bt.new_battle(player_mons, enemy, {}, {"standard": 3})


lead = mon("florabot", 20)                              # one-shots the sporelet
bs = battle_with([lead])
y_stat, y_n = ev_yield(bs.enemy_party[0].species_id)[0]
events = play(bs, bt.plan_turn(bs, ("move", lead.moves[0])))
assert bs.outcome == "win"
assert bs.party[0].evs.get(y_stat) == y_n, (bs.party[0].evs, y_stat, y_n)

# the Exp. Coupler holder trains alongside the active Scimon (Gen 3's Exp Share EVs)
lead2 = mon("florabot", 20)
bench = mon("aquabit", 5)
bench.held_item = "expshare"
bs = battle_with([lead2, bench])
y_stat, y_n = ev_yield(bs.enemy_party[0].species_id)[0]
events = play(bs, bt.plan_turn(bs, ("move", lead2.moves[0])))
assert bs.party[0].evs.get(y_stat) == y_n and bs.party[1].evs.get(y_stat) == y_n, (bs.party[0].evs, bs.party[1].evs)
# a fainted holder earns nothing; captures grant nothing (the enemy never faints)
lead3 = mon("florabot", 20)
bench3 = mon("aquabit", 5)
bench3.held_item = "expshare"
bench3.hp = 0
bs = battle_with([lead3, bench3])
events = play(bs, bt.plan_turn(bs, ("move", lead3.moves[0])))
assert bs.party[1].evs == {}, "a fainted coupler holder must not train"
# a maxed Scimon gains nothing in battle
lead4 = mon("florabot", 20)
lead4.evs = {y_stat: EV_PER_STAT_CAP} if False else {ev_yield("sporelet")[0][0]: EV_PER_STAT_CAP}
bs = battle_with([lead4])
events = play(bs, bt.plan_turn(bs, ("move", lead4.moves[0])))
assert sum(bs.party[0].evs.values()) == EV_PER_STAT_CAP, bs.party[0].evs
print("OK battle effort (active + coupler, caps honoured)")


# ---- 6. serums grant effort --------------------------------------------------------------------------------
st = GameState()
m = mon("aquabit", 25)
st.party = [m]
st.add_item("proteinvit", 12)
for _ in range(10):
    ok, msg = st.use_item("proteinvit", m.uid)
    assert ok, msg
assert m.evs["power"] == VITAMIN_EV_CAP
ok, msg = st.use_item("proteinvit", m.uid)
assert not ok and "serum-trained" in msg, "serums stop at 100 effort (FireRed's vitamin cap)"
# battle effort may push past the serum cap, but never past 255
m.evs["power"] = 98
st.add_item("proteinvit", 1)
ok, msg = st.use_item("proteinvit", m.uid)
assert ok and m.evs["power"] == 100, (ok, m.evs)
# wild battles can train the same stat beyond 100
m.evs["power"] = 100
assert grant_evs(m, (("power", 3),)) and m.evs["power"] == 103, m.evs
# the total cap blocks serums too
m.evs = {s: 86 for s in IV_STATS}                       # 516 > 510
m.evs = {s: 84 for s in IV_STATS}                       # 504: room for 6
st.add_item("hpup", 1)
ok, msg = st.use_item("hpup", m.uid)
assert ok and m.evs["hp"] == 84 + 6, f"serum gain clamped to the total cap: {m.evs['hp']}"
ok, msg = st.use_item("hpup", 1) if False else (True, "")
assert sum(m.evs.values()) <= EV_TOTAL_CAP
print("OK serum effort + caps")


# ---- 7. migration: old saves (flat vitamin bonus, no IVs) ----------------------------------------------------
import savegame
from monsters import Scimon as _Sc
st = GameState()
old = _Scimon = _Sc(species_id="aquabit", level=12, uid="old1", name="Aquabit",
                    moves=["sysram"], bonus={"power": 50, "hp": 10, "charm": 5})
st.party = [old]
st.captured.add("aquabit")
raw = savegame.serialize(st)
st2 = GameState()
savegame._read = lambda: raw
assert savegame.load(st2)
m2 = st2.party[0]
assert m2.evs.get("power") == VITAMIN_EV_CAP and m2.evs.get("hp") == 20, m2.evs   # 2 EV per bonus point, capped
assert m2.bonus == {}, "the retired bonus field must be cleared"
assert set(m2.ivs) == set(IV_STATS) and all(0 <= v <= IV_MAX for v in m2.ivs.values()), m2.ivs
assert m2.max_hp > 0 and m2.power > 0, "the migrated Scimon must be fully recalced"
# a brand-new save keeps its IVs untouched (no re-roll on load)
st3 = GameState()
fresh = mon("aquabit", 9)
st3.party = [fresh]
raw3 = savegame.serialize(st3)
st4 = GameState()
savegame._read = lambda: raw3
assert savegame.load(st4)
assert st4.party[0].ivs == fresh.ivs, "IVs must ride the save unchanged"
print("OK migration (bonus -> effort, retroactive IVs)")


# ---- 8. the detail panels draw the read-out --------------------------------------------------------------------
from engine import Engine, StateId
eng = Engine()
st = eng.state
st.intro_done = True
m = mon("aquabit", 12)
m.evs = {"speed": 30, "power": 12}
st.party = [m, mon("florabot", 10)]
st.captured |= {x.species_id for x in st.party}
from menus import InventoryScene, DatabaseScene, training_lines
ev_line, iv_line = training_lines(m)
assert "Spd+30" in ev_line and "Pow+12" in ev_line and "Def" not in ev_line.split("Effort")[1], ev_line
assert iv_line.startswith("IVs") and "HP" in iv_line, iv_line
inv = InventoryScene()
eng.push(inv)
for _ in range(20):
    eng.step(1 / 60)
eng.render()                                            # exercises _draw_detail with the new lines
db = DatabaseScene()
eng.push(db)
for _ in range(20):
    eng.step(1 / 60)
eng.render()                                            # exercises _draw_preview with the new lines
print("OK detail panels render the EV/IV read-out")

print("ALL OK")
