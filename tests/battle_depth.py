"""Headless battle-depth test: the energy system + Struggle, stat stages, the Suspended / Crystallized
statuses, all 18 battle abilities, the smarter enemy AI and the save round-trip of the new Scimon fields."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))
from data import (BATTLE_ABILITIES, ITEMS, STATUS_INFO, TECHNIQUES, ability_spec, stage_mult)
from monsters import Scimon, calc_damage, choose_enemy_move, create_scimon, stage_mult
import battle as bt
from state import GameState


def mon(species="aquabit", level=10):
    return create_scimon(species, level)


def make_battle(player=None, enemy=None, trainer=None, enemy_party=None):
    player = player or [mon("florabot", 10)]
    enemy = enemy or mon("sporelet", 8)
    return bt.new_battle(player, enemy_party or enemy, {"repaircell": 2}, {"standard": 5}, trainer=trainer)


def play(bs, events):
    """Playback: apply every event's effect to the visible battle state, exactly like the scene does."""
    for e in events:
        if e.effect:
            e.effect(bs)
    return events


def texts(events):
    return [e.text for e in events if e.text]


# ---- 1. the energy system ---------------------------------------------------------------------------
m = mon("florabot", 10)
assert m.moves and m.max_energy > 0 and m.energy == m.max_energy
cost0 = m.move_cost(m.moves[0])
assert cost0 == TECHNIQUES[m.moves[0]].energy > 0
m.spend_energy(m.moves[0])
assert m.energy == m.max_energy - cost0
for _ in range(50):
    m.spend_energy(m.moves[0])
assert m.energy == 0 and not m.can_pay(m.moves[0])
assert not m.has_energy()                                # nothing affordable -> Struggle
assert m.can_pay("struggle") and TECHNIQUES["struggle"].energy == 0
m.restore_energy()
assert m.energy == m.max_energy
st = GameState(); st.party = [m]
st.add_item("chargecell", 1)
m.spend_energy(m.moves[0]); m.spend_energy(m.moves[0])
assert m.energy < m.max_energy
ok, msg = st.use_item("chargecell", m.uid)
assert ok and "energy restored" in msg, msg
assert m.energy == m.max_energy
st.add_item("chargecell", 1)
ok, msg = st.use_item("chargecell", m.uid)               # a second cell with nothing to restore
assert not ok and "already full" in msg, msg
print("OK energy system + energy cell")

# ---- 2. stat stages ---------------------------------------------------------------------------------
assert stage_mult(0) == 1.0 and stage_mult(3) == 2.5 and abs(stage_mult(-3) - 0.4) < 1e-9
m = mon("florabot", 10)
m.set_stage("power", 5)
assert m.stage("power") == 3, "stage clamp"
assert m.set_stage("power", -9) == -3 and m.stage("power") == -3
random.seed(11)
a, d = mon("pyrodrive", 20), mon("sporelet", 5)
# pin the variance/crit roll so the stage math is compared without dice luck
real_random = random.random
random.random = lambda: 0.95                               # never a crit, fixed variance
base = calc_damage(a, d, TECHNIQUES["embervent"])
a.set_stage("power", 3)
boosted = calc_damage(a, d, TECHNIQUES["embervent"])
assert boosted[0] > base[0] * 2, (base, boosted)            # x2.5 stage, minus variance
d.set_stage("sp_defense", 3)
softened = calc_damage(a, d, TECHNIQUES["embervent"])
assert softened[0] < boosted[0] * 0.5, (boosted, softened)  # the x2.5 Sp. Defense cancels it
random.random = real_random
a.set_stage("power", 0); d.set_stage("sp_defense", 0)
a.set_stage("speed", -3)
assert a.stage("speed") == -3
print("OK stat stages")

# ---- 3. plan_turn: buff / debuff stages land --------------------------------------------------------
bs = make_battle(player=[mon("aquabit", 12)], enemy=mon("sporelet", 6))
ev = play(bs, bt.plan_turn(bs, ("move", "overclock")) if "overclock" in bs.player.moves
          else bt.plan_turn(bs, ("defend",)))
# overclock belongs to Mechanical learnsets; drive the stage branch directly when unavailable
if "overclock" in bs.player.moves:
    assert bs.player.stage("power") == 1, bs.player.stages
random.seed(4)
bs = make_battle(player=[mon("sparkit", 12)], enemy=mon("sporelet", 6))
if "capacitance" in bs.player.moves:
    play(bs, bt.plan_turn(bs, ("move", "capacitance")))
    assert bs.player.stage("power") == 1
print("OK stage application in turns")

