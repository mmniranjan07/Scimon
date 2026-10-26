"""The wider region end to end (headless): graph checks, a scripted walk across the network, the two hidden
chests, and a render pass over every new map.
Usage: python tests/network.py [screenshot_dir]"""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
import overworld as ow
import routes, towns, kanto
from data import CATALOG

OUT = sys.argv[1] if len(sys.argv) > 1 else None
if OUT: os.makedirs(OUT, exist_ok=True)
random.seed(7)

# ---- 1) the whole Kanto-shaped graph is present, validated and connected (routes.validate ran at import)
EXPECT = ({"stonreach", "tidebrook", "aurum", "emberport", "verdance", "dusklight", "vespera", "cinderfall",
           "astrion_plateau", "osts_cabin", "mossmere", "mt_crescent", "hollowgate", "ascent", "seaglass"}
          | {f"route{n}" for n in range(2, 26)} | {"route2n", "route1", "epidimy", "overworld"})
missing = EXPECT - set(routes.AREAS) - {"overworld"}
assert not missing, f"missing areas: {sorted(missing)}"
assert routes.validate()

# ---- 2) the hidden-chest rule: at most one town + one route, both with real catalogue loot
chest_areas = list(routes.CHESTS)
styled = [a for a in chest_areas if a == "overworld" or routes.AREAS[a].styled]
assert len(styled) <= 1 and len(chest_areas) - len(styled) <= 1, chest_areas
for area, chests in routes.CHESTS.items():
    for c in chests:
        for item, n in c["loot"]:
            assert item in CATALOG and n > 0, (area, c)
assert {"epidimy", "route4"} <= set(routes.CHESTS), routes.CHESTS

# ---- 3) every new map renders (props, buildings, glows, chest props)
pygame.init(); pygame.display.set_mode((320, 240))
for area_id in sorted(routes.AREAS):
    m = routes and __import__("map").TileMap.route(area_id)
    assert m.surface is not None, area_id
assert __import__("map").TileMap.overworld().surface is not None
r4 = __import__("map").TileMap.route("route4")
assert len(r4.interactables) == 1 and list(r4.interactables)[0] == routes.CHESTS["route4"][0]["tile"]
epi_map = __import__("map").TileMap.route("epidimy")
assert len(epi_map.interactables) == 1

# ---- 4) play it: walk the main road across the network
eng = Engine()
ow.ENCOUNTER_CHANCE = 0
eng.state.story |= {"bandit1", "bandit2"}                       # the ambushes already happened
for a in routes.AREAS.values():                                 # nobody scans; the road is ours
    eng.state.beaten_trainers |= {n["id"] for n in a.npcs if "battle" in n}
held = {"d": None}
ow.OverworldScene._held_dir = lambda self: held["d"]
ovs = ow.OverworldScene(); eng.push(ovs)

def run(sec, dt=1 / 60):
    for _ in range(int(sec / dt)):
        eng.step(dt)
def shot(n):
    if OUT: eng.render(); pygame.image.save(eng.screen, f"{OUT}/{n}.png")
def key(k): eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
def path(m, start, goal):
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
            run(1.2)
        ovs._walk_area = ovs.map.area
    run(0.1)
def goto(goal): walk(path(ovs.map, ovs.player.tile, goal))

def cross(to_area, gate_hint=None):
    """Walk to the link tile that leads to `to_area` (the nearest one), then across the fade."""
    links = [t for t, (dst, _a, _f) in routes.LINKS.get(ovs.map.area, {}).items() if dst == to_area]
    assert links, f"{ovs.map.area} has no link to {to_area}"
    target = min(links, key=lambda t: abs(t[0] - ovs.player.tile[0]) + abs(t[1] - ovs.player.tile[1]))
    goto(target)
    side = "s" if ovs.map.blocked(target[0], target[1] + 1) else None
    d = ("up" if target[1] == 0 else "down" if target[1] == ovs.map.h - 1 else
         "left" if target[0] == 0 else "right")
    walk([d]); run(1.2)
    assert ovs.map.area == to_area, (ovs.map.area, to_area)

# Riven -> Epidimy over Route 1
ovs.player.place(21, 3, "up"); run(0.2)
walk(["up", "up", "up"]); run(1.2)
assert ovs.map.area == "route1", ovs.map.area
cross("epidimy")
assert ovs.map.area == "epidimy"
shot("net_epidimy")

