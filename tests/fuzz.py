import faulthandler; faulthandler.dump_traceback_later(25, exit=True)
"""Fuzz + performance: random inputs and teleports for many simulated minutes; must never raise."""
import os, sys, random, time
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
from scenes import TitleScene
import overworld as ow, worldmap as wm
from monsters import create_scimon
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
eng = Engine(); eng.push(TitleScene())
held = {"d": None}
ow.OverworldScene._held_dir = lambda self: held["d"]
KEYS = [pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
        pygame.K_TAB, pygame.K_i, pygame.K_x, pygame.K_q, pygame.K_e, pygame.K_t, pygame.K_u, pygame.K_j, pygame.K_r, pygame.K_m]
frames, t0, draw_t = 0, time.time(), 0.0
for step in range(60 * 40):                      # forty simulated seconds at 60 fps
    dt = random.choice([1/60, 1/60, 1/30, 1/144, 0.05])  # varying frame times: movement must stay sane
    if random.random() < 0.05: eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=random.choice(KEYS), mod=0, unicode=""))
    if random.random() < 0.01: held["d"] = random.choice([None, "up", "down", "left", "right"])
    if random.random() < 0.01: eng.dispatch(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(random.randrange(960), random.randrange(640))))
    eng.step(dt)
    t = time.time(); eng.render(); draw_t += time.time() - t; frames += 1
    top = eng.top
    if isinstance(top, ow.OverworldScene) and random.random() < 0.002:   # teleport around, incl. interiors
        b = random.choice([None] + wm.BUILDINGS); top.building = b; top.map = top._get_map(b); top._load_npcs()
        top.player.place(*(b.interior.spawn if b else wm.PLAYER_START), "down")
    if not eng.scenes: eng.push(TitleScene())
    st = eng.state
    if st.party:
        for m in st.party: assert 0 <= m.hp <= m.max_hp and 0 <= m.stability <= m.max_stability, m
        assert len(st.party) <= 6
    if isinstance(top, ow.OverworldScene):
        assert not top.map.blocked(*top.player.tile) or top.map.tile_at(*top.player.tile) in "DE" , (top.player.tile)
print(f"OK {frames} frames, avg render {1000*draw_t/frames:.2f} ms, scenes now {[s.state_id.name for s in eng.scenes]}, "
      f"dex {sorted(eng.state.captured)}")