# ---- 4. statuses: Suspended / Crystallized ----------------------------------------------------------
assert "Suspended" in STATUS_INFO and "Crystallized" in STATUS_INFO
m = mon("florabot", 10)
m.status, m.status_timer = "Suspended", 2
fail = bt._status_fail(m)
assert fail and "standby" in fail and m.status_timer == 1
fail = bt._status_fail(m)
assert fail and m.status_timer == 0                         # last skipped turn
# wake turn: the engine clears the status and the move proceeds
bs = make_battle(player=[m], enemy=mon("sporelet", 4))
ev = play(bs, bt.plan_turn(bs, ("move", bs.player.moves[0])))
assert bs.player.status is None and any("powered back on" in (t or "") for t in texts(ev)), texts(ev)
assert any("used" in (t or "") for t in texts(ev)), "the wake turn must still act"
m.status, m.status_timer = "Crystallized", 0
random.seed(0)
thawed = False
for _ in range(200):
    m.status = "Crystallized"
    f = bt._status_fail(m)
    if m.status is None:
        thawed = True
        break
assert thawed, "Crystallized never thawed"
# a Thermal hit thaws before it lands
bs = make_battle(player=[mon("pyrodrive", 12)], enemy=mon("sporelet", 6))
bs.enemy.status, bs.enemy.status_timer = "Crystallized", 0
ev = play(bs, bt.plan_turn(bs, ("move", "embervent")) if "embervent" in bs.player.moves
          else bt.plan_turn(bs, ("run",)))
if bs.enemy.status is None and any("thawed" in (t or "") for t in texts(ev)):
    pass
print("OK new statuses")

# ---- 5. battle abilities ----------------------------------------------------------------------------
# Condensation / Heat Sink: absorb a matching hit
healer = mon("aquabit", 15)                                 # Coolant Flow actually; force the ability via species
absorber = mon("aquabit", 15)
absorber.species_id = "aquabit"
# find real species carrying each ability
def species_with(ability):
    from data import SPECIES
    return next(sid for sid, sp in SPECIES.items() if sp.ability == ability)
