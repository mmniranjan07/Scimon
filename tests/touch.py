"""Headless test of the touch layer: layouts, D-pad, buttons, tap routing, rendering in every layout."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
import touch
from engine import Engine, StateId
from scenes import TitleScene

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/touch_shots"
os.makedirs(OUT, exist_ok=True)
for name, size in (("side", "844x390"), ("stack", "390x844"), ("overlay", "1024x768")):
    os.environ["SCIMON_TOUCH"], os.environ["SCIMON_TOUCH_SIZE"] = "1", size
    eng = Engine(); eng.push(TitleScene())
    assert eng.layout.mode == name, (eng.layout, name)
    sw, sh = eng.screen.get_size()
    def finger(t, fid, x, y): eng.dispatch(pygame.event.Event(t, finger_id=fid, x=x / sw, y=y / sh, dx=0, dy=0))
    for _ in range(30): eng.step(1 / 60)
    cx, cy, r = eng.controls.geo["dpad"]
    finger(pygame.FINGERDOWN, 1, cx + r * .6, cy); assert touch.held_dir() == "right"
    finger(pygame.FINGERUP, 1, cx, cy); assert touch.held_dir() is None
    ax, ay, _ = eng.controls.geo["a"]
    finger(pygame.FINGERDOWN, 2, ax, ay); finger(pygame.FINGERUP, 2, ax, ay)
    for _ in range(60): eng.step(1 / 60)
    eng.render(); pygame.image.save(eng.screen, f"{OUT}/{name}.png")
    print("OK", name, eng.layout.size, eng.top.state_id.name)
