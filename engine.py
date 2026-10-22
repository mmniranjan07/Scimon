"""Game engine: the scene/state machine and the main loop.

Every screen is a `Scene` (START_MENU, WAKE, STARTER_SELECT, RIVAL, OVERWORLD, BATTLE, DIALOGUE, INVENTORY,
SHOP, DATABASE, SERVICE...). Scenes live on a stack: the top scene receives input, scenes below keep
drawing (when the scene above is translucent) and may keep animating (`background_update`). Nothing ever
blocks -- dialogue, battles and transitions are all driven one frame at a time by `update(dt)`."""
import asyncio
import enum
import math
import sys

import pygame

import assets
import audio
import savegame
import touch
from settings import FADE_TIME, FPS, W, H
from state import GameState
from ui import Toast, fade


class StateId(enum.Enum):
    START_MENU = "start_menu"
    CUSTOMIZE = "customize"
    WAKE = "wake"
    STARTER_SELECT = "starter_select"
    RIVAL = "rival"
    OVERWORLD = "overworld"
    BATTLE = "battle"
    DIALOGUE = "dialogue"
    INVENTORY = "inventory"
    SHOP = "shop"
    DATABASE = "database"
    SERVICE = "service"


class Scene:
    state_id = StateId.DIALOGUE
    opaque = True              # False => the scene below is drawn first (modals, dialogue overlays)
    background_update = False  # True => keeps update()-ing while covered by another scene

    engine = None

    def on_enter(self): pass
    def on_exit(self): pass
    def handle_event(self, e): pass
    def update(self, dt): pass
    def draw(self, surf): pass


