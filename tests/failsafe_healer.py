"""Failsafe check: a player who never talked to any healer gets warped to the nearest healer BEHIND them
after a wipe -- never stranded in the trainer's line of sight, never skipped ahead to Epidimy."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from routes import HEALERS, travel_cost, TOWN, ROUTE1_START
import epidimy as epi
from overworld import OverworldScene
from state import GameState

assert HEALERS, "HEALERS must not be empty"
TOWN_IDS = {h["id"] for h in HEALERS if h["area"] == TOWN}

# Simulate an OverworldScene on route1 with no visited healers (never spoke to Venn / entered Cush's).
ow = OverworldScene.__new__(OverworldScene)  # no engine boot needed; _nearest_visited_healer only touches these attrs

class FakeEngine:
    state = GameState()
class FakeMap:
    area = "route1"
class FakePlayer:
    tile = (8, 13)  # mid-route1, right in Luke/Walker territory after LOS approach

ow.engine = FakeEngine()
ow.building = None
ow.map = FakeMap()
ow.player = FakePlayer()

assert ow.engine.state.visited_healers == set()
h = ow._nearest_visited_healer()
assert h is not None, "FAILSAFE FAILED: no healer picked for an unvisited player"
assert h["area"] == TOWN, "player on route1 must be sent back to a town healer, got %r" % h["id"]

# north end of route1: the Epidimy center is far closer but is AHEAD of the player and must be skipped
ow.player.tile = (12, 1)
costs = {x["id"]: travel_cost("route1", (12, 1), x["area"], x["tile"]) for x in HEALERS}
nearest_town_cost = min(costs[i] for i in TOWN_IDS)
assert costs["epi-center"] is not None and costs["epi-center"] < nearest_town_cost, (
    "test premise broken: epi-center is not actually nearer here")
h2 = ow._nearest_visited_healer()
assert h2["id"] in TOWN_IDS, "wipe near the north gate must not send the player forward, got %r" % h2["id"]

# from the very start of route1 as well
ow.player.tile = ROUTE1_START
h3 = ow._nearest_visited_healer()
assert h3["area"] == TOWN, h3["id"]

# having legitimately been to Epidimy unlocks its center again (it is no longer "ahead")
ow.engine.state.visited_areas.add(epi.AREA_ID)
ow.player.tile = (12, 1)
h4 = ow._nearest_visited_healer()
assert h4["id"] == "epi-center", h4["id"]
print("OK: unvisited wipes on route1 always fall back to", "/".join(sorted(TOWN_IDS)),
      "; epi-center only once Epidimy has been visited")

