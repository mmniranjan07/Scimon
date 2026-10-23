"""Story scenes: title screen, click-through dialogue, the wake-up scene, the professor's lab briefing
(animated explanation of what Scimon are and how battles work), starter selection and the rival encounter,
plus the flow that chains them
(Title -> Customize -> Wake -> Brief -> Starter -> Rival -> Battle -> Overworld).

Dialogue is a state, not a loop: lines advance on input while the engine keeps running at full frame rate."""
import math

import pygame

import assets
import audio
import savegame
from data import SPECIES, STARTER_IDS
from engine import Scene, StateId
from monsters import create_scimon
from settings import CREAM, H, INK, ORANGE, TEAL, TEAL_DARK, W
from sprites import (CLOTH_HUES, HAIR_HUES, SKIN_OFFSETS, Character, class_swatches, look_animator, look_for, make_look)
from ui import (ButtonGrid, Button, DialogueBox, circuit_backdrop, draw_button, hp_color, is_back, is_click, is_confirm,
                label_chip, nav_dir, panel, text, type_chip, wrap_text)

RIVAL_NAME = "Kael"
# Kael always picks the starter that is WEAK against yours: florabot > aquabit > pyrodrive > florabot.
RIVAL_COUNTER = {"florabot": "aquabit", "aquabit": "pyrodrive", "pyrodrive": "florabot"}


def wake_lines(name):
    """The wake-up dialogue, addressed to the chosen player name."""
    return [
        "...",
        f"{name}, you wake up in your room in Riven Town.",
        "Prof. Venn messaged you last night: a new Scimon is ready and waiting at the lab.",
        "Time to get up and go see the professor.",
    ]


