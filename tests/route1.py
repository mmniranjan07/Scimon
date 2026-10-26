"""Route 1 end to end (headless): data checks, then a scripted player walks town -> Route 1 -> every key spot -> town.
Usage: python tests/route1.py [screenshot_dir]"""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")  # never touch the real save
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
import overworld as ow
import routes

OUT = sys.argv[1] if len(sys.argv) > 1 else None
if OUT: os.makedirs(OUT, exist_ok=True)
random.seed(5)
r1 = routes.AREAS["route1"]

# ---- data: the winding-ledge layout (26 x 30), Epidimy's gate at the top, only tiles the game already draws
assert (r1.w, r1.h) == (26, 30)
assert set("".join(r1.rows)) <= set("GFgPTurfhSl")
assert routes.validate()
link_tiles = set(routes.LINKS["route1"])                   # stepping on these fades to the town / Epidimy
assert routes.LINKS[routes.TOWN][(21, 0)] == ("route1", routes.ROUTE1_START, "up")
assert (routes.ROUTE1_START[0], 29) in link_tiles          # the arrival tile faces the town link one step below
tall = [(x, y) for y in range(r1.h) for x in range(r1.w) if r1.rows[y][x] == "g"]
stairs = [(x, y) for y in range(r1.h) for x in range(r1.w) if r1.rows[y][x] == "P" and (x, y) not in link_tiles]
assert len(tall) >= 15 and len(stairs) >= 5, (len(tall), len(stairs))

# ---- play it
eng = Engine(); ow.ENCOUNTER_CHANCE = 0                    # no random fights while we survey the map
eng.state.beaten_trainers |= {"luke", "walker"}            # trainers never scan; tests/route1_loop.py covers their battle
eng.state.story.add("bandit1")                             # the Corrupt Bandits already ambushed us once
held = {"d": None}
ow.OverworldScene._held_dir = lambda self: held["d"]
ovs = ow.OverworldScene(); eng.push(ovs)
def run(sec, dt=1 / 60):
    for _ in range(int(sec / dt)): eng.step(dt)
def shot(n):
    if OUT: eng.render(); pygame.image.save(eng.screen, f"{OUT}/{n}.png")
def key(k): eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
def path(m, start, goal):
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
    run(0.1)
def goto(goal): walk(path(ovs.map, ovs.player.tile, goal))
def poke(d, frames=90):
    """Hold a direction for exactly one step or ledge hop (a blocked push just holds); the input is dropped as
    soon as the move starts so a held key can't chain hops, then the move is given time to finish."""
    p = ovs.player
    t0 = p.tile
    held["d"] = d

    def one_move(begin):
        def wrapped(*a):
            begin(*a)
            held["d"] = None
        return wrapped
    begin_step, begin_jump = p.begin_step, p.begin_jump
    p.begin_step, p.begin_jump = one_move(begin_step), one_move(begin_jump)
    try:
        for _ in range(frames):
            eng.step(1 / 60)
            if p.tile != t0: break
    finally:
        p.begin_step, p.begin_jump = begin_step, begin_jump
        held["d"] = None
    for _ in range(240):
        if not p.moving and not eng.transitioning: break
        eng.step(1 / 60)
    run(0.1)
def face_and_talk(target):
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

# 2) collision: trees and stone ledges stop the player; a ledge is a one-way hop DOWN
ovs.player.place(5, 5, "left"); run(0.2); poke("left")
assert ovs.player.tile == (5, 5) and ovs.map.blocked(4, 5), ovs.player.tile          # the forest wall: no walking through
for wall in ((0, 0), (9, 5), (3, 7), (25, 24)):
    assert ovs.map.blocked(*wall), wall
ovs.player.place(10, 10, "up"); run(0.2); poke("up")
assert ovs.player.tile == (10, 10) and ovs.map.blocked(10, 9), ovs.player.tile       # cannot climb a ledge
ovs.player.place(9, 9, "right"); run(0.2); poke("right")
assert ovs.player.tile == (9, 9) and ovs.map.blocked(10, 9), ovs.player.tile         # ...nor cross it sideways
ovs.player.place(10, 8, "down"); run(0.2); poke("down")
assert ovs.player.tile == (10, 10), ovs.player.tile                                  # ...but hopping down works

# 3) every kind of spot can be walked to (nothing is sealed): tall grass, road/stair tiles, both Epidimy gates
ovs.player.place(*routes.ROUTE1_START, "up"); run(0.2)
for tgt in tall[::8] + stairs[::8] + [(18, 21), (19, 21)]:     # (18-19, 21): the stairs through the long ridge
    goto(tgt)
    assert ovs.player.tile == tgt
shot("r1_stairs")
goto((6, 1)); shot("r1_north_gate_west")                       # beside the Epidimy gate (x 6..9 on row 0)
goto((9, 1)); shot("r1_north_gate_east")

# 4) the signpost, the ranger and a beaten trainer all talk
lines = face_and_talk((11, 12)); assert lines and "Route 1" in lines[0], lines
lines = face_and_talk((14, 13)); assert lines and "Ranger Dana" in lines[0], lines
lines = face_and_talk((8, 10)); assert lines and "Luke" in lines[0], lines
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

# 6) back to town through the south link
goto((11, 28)); walk(["down"]); run(1.2)
assert ovs.map.name == "Riven Town" and ovs.player.tile == (21, 1), (ovs.map.name, ovs.player.tile)
shot("r1_back_in_town")
# the town still works: its plaza signpost keeps its own text
assert ovs.map.sign_at(*next(iter(ovs.map.signs)))[0].startswith("Signpost: Welcome to Riven Town")
print("OK Route 1:", len(tall), "tall-grass tiles,", len(stairs), "road/stair tiles, all reachable; town <-> route travel both ways")
