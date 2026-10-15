"""Render every interior to PNGs (normal + F3 hitbox view) for a quick visual check.  Usage: python tools/preview_rooms.py [outdir]"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine
import overworld as ow, worldmap as wm
from scenes import TitleScene

out = sys.argv[1] if len(sys.argv) > 1 else "previews"
os.makedirs(out, exist_ok=True)
eng = Engine(); eng.push(TitleScene())
scene = ow.OverworldScene(); eng.push(scene)
ow.OverworldScene._held_dir = lambda self: None
for b in wm.BUILDINGS:
    scene.building = b; scene.map = scene._get_map(b); scene._load_npcs(); scene.player.place(*b.interior.spawn, "up")
    for dbg in (False, True):
        eng.debug = dbg
        for _ in range(5): scene.update(0.05)
        scene.draw(eng.screen)
        pygame.image.save(eng.screen, f"{out}/{b.id}{'_hitbox' if dbg else ''}.png")
scene.building = None; scene.map = scene._get_map(None); scene._load_npcs(); scene.player.place(*wm.PLAYER_START, "down")
eng.debug = False; scene.update(0.05); scene.draw(eng.screen); pygame.image.save(eng.screen, f"{out}/overworld.png")
print("saved to", out)
