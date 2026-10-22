"""Find cells to map.  Renders an atlas with (col,row) labels, or reports what every role in tileset_map.py resolved to.
    python tools/atlas_inspector.py                  # primary atlas -> atlas_grid.png
    python tools/atlas_inspector.py secondary        # global.png (pixel-rect addressed) with a 16px grid
    python tools/atlas_inspector.py --report         # role -> source (primary / secondary / legacy / MISSING)"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((64, 64))
import tileset

if "--report" in sys.argv:
    for role, src in tileset.report().items():
        print(f"{role:22s} {src}")
    sys.exit()

pack = "secondary" if "secondary" in sys.argv else "primary"
a = tileset.atlas(pack)
if a is None:
    sys.exit(f"{pack} atlas not installed (see settings.py)")
Z, M = 4, 28
w, h = a.sheet.get_size()
out = pygame.Surface((w * Z + M, h * Z + M)); out.fill((32, 32, 44))
out.blit(pygame.transform.scale(a.sheet, (w * Z, h * Z)), (M, M))
font = pygame.font.Font(None, 16)
for c in range(a.cols):
    pygame.draw.line(out, (90, 90, 120), (M + c * a.grid * Z, M), (M + c * a.grid * Z, out.get_height()))
    out.blit(font.render(str(c), True, (255, 255, 0)), (M + c * a.grid * Z + 2, 6))
for r in range(a.rows):
    pygame.draw.line(out, (90, 90, 120), (M, M + r * a.grid * Z), (out.get_width(), M + r * a.grid * Z))
    out.blit(font.render(str(r), True, (0, 255, 255)), (4, M + r * a.grid * Z + 2))
pygame.image.save(out, "atlas_grid.png")
print("wrote atlas_grid.png", out.get_size())