# =========================================================================== dialogue
class DialogueScene(Scene):
    """Click-through text. With `bg` it is a full-screen scene (opaque); without, a bottom overlay on whatever
    is below. `sprites` are species ids shown bobbing above the box. `choices` = [(label, callable)] replaces
    the plain finish after the last line with a button row (rematch asks: accept or deny)."""
    state_id = StateId.DIALOGUE

    def __init__(self, lines, on_done=None, bg=None, sprites=None, pop_on_done=True, choices=None):
        self.lines, self.on_done, self.bg, self.sprites = list(lines), on_done, bg, sprites or []
        self.pop_on_done = pop_on_done
        self.opaque = bg is not None
        self.box = DialogueBox(self.lines, size=38 if bg else 36)
        self.choices = list(choices) if choices else None
        self.asking, self.grid = False, None
        self.t = 0.0
        self.done = False

    def on_enter(self):
        name = getattr(self.engine.state, "name", "") if self.engine is not None else ""
        if name:                                        # dialogue lines may address the player as {name}
            self.lines = [ln.replace("{name}", name) for ln in self.lines]
            self.box.set_lines(self.lines)

    def _line_done(self):
        """The last line was dismissed: open the choice row, or finish the scene."""
        if not self.choices:
            self.done = True
            if self.pop_on_done:
                self.engine.pop(self)
            if self.on_done:
                self.on_done()
            return
        bw, bh, gap = 224, 56, 14
        y = H - 132
        xs = W - 40 - len(self.choices) * (bw + gap) + gap
        self.grid = ButtonGrid([Button(lab, (xs + k * (bw + gap), y, bw, bh), tag=k, accent=(k == 0))
                                for k, (lab, _) in enumerate(self.choices)], cols=len(self.choices),
                               allow_back=False)
        self.asking = True

    def _pick(self, k):
        _, cb = self.choices[k]
        self.done, self.asking = True, False
        self.engine.pop(self)
        if cb:
            cb()

    def handle_event(self, e):
        if self.done:
            return
        if self.asking:
            r = self.grid.handle(e) if self.grid else None
            if r and r[0] == "activate":
                audio.play("select")
                self._pick(r[1].tag)
            return
        if is_confirm(e) or is_click(e):
            audio.play("move")
            if self.box.advance():
                self._line_done()

    def update(self, dt):
        self.t += dt
        self.box.update(dt)
        if self.grid:
            self.grid.update(dt)

    def _draw_stage(self, surf):
        """The animated stage above the text box: species sprites bobbing over their shadows."""
        n = len(self.sprites)
        for k, sid in enumerate(self.sprites):
            img = assets.mon_image(sid, 210, 210)
            x = W // 2 + (k - (n - 1) / 2) * 290 - img.get_width() // 2
            y = 430 - img.get_height() + math.sin(self.t * 2.6 + k * 1.3) * 4
            shadow = pygame.Surface((img.get_width() // 1.4, 22), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (10, 10, 14, 70), shadow.get_rect())
            surf.blit(shadow, shadow.get_rect(midtop=(x + img.get_width() // 2, 424)))
            surf.blit(img, (x, y))

    def draw(self, surf):
        if self.bg:
            self.bg(surf, self.t)
            self._draw_stage(surf)
        self.box.draw(surf)
        if self.asking and self.grid:
            self.grid.draw(surf, size=18)


# =========================================================================== backdrops
def bedroom_bg(surf, t):
    surf.fill((207, 227, 216))
    pygame.draw.rect(surf, (205, 189, 148), (0, 295, W, H - 295))
    pygame.draw.line(surf, (160, 146, 110), (0, 295), (W, 295), 4)
    # window with a slowly drifting sun glow
    win = pygame.Rect(96, 64, 212, 166)
    pygame.draw.rect(surf, (138, 106, 68), win.inflate(12, 12))
    for i in range(win.h):
        k = i / win.h
        pygame.draw.line(surf, (int(143 + 62 * k), int(208 + 26 * k), int(232 + 10 * k)), (win.x, win.y + i), (win.right, win.y + i))
    sun_y = win.y + 42 + math.sin(t * 0.4) * 4
    pygame.draw.circle(surf, (245, 226, 138), (win.centerx, int(sun_y)), 20)
    pygame.draw.rect(surf, (138, 106, 68), (win.centerx - 5, win.y, 10, win.h))
    pygame.draw.rect(surf, (138, 106, 68), (win.x, win.centery - 5, win.w, 10))
    glow = pygame.Surface((win.w, 120), pygame.SRCALPHA)
    glow.fill((255, 240, 180, int(40 + 12 * math.sin(t * 0.8))))
    surf.blit(glow, (win.x, 300))
    # shelf with decorations
    pygame.draw.rect(surf, (138, 106, 68), (590, 150, 250, 14))
    for x, y, w, h, c in ((610, 98, 28, 52, (224, 90, 114)), (660, 112, 24, 38, (91, 143, 214)), (708, 104, 26, 46, (87, 176, 111))):
        pygame.draw.rect(surf, c, (x, y, w, h), border_radius=3)
    # bed
    pygame.draw.rect(surf, (0, 0, 0, 40), (70, 520, 440, 14))
    pygame.draw.rect(surf, (224, 90, 114), (72, 350, 430, 170), border_radius=8)
    pygame.draw.rect(surf, (201, 68, 92), (86, 400, 402, 108), border_radius=6)
    pygame.draw.rect(surf, (245, 240, 224), (92, 326, 130, 58), border_radius=8)
    # desk + terminal
    pygame.draw.rect(surf, (138, 106, 68), (640, 410, 230, 110))
    pygame.draw.rect(surf, (42, 48, 56), (686, 318, 120, 88), border_radius=5)
    scr = pygame.Rect(694, 326, 104, 70)
    pygame.draw.rect(surf, (87, 176, 111), scr)
    for i in range(5):
        pygame.draw.line(surf, (190, 240, 200), (scr.x + 8, scr.y + 10 + i * 12), (scr.x + 20 + (i * 17 + int(t * 20)) % 70, scr.y + 10 + i * 12), 2)


def outdoor_bg(surf, t):
    """Outside the lab in Riven Town: sky, drifting clouds, the lab facade, path and hedges."""
    for i in range(340):                                   # sky gradient
        k = i / 340
        pygame.draw.line(surf, (int(120 + 60 * k), int(190 + 40 * k), int(215 + 25 * k)), (0, i), (W, i))
    for k, (cx, cy, spd, sc) in enumerate(((120, 60, 9, 1.0), (430, 96, 6, 1.4), (760, 48, 11, 0.8))):
        x = (cx + t * spd) % (W + 240) - 120               # clouds drift slowly to the right
        for dx, dy, r in ((0, 0, 26 * sc), (30 * sc, 8 * sc, 20 * sc), (-28 * sc, 10 * sc, 18 * sc)):
            pygame.draw.circle(surf, (246, 250, 252), (int(x + dx), int(cy + dy)), int(r))
    pygame.draw.rect(surf, (122, 176, 96), (0, 330, W, H - 330))          # lawn
    pygame.draw.rect(surf, (86, 140, 70), (0, 330, W, 8))
    for gx in range(0, W, 34):                              # grass tufts sway
        sway = int(math.sin(t * 1.8 + gx * 0.35) * 3)
        pygame.draw.line(surf, (74, 128, 60), (gx, 372 + (gx * 7) % 180), (gx + sway, 358 + (gx * 7) % 180), 3)
    # the lab building behind the stage: the town's real lab sprite, not a placeholder facade
    lab = assets.scaled("town/bld_lab.png", 246, 294, smooth=False)
    surf.blit(lab, (480 - lab.get_width() // 2, 336 - lab.get_height()))
    # sandy path the trainers stand on
    pygame.draw.ellipse(surf, (216, 196, 150), (140, 470, 680, 150))
    pygame.draw.ellipse(surf, (196, 176, 132), (140, 470, 680, 150), 4)


# =========================================================================== professor's lab briefing
def _demo_pad(surf, cx, cy, w):
    """A glowing lab scanner pad the demos stand on."""
    pygame.draw.ellipse(surf, (16, 40, 38), (cx - w // 2, cy - 14, w, 30))
    pygame.draw.ellipse(surf, (120, 134, 128), (cx - w // 2, cy - 24, w, 30))
    pygame.draw.ellipse(surf, (208, 216, 210), (cx - w // 2 + 10, cy - 21, w - 20, 24))


def _demo_materialize(surf, t):
    """Idea demo: a Scimon materializes on the scanner pad inside a sweeping scan beam."""
    text(surf, "SCI-MON", (480, 128), "display", 24, CREAM, anchor="center", shadow=(20, 40, 38))
    text(surf, "autonomous machine - research partner", (480, 164), "body", 26, (214, 230, 222), anchor="center", shadow=(20, 40, 38))
    _demo_pad(surf, 480, 404, 250)
    k = min(1.0, (t % 3.6) / 2.0)                          # materialize, then hold
    img = assets.mon_image("florabot", 190, 190)
    w, h = max(8, int(img.get_width() * (0.25 + 0.75 * k))), max(8, int(img.get_height() * (0.25 + 0.75 * k)))
    sc = pygame.transform.smoothscale(img, (w, h))
    sc.set_alpha(int(255 * k))
    surf.blit(sc, (480 - w // 2, 400 - h + int((1 - k) * 60)))
    beam = pygame.Surface((70, 196), pygame.SRCALPHA)      # scan beam sweeping across the pad
    pygame.draw.rect(beam, (140, 235, 205, 64), beam.get_rect())
    pygame.draw.line(beam, (190, 255, 230, 190), (0, 0), (0, 196), 3)
    pygame.draw.line(beam, (190, 255, 230, 190), (69, 0), (69, 196), 3)
    surf.blit(beam, (350 + int((t * 120) % 260), 200))
    if k < 1.0:                                            # sparkles while it forms
        for i in range(6):
            a = t * 5 + i * 1.9
            sx = 480 + int(math.cos(a) * (26 + 30 * math.sin(i * 2.2)))
            sy = 400 - int((a * 46 + i * 37) % 150)
            pygame.draw.circle(surf, (250, 250, 200), (sx, sy), 3)


def _demo_battle(surf, t):
    """Rules demo: Florabot lands a super-effective Leaf Cutter on a wild Aquabit; HP drains."""
    T = 3.4
    ph = t % T
    text(surf, "A SCIMON BATTLE", (480, 116), "display", 18, CREAM, anchor="center", shadow=(20, 40, 38))
    _demo_pad(surf, 330, 408, 210)
    _demo_pad(surf, 650, 408, 210)
    limg = assets.mon_image("florabot", 150, 130)
    rimg = assets.mon_image("aquabit", 150, 130)
    shake = 8 if 0.9 <= ph < 1.15 else 0
    surf.blit(limg, (330 - limg.get_width() // 2, 396 - limg.get_height()))
    surf.blit(rimg, (650 - rimg.get_width() // 2, 396 - rimg.get_height() + shake))

    def hp_bar(cx, y, ratio, label):
        text(surf, label, (cx, y - 16), "display", 12, CREAM, anchor="center", shadow=(20, 40, 38))
        r = pygame.Rect(cx - 80, y, 160, 14)
        pygame.draw.rect(surf, (24, 44, 42), r.inflate(6, 6), border_radius=7)
        pygame.draw.rect(surf, (60, 74, 70), r, border_radius=6)
        pygame.draw.rect(surf, hp_color(ratio), (r.x, r.y, max(4, int(r.w * ratio)), r.h), border_radius=6)

    hp_bar(330, 226, 1.0, "FLORABOT  Lv5")
    hp_bar(650, 226, 1.0 - 0.65 * min(1.0, max(0.0, (ph - 1.05) / 0.45)), "WILD AQUABIT  Lv5")
    if ph < 0.9:
        text(surf, "FLORABOT used LEAF CUTTER!", (480, 158), "display", 16, CREAM, anchor="center", shadow=(20, 40, 38))
    if 0.35 <= ph < 0.9:                                   # the leaf arcs across the arena
        p = (ph - 0.35) / 0.55
        x, y = int(405 + p * 170), int(320 - math.sin(p * math.pi) * 46)
        leaf = pygame.Surface((26, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(leaf, (96, 190, 92), leaf.get_rect())
        pygame.draw.line(leaf, (60, 130, 60), (2, 7), (24, 7), 2)
        surf.blit(leaf, (x, y))
    if 0.9 <= ph < 1.6:                                    # impact flash + effectiveness callout
        a = int(220 * (1 - (ph - 0.9) / 0.7))
        fl = pygame.Surface((130, 130), pygame.SRCALPHA)
        pygame.draw.circle(fl, (255, 240, 160, a), (65, 65), 60)
        pygame.draw.circle(fl, (255, 255, 255, a), (65, 65), 32)
        surf.blit(fl, (650 - 65, 320 - 65))
        if ph < 1.4:
            text(surf, "SUPER EFFECTIVE! x1.5", (650, 186 + int((1.4 - ph) * 40)), "display", 18, ORANGE,
                 anchor="center", shadow=(60, 20, 10))


def _demo_types(surf, t):
    """Types demo: the starter triangle, with counters lighting up one by one."""
    pos = {"florabot": (480, 268), "aquabit": (310, 400), "pyrodrive": (650, 400)}
    order = [("florabot", "aquabit", "BOTANIC drenches HYDRO"),
             ("aquabit", "pyrodrive", "HYDRO shorts THERMAL"),
             ("pyrodrive", "florabot", "THERMAL scorches BOTANIC")]
    text(surf, "TYPE TRIANGLE", (480, 104), "display", 18, CREAM, anchor="center", shadow=(20, 40, 38))
    imgs = {sid: assets.mon_image(sid, 150, 130) for sid in pos}
    for i, sid in enumerate(pos):
        cx, cy = pos[sid]
        _demo_pad(surf, cx, cy + 18, 200)
        bob = math.sin(t * 2.4 + i * 2.1) * 4
        img = imgs[sid]
        surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() + bob))
    k, p = int(t / 2.1) % 3, (t / 2.1) % 1
    src, dst, lab = order[k]
    c = {sid: (x, y - imgs[sid].get_height() // 2 - 10) for sid, (x, y) in pos.items()}
    (x0, y0), (x1, y1) = c[src], c[dst]
    if p < 0.62:                                           # attacker highlighted, arrow grows
        img = imgs[src]
        r = pygame.Rect(0, 0, img.get_width() + 16, img.get_height() + 16)
        r.center = (x0, y0 + 6)
        pygame.draw.rect(surf, ORANGE, r, 3, border_radius=10)
        g = min(1.0, p / 0.45)
        ex, ey = x0 + (x1 - x0) * g, y0 + (y1 - y0) * g
        pygame.draw.line(surf, ORANGE, (x0, y0), (ex, ey), 6)
        ang = math.atan2(y1 - y0, x1 - x0)
        for da in (2.65, -2.65):
            pygame.draw.line(surf, ORANGE, (ex, ey), (ex + math.cos(ang + da) * 18, ey + math.sin(ang + da) * 18), 6)
    if 0.5 <= p < 0.9:                                     # impact flash on the defender
        a = int(200 * (1 - (p - 0.5) / 0.4))
        fl = pygame.Surface((110, 110), pygame.SRCALPHA)
        pygame.draw.circle(fl, (255, 240, 160, a), (55, 55), 50)
        surf.blit(fl, (x1 - 55, y1 - 55))
    if 0.55 <= p < 0.95:
        text(surf, f"{lab}  x1.5!", (480, 448), "display", 18, ORANGE, anchor="center", shadow=(60, 20, 10))


def _demo_scan(surf, t):
    """Scanning demo: a wild Sporelet is caught in the scanner beam and added to the team."""
    pct = (t * 55) % 130
    _demo_pad(surf, 480, 404, 260)
    img = assets.mon_image("sporelet", 170, 150)
    bob = math.sin(t * 2.2) * 4
    surf.blit(img, (480 - img.get_width() // 2, 400 - img.get_height() - 12 + bob))
    beam = pygame.Surface((260, 230), pygame.SRCALPHA)     # beam cone from the ceiling scanner
    pygame.draw.polygon(beam, (140, 235, 205, 46), [(100, 0), (160, 0), (240, 230), (20, 230)])
    surf.blit(beam, (350, 140))
    pygame.draw.rect(surf, (66, 82, 78), (440, 100, 80, 40), border_radius=8)
    pygame.draw.circle(surf, (250, 240, 170), (480, 140), 8)
    for i in range(3):                                     # expanding scan rings
        rr = ((t * 90) + i * 46) % 140
        a = int(150 * (1 - rr / 140))
        ring = pygame.Surface((rr * 2 + 8, rr * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(ring, (120, 235, 205, a), (rr + 4, rr + 4), max(2, rr), 3)
        surf.blit(ring, (480 - rr - 4, 344 - rr - 4))
    bar = pygame.Rect(360, 152, 240, 18)
    pygame.draw.rect(surf, (24, 44, 42), bar.inflate(6, 6), border_radius=9)
    pygame.draw.rect(surf, (60, 74, 70), bar, border_radius=8)
    pygame.draw.rect(surf, (110, 235, 190), (bar.x, bar.y, int(bar.w * min(1.0, pct / 100)), bar.h), border_radius=8)
    if pct < 100:
        text(surf, f"SCANNING {int(pct)}%", (480, 184), "display", 14, CREAM, anchor="center", shadow=(20, 40, 38))
    else:
        text(surf, "SCANNED! +1 TO THE TEAM", (480, 184), "display", 14, (150, 240, 170), anchor="center", shadow=(20, 40, 38))
        pygame.draw.circle(surf, (150, 240, 170), (480, 344), int(40 + 26 * math.sin(t * 6)), 4)


BRIEF_STEPS = [
    ("idea", [
        "So! You're finally awake, {name}. Welcome to my lab - I'm Prof. Venn.",
        "This world runs on SCI-MON: Scientific Monsters - autonomous machines that behave like living creatures.",
        "Scan one with your Scanner and it becomes your research partner. It battles, learns techniques and grows with you.",
    ]),
    ("battle", [
        "Researchers settle their questions with Scimon battles. Every Scimon has HP: when it reaches zero, it powers down and is withdrawn.",
        "Watch closely: my Florabot hits a wild Aquabit with Leaf Cutter. Botanic against Hydro deals 1.5x damage - a super effective hit!",
    ]),
    ("types", [
        "Types decide battles. Botanic drenches Hydro, Hydro shorts out Thermal, and Thermal scorches Botanic - a triangle of counters.",
        "Pick a partner whose strengths cover your gaps. Learn the triangle and you've already half-won.",
    ]),
    ("scan", [
        "Out in the field, weaken a wild Scimon and then SCAN it to add it to your team. Up to six partners can travel with you.",
        "And that's everything. Three Scimons have gathered on my pads right now, curious about your Scanner.",
        "Choose the one you connect with, {name} - your research journey starts today!",
    ]),
]
DEMOS = {"idea": _demo_materialize, "battle": _demo_battle, "types": _demo_types, "scan": _demo_scan}


class ProfBriefScene(Scene):
    """Prof. Venn's lab briefing, on a generic backdrop (not the lab interior): the idea of Scimon and the
    battle rules, each point told with an animated demo on the stage while Prof. Venn (his actual in-game
    sprite) presents, then straight on to the starter selection."""
    state_id = StateId.BRIEF

    def __init__(self):
        self.t = 0.0
        self.step = 0
        self.box = DialogueBox(size=36)
        self._set_step(0)
        self.done = False
        self.prof = Character(3, 7, look_for("venn"), "down")     # Prof. Venn himself
        self.prof.pos = pygame.Vector2(148, 366)                  # fixed spot beside the demo stage

    def on_enter(self):
        self._set_step(self.step)                     # {name} is only known once the engine is attached

    def _set_step(self, i):
        name = getattr(self.engine.state, "name", "") if self.engine is not None else ""
        self.box.set_lines([ln.replace("{name}", name) for ln in BRIEF_STEPS[i][1]])

    def _advance(self):
        if self.box.advance():
            if self.step + 1 < len(BRIEF_STEPS):
                self.step += 1
                self._set_step(self.step)
                audio.play("move")
            else:
                self.done = True
                self.finish()

    def finish(self):
        eng = self.engine
        eng.fade_to(lambda: eng.replace(StarterScene()))

    def handle_event(self, e):
        if not self.done and (is_confirm(e) or is_click(e)):
            audio.play("move")
            self._advance()

    def update(self, dt):
        self.t += dt
        self.box.update(dt)
        self.prof.anim_t += dt                           # idle animation: breathing, blinking
        self.prof.refresh()

    def draw(self, surf):
        circuit_backdrop(surf, self.t)                   # generic backdrop, not the lab interior
        DEMOS[BRIEF_STEPS[self.step][0]](surf, self.t)   # the animated explanations on the stage
        surf.blit(self.prof.image, self.prof.draw_pos)
        self.box.draw(surf)
        for k in range(len(BRIEF_STEPS)):                  # progress dots
            c = ORANGE if k == self.step else (130, 152, 146)
            pygame.draw.circle(surf, c, (W - 36 - (len(BRIEF_STEPS) - 1 - k) * 24, 30), 6)


# =========================================================================== character customization (New Game)
SKIN_SWATCHES, HAIR_SWATCHES, OUTFIT_SWATCHES = class_swatches()

NAME_RECT = pygame.Rect(170, 108, 320, 48)
BODY_Y, BODY_SIZE, BODY_GAP = 176, 40, 8           # body chips: 10 base sprites, 40x52 with a gap of 8
SWATCH_Y = {"skin": 252, "hair": 312, "outfit": 372}
SWATCH_SIZE, SWATCH_GAP = 40, 12
PREVIEW_RECT = pygame.Rect(648, 108, 262, 344)
START_RECT = pygame.Rect(70, 442, 300, 56)
ROWS = 6                                           # name, body, skin, hair, outfit, start


class CustomizeScene(Scene):
    """New Game character creator: name entry plus body sprite, skin, hair and outfit colour, with a live preview."""
    state_id = StateId.CUSTOMIZE

    def __init__(self):
        self.t = 0.0
        self.row = 0                                  # 0 name, 1 body, 2 skin, 3 hair, 4 outfit, 5 start
        self.body = 1                                 # base sprite sheet (1..10): build / gender
        self.skin, self.hair, self.outfit = 1, 1, 4   # fair skin, brown hair, azure outfit
        self.name = "Robin"
        self._hit = []                                # (row, index, rect) for mouse picking, rebuilt by draw()
        self._thumbs = {}                             # (sheet, skin, hair, outfit) -> mini sprite

    # ---- selection ----------------------------------------------------------------------
    def _nudge(self, d):
        if self.row == 1:
            self.body = 1 + (self.body - 1 + d) % 10
        elif self.row == 2:
            self.skin = (self.skin + d) % len(SKIN_OFFSETS)
        elif self.row == 3:
            self.hair = (self.hair + d) % len(HAIR_HUES)
        elif self.row == 4:
            self.outfit = (self.outfit + d) % len(CLOTH_HUES)
        else:
            return
        audio.play("move")

    def _pick(self, pos):
        for row, idx, r in self._hit:
            if r.collidepoint(pos):
                self.row = row
                if row == 1:
                    self.body = 1 + idx
                elif row == 2:
                    self.skin = idx
                elif row == 3:
                    self.hair = idx
                elif row == 4:
                    self.outfit = idx
                elif row == 5:
                    self.confirm()
                else:
                    audio.play("move")
                return True
        return False

    def confirm(self):
        eng, st = self.engine, self.engine.state
        st.name = (self.name.strip() or "Robin")[:12]
        st.look = make_look(self.body, self.skin, self.hair, self.outfit)
        audio.play("select")

        def to_brief():
            eng.fade_to(lambda: eng.replace(ProfBriefScene()))

        eng.fade_to(lambda: eng.replace(DialogueScene(wake_lines(st.name), on_done=to_brief, bg=bedroom_bg,
                                                      pop_on_done=False)))

    # ---- input --------------------------------------------------------------------------
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            uni = getattr(e, "unicode", "")
            if e.key == pygame.K_ESCAPE:
                audio.play("move")
                self.engine.replace(TitleScene())
            elif e.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.confirm()
            elif e.key in (pygame.K_UP, pygame.K_w) and not uni:
                self.row = (self.row - 1) % ROWS
                audio.play("move")
            elif e.key in (pygame.K_DOWN, pygame.K_s) and not uni:
                self.row = (self.row + 1) % ROWS
                audio.play("move")
            elif e.key in (pygame.K_LEFT, pygame.K_a) and not uni:
                self._nudge(-1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d) and not uni:
                self._nudge(1)
            elif uni and (uni.isalnum() or uni in " -_'") and len(self.name) < 12:
                self.name += uni
            return
        if e.type == pygame.MOUSEMOTION:
            for row, idx, r in self._hit:
                if r.collidepoint(e.pos):
                    self.row = row
                    break
        elif is_click(e):
            self._pick(e.pos)

    def update(self, dt):
        self.t += dt

    # ---- drawing ------------------------------------------------------------------------
    def _thumb(self, n):
        """Mini idle sprite of base sheet n in the currently chosen palette (cached)."""
        key = (n, self.skin, self.hair, self.outfit)
        img = self._thumbs.get(key)
        if img is None:
            fr = look_animator(make_look(n, self.skin, self.hair, self.outfit)).frame_index("idle", "down", 0)
            k = min(BODY_SIZE / fr.get_width(), (BODY_SIZE + 12) / fr.get_height())
            img = self._thumbs[key] = pygame.transform.scale_by(fr, k)
            if len(self._thumbs) > 120:
                self._thumbs.clear()
        return img

    def draw(self, surf):
        circuit_backdrop(surf, self.t)
        text(surf, "CREATE YOUR RESEARCHER", (W // 2, 34), "display", 40, CREAM, anchor="center", shadow=(10, 30, 28))
        panel(surf, (48, 88, 570, 434), "panel", blur=False)
        self._hit = []
        # name row
        name_sel = self.row == 0
        text(surf, "NAME", (70, 122), "display", 16, TEAL if name_sel else (150, 190, 180))
        pygame.draw.rect(surf, (250, 246, 226, 230), NAME_RECT, border_radius=10)
        pygame.draw.rect(surf, ORANGE if name_sel else (120, 120, 110), NAME_RECT, 2, border_radius=10)
        caret = "|" if (name_sel and int(self.t * 2.4) % 2 == 0) else ""
        text(surf, (self.name or "") + caret, (NAME_RECT.x + 16, NAME_RECT.centery), "body", 30, INK, anchor="midleft")
        self._hit.append((0, 0, NAME_RECT))
        # body row: every available base sprite, tinted with the current palette
        text(surf, "BODY", (70, BODY_Y + 16), "display", 16, TEAL if self.row == 1 else (150, 190, 180))
        x = 140
        for i in range(10):
            r = pygame.Rect(x, BODY_Y, BODY_SIZE, BODY_SIZE + 12)
            self._hit.append((1, i, r))
            sel = self.row == 1 and self.body == i + 1
            pygame.draw.rect(surf, (255, 255, 255, 60) if sel else (0, 0, 0, 40), r, border_radius=8)
            img = self._thumb(i + 1)
            surf.blit(img, img.get_rect(midbottom=r.midbottom))
            pygame.draw.rect(surf, ORANGE if sel else (120, 120, 110), r, 2 if sel else 1, border_radius=8)
            x += BODY_SIZE + BODY_GAP
        # colour rows
        self._swatch_row(surf, "SKIN", 2, SKIN_SWATCHES, SWATCH_Y["skin"])
        self._swatch_row(surf, "HAIR", 3, HAIR_SWATCHES, SWATCH_Y["hair"])
        self._swatch_row(surf, "OUTFIT", 4, OUTFIT_SWATCHES, SWATCH_Y["outfit"])
        draw_button(surf, Button("START JOURNEY", START_RECT, accent=True), selected=(self.row == 5), size=20)
        self._hit.append((5, 0, START_RECT))
        # live preview: the actual in-game sprite, walking, with the chosen body and palette
        panel(surf, PREVIEW_RECT, "panel", blur=False)
        fr = look_animator(make_look(self.body, self.skin, self.hair, self.outfit)).frame("walk", "down", self.t)
        img = pygame.transform.scale_by(fr, 2)
        shadow = pygame.Surface((90, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (10, 30, 28, 90), shadow.get_rect())
        surf.blit(shadow, shadow.get_rect(midbottom=(PREVIEW_RECT.centerx, 388)))
        surf.blit(img, img.get_rect(midbottom=(PREVIEW_RECT.centerx, 388)))
        text(surf, self.name or "Robin", (PREVIEW_RECT.centerx, 408), "display", 24, INK, anchor="midtop")
        text(surf, "Type a name   Arrows: choose   Enter: start   Esc: back",
             (W // 2, 612), "body", 24, (150, 180, 170), anchor="center")

    def _swatch_row(self, surf, label, row, swatches, y):
        text(surf, label, (70, y + 10), "display", 16, TEAL if self.row == row else (150, 190, 180))
        cur = {2: self.skin, 3: self.hair, 4: self.outfit}[row]
        x = 170
        for i, c in enumerate(swatches):
            r = pygame.Rect(x, y, SWATCH_SIZE, SWATCH_SIZE)
            self._hit.append((row, i, r))
            sel = i == cur
            pygame.draw.rect(surf, c, r.inflate(-8, -8), border_radius=8)
            pygame.draw.rect(surf, (250, 246, 226) if sel else (0, 0, 0, 90), r.inflate(-8, -8),
                             3 if sel else 1, border_radius=8)
            if sel:
                pygame.draw.rect(surf, ORANGE, r, 2, border_radius=10)
            x += SWATCH_SIZE + SWATCH_GAP


# =========================================================================== title
class TitleScene(Scene):
    state_id = StateId.START_MENU

    def __init__(self):
        self.t = 0.0
        self.grid = None

    def on_enter(self):
        self.t = 0.0
        if savegame.has_save():
            self.grid = ButtonGrid([Button("CONTINUE", (W // 2 - 190, 420, 380, 58), accent=True, tag="continue"),
                                    Button("NEW GAME", (W // 2 - 190, 486, 380, 50), tag="new")], allow_back=False)
        else:
            self.grid = None

    def handle_event(self, e):
        if self.grid:
            r = self.grid.handle(e)
            if r and r[0] == "activate":
                audio.play("select")
                if r[1].tag == "continue":
                    self.engine.state.reset()
                    if savegame.load(self.engine.state):
                        from overworld import OverworldScene
                        self.engine.fade_to(lambda: self.engine.replace(OverworldScene()))
                        self.engine.toast.show(f"Welcome back, {self.engine.state.name}! Progress loaded.", 2.5)
                        return
                savegame.delete()                     # NEW GAME (or a broken save) starts fresh
                self.engine.state.reset()
                self.engine._saved = None
                start_game_flow(self.engine)
        elif is_confirm(e) or is_click(e):
            audio.play("select")
            start_game_flow(self.engine)

    def update(self, dt):
        self.t += dt
        if self.grid:
            self.grid.update(dt)

    def draw(self, surf):
        circuit_backdrop(surf, self.t)
        text(surf, "THE SCIENTIFIC MONSTER RPG", (W // 2, 108), "display", 16, (120, 220, 140), anchor="center")
        title = [("SCI", CREAM), ("-", ORANGE), ("MON", CREAM)]
        total = sum(assets.font("display", 64).size(s)[0] for s, _ in title)
        x = W // 2 - total // 2
        for s, c in title:
            r = text(surf, s, (x + 5, 150 + 5), "display", 64, (10, 30, 28), alpha=140)
            text(surf, s, (x, 150), "display", 64, c)
            x += r.w
        for i, sid in enumerate(STARTER_IDS):
            img = assets.mon_image(sid, 170, 170)
            bob = math.sin(self.t * 2.6 + i * 0.9) * 6
            cx = W // 2 + (i - 1) * 210
            pygame.draw.ellipse(surf, (20, 50, 48), (cx - 55, 378, 110, 20))
            surf.blit(img, (cx - img.get_width() // 2, 390 - img.get_height() + bob))
        if self.grid:
            self.grid.draw(surf)
        elif int(self.t * 2) % 2 == 0:
            b = Button("PRESS START", (W // 2 - 190, 440, 380, 62), accent=True)
            draw_button(surf, b, selected=True, size=24)
        text(surf, "A world of autonomous machines awaits.", (W // 2, 540), "body", 36, (190, 214, 204), anchor="center")
        text(surf, "Arrows/WASD move   Enter/Space/Z confirm   Esc/X back   I pack   M sound   F3 hitboxes",
             (W // 2, 604), "body", 24, (150, 180, 170), anchor="center")


# =========================================================================== starter select
class StarterScene(Scene):
    state_id = StateId.STARTER_SELECT

    def __init__(self):
        self.idx, self.t = 0, 0.0
        self.cards = [pygame.Rect(70 + i * 290, 130, 260, 236) for i in range(3)]

    def handle_event(self, e):
        d = nav_dir(e)
        if d and d[0]:
            self.idx = (self.idx + d[0]) % 3
            audio.play("move")
        elif is_confirm(e):
            self.choose(STARTER_IDS[self.idx])
        elif e.type == pygame.MOUSEMOTION:
            for i, c in enumerate(self.cards):
                if c.collidepoint(e.pos):
                    self.idx = i
        elif is_click(e):
            for i, c in enumerate(self.cards):
                if c.collidepoint(e.pos):
                    self.idx = i
                    self.choose(STARTER_IDS[i])
            if self.choose_rect.collidepoint(e.pos):
                self.choose(STARTER_IDS[self.idx])

    choose_rect = pygame.Rect(0, 0, 0, 0)

    def choose(self, sid):
        eng = self.engine
        st = eng.state
        st.party = [create_scimon(sid, 5)]
        st.captured = {sid}
        st.rival_species = RIVAL_COUNTER[sid]
        audio.play("capture")
        eng.fade_to(lambda: eng.replace(make_rival_scene(eng, sid, st.rival_species)))

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        circuit_backdrop(surf, self.t)
        panel(surf, (40, 22, W - 80, 84), "message")
        msg = ("Prof. Venn: Ah, you made it. These three Scimons responded to your Scanner. "
               "Choose the partner you'll research together.")
        for k, ln in enumerate(wrap_text(msg, "body", 30, W - 140)):
            text(surf, ln, (68, 36 + k * 30), "body", 30, (248, 246, 230), shadow=(20, 40, 38))
        for i, sid in enumerate(STARTER_IDS):
            sp, c, sel = SPECIES[sid], self.cards[i], i == self.idx
            panel(surf, c, "button_sel" if sel else "button", blur=False)
            img = assets.mon_image(sid, 180, 140)
            bob = math.sin(self.t * 4) * 5 if sel else 0
            surf.blit(img, (c.centerx - img.get_width() // 2, c.y + 150 - img.get_height() + bob))
            text(surf, sp.name, (c.centerx, c.y + 164), "display", 16, INK, anchor="midtop")
            w = sum(assets.font("display", 8).size(t.upper())[0] + 14 for t in sp.types)
            x = c.centerx - w // 2
            for t in sp.types:
                x = type_chip(surf, t, x, c.y + 196)
        sp = SPECIES[STARTER_IDS[self.idx]]
        info = pygame.Rect(70, 372, W - 140, 252)
        panel(surf, info, "panel")
        text(surf, sp.name, (info.x + 24, info.y + 16), "display", 16, INK)
        text(surf, sp.classification, (info.right - 24, info.y + 16), "body", 32, TEAL_DARK, anchor="topright")
        for k, ln in enumerate(wrap_text(sp.desc, "body", 28, info.w - 48)[:2]):
            text(surf, ln, (info.x + 24, info.y + 48 + k * 24), "body", 28, INK)
        rows = [[("HP", sp.b_hp), ("PWR", sp.b_power), ("DEF", sp.b_def), ("SPD", sp.b_speed)],
                [("S.PWR", sp.b_sp), ("S.DEF", sp.b_spdef), ("STB", sp.b_stab)],
                [("ABL", sp.ability)]]
        for r, row in enumerate(rows):
            for c, (lab, v) in enumerate(row):
                x, y = info.x + 24 + c * 200, info.y + 104 + r * 28
                text(surf, lab, (x, y), "body", 28, TEAL_DARK)
                text(surf, v, (x + 78, y), "body", 28, INK)
        self.choose_rect = pygame.Rect(info.centerx - 170, info.bottom - 52, 340, 38)
        draw_button(surf, Button(f"CHOOSE {sp.name.upper()}", self.choose_rect, accent=True), selected=True, size=16)


# =========================================================================== rival + flow
def make_rival_scene(engine, starter_id, rival_id):
    starter, rival = SPECIES[starter_id], SPECIES[rival_id]
    lines = [
        "Outside the lab, someone's waiting for you.",
        f"{RIVAL_NAME}: So the professor gave you {starter.name}, huh, {{name}}?",
        f"{RIVAL_NAME}: Then I'll take {rival.name}!",
        f"{RIVAL_NAME}: I don't care about type charts, {{name}}. I just want to battle!",
        f"{RIVAL_NAME}: Let's battle - right here, right now!",
    ]
    return DialogueScene(lines, on_done=lambda: start_rival_battle(engine), bg=outdoor_bg,
                         sprites=[starter_id, rival_id], pop_on_done=False)


def start_rival_battle(engine):
    from battle import BattleScene, new_battle
    from overworld import OverworldScene
    st = engine.state
    enemy = create_scimon(st.rival_species, 5)
    battle = new_battle(st.party, enemy, st.battle_bag(), st.battle_modules(), trainer=RIVAL_NAME)

    def done(res):
        st.merge_battle_result(res["bag"], res["modules"])
        st.party = res["party"]
        st.rival_beaten = res["outcome"] == "win"
        if res["outcome"] == "lose":
            st.heal_party()
            engine.toast.show(f"{RIVAL_NAME} won this time... you dropped \u00a2{-res['credits']}, but your Scimon is back to full strength.", 3.5)
        else:
            engine.toast.show(f"You beat {RIVAL_NAME}! +\u00a2{res['credits']} prize. Time to start your journey.", 3.5)

    def apply():
        engine.replace(OverworldScene())
        engine.push(BattleScene(battle, done, allow_capture=False, allow_run=False))
        audio.play("capture")

    engine.fade_to(apply, color=(255, 255, 255))


def start_game_flow(engine):
    """New Game: build your researcher (name, skin, hair, outfit), then wake up at home."""
    engine.fade_to(lambda: engine.replace(CustomizeScene()))
