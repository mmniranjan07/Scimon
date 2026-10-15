"""Extra interior furniture/decor in the same style as the generated furniture set (native 16 px-per-tile art).

Writes assets/interiors/x_*.png.  Each prop suits one of the buildings' purposes (lab gear, repair tools, farm stock...).
"""
import os

from pix import *

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(HERE, "..", "assets", "interiors")
LINE = rgb("#3a2a36")
WOOD, WOOD_L, WOOD_D = rgb("#a87848"), rgb("#c9955c"), rgb("#7a5230")
METAL, METAL_L, METAL_D = rgb("#8e9aa6"), rgb("#c3ccd4"), rgb("#5d6a76")


def out(im):
    return outline(im, LINE)


def server_rack():
    im = new(16, 46)
    p = Pen(im)
    p.rect(1, 1, 14, 44, rgb("#2e3742"))
    p.rect(1, 1, 14, 2, rgb("#4a5766"))
    for i in range(7):
        y = 4 + i * 6
        p.rect(2, y, 12, 5, rgb("#3d4856"))
        p.hline(2, y, 12, rgb("#56667a"))
        p.rect(3, y + 2, 5, 1, rgb("#222a33"))
        p.dot(10, y + 2, rgb("#5df29a") if i % 3 else rgb("#ffb347"))
        p.dot(12, y + 2, rgb("#5ad7ff") if i % 2 else rgb("#5df29a"))
    p.rect(1, 43, 14, 2, rgb("#222a33"))
    return out(im)


def microscope():
    im = new(14, 16)
    p = Pen(im)
    p.rect(2, 13, 10, 2, METAL_D)
    p.rect(8, 3, 3, 11, METAL)
    p.rect(3, 2, 3, 8, METAL_L)
    p.line(5, 9, 9, 5, METAL_L)
    p.rect(2, 10, 6, 1, rgb("#2a2a33"))
    p.dot(4, 1, rgb("#2a2a33"))
    p.rect(4, 11, 5, 1, rgb("#bfe9ff"))
    return out(im)


def specimen_tank():
    im = new(30, 44)
    p = Pen(im)
    p.rect(1, 36, 28, 7, rgb("#4a5766"))
    p.rect(1, 36, 28, 2, rgb("#6a7a8e"))
    p.rect(2, 4, 26, 33, rgb("#56d8a8"))
    for y in range(4, 37):
        t = (y - 4) / 33
        p.hline(2, y, 26, mix(rgb("#8af2cd"), rgb("#2a9a7a"), t))
    p.frame(2, 4, 26, 33, rgb("#cfe0e6"))
    p.rect(1, 2, 28, 3, rgb("#4a5766"))
    for x, y in ((8, 28), (20, 22), (14, 12), (22, 31)):
        p.dot(x, y, rgb("#dffff2"))
        p.dot(x + 1, y - 1, rgb("#dffff2"))
    # a tiny creature silhouette
    p.ellipse(10, 20, 9, 7, rgb("#1e6a5a"))
    p.rect(12, 18, 2, 3, rgb("#1e6a5a"))
    p.rect(15, 18, 2, 3, rgb("#1e6a5a"))
    p.dot(12, 22, rgb("#dffff2"))
    p.dot(16, 22, rgb("#dffff2"))
    p.vline(7, 5, 31, rgb("#dffcf6"))
    return out(im)


