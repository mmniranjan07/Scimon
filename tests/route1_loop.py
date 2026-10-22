"""End to end repro of the Route 1 battle loop: a player who never talked to anyone walks onto Route 1,
loses to Luke, and must be warped to the nearest healer instead of staying in his line of sight."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")  # never touch the real save
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
import overworld as ow
import routes
from monsters import create_scimon

random.seed(5)
eng = Engine(); ow.ENCOUNTER_CHANCE = 0
held = {"d": None}
ow.OverworldScene._held_dir = lambda self: held["d"]
ovs = ow.OverworldScene(); eng.push(ovs)

def run(sec, dt=1 / 60):
    for _ in range(int(sec / dt)): eng.step(dt)
def key(k): eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
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

# the reported scenario: straight out of the house onto Route 1, nobody talked to, no healers visited
assert eng.state.visited_healers == set(), eng.state.visited_healers
eng.state.party = [create_scimon("florabot", 5)]
ovs.player.place(21, 3, "up"); run(0.2)
walk(["up", "up", "up"]); run(1.2)
assert ovs.map.area == "route1" and ovs.player.tile == routes.ROUTE1_START, (ovs.map.area, ovs.player.tile)

# lose the trainer fight the way BattleScene._finish does: pop, then on_end(result)
luke = next(n for n in ovs.npcs if n.id == "luke")
assert luke.trainer_battle
ovs._fighting = luke
res = {"bag": {}, "modules": {}, "party": eng.state.party, "outcome": "lose"}
ovs.end_trainer_battle(res)
run(1.5)

# failsafe: warped off the route to the nearest healer (Prof. Venn in town), party restored
venn = next(h for h in routes.HEALERS if h["id"] == "venn")
assert ovs.map.area == routes.TOWN, ovs.map.area
assert ovs.player.tile == venn["tile"], ovs.player.tile
assert all(m.hp == m.max_hp for m in eng.state.party), [(m.hp, m.max_hp) for m in eng.state.party]

# and the loop is gone: no re-approach, no battle while standing next to Venn
for _ in range(60):
    run(0.1)
    assert eng.find(StateId.BATTLE) is None, "battle re-triggered after blackout!"
    assert ovs.approacher is None, ovs.approacher

# a second wipe with still-zero visited healers also lands safely (this time from town, mid-wilds equivalent)
eng.state.visited_healers.clear()
ovs._fighting = luke
ovs.end_trainer_battle(dict(res))
run(1.5)
assert ovs.map.area == routes.TOWN and ovs.player.tile == venn["tile"], (ovs.map.area, ovs.player.tile)

# the failsafe never advances the player: wiping at the NORTH end of route1 (Epidimy's center is far closer)
# must still send them back to a town healer, because Epidimy has not been visited
epi_center = next(h for h in routes.HEALERS if h["id"] == "epi-center")
eng.state.visited_healers.clear()
eng.state.visited_areas = {"route1"}              # pretend route1 is the only area ever walked through
ovs.map = ovs._get_map(None, "route1")            # stand the scene on route1 at the north gate
ovs._load_npcs()
ovs.player.place(12, 1, "up")
c_epi = routes.travel_cost("route1", (12, 1), epi_center["area"], epi_center["tile"])
c_town = routes.travel_cost("route1", (12, 1), venn["area"], venn["tile"])
assert c_epi is not None and c_epi < c_town, (c_epi, c_town)
ovs._fighting = luke
ovs.end_trainer_battle(dict(res))
run(1.5)
assert ovs.map.area == routes.TOWN, ovs.map.area
assert ovs.player.tile == venn["tile"], ovs.player.tile
print("OK: wiped on Route 1 with no healer visited -> blacked out to", venn["id"], "at", venn["tile"],
      "; never forward (north-gate wipe also returned to town, not the Epidimy center); no battle loop")
