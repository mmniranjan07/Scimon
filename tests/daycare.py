"""Headless Day-Care test: the compatibility score (same family 50, shared habitat 20, babies
infertile), the deposit guards, the step bank + FRLG's withdrawal cost, level-by-level EXP with the
replace-first-move rule, the egg roll window, egg acceptance + hatching, and the save round-trip."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))
random.seed(43)

import daycare
import savegame
from data import CHAIN_OF, FAMILY_OF, SPECIES
from monsters import create_scimon, xp_for_level
from settings import DAYCARE_LEVEL_COST, EGG_HATCH_LEVEL, EGG_ROLL_STEPS
from state import GameState

MID, FINAL = "florabot-mid", "florabot-final"          # one family, neither a baby
OTHER = "sporelet"                                     # a different family, same forest habitat

# ---- 1. compatibility --------------------------------------------------------------------------------
a, b = create_scimon(MID, 20), create_scimon(FINAL, 22)
c = create_scimon(OTHER, 20)
assert daycare.compat_score(a, b) == 50
assert daycare.compat_score(a, c) == 20
assert daycare.compat_text(a, b) == daycare.COMPAT_TEXT[50]
baby = create_scimon(CHAIN_OF[MID][0], 5)
assert baby.species.stage_role == "first" and daycare.compat_score(baby, b) == 0

# ---- 2. deposit guards --------------------------------------------------------------------------------
st = GameState()
st.party = [create_scimon(MID, 20)]
ok, msg = daycare.can_deposit(st)
assert not ok and "keep at least one" in msg
st.party.append(b)
ok, _ = daycare.can_deposit(st)
assert ok
st.party.append(baby)                                  # babies may sit in care (FRLG lets you deposit
ok, msg = daycare.deposit(st, baby.uid)                # them) -- the compat roll just never fires
assert ok and len(st.daycare) == 1, msg
st.daycare.clear()

# ---- 3. the step bank + withdrawal cost ---------------------------------------------------------------
st = GameState()
m1, m2 = create_scimon(MID, 20), create_scimon(FINAL, 22)
st.party = [m1, m2]
ok, _ = daycare.deposit(st, m1.uid)
assert ok and len(st.daycare) == 1 and st.party == [m2]
slot = st.daycare[0]
slot["steps"] = xp_for_level(20)                       # enough banked EXP for exactly one level
cost, gained = daycare.withdraw_cost(slot)
assert (cost, gained) == (DAYCARE_LEVEL_COST * 2, 1), (cost, gained)
st.credits = 0
ok, msg = daycare.withdraw(st, 0)
assert not ok and "credits" in msg
st.credits = 1000
moves_before = list(m1.moves)
ok, msg = daycare.withdraw(st, 0)
assert ok and m1 in st.party and m1.level == 21, (m1.level, msg)
assert "-200" in msg and m1.hp > 0
# the level-up taught a learnset move if one existed at level 21 (replacing the first, FRLG's rule)
learned = [t for _lv, t in SPECIES[MID].learnset if _lv == 21 and t not in moves_before]
if learned:
    assert learned[0] in m1.moves and moves_before[0] not in m1.moves, (m1.moves, moves_before)

# ---- 4. the egg roll window + acceptance + hatching ----------------------------------------------------
class Always:
    """An rng whose rolls always succeed."""
    def randrange(self, n):
        return 0

    def choice(self, seq):
        return seq[0]

st = GameState()
m1, m2 = create_scimon(MID, 20), create_scimon(FINAL, 22)
st.party = [m1, m2, create_scimon(OTHER, 20)]          # one Scimon always stays home
daycare.deposit(st, m1.uid)
daycare.deposit(st, m2.uid)
assert len(st.daycare) == 2 and len(st.party) == 1
msgs = []
for _ in range(EGG_ROLL_STEPS):                        # the roll fires when slot 2's steps hit the window
    msgs += daycare.on_step(st, Always())
assert st.daycare_egg == CHAIN_OF[m1.species_id][0], (st.daycare_egg, msgs)
assert any("egg" in m.lower() for m in msgs), msgs
n_more = [daycare.on_step(st, Always()) for _ in range(EGG_ROLL_STEPS)]
assert not any(m for m in n_more if "found an egg" in str(m)), "no second egg while one is pending"
assert all(s["steps"] > 0 for s in st.daycare), "care slots bank steps too"

st.party = []                                          # make room and take the egg
ok, msg = daycare.take_egg(st)
assert ok and st.daycare_egg is None
egg = st.party[0]
assert egg.is_egg and egg.species_id == CHAIN_OF[MID][0] and egg.level == EGG_HATCH_LEVEL
assert egg.hatch_left == 300, egg.hatch_left           # rare family: 5 hatch cycles x 60 steps
inherited = sum(1 for iv in egg.ivs.values() if iv == 31) if hasattr(egg, "ivs") else 0
hatch_left = egg.hatch_left
st.captured.add(egg.species_id)
hatch_msgs = [daycare.on_step(st) for _ in range(hatch_left)]
fresh = st.party[0]
assert not fresh.is_egg and fresh.level == EGG_HATCH_LEVEL and fresh.species_id == CHAIN_OF[MID][0], \
    (fresh.is_egg, fresh.level)
assert any("hatched" in str(m) for m in hatch_msgs if m), "the hatch announcement must toast"

# ---- 5. the save round-trip (daycare slots, the egg, the safari session) ------------------------------
# SCIMON_NO_SAVE blocks the real file: the round-trip runs against an in-memory stand-in for the
# store, exercising the real serialize/parse paths.
buf = {}
savegame._read = lambda: buf.get("raw")
savegame._write = lambda raw: (buf.__setitem__("raw", raw) or True)
savegame.delete = lambda: buf.clear()
st2 = GameState()
m1 = create_scimon(MID, 20)
m1.hatch_left = 12
st2.party = [m1, create_scimon(FINAL, 22)]
st2.daycare = [{"mon": create_scimon(OTHER, 30), "steps": 55}]
st2.daycare_egg = CHAIN_OF[MID][0]
st2.safari = {"balls": 7, "steps": 123}
st2.coins = 42
savegame.save(st2)
st3 = GameState()
assert savegame.load(st3)
assert [s["mon"].species_id for s in st3.daycare] == [OTHER] and st3.daycare[0]["steps"] == 55
assert st3.daycare_egg == CHAIN_OF[MID][0]
assert st3.safari == {"balls": 7, "steps": 123} and st3.coins == 42
assert st3.party[0].hatch_left == 12
savegame.delete()
st4 = GameState()
assert not savegame.load(st4) or not st4.party         # a deleted save loads as fresh

print("OK daycare: compat, guards, step bank + cost, level-up moves, egg roll + hatch, save round-trip")