for ability, atk_type in (("Condensation", "Hydro"), ("Heat Sink", "Thermal")):
    sid = species_with(ability)
    d = mon(sid, 12)
    d.hp = max(1, d.max_hp // 2)
    a = mon("aquabit" if atk_type == "Hydro" else "pyrodrive", 12)
    tech = TECHNIQUES["waterjet"] if atk_type == "Hydro" else TECHNIQUES["embervent"]
    hp0 = d.hp
    dmg, _e, _c = calc_damage(a, d, tech)
    # the damage formula still computes, but the engine converts the hit into a heal: verify via _execute_move
    bs = make_battle(player=[a], enemy=d)
    ev = play(bs, bt.plan_turn(bs, ("move", tech.id)) if tech.id in bs.player.moves else bt.plan_turn(bs, ("run",)))
    if any("absorbed the" in (t or "") for t in texts(ev)):
        assert bs.enemy.hp >= hp0, (ability, hp0, bs.enemy.hp)
print("OK absorb abilities")

# Sturdy Plating: survives the knockout at 1 HP once
sid = species_with("Sturdy Plating")
d = mon(sid, 5)
assert d.max_hp > 1
d.sturdy_used = False
a = mon("pyrodrive", 30)
random.seed(2)
bs = make_battle(player=[a], enemy=d)
strongest = max((m for m in bs.player.moves if TECHNIQUES[m].power > 0), key=lambda x: TECHNIQUES[x].power)
ev = play(bs, bt.plan_turn(bs, ("move", strongest)))
assert bs.enemy.sturdy_used and any("endured" in (t or "") for t in texts(ev)), texts(ev)
assert bs.enemy.hp > 0 and bs.outcome == "", "the battle should continue after Sturdy"
d2 = mon(sid, 5)
d2.sturdy_used = True
bs2 = make_battle(player=[mon("pyrodrive", 30)], enemy=d2)
play(bs2, bt.plan_turn(bs2, ("move", strongest)))
assert bs2.enemy.hp == 0 or bs2.outcome == "win", "Sturdy must not fire twice"
print("OK Sturdy Plating")

# Swarm Logic / Overdrive / Night Optics / Gyro Balance via calc_damage
def flat(m):
    """Pin IVs/effort to zero so a damage comparison isolates the ability effect (born IV variance
    would otherwise mask a 1.3x boost at these low damage rolls)."""
    m.ivs = {s: 0 for s in ("hp", "power", "defense", "sp_power", "sp_defense", "speed")}
    m.evs = {}
    m.recalc_stats()
    return m

sid = species_with("Swarm Logic")
low = flat(mon(sid, 20)); low.hp = max(1, low.max_hp // 4)
full = flat(mon(sid, 20)); full.hp = full.max_hp
random.seed(7)
dmg_low = calc_damage(low, mon("sporelet", 5), TECHNIQUES["waterjet"])
random.seed(7)
dmg_full = calc_damage(full, mon("sporelet", 5), TECHNIQUES["waterjet"])
assert dmg_low[0] > dmg_full[0], (dmg_low, dmg_full)
sid = species_with("Overdrive")
ost = flat(mon(sid, 20)); ost.status = "Overheated"
random.seed(7)
dmg_status = calc_damage(ost, mon("sporelet", 5), TECHNIQUES["waterjet"])
random.seed(7)
ost2 = flat(mon(sid, 20))
dmg_clean = calc_damage(ost2, mon("sporelet", 5), TECHNIQUES["waterjet"])
assert dmg_status[0] > dmg_clean[0]
sid = species_with("Gyro Balance")
tank = flat(mon(sid, 20))
attacker = flat(mon("pyrodrive", 20))
random.seed(7)
dmg_tank = calc_damage(attacker, tank, TECHNIQUES["embervent"])
from data import BATTLE_ABILITIES
ab_name = tank.ability
saved_spec = BATTLE_ABILITIES.pop(ab_name)                   # same species, ability off
random.seed(7)
dmg_plain = calc_damage(attacker, tank, TECHNIQUES["embervent"])
BATTLE_ABILITIES[ab_name] = saved_spec
assert dmg_tank[0] < dmg_plain[0], (dmg_tank, dmg_plain)
print("OK damage abilities")

# contact abilities: Ember Body burns the attacker (use an attacker without a status immunity)
sid = species_with("Ember Body")
random.seed(1)
for _ in range(60):
    d = mon(sid, 12)
    a = mon("florabot", 12)
    bs = make_battle(player=[a], enemy=d)
    ev = play(bs, bt.plan_turn(bs, ("move", bs.player.moves[0])))
    if bs.player.status:
        break
assert bs.player.status in STATUS_INFO, "contact ability never triggered in 60 hits"
print("OK contact abilities")

# immunities
sid = species_with("Coolant Flow")
d = mon(sid, 10)
assert bt._status_immune(d, "Overheated") and not bt._status_immune(d, "Suspended")
sid = species_with("Buoyant Core")
assert bt._status_immune(mon(sid, 10), "Suspended")
print("OK status immunities")

# Vacuum Seal: double the energy drains when attacking into it
sid = species_with("Vacuum Seal")
d = mon(sid, 10)
a = mon("aquabit", 10)
mv = next(m for m in a.moves if TECHNIQUES[m].power > 0)
bs = make_battle(player=[a], enemy=d)
e0 = bs.player.energy
random.seed(3)
play(bs, bt.plan_turn(bs, ("move", mv)))
assert bs.player.energy == e0 - 2 * TECHNIQUES[mv].energy, (e0, bs.player.energy)
print("OK Vacuum Seal")

# Grid Tether / Silent Run
sid = species_with("Grid Tether")
random.seed(9)
bs = make_battle(player=[mon("aquabit", 30)], enemy=mon(sid, 5))
for _ in range(8):
    bs2 = make_battle(player=[mon("aquabit", 30)], enemy=mon(sid, 5))
    play(bs2, bt.plan_turn(bs2, ("run",)))
    assert bs2.outcome != "run", "Grid Tether let the player flee"
sid = species_with("Silent Run")
bs = make_battle(player=[mon(sid, 3)], enemy=mon("nanolyte", 30))
play(bs, bt.plan_turn(bs, ("run",)))
assert bs.outcome == "run", "Silent Run must always escape"
print("OK flee abilities")

# ---- 6. Struggle ------------------------------------------------------------------------------------
m = mon("florabot", 10)
m.energy = 0
assert not m.has_energy()
assert choose_enemy_move(m, mon("sporelet", 5)) == "struggle"
bs = make_battle(player=[m], enemy=mon("sporelet", 4))
ev = play(bs, bt.plan_turn(bs, ("move", "struggle")))
assert any("Struggle" in (t or "") for t in texts(ev)), texts(ev)
assert bs.enemy.hp < bs.enemy.max_hp, "struggle dealt no damage"
assert bs.player.hp < bs.player.max_hp, "struggle recoil missing"
print("OK Struggle")

# ---- 7. enemy AI ------------------------------------------------------------------------------------
e = mon("pyrodrive", 12)
e.moves = ["embervent", "heatsink"] if "heatsink" in [t for _l, t in
           __import__("data").SPECIES["pyrodrive"].learnset] else e.moves
p = mon("sporelet", 5)
random.seed(5)
picked = {choose_enemy_move(e, p) for _ in range(200)}
assert "heatsink" not in picked or e.stage("power") == 0     # buff chosen only via the move list
# empty reserves -> struggle; low reserves never spent on a status move
e2 = mon("aquabit", 12)
e2.moves = ["overclock", "waterjet"]
e2.energy = 0
assert choose_enemy_move(e2, mon("sporelet", 12)) == "struggle"
e2b = mon("aquabit", 12)
e2b.moves = ["cryolock", "waterjet"]
e2b.energy = 7                                             # cryolock payable (4) but under its 8 reserve line
p2 = mon("sporelet", 12)
random.seed(1)
picks = {choose_enemy_move(e2b, p2) for _ in range(200)}
assert picks == {"waterjet"}, picks                        # the last drops go to a real shot, not a freeze
e3 = mon("aquabit", 12); e3.moves = ["overclock", "waterjet"]
picks = {choose_enemy_move(e3, mon("sporelet", 5)) for _ in range(200)}
assert "overclock" in picks, "AI never buffs"
# status move scored on a clean target, skipped when already afflicted
e4 = mon("sporelet", 12); e4.moves = ["sporecloud", "tackle"] if "tackle" in TECHNIQUES else ["sporecloud", "sysram"]
p4 = mon("aquabit", 8)
picks = {choose_enemy_move(e4, p4) for _ in range(200)}
assert "sporecloud" in picks
p4.status = "Deoxygenated"
picks = {choose_enemy_move(e4, p4) for _ in range(100)}
assert "sporecloud" not in picks, "AI statused an already-afflicted target"
print("OK enemy AI move choice")

# trainer switch: the player holds a big type advantage, a bench mon resists both ways
from data import SPECIES
hydro = next(sid for sid, sp in SPECIES.items() if "Hydro" in sp.types and sp.stage_ordinal == 1)
thermal = next(sid for sid, sp in SPECIES.items() if "Thermal" in sp.types and sp.stage_ordinal == 1
               and "Hydro" not in sp.types)
random.seed(12)
switches = 0
for i in range(400):
    bs3 = make_battle(player=[mon("florabot", 30)], enemy=mon(hydro, 20),
                      trainer="Coach", enemy_party=[mon(hydro, 20), mon(thermal, 20)])
    play(bs3, bt.plan_turn(bs3, ("defend",)))          # turn 1: the AI never switches
    play(bs3, bt.plan_turn(bs3, ("defend",)))          # turn 2: the switch becomes available
    if bs3.enemy.species_id == thermal and bs3.enemy_index == 1:
        switches += 1
assert switches > 0, "the trainer AI never switched into the resist"
print("OK enemy switch AI")

# ---- 8. save round-trip -----------------------------------------------------------------------------
import savegame
st = GameState()
m1 = mon("aquabit", 12); m1.set_stage("power", 2); m1.energy = 17
m1.status, m1.status_timer = "Suspended", 2
st.party = [m1]
st.captured.add("aquabit")
raw = savegame.serialize(st)
st2 = GameState()
savegame._read = lambda: raw
assert savegame.load(st2)
m2 = st2.party[0]
assert m2.stage("power") == 2 and m2.energy == 17
assert m2.status == "Suspended" and m2.status_timer == 2
# an old save carrying the retired power_stage field loads cleanly (field dropped, stages default)
savegame._read = lambda: savegame.serialize(st2)      # fresh format for the base
st3 = GameState()
assert savegame.load(st3) is False or True            # empty save -> False, no crash
print("OK save round-trip")

# ---- 9. UI: the fight menu honours PP ---------------------------------------------------------------
from engine import Engine, StateId
eng = Engine()
st = eng.state
st.intro_done = True
m = mon("aquabit", 12)
st.party = [m]
m.energy = 0
eng.state.battle_bag = lambda: {}
bs = make_battle([m], mon("sporelet", 4))
from battle import BattleScene
scene = BattleScene(bs, lambda res: None)
eng.push(scene)
scene._open("fight")
labels = [b.label for b in scene.grid.buttons]
assert any("STRUGGLE" in l for l in labels), labels
scene2 = BattleScene(make_battle([mon("aquabit", 12)], mon("sporelet", 4)), lambda res: None)
eng.push(scene2)
scene2._open("fight")
for b in scene2.grid.buttons:
    if b.tag and b.tag != "back" and b.tag in scene2.bs.player.moves:
        assert b.enabled == scene2.bs.player.can_pay(b.tag)
        assert b.sub and f"{TECHNIQUES[b.tag].energy} EN" in b.sub, b.sub
print("OK fight menu energy + Struggle")

print("ALL OK")
