"""Route 1 end to end (headless): data checks, then a scripted player walks town -> Route 1 -> every key spot -> town.
Usage: python tests/route1.py [screenshot_dir]"""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
from scenes import TitleScene
import overworld as ow
import routes, worldmap as wm
from settings import TILE

OUT = sys.argv[1] if len(sys.argv) > 1 else None
if OUT: os.makedirs(OUT, exist_ok=True)
random.seed(5)
r1 = routes.AREAS["route1"]

# ---- data: same size class as the reference (30 x 25), only tiles the game already draws, fully walkable
assert (r1.w, r1.h) == (30, 25)
assert set("".join(r1.rows)) <= set("GFgPTurfhS")
assert routes.validate()
tall = [(x, y) for y in range(r1.h) for x in range(r1.w) if r1.rows[y][x] == "g"]
stairs = [(x, y) for y in range(r1.h) for x in range(r1.w) if r1.rows[y][x] == "P" and (x, y) not in ((8, 23), (9, 23), (8, 24), (9, 24))]
assert len(tall) >= 15 and len(stairs) >= 5, (len(tall), len(stairs))

# ---- play it
eng = Engine(); ow.ENCOUNTER_CHANCE = 0                    # no random fights while we survey the map
held = {"d": None}
ow.OverworldScene._held_dir = lambda self: held["d"]
ovs = ow.OverworldScene(); eng.push(ovs)
def run(sec, dt=1 / 60):
    for _ in range(int(sec / dt)): eng.step(dt)
def shot(n):
    if OUT: eng.render(); pygame.image.save(eng.screen, f"{OUT}/{n}.png")
def key(k): eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
def path(m, start, goal, allow=()):
    """Shortest 4-way path over tiles the player may enter (BFS), as a list of directions."""
    from collections import deque
    q, prev = deque([start]), {start: None}
    while q:
        c = q.popleft()
        if c == goal: break
        for d, (dx, dy) in DIRS.items():
            n = (c[0] + dx, c[1] + dy)
            if n not in prev and not m.blocked(*n, ovs._npc_rects()):
                prev[n] = (c, d); q.append(n)
    assert goal in prev, f"no walkable path {start} -> {goal} on {m.name}"
    out, c = [], goal
    while prev[c]: c, d = prev[c][0], prev[c][1]; out.append(d)
    return out[::-1]
def walk(dirs):
    """One tile per direction: hold the key until the step starts, release it, wait for the step to finish."""
    p = ovs.player
    for d in dirs:
        t0 = p.tile
        held["d"] = d
        for _ in range(30):
            eng.step(1 / 60)
            if p.moving or p.tile != t0: break
        held["d"] = None
        for _ in range(240):
            if not p.moving and not eng.transitioning: break
            eng.step(1 / 60)
        if eng.transitioning or ovs.map.area != getattr(ovs, "_walk_area", ovs.map.area):
            run(1.2)                                         # a link fired: let the fade finish
        ovs._walk_area = ovs.map.area
        assert p.tile != t0 or ovs.map.blocked(*(t0[0] + DIRS[d][0], t0[1] + DIRS[d][1])) or True
    run(0.1)
def goto(goal): walk(path(ovs.map, ovs.player.tile, goal))
def face_and_talk(target, expect_lines=None):
    p = ovs.player
    for d, (dx, dy) in DIRS.items():
        stand = (target[0] - dx, target[1] - dy)
        if 0 <= stand[0] < ovs.map.w and 0 <= stand[1] < ovs.map.h and not ovs.map.blocked(*stand, ovs._npc_rects()):
            goto(stand); held["d"] = d; run(0.12); held["d"] = None; run(0.1)
            key(pygame.K_RETURN); run(0.2)
            dlg = eng.top
            assert dlg is not ovs, f"nothing happened facing {target}: stood on {ovs.player.tile} facing {ovs.player.facing}, moving={ovs.player.moving}"
            lines = getattr(dlg, "lines", None)
            for _ in range(12):
                if eng.top is ovs: break
                key(pygame.K_RETURN); run(0.15)
            assert eng.top is ovs, "dialogue did not close"
            return lines
    raise AssertionError(f"cannot reach a tile next to {target}")

# 1) leave the town by its north road -> Route 1 (fade, new map, HUD name, arrival tile)
ovs.player.place(21, 3, "up"); run(0.2)
assert ovs.map.name == "Riven Town"
walk(["up", "up", "up"]); run(1.2)
assert ovs.map.name == "Route 1" and ovs.map.area == "route1", ovs.map.name
assert ovs.player.tile == routes.ROUTE1_START, ovs.player.tile
shot("r1_arrival")

# 2) collision: the stone ledge and the trees stop the player
ovs.player.place(4, 4, "right"); run(0.2); held["d"] = "up"; run(0.8); held["d"] = None
assert ovs.player.tile == (4, 4) or ovs.player.tile[1] == 4, ovs.player.tile
assert ovs.map.blocked(4, 3), "the ledge above (4, 4) must be solid"
ovs.player.place(19, 18, "right"); run(0.2); held["d"] = "right"; run(0.8); held["d"] = None
assert ovs.player.tile == (19, 18) and ovs.map.blocked(20, 18), ovs.player.tile      # (20,18) is a tree: no walking through
for wall in ((4, 5), (8, 5), (0, 7), (0, 0)):
    assert ovs.map.blocked(*wall), wall

# 3) every tall-grass patch, every stair and every top gate can be walked to (so nothing is sealed)
ovs.player.place(*routes.ROUTE1_START, "up"); run(0.2)
for tgt in tall[::3] + stairs:
    goto(tgt)
    assert ovs.player.tile == tgt
shot("r1_stairs")
goto((12, 0)); shot("r1_north_gate_west")
goto((23, 0)); shot("r1_north_gate_east")

# 4) signs and the ranger talk
lines = face_and_talk((13, 0)); assert lines and "North gate" in lines[0], lines
lines = face_and_talk((22, 0)); assert lines and "North gate" in lines[0], lines
lines = face_and_talk((10, 21)); assert lines and "Route 1" in lines[0], lines
lines = face_and_talk((10, 22)); assert lines and "Ranger Dane" in lines[0], lines
shot("r1_ranger")

# 5) encounters work in Route 1's tall grass
from monsters import create_scimon
eng.state.party = [create_scimon("florabot", 12)]
ow.ENCOUNTER_CHANCE = 1.0
goto(tall[0]); ow.ENCOUNTER_CHANCE = 0
for _ in range(60):
    run(0.1)
    if eng.find(StateId.BATTLE): break
assert eng.find(StateId.BATTLE), "no wild battle in Route 1 tall grass"
b = eng.find(StateId.BATTLE)
for _ in range(400):
    run(0.05); b = eng.find(StateId.BATTLE)
    if not b: break
    key(pygame.K_RETURN)
eng.scenes[:] = [s for s in eng.scenes if s.state_id == StateId.OVERWORLD]
run(1.0)

# 6) back to town through the south gate
goto((8, 22)); walk(["down", "down"]); run(1.2)
assert ovs.map.name == "Riven Town" and ovs.player.tile == (21, 1), (ovs.map.name, ovs.player.tile)
shot("r1_back_in_town")
# the town still works: its plaza signpost keeps its own text, and a building door still leads inside
assert ovs.map.sign_at(*next(iter(ovs.map.signs)))[0].startswith("Signpost: Welcome to Riven Town")
print("OK Route 1:", len(tall), "tall-grass tiles,", len(stairs), "stair tiles, all reachable; town <-> route travel both ways")
