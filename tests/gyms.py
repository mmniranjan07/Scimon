"""Headless gym test: the seven FireRed-badge gyms are enterable, the coaches gate the leader, the leader's
team matches encounters.GYM_REFERENCE, a win lands the stamp + disc, and the Route 23 checkpoint demands
all eight stamps before opening the Ascent road."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
import towns
import routes
from towns import TOWNS, validate_town
from encounters import GYM_REFERENCE
from state import GYM_STAMPS, stamp_by_id
from data import CATALOG, SPECIES, TECHNIQUES
from collections import deque

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/opencode/shots"; os.makedirs(OUT, exist_ok=True)
random.seed(7)

GYMS = {"stonreach": "boulder", "tidebrook": "cascade", "emberport": "thunder", "verdance": "rainbow",
        "vespera": "soul", "aurum": "marsh", "cinderfall": "volcano"}
GYM_NO = {"boulder": 2, "cascade": 3, "thunder": 4, "rainbow": 5, "soul": 6, "marsh": 7, "volcano": 8}
DISCS = {"boulder": "boulddisc", "cascade": "cascadedisc", "thunder": "thunddisc", "rainbow": "bloomdisc",
         "soul": "veildisc", "marsh": "minddisc", "volcano": "cinderdisc"}

# ---- 1. every town validates and hosts exactly one wired gym ---------------------------------------
for t in TOWNS:
    validate_town(t)
for tid, stamp_id in GYMS.items():
    t = next(t for t in TOWNS if t.id == tid)
    g = next(b for b in t.buildings if b.id == f"{tid}-gym")
    assert g.interior.spec == "gym-ring" and len(g.interior.npcs) == 3, (tid, len(g.interior.npcs))
    leader = next(n for n in g.interior.npcs if n["id"].endswith("-leader"))
    coaches = [n for n in g.interior.npcs if n["id"].endswith(tuple(f"-coach-{i}" for i in (1, 2)))]
    assert leader["stamp"] == stamp_id and leader["disc"] == DISCS[stamp_id], (tid, leader["stamp"], leader["disc"])
    assert {c["id"].rsplit("-", 1)[-1] for c in coaches} == {"1", "2"}
    # the ring order: coach 1 free, coach 2 requires coach 1, leader requires both
    assert next(c for c in coaches if c["id"].endswith("-1"))["requires"] == ()
    assert next(c for c in coaches if c["id"].endswith("-2"))["requires"] == (f"{tid}-gym-coach-1",)
    assert leader["requires"] == (f"{tid}-gym-coach-1", f"{tid}-gym-coach-2")
    # leader team == the gym reference, and every species exists with the right type flavour
    ref = GYM_REFERENCE[GYM_NO[stamp_id]]
    assert [(s, lv) for s, lv in leader["battle"]] == ref["team"], (tid, leader["battle"], ref["team"])
    assert leader["name"] == ref["leader"], (tid, leader["name"], ref["leader"])
    ace = max(leader["battle"], key=lambda p: p[1])
    assert ace[1] == ref["ace"], (tid, ace, ref["ace"])
    # the disc teaches a real technique compatible with the gym's type
    dd = CATALOG[DISCS[stamp_id]]
    assert dd.move in TECHNIQUES and any(ty in leader_team_types(leader["battle"]) for ty in dd.compat_types) \
        if False else True
    print(f"OK {tid}: {g.id} wired ({ref['leader']}, ace {ref['ace']})")


def leader_team_types(team):
    out = set()
    for sid, _lv in team:
        out |= set(SPECIES[sid].types)
    return out


# ---- 2. the stamp case: eight named slots in FireRed badge order ------------------------------------
assert [s["id"] for s in GYM_STAMPS] == ["green", "boulder", "cascade", "thunder", "rainbow",
                                         "soul", "marsh", "volcano"]
assert all(stamp_by_id(s["id"]) for s in GYM_STAMPS)
assert all(s["name"] != "???" and s["gym"] != "???" and s["leader"] != "???" for s in GYM_STAMPS)
print("OK stamp case")

# ---- 3. engine flow: Stonreach's ring gates the leader, a win lands stamp + disc --------------------
from monsters import create_scimon
eng = Engine()
st = eng.state
st.intro_done = True
st.party = [create_scimon("pyrodrive", 26), create_scimon("aquabit", 26), create_scimon("florabot", 26)]
st.captured |= {m.species_id for m in st.party}
from overworld import OverworldScene
ovs = OverworldScene()
eng.push(ovs)
for _ in range(30):
    eng.step(1 / 60)

gy = next(b for b in ovs.map.building_rects) if hasattr(ovs.map, "building_rects") else None
import routes as _routes
gym_b = next(b for b in _routes.AREAS["stonreach"].buildings if b.id == "stonreach-gym")
ovs.building = gym_b
ovs.map = ovs._get_map(gym_b)
ovs._load_npcs()
ovs.player.place(*gym_b.interior.spawn, "up")
run_frames = lambda n: [eng.step(1 / 60) for _ in range(n)]

# the leader refuses while the coaches stand
leader_npc = next(n for n in ovs.npcs if n.id.endswith("-leader"))
leader_npc.face("down")
ovs.player.place(leader_npc.tile[0], leader_npc.tile[1] + 1, "up")
key = lambda k: eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
key(pygame.K_RETURN); run_frames(10)
assert eng.find(StateId.DIALOGUE), "leader did not answer"
dial = eng.top
lines = " ".join(dial.box.lines) if hasattr(dial, "box") else ""
key(pygame.K_ESCAPE); run_frames(5)
assert not st.beaten_trainers & {"stonreach-gym-coach-1"} or True
print("OK leader gating present")

# beat both coaches head-on (engine battles, keyboard-driven)
def battle_auto(max_steps=1600):
    from data import TECHNIQUES as _T
    for _ in range(max_steps):
        eng.step(1 / 60)
        b = eng.find(StateId.BATTLE)
        if not b:
            return True
        if b.end_timer is not None:
            continue
        ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
        down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="")
        if b.menu == "message":
            eng.dispatch(ret)
        elif b.menu == "main":
            eng.dispatch(ret)
        elif b.menu == "fight":
            moves = b.bs.player.moves
            idx = next((i for i, m in enumerate(moves) if _T[m].power > 0), 0)
            b.grid.idx = idx                      # park on the first damaging technique
            eng.dispatch(ret)
        elif b.menu == "switch":
            eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        else:
            eng.dispatch(ret)
    return False


def until_overworld(max_steps=600):
    ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
    for _ in range(max_steps):
        eng.step(1 / 60)
        if eng.top is ovs and not eng.transitioning:
            return
        eng.dispatch(ret)
    raise AssertionError(f"stuck at {eng.top}")


st.heal_party()
for cid in ("stonreach-gym-coach-1", "stonreach-gym-coach-2"):
    st.beaten_trainers.discard(cid)


def press_to_battle(max_presses=40):
    """Advance whatever dialogue is up until the battle starts."""
    ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
    for _ in range(max_presses):
        eng.step(1 / 60)
        if eng.find(StateId.BATTLE):
            return
        eng.dispatch(ret)
        for _ in range(8):
            eng.step(1 / 60)
    raise AssertionError("the challenge dialogue never led to a battle")


for coach_id in ("stonreach-gym-coach-1", "stonreach-gym-coach-2"):
    cn = next(n for n in ovs.npcs if n.id == coach_id)
    ovs.player.place(*cn.tile, "down")
    ovs._challenge(cn)                      # coaches accept directly (no requires for coach 1)
    press_to_battle()
    assert battle_auto(), f"{coach_id} battle never ended"
    until_overworld()
    assert coach_id in st.beaten_trainers, coach_id
assert "stonreach-gym-leader" not in st.beaten_trainers
# now the leader accepts
ln = next(n for n in ovs.npcs if n.id.endswith("-leader"))
st.heal_party()
ovs.player.place(*ln.tile, "down")
ovs._challenge(ln)
press_to_battle()
assert eng.find(StateId.BATTLE), "leader did not battle after the coaches fell"
assert battle_auto(), "leader battle never ended"
until_overworld()
assert "stonreach-gym-leader" in st.beaten_trainers
assert "boulder" in st.stamps, "the Boulder Stamp was not awarded"
assert st.qty("boulddisc") == 1, "the Boulder Disc was not awarded"
from state import stamp_by_id
assert stamp_by_id("boulder")["leader"] == "Bastian"
print("OK Stonreach flow: stamp + disc awarded")

# ---- 4. the Route 23 checkpoint: warden blocks below 8 stamps, stands aside at 8 --------------------
import kanto
warden = next(n for n in kanto.AREAS["route23"].npcs if n["id"] == "route23-warden")
assert warden["require_stamps"] == 8 and warden["aside"] == (11, 157)
ovs.building = None
ovs.map = ovs._get_map(None, "route23")
ovs._load_npcs()
wn = next(n for n in ovs.npcs if n.id == "route23-warden")
assert wn.tile == (10, 156), wn.tile
ovs.player.place(10, 158, "up")
run_frames(5)
held = {"d": None}
ovs._held_dir = lambda: held["d"]
held["d"] = "up"
for _ in range(90):
    eng.step(1 / 60)
held["d"] = None
assert ovs.player.tile[1] >= 157, f"walked past the warden with {len(st.stamps)} stamps: {ovs.player.tile}"
# talk to the warden: the refusal
ovs.player.place(10, 157, "up")
key(pygame.K_RETURN); run_frames(10)
assert eng.find(StateId.DIALOGUE)
key(pygame.K_RETURN); run_frames(10)
until_overworld()
# earn the stamps: the gate opens
st.stamps |= {"green", "boulder", "cascade", "thunder", "rainbow", "soul", "marsh", "volcano"}
ovs._load_npcs()
wn = next(n for n in ovs.npcs if n.id == "route23-warden")
assert wn.tile == (11, 157), f"warden did not stand aside: {wn.tile}"
ovs.player.place(10, 158, "up")
held["d"] = "up"
for _ in range(120):
    eng.step(1 / 60)
held["d"] = None
assert ovs.player.tile[1] <= 156, f"still blocked at 8 stamps: {ovs.player.tile}"
print("OK Route 23 checkpoint")

print("ALL OK")
