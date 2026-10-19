"""Story scenes: title screen, click-through dialogue, the wake-up scene, starter selection and the rival
encounter, plus the flow that chains them (Title -> Wake -> Starter -> Rival -> Battle -> Overworld).

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
from ui import (ButtonGrid, Button, DialogueBox, circuit_backdrop, draw_button, is_back, is_click, is_confirm, label_chip, nav_dir,
                panel, text, type_chip, wrap_text)

RIVAL_NAME = "Kael"
# Kael always picks the starter that is WEAK against yours: florabot > aquabit > pyrodrive > florabot.
RIVAL_COUNTER = {"florabot": "aquabit", "aquabit": "pyrodrive", "pyrodrive": "florabot"}

WAKE_LINES = [
    "...",
    "You wake up in your room in Riven Town.",
    "Prof. Venn messaged you last night: a new Scimon is ready and waiting at the lab.",
    "Time to get up and go see the professor.",
]


# =========================================================================== dialogue
class DialogueScene(Scene):
    """Click-through text. With `bg` it is a full-screen scene (opaque); without, a bottom overlay on whatever
    is below. `sprites` are species ids shown bobbing above the box."""
    state_id = StateId.DIALOGUE

    def __init__(self, lines, on_done=None, bg=None, sprites=None, pop_on_done=True):
        self.lines, self.on_done, self.bg, self.sprites = lines, on_done, bg, sprites or []
        self.pop_on_done = pop_on_done
        self.opaque = bg is not None
        self.box = DialogueBox(lines, size=38 if bg else 36)
        self.t = 0.0
        self.done = False

    def handle_event(self, e):
        if self.done:
            return
        if is_confirm(e) or is_click(e):
            audio.play("move")
            if self.box.advance():
                self.done = True
                if self.pop_on_done:
                    self.engine.pop(self)
                if self.on_done:
                    self.on_done()

    def update(self, dt):
        self.t += dt
        self.box.update(dt)

    def draw(self, surf):
        if self.bg:
            self.bg(surf, self.t)
            n = len(self.sprites)
            for k, sid in enumerate(self.sprites):
                img = assets.mon_image(sid, 210, 210)
                x = W // 2 + (k - (n - 1) / 2) * 290 - img.get_width() // 2
                y = 430 - img.get_height() + math.sin(self.t * 2.6 + k * 1.3) * 4
                shadow = pygame.Surface((img.get_width() // 1.4, 22), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (10, 10, 14, 70), shadow.get_rect())
                surf.blit(shadow, shadow.get_rect(midtop=(x + img.get_width() // 2, 424)))
                surf.blit(img, (x, y))
        self.box.draw(surf)


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
    surf.fill((207, 227, 198))
    for y in range(352, H):
        k = (y - 352) / (H - 352)
        pygame.draw.line(surf, (int(183 - 16 * k), int(207 - 14 * k), int(166 - 21 * k)), (0, y), (W, y))
    for i in range(5):
        x = (i * 230 - t * 10) % (W + 240) - 120
        cl = pygame.Surface((140, 36), pygame.SRCALPHA)
        pygame.draw.ellipse(cl, (255, 255, 255, 140), cl.get_rect())
        surf.blit(cl, (x, 50 + (i * 53) % 120))


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
                        self.engine.toast.show("Welcome back! Progress loaded.", 2.5)
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
        f"{RIVAL_NAME}: So the professor gave you {starter.name}, huh?",
        f"{RIVAL_NAME}: Then I'll take {rival.name}!",
        f"{RIVAL_NAME}: I don't care about type charts. I just want to battle!",
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
            engine.toast.show(f"{RIVAL_NAME} won this time... but your Scimon is back to full strength.", 3.5)
        else:
            engine.toast.show(f"You beat {RIVAL_NAME}! Time to start your journey.", 3.5)

    def apply():
        engine.replace(OverworldScene())
        engine.push(BattleScene(battle, done, allow_capture=False, allow_run=False))
        audio.play("capture")

    engine.fade_to(apply, color=(255, 255, 255))


def start_game_flow(engine):
    def to_wake():
        engine.replace(DialogueScene(WAKE_LINES, on_done=to_starter, bg=bedroom_bg, pop_on_done=False))

    def to_starter():
        engine.fade_to(lambda: engine.replace(StarterScene()))

    engine.fade_to(to_wake)
