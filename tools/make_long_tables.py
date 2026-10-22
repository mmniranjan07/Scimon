"""Generate the long / large Sci-Database counter tables (assets/interiors/x_table_long.png, x_table_big.png).

Cush and the supply mart used to butt two `m_counter` sprites together (six small drawer tables with visible
seams) and the gym ring stacked three of them vertically.  These replacements are drawn from scratch in the
same Modern Interiors style -- same wood / navy palette (sampled from the pack's counter), same drawer and
plank row structure -- but as ONE seamless piece.  Run:  python tools/make_long_tables.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame

pygame.init()

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "interiors")

# Palette sampled from the Modern Interiors counter crop M(0, 917, 48, 20).
NAVY = (58, 58, 80)        # outline / counter body
NAVY2 = (70, 70, 94)       # softer outline
FOOT = (107, 80, 82)       # dark foot / handle shade
WOOD = (199, 140, 89)      # plank base
WOOD_D = (196, 130, 83)    # plank grain
WOOD_L = (218, 164, 99)    # plank highlight / bevel light
WOOD_HL = (224, 184, 112)  # plank top sheen
MID = (202, 136, 84)       # drawer face
DK = (181, 117, 77)        # drawer frame / shade
DK2 = (168, 95, 70)        # drawer frame dark
RED = (171, 74, 54)        # feet
PAPER = (222, 236, 244)    # pinned note
PAPER_D = (167, 151, 150)  # note shading
INK = (58, 58, 80)         # note scribbles


def plank(s, x, y, w):
    """Countertop: navy top edge, wood sheen + vertical grain, bevelled front edge, dashed shadow below."""
    h = s.get_height()
    for i in range(w):
        xx = x + i
        end = i == 0 or i == w - 1
        s.set_at((xx, y), NAVY if not end else NAVY)   # top edge, corners rounded below
        for yy in range(y + 1, y + 7):
            grain = (i % 3 == 1)
            col = WOOD_D if grain else WOOD
            if yy == y + 1 and not grain:
                col = WOOD_HL
            elif yy == y + 1 and grain:
                col = WOOD_L
            s.set_at((xx, yy), col)
        s.set_at((xx, y + 7), WOOD_L if i % 4 < 2 else DK)          # bevel
        s.set_at((xx, y + 8), FOOT if i % 2 == 0 else NAVY)         # dashed shadow
    s.set_at((x, y), (0, 0, 0, 0))                                  # rounded corners
    s.set_at((x + w - 1, y), (0, 0, 0, 0))
    for yy in range(y + 1, y + 8):
        s.set_at((x, yy), NAVY)                                     # solid end caps
        s.set_at((x + w - 1, yy), NAVY)


def drawer(s, x, y, paper=False):
    """One 14x8 drawer front: dark frame, wood face, handle or pinned note."""
    for i in range(14):
        for j in range(8):
            edge = i in (0, 13) or j in (0, 7)
            col = DK2 if edge else MID
            if j == 6 and not edge:
                col = DK
            s.set_at((x + i, y + j), col)
    if paper:
        for i in range(7):
            for j in range(4):
                col = PAPER if j < 3 or i < 5 else PAPER_D
                s.set_at((x + 3 + i, y + 2 + j), col)
        for i in (4, 6):
            s.set_at((x + i, y + 3), INK)
    else:
        for i in range(5):
            s.set_at((x + 4 + i, y + 2), FOOT)
            s.set_at((x + 4 + i, y + 3), NAVY2)


def base(s, y, w, feet, blobs):
    """Bottom edge, red-brown feet and grey floor-contact shadows."""
    h = s.get_height()
    for i in range(w):
        s.set_at((x := i, y), NAVY)
        s.set_at((x, y + 1), (0, 0, 0, 0))
    for fx in feet:
        for i in range(3):
            s.set_at((fx + i, y), RED)
            s.set_at((fx + i, y + 1), RED)
    for bx in blobs:
        for i in range(6):
            s.set_at((bx + i, y + 1), (167, 151, 150))


def make_long():
    """96x20: one six-drawer counter table (replaces two butted m_counter sprites)."""
    s = pygame.Surface((96, 20), pygame.SRCALPHA)
    plank(s, 0, 0, 96)
    for i in range(6):
        drawer(s, 1 + i * 16, 10, paper=i % 3 == 0)
    base(s, 18, 96, feet=(2, 30, 62, 91), blobs=(13, 45, 77))
    return s


def make_big():
    """48x60: one large platform table, three fused counter tiers (replaces the gym's stacked trio)."""
    s = pygame.Surface((48, 60), pygame.SRCALPHA)
    plank(s, 0, 0, 48)

    def band(y):                                        # drawer row + bevel + navy rail below it
        for i in range(2, 46):
            s.set_at((i, y), FOOT if i % 2 == 0 else NAVY)
        for d in range(3):
            drawer(s, 1 + d * 16, y + 1, paper=False)
        for i in range(1, 47):
            s.set_at((i, y + 9), WOOD_L if i % 4 < 2 else DK)
            s.set_at((i, y + 10), NAVY)

    def shelf(y):                                       # fused mini-plank between tiers
        for i in range(1, 47):
            s.set_at((i, y), NAVY)
            for j in range(1, 5):
                s.set_at((i, y + j), WOOD_D if i % 3 == 1 else WOOD)
            s.set_at((i, y + 5), WOOD_L if i % 4 < 2 else DK)
        s.set_at((0, y + 1), NAVY)
        s.set_at((47, y + 1), NAVY)

    for i in range(1, 47):
        s.set_at((i, 9), FOOT if i % 2 == 0 else NAVY)
    for d in range(3):
        drawer(s, 1 + d * 16, 10, paper=d == 0)
    for i in range(1, 47):
        s.set_at((i, 19), WOOD_L if i % 4 < 2 else DK)
        s.set_at((i, 20), NAVY)
    shelf(21)
    band(27)
    shelf(39)
    for i in range(1, 47):
        s.set_at((i, 45), FOOT if i % 2 == 0 else NAVY)
    for d in range(3):
        drawer(s, 1 + d * 16, 46, paper=False)
    for i in range(48):
        for j in (54, 55, 56, 57):
            s.set_at((i, j), NAVY)
        s.set_at((i, 58), (0, 0, 0, 0))
        s.set_at((i, 59), (0, 0, 0, 0))
    for fx in (2, 22, 43):
        for i in range(3):
            s.set_at((fx + i, 57), RED)
            s.set_at((fx + i, 58), RED)
    for bx in (12, 30):
        for i in range(6):
            s.set_at((bx + i, 58), (167, 151, 150))
    return s


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, surf in (("x_table_long", make_long()), ("x_table_big", make_big())):
        pygame.image.save(surf, os.path.join(OUT, f"{name}.png"))
        print("wrote", name, surf.get_size())