def hydro_tray(variant=0):
    im = new(48, 34)
    p = Pen(im)
    p.rect(2, 22, 44, 10, rgb("#e6ecef"))
    p.rect(2, 22, 44, 2, rgb("#ffffff"))
    p.hline(2, 31, 44, rgb("#aab4be"))
    p.rect(4, 24, 40, 5, rgb("#3a6a8a"))
    for x in range(5, 43, 4):
        p.rect(x, 14 + (x // 4 + variant) % 3, 3, 10, rgb("#2f7a3a"))
        p.rect(x - 1, 12 + (x // 4 + variant) % 3, 5, 5, rgb("#58b85a"))
        p.dot(x, 12 + (x // 4 + variant) % 3, rgb("#8fe07a"))
        if (x // 4 + variant) % 3 == 0:
            p.dot(x + 1, 16, rgb("#e0453c"))
    p.rect(2, 4, 44, 4, rgb("#4a5766"))
    p.hline(2, 4, 44, rgb("#6a7a8e"))
    p.rect(4, 8, 40, 2, rgb("#ffd6ff") if variant else rgb("#ffb8f0"))
    p.vline(3, 8, 14, METAL_D)
    p.vline(44, 8, 14, METAL_D)
    return out(im)


def holo_table():
    im = new(46, 44)
    p = Pen(im)
    p.rect(3, 28, 40, 10, rgb("#3d4a5a"))
    p.rect(3, 28, 40, 3, rgb("#6a7e94"))
    p.rect(5, 38, 4, 5, rgb("#2e3742"))
    p.rect(37, 38, 4, 5, rgb("#2e3742"))
    p.rect(8, 25, 30, 4, rgb("#1e2a36"))
    p.frame(8, 25, 30, 4, rgb("#6be6ee"))
    # projection cone + globe
    for i in range(14):
        half = 4 + i
        c = rgb("#7ef2ff", 40 + i * 4)
        p.hline(23 - half, 24 - i, half * 2, c)
    p.ellipse(15, 3, 16, 16, rgb("#59d8f2"))
    p.ellipse(17, 5, 12, 12, rgb("#9ff7ff"))
    p.hline(15, 11, 16, rgb("#d9ffff"))
    p.vline(23, 3, 16, rgb("#d9ffff"))
    p.dot(19, 7, rgb("#ffffff"))
    return out(im)


def lab_bench():
    im = new(48, 30)
    p = Pen(im)
    p.rect(1, 12, 46, 16, rgb("#d9e2e6"))
    p.rect(1, 12, 46, 3, rgb("#f6fafb"))
    p.hline(1, 27, 46, rgb("#8e9aa6"))
    p.rect(3, 15, 20, 11, rgb("#aab6be"))
    p.rect(25, 15, 20, 11, rgb("#aab6be"))
    p.dot(13, 20, rgb("#2a2a33"))
    p.dot(35, 20, rgb("#2a2a33"))
    # glassware
    for x, c in ((6, "#ff7ab0"), (12, "#7ef2a0"), (18, "#7ac8ff")):
        p.rect(x, 4, 4, 8, rgb("#e8f6ff"))
        p.rect(x + 1, 7, 2, 5, rgb(c))
    p.rect(30, 6, 6, 6, rgb("#e8f6ff"))
    p.rect(31, 9, 4, 3, rgb("#ffe27a"))
    p.rect(40, 3, 5, 9, rgb("#4a5766"))
    p.rect(41, 4, 3, 3, rgb("#7ef2ff"))
    return out(im)


def workbench():
    im = new(48, 34)
    p = Pen(im)
    p.rect(1, 16, 46, 4, WOOD_L)
    p.hline(1, 16, 46, rgb("#e3b87a"))
    p.rect(3, 20, 4, 12, WOOD_D)
    p.rect(41, 20, 4, 12, WOOD_D)
    p.rect(7, 22, 34, 3, WOOD)
    # gadgets on top
    p.rect(5, 9, 10, 7, rgb("#e0b040"))
    p.rect(6, 10, 4, 2, rgb("#7ef2ff"))
    p.rect(8, 4, 2, 5, METAL)
    p.rect(20, 11, 7, 5, METAL)
    p.rect(20, 11, 7, 1, METAL_L)
    p.rect(30, 12, 3, 4, rgb("#e0453c"))
    p.rect(35, 7, 8, 9, rgb("#4a86c9"))
    p.rect(36, 8, 6, 3, rgb("#bfe9ff"))
    p.dot(40, 14, rgb("#ffe27a"))
    return out(im)


def tool_wall():
    im = new(48, 34)
    p = Pen(im)
    p.rect(0, 0, 48, 34, rgb("#7a5a3c"))
    p.frame(0, 0, 48, 34, rgb("#563620"))
    for y in range(3, 33, 4):
        for x in range(3, 46, 4):
            p.dot(x, y, rgb("#5e4430"))
    tools = [(5, "#c9d4dc", 14), (11, "#e0453c", 12), (17, "#f2cf4a", 16), (23, "#9aa4ae", 10), (29, "#4a86c9", 14), (36, "#c9d4dc", 18), (42, "#e0453c", 11)]
    for x, c, h in tools:
        p.rect(x, 5, 2, h, rgb(c))
        p.rect(x - 1, 4, 4, 3, rgb("#2a2a33"))
    p.ellipse(8, 22, 8, 8, rgb("#9aa4ae"))
    p.ellipse(10, 24, 4, 4, rgb("#5d6a76"))
    p.rect(26, 24, 16, 5, rgb("#d1552f"))
    p.rect(26, 24, 16, 1, rgb("#f08a6a"))
    return out(im)


def parts_shelf():
    im = new(48, 42)
    p = Pen(im)
    p.rect(1, 1, 46, 40, rgb("#6a7480"))
    p.frame(1, 1, 46, 40, rgb("#3d4856"))
    for y in (12, 24, 36):
        p.rect(2, y, 44, 2, rgb("#9aa4ae"))
    cols = ["#e0453c", "#f2cf4a", "#4a86c9", "#6fc254", "#b78cf0", "#e8861e"]
    for row, y in enumerate((5, 17, 29)):
        for i, x in enumerate(range(4, 44, 7)):
            c = rgb(cols[(i + row * 2) % len(cols)])
            p.rect(x, y, 5, 6, c)
            p.hline(x, y, 5, shade(c, 1.3))
            p.rect(x + 1, y + 2, 3, 2, rgb("#f4f4f4"))
    return out(im)


def toolbox():
    im = new(18, 14)
    p = Pen(im)
    p.rect(1, 5, 16, 8, rgb("#d1552f"))
    p.rect(1, 5, 16, 2, rgb("#f08a6a"))
    p.rect(6, 2, 6, 3, rgb("#9aa4ae"))
    p.rect(8, 8, 2, 2, rgb("#f2cf4a"))
    return out(im)


def podium():
    im = new(22, 28)
    p = Pen(im)
    p.rect(3, 8, 16, 18, WOOD)
    p.rect(3, 8, 16, 3, WOOD_L)
    p.rect(1, 4, 20, 5, WOOD_D)
    p.hline(1, 4, 20, WOOD)
    p.rect(8, 13, 6, 6, rgb("#e6c35a"))
    p.rect(9, 14, 4, 4, rgb("#b8923a"))
    p.rect(3, 24, 16, 2, WOOD_D)
    return out(im)


def flag_stand(color="#d1552f"):
    im = new(14, 44)
    p = Pen(im)
    p.rect(6, 4, 2, 38, rgb("#c9a14a"))
    p.rect(2, 40, 10, 3, rgb("#7a5230"))
    p.rect(1, 6, 5, 14, rgb(color))
    p.rect(8, 6, 5, 14, rgb(color))
    p.rect(3, 9, 2, 5, rgb("#f6e6a0"))
    p.rect(10, 9, 2, 5, rgb("#f6e6a0"))
    p.rect(5, 1, 4, 3, rgb("#e6c35a"))
    return out(im)


def portrait(v=0):
    im = new(16, 20)
    p = Pen(im)
    p.rect(0, 0, 16, 20, rgb("#8a6a2a"))
    p.rect(2, 2, 12, 16, rgb(["#9ec3d8", "#d8c49e", "#b9d89e"][v % 3]))
    p.ellipse(5, 5, 6, 6, rgb("#e0bc8a"))
    p.rect(4, 11, 8, 6, rgb(["#4a5a8a", "#8a4a4a", "#4a7a5a"][v % 3]))
    p.rect(5, 4, 6, 2, rgb(["#3a3a4a", "#6a4a2a", "#8a8a8a"][v % 3]))
    p.dot(7, 8, LINE)
    p.dot(9, 8, LINE)
    return out(im)


def banner(color="#d1552f"):
    im = new(16, 36)
    p = Pen(im)
    p.rect(0, 0, 16, 2, rgb("#c9a14a"))
    p.rect(2, 2, 12, 28, rgb(color))
    for i in range(6):
        p.hline(2 + i, 30 + i, 12 - i * 2, rgb(color))
    p.rect(6, 8, 4, 8, rgb("#f6e6a0"))
    p.rect(4, 10, 8, 4, rgb("#f6e6a0"))
    p.rect(7, 18, 2, 6, rgb("#f6e6a0"))
    p.vline(2, 2, 28, shade(rgb(color), 1.2))
    return out(im)


def book_stack():
    im = new(16, 14)
    p = Pen(im)
    for y, w, c in ((9, 14, "#4a6ac9"), (5, 12, "#c94a4a"), (1, 10, "#4ac97a")):
        p.rect(1, y, w, 4, rgb(c))
        p.hline(1, y, w, shade(rgb(c), 1.3))
        p.hline(2, y + 3, w - 1, rgb("#f6ecd2"))
    return out(im)


def reading_desk():
    im = new(48, 36)
    p = Pen(im)
    p.rect(1, 14, 46, 4, WOOD_L)
    p.hline(1, 14, 46, rgb("#e3b87a"))
    p.rect(2, 18, 4, 16, WOOD_D)
    p.rect(42, 18, 4, 16, WOOD_D)
    p.rect(6, 20, 36, 3, WOOD)
    # open book + lamp + papers
    p.rect(8, 9, 10, 6, rgb("#f6ecd2"))
    p.vline(13, 9, 6, rgb("#b8a47a"))
    p.rect(22, 11, 6, 4, rgb("#c94a4a"))
    p.rect(36, 3, 3, 11, rgb("#3d4856"))
    p.rect(33, 2, 9, 4, rgb("#2e8a5a"))
    p.rect(34, 3, 7, 1, rgb("#5ad79a"))
    return out(im)


def library_ladder():
    im = new(14, 48)
    p = Pen(im)
    p.vline(2, 0, 47, WOOD_D)
    p.vline(11, 0, 47, WOOD_D)
    p.vline(3, 0, 47, WOOD)
    p.vline(10, 0, 47, WOOD)
    for y in range(4, 46, 6):
        p.rect(2, y, 10, 2, WOOD_L)
    return out(im)


def basket():
    im = new(16, 12)
    p = Pen(im)
    p.rect(1, 4, 14, 7, rgb("#c9955c"))
    for x in range(2, 14, 3):
        p.vline(x, 4, 7, rgb("#a87848"))
    p.hline(1, 7, 14, rgb("#a87848"))
    p.rect(0, 3, 16, 2, rgb("#e3b87a"))
    p.rect(3, 1, 3, 3, rgb("#e0453c"))
    p.rect(8, 0, 3, 4, rgb("#f2cf4a"))
    p.rect(12, 1, 2, 3, rgb("#6fc254"))
    return out(im)


def sale_sign():
    im = new(18, 24)
    p = Pen(im)
    p.rect(8, 12, 2, 11, METAL_D)
    p.rect(2, 12, 14, 2, METAL_D)
    p.rect(1, 1, 16, 12, rgb("#f6ecd2"))
    p.frame(1, 1, 16, 12, rgb("#d9402f"))
    p.rect(3, 3, 12, 3, rgb("#d9402f"))
    p.rect(4, 8, 4, 2, rgb("#3a2a36"))
    p.rect(10, 8, 4, 2, rgb("#3a2a36"))
    return out(im)


def fruit_crate(color="#e0453c"):
    im = new(20, 16)
    p = Pen(im)
    p.rect(1, 6, 18, 9, WOOD)
    p.frame(1, 6, 18, 9, WOOD_D)
    p.hline(2, 10, 16, WOOD_D)
    for i, x in enumerate(range(2, 17, 3)):
        p.ellipse(x, 2 + i % 2, 4, 4, rgb(color))
        p.dot(x + 1, 3 + i % 2, shade(rgb(color), 1.4))
    return out(im)


def register():
    im = new(16, 16)
    p = Pen(im)
    p.rect(1, 7, 14, 8, rgb("#4a5766"))
    p.rect(1, 7, 14, 2, rgb("#6a7a8e"))
    p.rect(3, 2, 10, 5, rgb("#2e3742"))
    p.rect(4, 3, 8, 3, rgb("#7ef2a0"))
    for x in (3, 7, 11):
        p.rect(x, 10, 2, 2, rgb("#c3ccd4"))
    return out(im)


def seed_bins():
    im = new(48, 28)
    p = Pen(im)
    for i, (x, c) in enumerate(((1, "#e8cf78"), (17, "#e0873a"), (33, "#6fc254"))):
        p.rect(x, 10, 14, 16, WOOD)
        p.frame(x, 10, 14, 16, WOOD_D)
        p.rect(x + 1, 11, 12, 6, rgb(c))
        for k in range(0, 12, 3):
            p.dot(x + 1 + k, 10, shade(rgb(c), 1.2))
        p.rect(x + 3, 19, 8, 5, rgb("#f6ecd2"))
        p.hline(x + 4, 21, 6, rgb("#8a7a5a"))
    return out(im)


def planter_trough(kind=0):
    im = new(48, 26)
    p = Pen(im)
    leaf, fruit = [("#2f7a3a", "#e0453c"), ("#5fae55", "#9fd58a"), ("#c9a84a", "#e8cf78")][kind % 3]
    p.rect(1, 14, 46, 11, rgb("#8a6a44"))
    p.rect(1, 14, 46, 2, rgb("#b8905a"))
    p.rect(2, 16, 44, 8, rgb("#5e4430"))
    p.hline(1, 24, 46, rgb("#563620"))
    for x in range(3, 44, 5):
        p.rect(x, 7, 4, 9, rgb(leaf))
        p.rect(x - 1, 5, 6, 5, shade(rgb(leaf), 1.2))
        p.dot(x + 1, 6, rgb(fruit))
        p.dot(x + 3, 9, rgb(fruit))
    return out(im)


def watering_can():
    im = new(18, 14)
    p = Pen(im)
    p.rect(3, 4, 10, 8, rgb("#4a86c9"))
    p.rect(3, 4, 10, 2, rgb("#78acea"))
    p.line(12, 6, 17, 2, rgb("#4a86c9"))
    p.rect(15, 0, 3, 3, rgb("#78acea"))
    p.rect(0, 3, 3, 6, rgb("#3a6fa8"))
    return out(im)


def hanging_plants():
    im = new(26, 22)
    p = Pen(im)
    p.rect(0, 0, 26, 2, rgb("#7a5230"))
    for x in (4, 13, 21):
        p.vline(x, 2, 4, rgb("#c9a14a"))
        p.rect(x - 3, 6, 7, 5, rgb("#a06a44"))
        for k in range(-3, 4):
            p.vline(x + k, 11, 3 + (abs(k) * 2) % 6, rgb("#3f9a46"))
        p.dot(x - 1, 9, rgb("#f08cb0"))
        p.dot(x + 2, 9, rgb("#ffd24a"))
    return out(im)


def family_photo():
    im = new(16, 14)
    p = Pen(im)
    p.rect(0, 0, 16, 14, rgb("#a87848"))
    p.rect(2, 2, 12, 10, rgb("#cfe6f2"))
    p.rect(2, 8, 12, 4, rgb("#6fa95a"))
    for x, c in ((4, "#e0453c"), (7, "#4a86c9"), (10, "#f2cf4a")):
        p.rect(x, 6, 2, 4, rgb(c))
        p.dot(x, 5, rgb("#e0bc8a"))
        p.dot(x + 1, 5, rgb("#e0bc8a"))
    return out(im)


def wall_shelf():
    im = new(34, 18)
    p = Pen(im)
    p.rect(0, 12, 34, 3, WOOD_L)
    p.rect(0, 14, 34, 2, WOOD_D)
    p.rect(3, 15, 3, 3, WOOD_D)
    p.rect(28, 15, 3, 3, WOOD_D)
    for x, c, h in ((3, "#c94a4a", 9), (6, "#4a6ac9", 7), (9, "#4ac97a", 8), (12, "#c9a14a", 9), (15, "#8a4ac9", 6)):
        p.rect(x, 12 - h, 3, h, rgb(c))
    p.rect(21, 4, 8, 8, rgb("#e0a050"))
    p.rect(21, 4, 8, 2, rgb("#f6c68a"))
    p.rect(24, 1, 2, 3, rgb("#3f9a46"))
    return out(im)


def window_light():
    """Soft trapezoid of daylight falling on the floor (baked into the room, not collidable)."""
    im = new(48, 48)
    p = Pen(im)
    for y in range(48):
        half_l, half_r = 6 + y // 3, 40 + y // 6
        a = int(55 * (1 - y / 52))
        p.hline(half_l, y, max(0, half_r - half_l), (255, 244, 205, a))
    return im


def build():
    os.makedirs(OUTD, exist_ok=True)
    items = {
        "x_server_rack": server_rack(), "x_microscope": microscope(), "x_tank": specimen_tank(),
        "x_hydro_a": hydro_tray(0), "x_hydro_b": hydro_tray(1), "x_holo_table": holo_table(), "x_lab_bench": lab_bench(),
        "x_workbench": workbench(), "x_tool_wall": tool_wall(), "x_parts_shelf": parts_shelf(), "x_toolbox": toolbox(),
        "x_podium": podium(), "x_flag_red": flag_stand("#d1552f"), "x_flag_teal": flag_stand("#3f9a98"),
        "x_portrait_0": portrait(0), "x_portrait_1": portrait(1), "x_portrait_2": portrait(2),
        "x_banner_red": banner("#d1552f"), "x_banner_teal": banner("#3f9a98"), "x_banner_blue": banner("#4a6ac9"),
        "x_book_stack": book_stack(), "x_reading_desk": reading_desk(), "x_ladder": library_ladder(),
        "x_basket": basket(), "x_sale_sign": sale_sign(), "x_fruit_crate_a": fruit_crate("#e0453c"),
        "x_fruit_crate_b": fruit_crate("#f2cf4a"), "x_fruit_crate_c": fruit_crate("#6fc254"), "x_register": register(),
        "x_seed_bins": seed_bins(), "x_trough_a": planter_trough(0), "x_trough_b": planter_trough(1),
        "x_trough_c": planter_trough(2), "x_watering_can": watering_can(), "x_hanging_plants": hanging_plants(),
        "x_family_photo": family_photo(), "x_wall_shelf": wall_shelf(), "x_window_light": window_light(),
    }
    for name, im in items.items():
        im.save(os.path.join(OUTD, name + ".png"))
    return list(items)


if __name__ == "__main__":
    print(len(build()), "interior props written")
