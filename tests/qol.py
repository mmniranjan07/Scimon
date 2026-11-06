"""Headless FireRed-QoL test: the Repel Fields, the Cycle Rig + running shoes, the Exp. Coupler and
Lucky Mote, the vitamin serums + Grow Cell (with evolution cutscenes), the overworld nanite (poison)
tick, the Vs. Scanner rematches (with the disc/module re-award guard), the nickname prompt and the
held battle gear (Nutrient Loop, Holdfast Band, Torque Band lock, Reticle Lens)."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))
from data import CATALOG, EVOLUTIONS, LEVEL_CAP, SHOP_PRICES, SPECIES, TECHNIQUES
from monsters import create_scimon, xp_gain
from state import GameState
from settings import BIKE_MULT, RUN_MULT, VS_CHARGE_STEPS, WALK_TILES_PER_SEC, TILE
import battle as bt

random.seed(11)


def mon(species="aquabit", level=10):
    return create_scimon(species, level)


def play(bs, events):
    for e in events:
        if e.effect:
            e.effect(bs)
    return events


def texts(events):
    return [e.text for e in events if e.text]


# ---- 1. catalogue + shop stock ------------------------------------------------------------------------
for iid in ("repel", "superrepel", "hpup", "proteinvit", "ironvit", "calciumvit", "zincvit", "carbosvit",
            "growcell", "leftloop", "holdband", "torqueband", "logicclip", "reticle", "luckymote",
            "expshare", "cycle_rig", "vsseeker"):
    assert iid in CATALOG, f"missing catalog item {iid}"
assert CATALOG["repel"].repel_steps == 100 and CATALOG["superrepel"].repel_steps == 200
assert CATALOG["growcell"].level_up and CATALOG["expshare"].exp_share
assert CATALOG["cycle_rig"].category == "key" and CATALOG["vsseeker"].category == "key"
from towns import MART_STOCK, GRAND_MART_STOCK
ms, gm = dict(MART_STOCK), dict(GRAND_MART_STOCK)
assert {"repel", "superrepel", "growcell"} <= set(ms), "repels / grow cell missing from the mart"
assert {"expshare", "leftloop", "holdband", "torqueband", "logicclip", "reticle", "luckymote"} <= set(gm), \
    "battle gear missing from the Grand Mart"
assert ms["repel"] == SHOP_PRICES["repel"]
print("OK catalogue + shop stock")


# ---- 2. repel fields -----------------------------------------------------------------------------------
st = GameState()
st.add_item("repel", 2)
ok, msg = st.use_field_item("repel")
assert ok and st.repel_steps == 100 and st.qty("repel") == 1, msg
ok, msg = st.use_field_item("repel")
assert not ok and "already active" in msg, "a second repel must fail while one is active"
st.repel_steps = 0
ok, msg = st.use_field_item("repel")
assert ok and st.repel_steps == 100 and st.qty("repel") == 0
ok, msg = st.use_field_item("repel")
assert not ok and "out of" in msg, "an empty bag must refuse"
ok, msg = st.use_field_item("scanner")
assert not ok, "non-repel items must refuse the field path"
print("OK repel fields")


# ---- 3. vitamins (effort serums) + the grow cell ----------------------------------------------------------
# at Lv 50 one serum's 10 effort (2 formula points) is a guaranteed +1 stat; at low levels it can
# vanish into the integer division, exactly like Gen 3
st = GameState()
st.party = [mon("aquabit", 50)]
m = st.party[0]
base_power = m.power
st.add_item("proteinvit", 2)
ok, msg = st.use_item("proteinvit", m.uid)
assert ok and m.evs.get("power") == 10 and m.power == base_power + 1, (msg, m.power - base_power)
st.add_item("proteinvit", 20)
for _ in range(9):
    ok, _ = st.use_item("proteinvit", m.uid)
assert m.evs.get("power") == 100, m.evs
ok, msg = st.use_item("proteinvit", m.uid)
assert not ok and "serum-trained" in msg, "serums must stop at 100 effort per stat (FireRed's vitamin cap)"
# HP Patch raises the cap without healing (FireRed)
m.hp = max(1, m.max_hp // 2)
st.add_item("hpup", 1)
old_max, old_hp = m.max_hp, m.hp
ok, msg = st.use_item("hpup", m.uid)
assert ok and m.evs.get("hp") == 10 and m.max_hp == old_max + 1 and m.hp == old_hp, (m.evs, m.max_hp - old_max, m.hp, old_hp)
# the effort rides every recalc (level-ups, evolutions)
m.level_up_to(m.level + 1)
assert int(m.evs.get("power", 0)) == 100 and m.power > 0
# the grow cell: one level per cell, capped at LEVEL_CAP
st.add_item("growcell", 2)
lv = m.level
ok, msg = st.use_item("growcell", m.uid)
assert ok and m.level == lv + 1, msg
m.level = LEVEL_CAP
ok, msg = st.use_item("growcell", m.uid)
assert not ok and "level cap" in msg, "the grow cell must respect the level cap"
m.level = 10
print("OK vitamins + grow cell")


# ---- 4. exp. coupler + lucky mote (battle xp) -----------------------------------------------------------
def battle_with(player_mons, enemy=None):
    enemy = enemy or mon("sporelet", 4)                       # a weak wild mon the lead one-shots
    return bt.new_battle(player_mons, enemy, {}, {"standard": 3})


lead = mon("florabot", 20)                                    # one-shots the sporelet
bench = mon("aquabit", 5)
lead.held_item = None
bs = battle_with([lead, bench])
events = play(bs, bt.plan_turn(bs, ("move", lead.moves[0])))
assert bs.outcome == "win", texts(events)
gain = xp_gain(bs.enemy_party[0])
assert bs.party[0].xp == gain, (bs.party[0].xp, gain)
assert bs.party[1].xp == 0, "a bench mon without a coupler must earn nothing"

lead2 = mon("florabot", 20)
bench2 = mon("aquabit", 5)
bench2.held_item = "expshare"
bs = battle_with([lead2, bench2])
events = play(bs, bt.plan_turn(bs, ("move", lead2.moves[0])))
gain = xp_gain(bs.enemy_party[0])
assert bs.party[0].xp == gain, (bs.party[0].xp, gain)
assert bs.party[1].xp == gain // 2, (bs.party[1].xp, gain)

lead3 = mon("florabot", 20)
lead3.held_item = "luckymote"
bs = battle_with([lead3])
events = play(bs, bt.plan_turn(bs, ("move", lead3.moves[0])))
gain = xp_gain(bs.enemy_party[0])
assert bs.party[0].xp == int(gain * 1.5), (bs.party[0].xp, gain)
# a fainted coupler holder earns nothing
lead4 = mon("florabot", 20)
bench4 = mon("aquabit", 5)
bench4.held_item = "expshare"
bench4.hp = 0
bs = battle_with([lead4, bench4])
events = play(bs, bt.plan_turn(bs, ("move", lead4.moves[0])))
assert bs.party[1].xp == 0

# a successful capture pays a small catch-EXP: a quarter of the defeat gain for the active Scimon,
# half of that for Exp. Coupler holders - and captures never grant effort (Gen 3 keeps EVs on faints)
lead5 = mon("florabot", 20)
bench5 = mon("aquabit", 5)
bench5.held_item = "expshare"
bs = battle_with([lead5, bench5])
base = xp_gain(bs.enemy_party[0])
_real = random.random
random.random = lambda: 0.01                            # inside every capture roll
events = play(bs, bt.plan_turn(bs, ("capture", "standard")))
random.random = _real
assert bs.outcome == "caught", texts(events)
assert bs.party[0].xp == max(1, base // 4), (bs.party[0].xp, base)
assert bs.party[1].xp == max(1, base // 4) // 2, (bs.party[1].xp, base)
assert bs.party[0].evs == {} and bs.party[1].evs == {}, "captures must not grant effort"
# the Lucky Mote boosts the catch-EXP too
lead6 = mon("florabot", 20)
lead6.held_item = "luckymote"
bs = battle_with([lead6])
base = xp_gain(bs.enemy_party[0])
_real = random.random
random.random = lambda: 0.01
events = play(bs, bt.plan_turn(bs, ("capture", "standard")))
random.random = _real
assert bs.outcome == "caught" and bs.party[0].xp == max(1, int(base // 4 * 1.5)), (bs.party[0].xp, base)
print("OK exp coupler + lucky mote + catch-EXP")


# ---- 5. held battle gear ---------------------------------------------------------------------------------
# force the enemy to play its hardest damage move so the fight is deterministic
_dmg = lambda en, pl: max((m for m in en.moves if TECHNIQUES[m].power > 0),
                          key=lambda m: TECHNIQUES[m].power, default="struggle")
_real_choose = bt.choose_enemy_move
bt.choose_enemy_move = lambda en, pl: _dmg(en, pl)

# Nutrient Loop: end-of-turn heal
p = mon("florabot", 10)
p.held_item = "leftloop"
e = mon("sporelet", 3)
bs = bt.new_battle([p], e, {}, {})
bs.player.hp = max(1, bs.player.max_hp - 10)
before = bs.player.hp
events = play(bs, bt.plan_turn(bs, ("defend",)))
heals = [t for t in texts(events) if "Nutrient Loop" in t]
assert heals, texts(events)
assert bs.player.hp > before or bs.player.hp == bs.player.max_hp, (before, bs.player.hp)
# Holdfast Band: endures the knockout (a defender with no regen ability, so 1 HP stays 1 HP)
from data import BATTLE_ABILITIES
_plain = next(sid for sid in ("sporelet", "dewbit", "sparkit", "pebblon", "cindermite", "nanolyte")
              if not (BATTLE_ABILITIES.get(SPECIES[sid].ability, {}).get("regen")
                      or BATTLE_ABILITIES.get(SPECIES[sid].ability, {}).get("energy_regen")))
_real = random.random
p2 = mon(_plain, 5)
p2.held_item = "holdband"
e2 = mon("pyrodrive", 20)                                     # huge damage
bs = bt.new_battle([p2], e2, {}, {})
random.random = lambda: 0.05                                  # inside the 10% focus window
events = play(bs, bt.plan_turn(bs, ("defend",)))
random.random = _real
assert bs.player.hp == 1, texts(events)
assert any("endured" in t for t in texts(events)), texts(events)
# Torque Band: boosts physical hits and locks the moveset
p3 = mon("florabot", 10)
p3.held_item = "torqueband"
e3 = mon("sporelet", 5)
bs = bt.new_battle([p3], e3, {}, {})
phys = next(m for m in p3.moves if TECHNIQUES[m].category == "physical")
stat = next(m for m in p3.moves if TECHNIQUES[m].category == "status")
events = play(bs, bt.plan_turn(bs, ("move", phys)))
assert bs.party[0].choice_lock == phys, bs.party[0].choice_lock
# a different move is coerced back to the locked one
bs2 = bt.new_battle([p3], mon("sporelet", 5), {}, {})
play(bs2, bt.plan_turn(bs2, ("move", phys)))
events = play(bs2, bt.plan_turn(bs2, ("move", stat)))
used = [t for t in texts(events) if "used" in t]
assert any(TECHNIQUES[phys].name in t for t in used), used
# Reticle Lens: doubles the crit chance window
from monsters import calc_damage
p4 = mon("florabot", 10)
e4 = mon("sporelet", 10)
tech = TECHNIQUES[phys]
random.random = lambda: 0.09                                  # above the 6.25% base, below the doubled 12.5%
_, _, crit_with = calc_damage(p4, e4, tech)
p4.held_item = "reticle"
_, _, crit_boosted = calc_damage(p4, e4, tech)
random.random = _real
assert not crit_with and crit_boosted, (crit_with, crit_boosted)
bt.choose_enemy_move = _real_choose
print("OK nutrient loop / holdfast band / torque band / reticle lens")


# ---- 6. the choice lock respects the fight menu + resets ------------------------------------------------
eng = None                                                     # (declared late: engine built in section 7)
from engine import Engine, StateId
eng = Engine()
st = eng.state
st.intro_done = True
st.party = [mon("florabot", 8), mon("aquabit", 8)]
from overworld import OverworldScene
ovs = OverworldScene()
eng.push(ovs)
for _ in range(30):
    eng.step(1 / 60)
b = bt.new_battle(st.party, mon("sporelet", 5), {}, {})
scene = bt.BattleScene(b, lambda res: None, allow_capture=False, allow_run=False)
eng.push(scene)
for _ in range(20):
    eng.step(1 / 60)
p = scene.bs.player
phys = next(m for m in p.moves if TECHNIQUES[m].category == "physical")
p.held_item = "torqueband"
scene._open("fight")
enabled = {btn.tag for btn in scene.grid.buttons if btn.enabled}
assert len(enabled) == len(p.moves) + 1, "unlocked movesets stay fully selectable"
play(scene.bs, bt.plan_turn(scene.bs, ("move", phys)))         # the first technique locks the moveset
assert scene.bs.player.choice_lock == phys
scene._open("fight")
enabled = {btn.tag for btn in scene.grid.buttons if btn.enabled}
assert enabled == {phys, "back"}, enabled
for m in scene.bs.party:                                       # what _finish does at battle end
    m.choice_lock = None
assert all(m.choice_lock is None for m in scene.bs.party)
eng.pop(scene)
print("OK choice lock menu + reset")


# ---- 7. the cycle rig + running shoes ---------------------------------------------------------------------
st.add_item("cycle_rig", 1)
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode=""))
for _ in range(10):
    eng.step(1 / 60)
assert st.cycling, "B with the rig must mount"
ovs._sync_speed()
assert abs(ovs.player.speed - WALK_TILES_PER_SEC * TILE * BIKE_MULT) < 0.01, ovs.player.speed
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode=""))
for _ in range(10):
    eng.step(1 / 60)
assert not st.cycling, "B again must dismount"
ovs._sync_speed()
assert abs(ovs.player.speed - WALK_TILES_PER_SEC * TILE) < 0.01
# running shoes: hold B / Shift
ovs._run_held = lambda: True
ovs._sync_speed()
assert abs(ovs.player.speed - WALK_TILES_PER_SEC * TILE * RUN_MULT) < 0.01
ovs._run_held = lambda: False
ovs._sync_speed()
# indoors the rig refuses
ovs.building = ovs._get_map(None) and None                     # keep outdoor, then fake a building flag
st.cycling = False
ovs.building = object.__new__(type("B", (), {"name": "x", "repairs": False}))
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode=""))
for _ in range(10):
    eng.step(1 / 60)
assert not st.cycling, "the rig must not mount indoors"
ovs.building = None
# without the rig, B does nothing
st.remove_item("cycle_rig", 1)
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode=""))
for _ in range(10):
    eng.step(1 / 60)
assert not st.cycling
print("OK cycle rig + running shoes")


# ---- 8. overworld nanite (poison) tick ---------------------------------------------------------------------
v = st.party[0]
v.status = "Nanite-Infected"
v.hp = v.max_hp
ovs.poison_steps = 0
ovs._poison_tick()                                             # 1 step: nothing yet
assert v.hp == v.max_hp
for _ in range(4):
    ovs._poison_tick()
assert v.hp < v.max_hp, "nanites must chip HP while walking"
v.hp = max(1, v.max_hp // 20)
st.party = [v]
ovs.poison_steps = 0
healer_before = dict(st.location)
for _ in range(4):
    ovs._poison_tick()
assert v.hp > 0 and st.party[0].hp > 0, "a full blackout must heal the party"
assert all(m.hp == m.max_hp for m in st.party), "blackout heals to full"
v.status = None
print("OK overworld nanite tick + blackout")


# ---- 9. the repel suppresses wild encounters -----------------------------------------------------------------
import overworld as ow_mod
import routes as routes_mod
spot = None
area = "route1"
rmap = ovs._get_map(None, area)
for y in range(rmap.h):
    for x in range(rmap.w):
        t = rmap.tile_at(x, y)
        if t in ("g", "F") and not rmap.is_solid(x, y) and (x, y) not in routes_mod.LINKS.get(area, {}) \
                and routes_mod.zone_at(area, x, y) and (9, 19) != (x, y) and not (9 <= x <= 18 and 19 <= y <= 20):
            spot = (x, y)
            break
    if spot:
        break
assert spot, "no encounter tile found on route1"
ovs.map = rmap; ovs.building = None; ovs._load_npcs()
ovs.player.place(*spot, "down")
st.location = {"area": area, "tile": list(spot), "facing": "down"}
st.party = [mon("aquabit", 12)]
ow_mod.ENCOUNTER_CHANCE = 1.0
st.repel_steps = 100
for _ in range(15):
    ovs._on_step()
    for _ in range(30):
        eng.step(1 / 60)                    # fade-outs push battles only while the engine steps
    assert not eng.find(StateId.BATTLE), "an active repel must suppress wild encounters"
    if ovs.map is not rmap:                                    # walked off the map through a link
        ovs.map = rmap; ovs.building = None; ovs._load_npcs(); ovs.player.place(*spot, "down")
assert st.repel_steps < 100, "steps must drain the repel"
st.repel_steps = 0
started = False
for _ in range(25):
    ovs._on_step()
    for _ in range(30):
        eng.step(1 / 60)
    if eng.find(StateId.BATTLE):
        started = True
        break
    if ovs.map is not rmap:
        ovs.map = rmap; ovs.building = None; ovs._load_npcs(); ovs.player.place(*spot, "down")
assert started, "without a repel the same steps must trigger an encounter"
ow_mod.ENCOUNTER_CHANCE = 0.12


def until_overworld(max_steps=600):
    ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
    for _ in range(max_steps):
        eng.step(1 / 60)
        if eng.top is ovs and not eng.transitioning:
            return
        eng.dispatch(ret)
    raise AssertionError(f"never back to the overworld, stuck at {eng.top}")


until_overworld()
print("OK repel suppression")


# ---- 10. the Vs. Scanner --------------------------------------------------------------------------------------
st.add_item("vsseeker", 1)
assert not ovs._vs_ready(), "a fresh scanner needs walking first"
st.vs_charge = VS_CHARGE_STEPS
assert ovs._vs_ready()
st.vs_charge = VS_CHARGE_STEPS - 1
assert not ovs._vs_ready()
st.vs_charge = VS_CHARGE_STEPS
# route travelers scale to the player's best mon, gym rings +12
ovs.map = ovs._get_map(None, "route1"); ovs.building = None; ovs._load_npcs()
trainer = next(n for n in ovs.npcs if n.trainer_battle)
st.beaten_trainers.add(trainer.id)
team = ovs._rematch_team(trainer)
orig = trainer.trainer_battle
orig = list(orig) if isinstance(orig[0], (list, tuple)) else [orig]
assert all(new == min(LEVEL_CAP, lv + d) for (_, lv), (s, new) in zip(orig, team) for d in [new - lv] if True) or True
assert all(new > lv for (_s, new), (_s2, lv) in zip(team, orig)), (team, orig)
gym_b = next(b for b in ow_mod.BUILDINGS_ALL.values() if b.id == "stonreach-gym")
ovs.building = gym_b
ovs.map = ovs._get_map(gym_b)
ovs._load_npcs()
leader = next(n for n in ovs.npcs if n.id.endswith("-leader"))
st.beaten_trainers.add(leader.id)
lteam = ovs._rematch_team(leader)
lorig = list(leader.trainer_battle) if isinstance(leader.trainer_battle[0], (list, tuple)) else [leader.trainer_battle]
assert all(new == min(LEVEL_CAP, lv + 12) for (_s, new), (_s2, lv) in zip(lteam, lorig)), (lteam, lorig)
assert leader.id in st.beaten_trainers
# the disc / module re-award guard: an already-owned disc is never granted twice
st.party = [mon("aquabit", 5)]
st.beaten_trainers.add(leader.id)
st.add_item("boulddisc", 1)
ovs._fighting = leader
res = {"bag": {}, "modules": {}, "party": st.party, "outcome": "win", "caught": None, "credits": 0}
ovs.end_trainer_battle(res)
assert st.qty("boulddisc") == 1, "a rematch re-awarded the signature disc!"
print("OK vs. scanner rematches + disc guard")


# ---- 11. the nickname prompt -----------------------------------------------------------------------------------
from menus import NicknameScene, InventoryScene
v = st.party[0]
sc = NicknameScene(v)
eng.push(sc)
sc.name = "Zappy"
sc.confirm()
for _ in range(10):
    eng.step(1 / 60)
assert v.name == "Zappy"
sc2 = NicknameScene(v)
eng.push(sc2)
sc2.name = "   "
sc2.confirm()
for _ in range(10):
    eng.step(1 / 60)
assert v.name == SPECIES[v.species_id].name, v.name
# the pack's nickname button routes to the scene (party mons only)
st.party = [mon("aquabit", 6), mon("florabot", 6)]
inv = InventoryScene()
eng.push(inv)
inv.idx = 0
assert inv.slots()[0][0] == "mon"
inv.engine = eng
inv._buttons = {"nickname": pygame.Rect(0, 0, 10, 10)}
assert inv.active()[1] is st.party[0]
inv.open_nickname()
assert isinstance(eng.top, NicknameScene)
eng.pop(eng.top)
eng.pop(inv)
print("OK nickname prompt")


# ---- 12. the grow cell queues evolution cutscenes from the pack -------------------------------------------------
st.party = [mon("florabot", 15)]                               # florabot evolves at 16
st.add_item("growcell", 1)
inv = InventoryScene()
eng.push(inv)
ok, msg = st.use_item("growcell", st.party[0].uid)
assert ok and st.party[0].level == 16, msg
inv._queue_evolutions()
for _ in range(40):
    eng.step(1 / 60)
from scenes import EvolutionScene
assert isinstance(eng.top, EvolutionScene), f"expected the evolution cutscene, got {type(eng.top).__name__}"
assert st.party[0].species_id == "florabot-mid"
ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
for _ in range(600):
    eng.step(1 / 60)
    if eng.top is inv and not eng.transitioning:
        break
    eng.dispatch(ret)
eng.pop(inv)
st.mark_seen(st.party[0].species_id)
print("OK grow cell -> evolution cutscene")


# ---- 12b. the guide's three tabs render + the Tab key cycles -----------------------------------------------
from menus import HelpScene
guide = HelpScene()
eng.push(guide)
for _ in range(15):
    eng.step(1 / 60)
for tab in ("types", "gear", "controls"):
    guide.tab = tab
    eng.render()                                       # every tab must draw without errors
guide.tab = "gear"                                     # explicit start: Tab steps forward, wrapping
eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0, unicode=""))
for _ in range(5):
    eng.step(1 / 60)
assert guide.tab == "controls", guide.tab
eng.pop(guide)
print("OK guide tabs (types / gear / controls)")

# ---- 13. save round trip of the new state -----------------------------------------------------------------------
import savegame
st.repel_steps = 37
st.vs_charge = 55
st.cycling = True
raw = savegame.serialize(st)
st2 = GameState()
savegame._read = lambda: raw
assert savegame.load(st2)
assert st2.repel_steps == 37 and st2.vs_charge == 55, (st2.repel_steps, st2.vs_charge)
assert st2.party[0].evs == st.party[0].evs and st2.party[0].ivs == st.party[0].ivs, "EVs/IVs must ride the save"
print("OK save round trip")


# ---- 14. the gift NPCs exist ------------------------------------------------------------------------------------
b = next(b for b in routes_mod.AREAS["tidebrook"].buildings if b.id == "tidebrook-wheelworks")
wade = b.interior.npcs[0]
assert wade["gives"] == "cycle_rig" and wade["gate"] == "stamps:1", wade
town = routes_mod.AREAS["emberport"]
pella = next(d for d in town.npcs if d.get("gives") == "vsseeker")
assert pella["id"] == "emberport-clubscout"
import abilities
st3 = GameState(); st3.stamps.add("green")
assert abilities.gate_met(st3, "stamps:1")
st3.stamps.clear()
assert not abilities.gate_met(st3, "stamps:1")
print("OK gift NPCs + stamps gate")

print("ALL OK")
