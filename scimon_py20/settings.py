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


# --- SPRITE PACKS: every raw sprite path lives here (paths are relative to ASSETS) ------------------------------
# To swap art, change a path or a grid size here -- no game logic references a file name directly.
# Packs are used in this order for every tile (see tileset_map.py): PRIMARY -> SECONDARY -> project art (legacy).
INTERIOR_DIR = "sprites/interiors"

# PRIMARY: SuperRetroWorld interior pack. All three atlases share one cell layout, so the (col, row) mapping in
# tileset_map.py is valid for any of them; PRIMARY_GRID only decides which file is cut and at what scale.
#   16 -> drawn 3.0x (integer, same pixel size as the characters and props)   <- recommended
#   32 -> drawn 1.5x (non-integer: uneven pixels)       48 -> drawn 1.0x (finer pixels than the rest of the game)
PRIMARY_GRID = 16
PRIMARY_ATLASES = {
    16: f"{INTERIOR_DIR}/atlas_16x.png",
    32: f"{INTERIOR_DIR}/atlas_32x.png",
    48: f"{INTERIOR_DIR}/atlas_48x.png",
}
PRIMARY_ANIM_DIR = f"{INTERIOR_DIR}/animation"      # chest_00N.png / fire.png / fire2.png: 6 frames of 16x32

# SECONDARY: Cute RPG Interiors (DEMO) -- generic, non-tech decor only. Its props are not cell aligned, so
# tileset_map.py addresses them by pixel rectangle. CREDIT REQUIRED by its licence: Heather Wait (RPGCookie).
SECONDARY_ATLAS = f"{INTERIOR_DIR}/global.png"
SECONDARY_GRID = 16

# TERTIARY: Modern Interiors (free) by LimeZu -- furniture sheet (addressed by exact pixel rect) and Room Builder sheet
# (walls / floors, addressed by cell).  Used for the town's houses, shops, hall, library and farm market.
MODERN_INTERIORS = f"{INTERIOR_DIR}/modern/Interiors_free_16x16.png"
MODERN_ROOM_BUILDER = f"{INTERIOR_DIR}/modern/Room_Builder_free_16x16.png"
MODERN_GRID = 16

# Characters: MPWSP01 overworld sheets (assets/mpw/ow/ow1..ow10.png, 128x128 = 4x4 frames of 32x32; rows: down, left, right, up).
# Who plays whom is MPW_CAST in sprites.py (animation.MpwSheetAnimator reads the sheets).  The legacy 16x32 layout below is
# only used by animation.SheetAnimator, which the game no longer instantiates.
CHARACTERS_DIR = "characters"
# Size of the MPW character sprites in the world: screen pixels per art pixel.  3 (= PX) was the original, very large look;
# 2 draws every character at two thirds of that (a 32x32 frame becomes 64x64).  Keep it an integer so the pixels stay crisp.
CHAR_PX = 2
PLAYER_SHEET = None
SHEET_LAYOUT = dict(
    frame=(16, 32),
    frames_per_dir=6,
    dir_col={"right": 0, "up": 6, "left": 12, "down": 18},
    rows={"idle": 1, "walk": 2},
    fps={"idle": 4.0, "walk": 16.0},
)

# Overworld Sci-Mon: static species art + procedural hover. A species can instead name an idle sheet here:
#   "sparkit": dict(sheet="sprites/creatures/sparkit_idle.png", frame=(96, 96), frames=4, fps=6)
CREATURE_SHEETS = {}
CREATURE_HOVER = dict(amplitude=0.07, period=2.4)     # amplitude in sprite heights, period in seconds

# Asset safety limits (enforced in assets.py)
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_IMAGE_SIDE = 8192
ASSET_EXTENSIONS = (".png", ".ttf")


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
