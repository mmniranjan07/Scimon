"""Item icons: 16x16 pixel-art sprites for every disc, module and item in the catalogue.

Run:  python tools/item_icons.py          # writes assets/items/<id>.png + a preview sheet
Every icon shares one language: 1px ink outline, the item's own colour, a light top-left shine.
"""
import os
import pygame

INK = (42, 42, 51)
WHITE = (250, 246, 226)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "items")

pygame.init()


def canvas():
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    return s


def px(s, color, x, y, w=1, h=1):
    s.fill(color, (x, y, w, h))


def outline(s, x, y, w, h):
    """1px ink frame around the (x, y, w, h) box."""
    px(s, INK, x, y, w, 1)
    px(s, INK, x, y + h - 1, w, 1)
    px(s, INK, x, y, 1, h)
    px(s, INK, x + w - 1, y, 1, h)


def shine(s, x, y):
    px(s, WHITE, x, y, 1, 1)
    px(s, WHITE, x + 1, y, 1, 1)
    px(s, WHITE, x, y + 1, 1, 1)


def capsule(col, dark, band=None):
    """The containment-module body: a rounded 10x11 capsule with a dark foot band."""
    s = canvas()
    px(s, col, 4, 4, 8, 8)
    px(s, col, 3, 5, 10, 6)
    px(s, INK, 3, 4, 10, 1); px(s, INK, 3, 10, 10, 1)
    px(s, INK, 3, 4, 1, 7); px(s, INK, 12, 4, 1, 7)
    px(s, dark, 4, 10, 8, 1)
    px(s, dark, 5, 11, 6, 1)
    shine(s, 4, 5)
    if band:
        px(s, band, 3, 7, 10, 2)
        px(s, INK, 3, 7, 10, 1)
    return s


def cross(s, col, cx, cy):
    px(s, col, cx - 1, cy - 3, 3, 7)
    px(s, col, cx - 3, cy - 1, 7, 3)


def droplet(s, col, cx, cy):
    px(s, col, cx, cy - 3, 1, 1)
    px(s, col, cx - 1, cy - 2, 3, 1)
    px(s, col, cx - 2, cy - 1, 5, 2)
    px(s, col, cx - 1, cy + 1, 3, 1)


