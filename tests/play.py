"""Headless gameplay test: battle, movement/collision, doors, shop, pack, database, capture."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
from scenes import TitleScene
import overworld as ow
from settings import TILE

OUT = "/home/claude/shots"; os.makedirs(OUT, exist_ok=True)
random.seed(3)
eng = Engine(); eng.push(TitleScene())
held = {"d": None}
ow.OverworldScene._held_dir = lambda self: held["d"]

def key(k): eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
def run(sec, dt=1/60):
    for _ in range(int(sec / dt)): eng.step(dt)
def shot(n): eng.render(); pygame.image.save(eng.screen, f"{OUT}/{n}.png")

def battle_auto(max_steps=400, shots=None, prefer="fight"):
    """Drive a battle to completion with keyboard input only."""
    b = eng.find(StateId.BATTLE)
    for i in range(max_steps):
        run(0.05)
        b = eng.find(StateId.BATTLE)
        if not b: return True
        if b.end_timer is not None: continue
        if b.menu == "message": key(pygame.K_RETURN); key(pygame.K_RETURN)
        elif b.menu == "main": 
            if shots is not None and "main" not in shots: shots["main"] = 1; shot("10_battle_main")
            key(pygame.K_RETURN)
        elif b.menu == "fight":
            if shots is not None and "fight" not in shots: shots["fight"] = 1; shot("11_battle_fight")
            key(pygame.K_RETURN)
        elif b.menu == "switch":
            for _ in range(len(b.grid.buttons)): 
                if b.grid.current.enabled: break
                key(pygame.K_DOWN)
            key(pygame.K_RETURN)
        else: key(pygame.K_ESCAPE)
    return False

# ---- story flow to overworld
run(0.3); key(pygame.K_RETURN); run(0.6)
for _ in range(5): key(pygame.K_RETURN); key(pygame.K_RETURN); run(0.1)
run(0.6); key(pygame.K_RETURN); run(1.0)               # choose Florabot
for _ in range(6): key(pygame.K_RETURN); key(pygame.K_RETURN); run(0.1)
run(1.0)
assert battle_auto(shots={}), "rival battle did not finish"
run(1.0)
st = eng.state
print("after rival: party", [(m.name, m.level, m.hp, m.xp) for m in st.party], "beaten", st.rival_beaten)
ovs = eng.find(StateId.OVERWORLD); assert ovs and eng.top is ovs, [s.state_id for s in eng.scenes]
shot("12_overworld_start")

# ---- movement + collision
p = ovs.player
assert p.tile == (38, 5)
held["d"] = "right"; run(0.5)
print("tile after right (open grass x39 free?)", p.tile)
held["d"] = "left"; run(1.2)
print("after left", p.tile)
held["d"] = "down"; run(0.6); print("after down", p.tile)
# solid: walk into the house wall (38,4 is door; (37,4) is B)
p.place(37, 5, "up"); held["d"] = "up"; run(0.5); held["d"] = None
assert p.tile == (37, 5), f"walked through wall {p.tile}"
# NPC collision: Prof Venn at (20,7)
p.place(20, 6, "down"); held["d"] = "down"; run(0.5); held["d"] = None
assert p.tile == (20, 6), f"walked through NPC {p.tile}"
# talk to NPC, heals
st.party[0].hp = 3
key(pygame.K_RETURN); run(0.3); shot("13_dialogue")
while eng.find(StateId.DIALOGUE): key(pygame.K_RETURN); run(0.1)
assert st.party[0].hp == st.party[0].max_hp, "Venn did not heal"
# ---- doors: house
print("scenes before door:", [s.state_id.name for s in eng.scenes], eng.transitioning); p.place(38, 5, "up"); held["d"] = "up"; run(0.12)
held["d"] = None; run(0.8)
print("in building:", ovs.building and ovs.building.id, p.tile)
assert ovs.building and ovs.building.id == "player-house"
shot("14_house")
# walk out: exit at (5,9)/(6,9)
held["d"] = "down"; run(1.2); held["d"] = None; run(0.8)
print("exited ->", ovs.building, p.tile)
assert ovs.building is None and p.tile == (38, 5)

# ---- interiors screenshots
import worldmap as wm
for b in wm.BUILDINGS:
    if b.id in ("lab", "mart", "cush", "hall", "library"):
        ovs.building = b; ovs.map = ovs._get_map(b); ovs._load_npcs(); p.place(*b.interior.spawn, "up"); run(0.1)
        shot("20_int_" + b.id)
ovs.building = None; ovs.map = ovs._get_map(None); ovs._load_npcs(); p.place(38, 5, "down"); run(0.2)

# ---- shop
b = wm.BUILDINGS[4]
from menus import ShopScene, InventoryScene, DatabaseScene, ServiceScene
eng.push(ShopScene(b)); run(0.2); shot("30_shop")
c0 = st.credits; key(pygame.K_RETURN); assert st.credits < c0, "buy failed"
key(pygame.K_TAB); run(0.1); shot("31_shop_sell"); tag=eng.top.grid.current.tag; n=st.qty(tag); key(pygame.K_RETURN); assert st.qty(tag)==n-1, (tag,n)
key(pygame.K_ESCAPE); run(0.1); assert eng.top is ovs

# ---- pack
st.party[0].hp = 5
eng.push(InventoryScene()); run(0.2); shot("40_pack_party")
key(pygame.K_TAB); run(0.1); shot("41_pack_bag")
key(pygame.K_RETURN); run(0.1)                     # begin target for first consumable
assert eng.top.pending, "no pending item"
key(pygame.K_RETURN); run(0.2); shot("42_pack_after_use")
assert st.party[0].hp > 5
key(pygame.K_TAB); key(pygame.K_e); key(pygame.K_e); run(0.1)          # equipment tab
key(pygame.K_RETURN); key(pygame.K_RETURN); run(0.2); shot("43_pack_held")
print("held:", st.party[0].held_item)
key(pygame.K_ESCAPE); run(0.1); assert eng.top is ovs

# ---- database
from monsters import create_scimon
st.party.append(create_scimon("dewbit", 3))
eng.push(DatabaseScene()); run(0.1); key(pygame.K_DOWN); key(pygame.K_RETURN); run(0.1)
assert len(st.storage) == 1 and len(st.party) == 1 or len(st.storage)==1, (len(st.party), len(st.storage))
key(pygame.K_RIGHT); key(pygame.K_RETURN); run(0.1); assert len(st.storage) == 0
key(pygame.K_RETURN); shot("50_database"); key(pygame.K_ESCAPE)

# ---- wild battle + capture
random.seed(11); st.heal_party()
ovs.start_wild_battle("sporelet", 3); run(1.0)
assert eng.find(StateId.BATTLE)
bt = eng.find(StateId.BATTLE)
while bt.menu == "message": key(pygame.K_RETURN); run(0.1)
assert bt.menu == "main", bt.menu
key(pygame.K_DOWN); key(pygame.K_RETURN); run(0.1)       # CAPTURE (row 2)
bt = eng.find(StateId.BATTLE); print("menu now", bt.menu)
shot("60_capture_menu")
# choose standard module repeatedly until caught
for _ in range(60):
    bt = eng.find(StateId.BATTLE)
    if not bt: break
    if bt.menu == "main":
        bt.grid.idx = 2; key(pygame.K_RETURN)
    elif bt.menu == "capture": key(pygame.K_RETURN)
    elif bt.menu == "message": key(pygame.K_RETURN); key(pygame.K_RETURN)
    elif bt.menu == "switch": key(pygame.K_RETURN)
    run(0.1)
run(1.0)
print("captured:", sorted(st.captured), "party", [m.name for m in st.party], "storage", [m.name for m in st.storage])
print("ALL OK")
