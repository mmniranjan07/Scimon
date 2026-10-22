"""Epidimy Town (headless): data checks, then a scripted player walks Route 1 -> Epidimy -> a house -> out -> Scimon Center -> Route 1.
Usage: python tests/epidimy.py [screenshot_dir]"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")  # never touch the real save
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine
import overworld as ow
import routes, epidimy as epi
from collections import deque

OUT = sys.argv[1] if len(sys.argv) > 1 else None
if OUT: os.makedirs(OUT, exist_ok=True)
assert routes.validate() and epi.validate()
eng = Engine(); ow.ENCOUNTER_CHANCE = 0
held = {"d": None}
ow.OverworldScene._held_dir = lambda self: held["d"]
ovs = ow.OverworldScene(); eng.push(ovs)
D = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

def run(sec):
    for _ in range(int(sec * 60)): eng.step(1 / 60)
def shot(n):
    if OUT: eng.render(); pygame.image.save(eng.screen, f"{OUT}/{n}.png")
def walk_to(goal):
    m, p = ovs.map, ovs.player
    q, prev = deque([p.tile]), {p.tile: None}
    while q:
        c = q.popleft()
        if c == goal: break
        for d, (dx, dy) in D.items():
            n = (c[0] + dx, c[1] + dy)
            if n not in prev and not m.blocked(*n, ovs._npc_rects()): prev[n] = (c, d); q.append(n)
    assert goal in prev, f"no path to {goal} on {m.name}"
    steps, c = [], goal
    while prev[c]: steps.append(prev[c][1]); c = prev[c][0]
    for d in steps[::-1]:
        t0 = p.tile
        held["d"] = d
        for _ in range(30):
            eng.step(1 / 60)
            if p.moving or p.tile != t0: break
        held["d"] = None
        for _ in range(60):
            eng.step(1 / 60)
            if not p.moving and not eng.transitioning: break
        if ovs.map is not m: return          # an area link fired mid-walk

# Route 1 -> Epidimy through the north gate
eng.step(0); ovs.travel(("route1", (7, 1), "down")); run(1)
assert ovs.map.area == "route1"
walk_to((7, 0)); run(1)
assert ovs.map.area == "epidimy", ovs.map.area
assert ovs.player.tile == (7, epi.H - 2), ovs.player.tile
shot("arrive")
# enter and leave a cottage, then the Scimon Center
for bid in ("epi-corin", "epi-center", "epi-mart", "epi-gym", "epi-brin"):
    b = next(x for x in epi.BUILDINGS if x.id == bid)
    walk_to(b.entry_return); held["d"] = "up"; run(0.3); held["d"] = None; run(1)
    assert ovs.building is b and ovs.map.kind == "interior", (bid, ovs.player.tile, b.door, ovs.map.area, ovs.building)
    shot(bid)
    walk_to(b.interior.exit_tile); run(1.2)
    assert ovs.building is None and ovs.map.area == "epidimy" and ovs.player.tile == b.entry_return, (bid, ovs.player.tile)
# back to Route 1
walk_to((7, epi.H - 1)); run(1)
assert ovs.map.area == "route1" and ovs.player.tile[1] == 1 and ovs.player.tile[0] in epi.ROUTE1_GATE_X, (ovs.map.area, ovs.player.tile)
print("OK Epidimy: Route 1 <-> town, 5 buildings enter/exit")