def leaf(s, col, cx, cy, w=4, h=5):
    for i in range(h):
        ww = max(1, w - abs(i - h // 2))
        px(s, col, cx - ww // 2, cy + i, ww, 1)
    px(s, INK, cx, cy, 1, h)


def card(col, dark, emblem):
    """The town passes: a credit-card with a stripe and an emblem."""
    s = canvas()
    px(s, col, 2, 4, 12, 9)
    outline(s, 2, 4, 12, 9)
    px(s, dark, 3, 6, 10, 2)
    px(s, WHITE, 3, 6, 10, 1)
    emblem(s, 8, 10)
    shine(s, 3, 5)
    return s


def disc(col, light, emblem):
    s = canvas()
    r = 6
    cx = cy = 8
    for y in range(16):
        for x in range(16):
            d2 = (x - cx + 0.5) ** 2 + (y - cy + 0.5) ** 2
            if r * r - 1 <= d2 <= r * r + 2:
                px(s, INK, x, y)
            elif d2 <= r * r - 1 and d2 >= 4:
                px(s, col, x, y)
    px(s, INK, 7, 7, 3, 3)
    px(s, (230, 230, 224), 8, 8, 1, 1)
    px(s, light, 4, 5, 2, 1); px(s, light, 3, 6, 1, 2)
    emblem(s, 8, 12)
    return s


def star(s, cx, cy, col=WHITE):
    px(s, col, cx, cy - 2, 1, 5)
    px(s, col, cx - 2, cy, 5, 1)
    px(s, col, cx - 1, cy - 1, 3, 3)


# --------------------------------------------------------------------------- the catalogue
def repaircell():
    s = canvas()
    px(s, (233, 90, 110), 4, 4, 8, 9)
    outline(s, 4, 4, 8, 9)
    px(s, (150, 40, 60), 4, 12, 8, 1)
    px(s, (150, 40, 60), 6, 2, 4, 2)
    px(s, INK, 5, 2, 6, 1)
    cross(s, WHITE, 8, 8)
    shine(s, 5, 5)
    return s


def nanorepair():
    s = canvas()
    px(s, (47, 191, 174), 4, 4, 8, 9)
    outline(s, 4, 4, 8, 9)
    px(s, (24, 110, 100), 4, 12, 8, 1)
    px(s, (200, 210, 208), 6, 2, 4, 2)
    px(s, INK, 5, 2, 6, 1)
    cross(s, WHITE, 8, 8)
    px(s, (24, 110, 100), 6, 6, 4, 1)
    shine(s, 5, 5)
    return s


def stabilizer():
    s = canvas()
    px(s, (91, 91, 214), 4, 4, 8, 9)
    outline(s, 4, 4, 8, 9)
    px(s, (52, 52, 130), 4, 12, 8, 1)
    px(s, (200, 210, 208), 6, 2, 4, 2)
    px(s, INK, 5, 2, 6, 1)
    px(s, WHITE, 8, 5, 2, 3)          # the bolt
    px(s, WHITE, 6, 8, 3, 2)
    px(s, WHITE, 8, 10, 2, 2)
    shine(s, 5, 5)
    return s


def standard():
    return capsule((168, 172, 178), (110, 114, 120), band=(209, 90, 52))


def cryo():
    s = capsule((127, 208, 224), (70, 140, 156))
    px(s, WHITE, 7, 6, 3, 1); px(s, WHITE, 8, 5, 1, 5)
    px(s, WHITE, 6, 6, 1, 1); px(s, WHITE, 10, 6, 1, 1)
    px(s, WHITE, 6, 9, 1, 1); px(s, WHITE, 10, 9, 1, 1)
    return s


def magnetic():
    s = capsule((154, 164, 173), (100, 106, 112))
    px(s, (209, 69, 60), 6, 5, 2, 4)
    px(s, (60, 90, 200), 9, 5, 2, 4)
    px(s, WHITE, 6, 9, 5, 1)
    return s


def bio():
    s = capsule((87, 176, 111), (48, 110, 66))
    leaf(s, (250, 246, 226), 8, 5, 4, 6)
    return s


def thermalcore():
    s = canvas()
    px(s, (224, 89, 47), 4, 6, 8, 7)
    px(s, (224, 89, 47), 3, 7, 10, 5)
    outline(s, 3, 6, 10, 7)
    px(s, (250, 210, 120), 6, 8, 4, 3)
    px(s, (250, 240, 170), 7, 9, 2, 1)
    px(s, (224, 89, 47), 6, 3, 4, 2)      # the flame tip
    px(s, (250, 210, 120), 7, 2, 2, 2)
    px(s, INK, 6, 2, 4, 1)
    shine(s, 4, 7)
    return s


def hydrocell():
    s = canvas()
    px(s, (61, 132, 198), 5, 4, 6, 9)
    px(s, (61, 132, 198), 4, 5, 8, 7)
    outline(s, 4, 4, 8, 9)
    px(s, (40, 84, 130), 6, 2, 4, 2)
    px(s, INK, 5, 2, 6, 1)
    droplet(s, WHITE, 8, 8)
    shine(s, 5, 5)
    return s


def biotrellis():
    s = canvas()
    px(s, (122, 90, 54), 3, 4, 10, 9)
    outline(s, 3, 4, 10, 9)
    for x in (6, 9, 12):
        px(s, (90, 66, 40), x, 4, 1, 9)
    px(s, (90, 66, 40), 3, 8, 10, 1)
    leaf(s, (122, 200, 96), 5, 5, 3, 3)
    leaf(s, (122, 200, 96), 11, 10, 3, 3)
    return s


def plating():
    s = canvas()
    px(s, (154, 164, 173), 3, 3, 10, 4)
    outline(s, 3, 3, 10, 4)
    px(s, (122, 130, 138), 4, 7, 8, 4)
    outline(s, 4, 7, 8, 4)
    px(s, (96, 102, 110), 5, 11, 6, 2)
    for x, y in ((5, 5), (10, 5), (6, 9)):
        px(s, WHITE, x, y, 1, 1)
    return s


def scanner():
    s = canvas()
    px(s, (47, 191, 174), 3, 4, 10, 9)
    outline(s, 3, 4, 10, 9)
    px(s, (24, 60, 56), 5, 6, 6, 4)       # the screen
    px(s, (150, 250, 220), 6, 7, 4, 2)
    px(s, (232, 195, 58), 11, 6, 1, 2)    # the trigger light
    px(s, (200, 210, 208), 5, 11, 6, 1)
    px(s, (250, 240, 170), 12, 2, 1, 2)   # the antenna tip
    px(s, INK, 12, 4, 1, 2)
    return s


def townpass():
    return card((232, 195, 58), (196, 150, 24), lambda s, cx, cy: star(s, cx, cy))


def epipass():
    return card((87, 176, 111), (52, 120, 70), lambda s, cx, cy: leaf(s, (250, 246, 226), cx, cy - 2, 4, 4))


def verdantdisc():
    return disc((90, 166, 63), (170, 220, 150), lambda s, cx, cy: leaf(s, (250, 246, 226), cx, cy - 3, 3, 3))


ICONS = {
    "repaircell": repaircell, "nanorepair": nanorepair, "stabilizer": stabilizer,
    "standard": standard, "cryo": cryo, "magnetic": magnetic, "bio": bio,
    "thermalcore": thermalcore, "hydrocell": hydrocell, "biotrellis": biotrellis, "plating": plating,
    "scanner": scanner, "townpass": townpass, "epipass": epipass, "verdantdisc": verdantdisc,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for item_id, fn in ICONS.items():
        pygame.image.save(fn(), os.path.join(OUT, f"{item_id}.png"))
    sheet = pygame.Surface((len(ICONS) * 56, 64), pygame.SRCALPHA)
    sheet.fill((240, 236, 214))
    for i, (item_id, fn) in enumerate(ICONS.items()):
        icon = fn()
        sheet.blit(pygame.transform.scale_by(icon, 3), (i * 56 + 4, 6))
        f = pygame.font.Font(None, 16)
        lab = f.render(item_id, True, (40, 40, 40))
        sheet.blit(lab, (i * 56 + 28 - lab.get_width() // 2, 56))
    pygame.image.save(sheet, os.path.join(OUT, "_sheet.png"))
    print("wrote", len(ICONS), "icons to", OUT)


if __name__ == "__main__":
    main()
