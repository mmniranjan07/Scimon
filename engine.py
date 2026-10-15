"""Game engine: the scene/state machine and the main loop.

Every screen is a `Scene` (START_MENU, WAKE, STARTER_SELECT, RIVAL, OVERWORLD, BATTLE, DIALOGUE, INVENTORY,
SHOP, DATABASE, SERVICE...). Scenes live on a stack: the top scene receives input, scenes below keep
drawing (when the scene above is translucent) and may keep animating (`background_update`). Nothing ever
blocks -- dialogue, battles and transitions are all driven one frame at a time by `update(dt)`."""
import asyncio
import enum
import sys

import pygame

import assets
import audio
from settings import FADE_TIME, FPS, W, H
from state import GameState
from ui import Toast, fade


class StateId(enum.Enum):
    START_MENU = "start_menu"
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
    def __init__(self, headless=False):
        pygame.init()
        pygame.display.set_caption("SCI-MON - The Scientific Monster RPG (Python)")
        flags = pygame.SCALED | pygame.RESIZABLE
        if sys.platform == "emscripten":      # browser (pygbag): plain canvas, the page does the scaling
            flags = 0
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        assets.preload()
        audio.init()
        self.state = GameState()          # global data singleton: party, storage, bag, credits
        self.toast = Toast()
        self.scenes = []
        self.debug = False
        self.running = True
        self.time = 0.0
        self._transition = None           # dict(phase, t, apply)

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

    def dispatch(self, e):
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

    def render(self, surf=None):
        surf = surf or self.screen
        start = max((i for i, s in enumerate(self.scenes) if s.opaque), default=0)
        for s in self.scenes[start:]:
            s.draw(surf)
        self.toast.draw(surf)
        tr = self._transition
        if tr:
            p = min(1.0, tr["t"] / FADE_TIME)
            fade(surf, p if tr["phase"] == "out" else 1 - p, tr["color"])
        return surf

    async def run_async(self):
        """Main loop. `await asyncio.sleep(0)` each frame hands control back to the browser when the
        game runs as WebAssembly (pygbag); on desktop it is a no-op, so behaviour is unchanged."""
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)      # clamp so a stall can't teleport the player
            for e in pygame.event.get():
                self.dispatch(e)
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
