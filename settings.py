"""Global constants and the shared colour palette (ported from V34's globals.css theme)."""
import os

W, H = 960, 640            # logical resolution; the window scales this (SCALED flag)
FPS = 60
TILE = 48                  # world tile size in logical pixels (V34 art is authored at 16 px, x3)
PX = TILE // 16            # one "art pixel" in world space

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

# Movement: V34 moves 2 px/frame at 60 fps on a 16 px tile = 7.5 tiles/s. A touch slower reads better at 48 px.
WALK_TILES_PER_SEC = 6.5
ENCOUNTER_CHANCE = 0.12    # per step in tall grass (V34)
FADE_TIME = 0.18           # seconds per half of a map/scene transition


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


# --- SCI-MON theme tokens -------------------------------------------------------------
CREAM = hexc("#f3efd6")
CREAM_2 = hexc("#e6e0bf")
SHADE = hexc("#b8b48f")
INK = hexc("#2a2a33")
TEAL = hexc("#5a8a86")
TEAL_2 = hexc("#6f9c98")
TEAL_DARK = hexc("#3d6763")
ORANGE = hexc("#d1552f")
OLIVE = hexc("#b2b06e")
OLIVE_DARK = hexc("#8e8c52")
HP_GREEN = hexc("#78c850")
HP_YELLOW = hexc("#f0c020")
HP_RED = hexc("#e04838")
EXP_BLUE = hexc("#38a8e0")
STAB_BLUE = hexc("#5b8fd6")
VOID = hexc("#0a0c10")
WHITE = (255, 255, 255)