class Engine:
    def __init__(self, headless=False, preload=True):
        pygame.init()
        pygame.display.set_caption("SCI-MON - The Scientific Monster RPG (Python)")
        # Touch devices get a bigger canvas with on-screen controls around the 960x640 game (see touch.py).
        self.touch_on = False if headless else touch.detect()
        self._win = touch.window_size()
        self.layout = touch.compute_layout(self._win, self.touch_on)
        self.controls = None
        self.canvas = None
        self._tap = None                  # finger-down bookkeeping for the tap fallback
        self._saw_touch_mouse = False     # True once SDL itself turns touches into mouse events
        self._win_t = 0.0
        self._apply_layout(self.layout)
        self.clock = pygame.time.Clock()
        if preload:
            assets.preload()
        audio.init()
        self.state = GameState()          # global data singleton: party, storage, bag, credits
        self.toast = Toast()
        self.scenes = []
        self.debug = False
        self.running = True
        self.time = 0.0
        self._transition = None           # dict(phase, t, apply)
        self._save_t = 0.0
        self.autosave = not headless      # tests/headless runs never touch the save file
        self._saved = None                # last string written by the autosave

    # ---- display / touch layout -----------------------------------------------------------
    def _apply_layout(self, layout):
        flags = pygame.SCALED | pygame.RESIZABLE
        if sys.platform == "emscripten":      # browser (pygbag): plain canvas, the page does the scaling
            flags = 0
        try:
            self.screen = pygame.display.set_mode(layout.size, flags)
        except pygame.error:
            self.screen = pygame.display.set_mode(layout.size)
        self.layout = layout
        if layout.mode == "plain":
            self.canvas = self.controls = None
            touch.reset()
        else:
            self.canvas = pygame.Surface((W, H))
            try:
                self.canvas = self.canvas.convert()
            except pygame.error:
                pass
            if self.controls:
                self.controls.reset()
            self.controls = touch.TouchControls(layout)

    def _enable_touch(self):
        """First finger on a device we did not recognise as touch (hybrid laptop, odd browser): turn controls on."""
        self.touch_on = True
        self._apply_layout(touch.compute_layout(self._win or (W, H), True))

    def _check_window(self, dt):
        """Browser only: follow rotations / resizes by re-choosing the layout (side <-> stack <-> overlay)."""
        self._win_t += dt
        if self._win_t < 0.5 or not self.touch_on:
            return
        self._win_t = 0.0
        win = touch.window_size()
        if win and win != self._win:
            self._win = win
            new = touch.compute_layout(win, True)
            if new != self.layout:
                self._apply_layout(new)

    def _to_game(self, pos):
        gx, gy = self.layout.game_pos
        return pos[0] - gx, pos[1] - gy

    def _in_game(self, pos):
        x, y = self._to_game(pos)
        return 0 <= x < W and 0 <= y < H

    def _finger(self, e):
        """Route a touch event: on-screen buttons first, everything else is a tap on the game."""
        if not self.controls:
            if e.type != getattr(pygame, "FINGERDOWN", -1) or sys.platform != "emscripten":
                return
            self._enable_touch()
        sw, sh = self.screen.get_size()
        pos = (e.x * sw, e.y * sh)
        if self.controls.handle(e, self, pos):
            return
        fid = getattr(e, "finger_id", 0)
        if e.type == pygame.FINGERDOWN and self._in_game(pos):
            self._tap = (fid, pos, self.time, False)
        elif e.type == pygame.FINGERUP and self._tap and self._tap[0] == fid:
            _, p0, t0, _ = self._tap
            moved = math.hypot(pos[0] - p0[0], pos[1] - p0[1]) / max(sw, sh)
            if self.time - t0 <= touch.TAP_MAX_TIME and moved <= touch.TAP_MAX_MOVE:
                self._tap = (fid, pos, self.time + 0.1, True)      # fire shortly, unless SDL sent its own click
            else:
                self._tap = None

    def _fire_tap(self):
        fid, pos, due, armed = self._tap
        if not armed or self.time < due:
            return
        self._tap = None
        if self._saw_touch_mouse or not self._in_game(pos) or not self.top or self._transition:
            return
        gp = self._to_game(pos)
        self.top.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=gp, rel=(0, 0), buttons=(0, 0, 0)))
        self.top.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=gp, button=1))

    # ---- state machine -----------------------------------------------------------------
    @property
    def top(self):
        return self.scenes[-1] if self.scenes else None

    def push(self, scene):
        scene.engine = self
        self.scenes.append(scene)
        scene.on_enter()
        return scene

    def pop(self, scene=None):
        scene = scene or self.top
        if scene in self.scenes:
            self.scenes.remove(scene)
            scene.on_exit()

    def replace(self, scene):
        for s in list(self.scenes):
            self.pop(s)
        return self.push(scene)

    def find(self, state_id):
        return next((s for s in reversed(self.scenes) if s.state_id == state_id), None)

    def fade_to(self, apply, color=(0, 0, 0)):
        """Fade out, run `apply()` (swap scenes), fade back in. Input is ignored meanwhile."""
        if self._transition is None:
            self._transition = {"phase": "out", "t": 0.0, "apply": apply, "color": color}

    @property
    def transitioning(self):
        return self._transition is not None

    # ---- loop -----------------------------------------------------------------------------
    def step(self, dt):
        """Advance the whole game by dt seconds (used by run() and by the headless tests)."""
        self.time += dt
        self._save_t += dt
        if self._save_t >= 3.0:           # autosave (only writes when something changed)
            self._save_t = 0.0
            if getattr(self, "autosave", True):
                self._saved = savegame.save(self.state, self._saved)
        tr = self._transition
        if tr:
            tr["t"] += dt
            if tr["phase"] == "out" and tr["t"] >= FADE_TIME:
                tr["apply"]()
                tr["phase"], tr["t"] = "in", 0.0
            elif tr["phase"] == "in" and tr["t"] >= FADE_TIME:
                self._transition = None
        top = self.top
        for s in list(self.scenes):
            if s is top or s.background_update:
                s.update(dt)
        self.toast.update(dt)
        if self.controls:
            self.controls.update(dt, self)
        if self._tap:
            self._fire_tap()

    def dispatch(self, e):
        if e.type in touch._FINGER:
            self._finger(e)
            return
        if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            if getattr(e, "touch", False):
                self._saw_touch_mouse = True
            if self.layout.mode != "plain":
                # only clicks inside the game reach it (with game coordinates); clicks on a control are swallowed
                if (self.controls and self.controls.hit(e.pos)) or not self._in_game(e.pos):
                    return
                e.pos = self._to_game(e.pos)
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_F3:
            self.debug = not self.debug
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_m:
            self.toast.show("SFX OFF" if audio.toggle_mute() else "SFX ON", 1.0)
        elif self.top and not self._transition:
            self.top.handle_event(e)

    def _draw_scenes(self, surf):
        start = max((i for i, s in enumerate(self.scenes) if s.opaque), default=0)
        for s in self.scenes[start:]:
            s.draw(surf)
        self.toast.draw(surf)
        tr = self._transition
        if tr:
            p = min(1.0, tr["t"] / FADE_TIME)
            fade(surf, p if tr["phase"] == "out" else 1 - p, tr["color"])

    def render(self, surf=None):
        if surf is not None or self.layout.mode == "plain":
            surf = surf or self.screen
            self._draw_scenes(surf)
            return surf
        self._draw_scenes(self.canvas)             # touch layout: game on its own 960x640 surface ...
        self.screen.fill(touch.BG)
        self.screen.blit(self.canvas, self.layout.game_pos)
        self.controls.draw(self.screen)            # ... with the controls drawn around / over it
        return self.screen

    async def run_async(self):
        """Main loop. `await asyncio.sleep(0)` each frame hands control back to the browser when the
        game runs as WebAssembly (pygbag); on desktop it is a no-op, so behaviour is unchanged."""
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)      # clamp so a stall can't teleport the player
            for e in pygame.event.get():
                self.dispatch(e)
            if sys.platform == "emscripten":
                self._check_window(dt)
            self.step(dt)
            self.render()
            pygame.display.flip()
            await asyncio.sleep(0)
        pygame.quit()
        if sys.platform != "emscripten":
            sys.exit(0)

    def run(self):
        """Blocking desktop entry (kept for tools/tests)."""
        asyncio.run(self.run_async())
