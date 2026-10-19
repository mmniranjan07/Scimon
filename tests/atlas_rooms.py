"""Atlas / tile map / animation / collision tests (headless).  Usage: python tests/atlas_rooms.py"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))
import assets, animation, atlas, tileset, interiors, layered_room, worldmap as wm
from map import TileMap
from settings import TILE
from sprites import Player
from state import GameState

# --- atlas slicing: every cell of every installed atlas is uniform; 16/32/48 share one layout
for g, rel in ((16, "sprites/interiors/atlas_16x.png"), (32, "sprites/interiors/atlas_32x.png")):
    a = atlas.Atlas.try_load(rel, g)
    assert a and (a.cols, a.rows) == (48, 16), rel
    assert all(s.get_size() == (g, g) for _, _, s in a.cells())
try:
    a.cell(48, 0); raise SystemExit("out-of-range cell was accepted")
except IndexError:
    pass

# --- path safety
for bad in ("../settings.py", "/etc/passwd", "interiors/../../main.py", "scimon/x.txt", "a\x00.png", ""):
    try:
        assets.safe_path(bad); raise SystemExit(f"accepted {bad!r}")
    except ValueError:
        pass

# --- every role resolves to real art (no magenta placeholders) and the lab uses the packs
rep = tileset.report()
assert "MISSING" not in rep.values(), {k: v for k, v in rep.items() if v == "MISSING"}
assert rep["floor_grid"].startswith("primary") and rep["specimen_jars"].startswith("secondary")
assert rep["m_bookcase_a"].startswith("modern") and rep["m_wall_yellow_cap"].startswith("builder"), "Modern Interiors not loading"
assert rep["bed_blue"].startswith("legacy"), "the bed must stay the project sprite"
assert rep["server_rack"].startswith("legacy")          # no sci-fi rack in the packs -> project art

# --- collision derived from placements: racks, pod, terminals, cores, chest, creature are all solid
rows = interiors.ROWS["lab"]
assert all(len(r) == 12 for r in rows) and len(rows) == 10
for name, x, y in (("server_rack", 1, 3), ("containment_pod", 4, 3), ("terminal_big", 5, 3),
                   ("plasma_core", 1, 5), ("chest_steel", 10, 8)):
    assert rows[y][x] in "#@", (name, rows[y])
assert rows[3][5] == "@" and rows[3][7] == "@" and rows[9][5] == "E" and rows[4][9] == "#"   # creature tile
assert all(c == "#" for c in rows[0]) and rows[5][0] == "#" and rows[5][11] == "#"

# --- town interiors (Modern Interiors art): gameplay-critical tiles are unchanged
house = interiors.ROWS["house"]
assert all(house[y][x] == "#" for y in (6, 7) for x in (1, 2, 3)), "bed footprint moved"           # the bed
assert interiors.LAYERED["house"].things[[t.name for t in interiors.LAYERED["house"].things].index("bed_blue")].x == 1
for room, cells in (("hall", [(5, 5), (6, 5), (7, 5)]), ("cush", [(3, 5), (5, 5), (6, 5), (8, 5)]),
                    ("library", [(4, 5), (5, 5), (6, 5)]), ("farms-a", [(4, 5), (5, 5), (6, 5)]),
                    ("mart", [(2, 7), (4, 7), (5, 7), (7, 7)])):
    assert all(interiors.ROWS[room][y][x] == "C" for x, y in cells), (room, "counter tiles moved")
assert interiors.ROWS["cush"][3][8:11] == "@@@", "Cush's terminal"
for b in wm.BUILDINGS:                                                  # NPC talk tiles stay open, rooms stay connected
    wm.validate() if b is wm.BUILDINGS[0] else None
    for n in b.interior.npcs:
        assert b.interior.rows[n["y"]][n["x"]] == ".", (b.id, n["id"])

# --- the player cannot walk through any of it (real TileMap.blocked on the real lab)
lab = next(b for b in wm.BUILDINGS if b.id == "lab")
m = TileMap.interior(lab)
for x, y in ((1, 3), (5, 3), (1, 5), (10, 8), (9, 4), (0, 5), (11, 5)):
    assert m.blocked(x, y), (x, y)
assert not m.blocked(5, 8) and not m.blocked(6, 6)
p = Player(*lab.interior.spawn); p.place(1, 6, "up")        # stand under a core: stepping up must be refused
dx = (1, 5)
assert m.blocked(p.tile[0], p.tile[1] - 1)

# --- animator: one-shot chains into the next state with exact timing; ping-pong; loop
f = [pygame.Surface((1, 1)) for _ in range(4)]
a = animation.Animation(f, fps=10, loop=False)
assert a.index_at(0) == 0 and a.index_at(0.25) == 2 and a.index_at(9) == 3 and a.finished(0.4)
pp = animation.Animation(f, fps=10, pingpong=True)
assert [pp.index_at(i / 10) for i in range(8)] == [0, 1, 2, 3, 2, 1, 0, 1]
an = animation.Animator({"closed": animation.Animation(f[:1]), "opening": a, "open": animation.Animation(f[3:])},
                        "closed", {"opening": "open"})
an.play("opening"); an.update(0.5)
assert an.state == "open" and abs(an.t - 0.1) < 1e-9

# --- chest: interact once -> loot + remembered; second time empty; sync restores 'open' on a fresh room
st = GameState(); chest = m.interactable_at(10, 8); assert chest
before = st.qty("repaircell")
lines = chest.interact(st)
assert st.qty("repaircell") == before + 2 and "lab:lab-case" in st.opened_chests and len(lines) == 2
assert chest.interact(st) == ["The case is empty."] and st.qty("repaircell") == before + 2
for _ in range(60): m.update(1 / 30)
assert chest.animator.state == "open"
m2 = TileMap.interior(lab); m2.sync_state(st)
assert m2.interactable_at(10, 8).animator.state == "open"

# --- animated props really change frame over time
core = next(pr for pr in m.props if getattr(pr, "key", "").startswith("lab:plasma_core@"))
imgs = {id(core.animator.frame)}
for _ in range(30): m.update(1 / 30); imgs.add(id(core.animator.frame))
assert len(imgs) > 3

# --- packs missing: nothing crashes, roles fall back to project art
saved = dict(tileset._atlases)
tileset.reset(); tileset._atlases.update(primary=None, secondary=None, modern=None, builder=None)
rep2 = tileset.report()
assert not any(v.startswith(("primary", "secondary", "modern", "builder")) for v in rep2.values())
for b in wm.BUILDINGS:                                       # every room still builds from project art alone
    TileMap.interior(b).update(0.1)
tileset.reset()
print("OK atlas/tilemap/animation/collision; roles by source:",
      {k: sum(v.startswith(k) for v in rep.values()) for k in ("primary", "secondary", "modern", "builder", "legacy")})