# Epidimy -> Route 2 -> Mossmere -> Route 2 North -> Stonreach -> Route 3 -> Mt. Crescent
cross("route2"); cross("mossmere"); shot("net_mossmere")
cross("route2n"); cross("stonreach"); shot("net_stonreach")
assert ovs.map.name == "Stonreach Town"
cross("route3"); cross("mt_crescent"); shot("net_crescent")

# Mt. Crescent -> Route 4 -> Tidebrook
cross("route4"); cross("tidebrook"); shot("net_tidebrook")

# ---- 5) the Route 4 chest: walk back, find the pocket, open it, take the loot
cross("route4")
chest = routes.CHESTS["route4"][0]
cx, cy = chest["tile"]
before = {i: eng.state.qty(i) for i, _ in chest["loot"]}
approach = next((cx + dx, cy + dy) for dx, dy in DIRS.values()
                if not ovs.map.blocked(cx + dx, cy + dy, ovs._npc_rects()))
goto(approach)
d = next(d for d, (dx, dy) in DIRS.items() if (cx + dx, cy + dy) == (ovs.player.tile[0] + (cx - ovs.player.tile[0]), 0) or True)
face = next(d for d, (dx, dy) in DIRS.items() if ovs.player.tile[0] + dx == cx and ovs.player.tile[1] + dy == cy)
held["d"] = face; run(0.12); held["d"] = None
key(pygame.K_RETURN); run(0.2)
for _ in range(12):
    if eng.top is ovs: break
    key(pygame.K_RETURN); run(0.15)
assert eng.top is ovs, "chest dialogue did not close"
for item, n in chest["loot"]:
    assert eng.state.qty(item) == before[item] + n, (item, eng.state.qty(item), before[item])
assert "route4:chest" in eng.state.opened_chests
shot("net_chest_route4")

# an opened chest stays open when the map is rebuilt (the save-state sync path)
fresh = __import__("map").TileMap.route("route4")
fresh.sync_state(eng.state)
assert fresh.interactable_at(cx, cy).opened

# ---- 6) the Epidimy chest too (town chest), then a far-wipe home
ovs.building = None
ovs.map = ovs._get_map(None, "epidimy")
ovs._load_npcs()
ovs.player.place(*ow.AREA_STARTS["epidimy"], "up")
ovs.map.sync_state(eng.state)
run(0.5)
ec = routes.CHESTS["epidimy"][0]
ex, ey = ec["tile"]
before_e = {i: eng.state.qty(i) for i, _ in ec["loot"]}
approach = next((ex + dx, ey + dy) for dx, dy in DIRS.values()
                if not ovs.map.blocked(ex + dx, ey + dy, ovs._npc_rects()))
goto(approach)
face = next(d for d, (dx, dy) in DIRS.items() if ovs.player.tile[0] + dx == ex and ovs.player.tile[1] + dy == ey)
held["d"] = face; run(0.12); held["d"] = None
key(pygame.K_RETURN); run(0.2)
for _ in range(12):
    if eng.top is ovs: break
    key(pygame.K_RETURN); run(0.15)
assert eng.top is ovs
for item, n in ec["loot"]:
    assert eng.state.qty(item) == before_e[item] + n, (item, eng.state.qty(item))

# a wipe in a far town sends the player back to the nearest *visited* healer (never forward to an unseen area)
eng.state.visited_areas |= {"stonreach"}
ovs.building = None
ovs.map = ovs._get_map(None, "tidebrook")
ovs.player.place(*ow.AREA_STARTS["tidebrook"], "down")
healer = ovs._nearest_visited_healer()
assert healer["area"] in eng.state.visited_areas, healer
assert healer["area"] == "tidebrook", healer       # Tidebrook was visited on the way: its nook is nearest
ovs._blackout_to(healer)
assert ovs.map.area == healer["area"], ovs.map.area
shot("net_blackout")

print("OK network: 42 areas validated + rendered; Riven->Epidimy->Mossmere->Stonreach->Crescent->Tidebrook walked;"
      " both hidden chests opened and synced; far-wipe returns to the nearest visited healer")
