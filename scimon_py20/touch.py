"""Touch / mobile support: an on-screen D-pad with A, B and PACK buttons.

The game itself always renders to a fixed 960x640 surface.  On a touch device the engine opens a bigger
window and places that surface inside it, so the controls never cover the game:

    side     phones in landscape  -> game in the middle, D-pad in the left gutter, A/B/PACK in the right
    stack    phones in portrait   -> game on top, controls underneath
    overlay  tablets / squarish   -> game fills the window, translucent controls drawn over the corners
    plain    desktop              -> exactly the old behaviour (no controls)

Fingers are tracked one by one (hold the D-pad with one thumb, press A with the other).  Buttons are turned
into ordinary KEYDOWN events, so every scene keeps working unchanged; the overworld reads `held_dir()` for
smooth walking.  Taps on the game area become normal mouse clicks (SDL already does this in the browser; a
small fallback covers builds that do not).

Testing on a desktop:  SCIMON_TOUCH=1 SCIMON_TOUCH_SIZE=844x390 python main.py   (any WxH, e.g. 390x844 portrait)
"""
import math
import os
import sys
from collections import namedtuple

import pygame

from settings import H, W

Layout = namedtuple("Layout", "mode size game_pos")
PLAIN = Layout("plain", (W, H), (0, 0))

REPEAT_DELAY, REPEAT_RATE = 0.40, 0.13      # menu auto-repeat while the D-pad is held
TAP_MAX_TIME, TAP_MAX_MOVE = 0.35, 0.03     # a finger counts as a tap below this duration / normalised travel
BG = (12, 15, 26)

_FINGER = tuple(getattr(pygame, n, -1) for n in ("FINGERDOWN", "FINGERMOTION", "FINGERUP"))
_ARROW_KEYS = {"up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT}

# What the player sees held right now ("up"/"down"/"left"/"right"/None); read by OverworldScene.
_held = None


def held_dir():
    return _held


def reset():
    global _held
    _held = None


# --------------------------------------------------------------------------- environment
def _browser():
    if sys.platform != "emscripten":
        return None
    try:
        import platform
        return platform.window
    except Exception:
        return None


def window_size():
    """Size of the browser viewport (or the SCIMON_TOUCH_SIZE test override); None when unknown."""
    env = os.environ.get("SCIMON_TOUCH_SIZE", "")
    if "x" in env:
        try:
            w, h = env.lower().split("x")
            return int(w), int(h)
        except ValueError:
            pass
    win = _browser()
    if win is not None:
        try:
            w, h = int(win.innerWidth), int(win.innerHeight)
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass
    return None


def detect():
    """True on phones and tablets (coarse primary pointer), or when SCIMON_TOUCH is set."""
    if os.environ.get("SCIMON_TOUCH", "") not in ("", "0"):
        return True
    win = _browser()
    if win is None:
        return False
    try:
        if bool(win.matchMedia("(pointer: coarse)").matches):
            return True
    except Exception:
        pass
    try:
        return int(win.navigator.maxTouchPoints) > 0 and not bool(win.matchMedia("(pointer: fine)").matches)
    except Exception:
        return False


def vibrate(ms=10):
    win = _browser()
    if win is not None:
        try:
            win.navigator.vibrate(ms)
        except Exception:
            pass


# --------------------------------------------------------------------------- layout
def compute_layout(win, touch):
    """Pick the canvas size / game position for a window of `win` = (w, h) pixels."""
    if not touch or not win:
        return PLAIN
    ww, wh = win
    aspect = ww / float(max(1, wh))
    if aspect >= 1.6:                                           # wide phone: controls in the side gutters
        cw = min(1500, max(1300, int(round(H * aspect))))
        cw += cw % 2
        return Layout("side", (cw, H), ((cw - W) // 2, 0))
    if aspect >= 1.0:                                           # tablet landscape: translucent overlay
        return Layout("overlay", (W, H), (0, 0))
    extra = int(round(W / aspect)) - H                          # portrait: game on top, controls below
    extra = max(340, min(extra, 720))
    return Layout("stack", (W, H + extra), (0, 0))


def geometry(layout):
    """Control shapes in canvas pixels: dict(dpad=(cx,cy,r), a=(cx,cy,r), b=(cx,cy,r), pack=(x,y,w,h))."""
    cw, ch = layout.size
    if layout.mode == "side":
        gx = layout.game_pos[0]
        pr = max(60, min(gx // 2 - 10, 100))
        br = int(max(34, min(56, gx * 0.25)))
        rcx = cw - gx // 2
        pw = min(gx - 24, 160)
        return dict(dpad=(gx // 2, 410, pr),
                    a=(rcx + int(br * 0.85), 410 - int(br * 0.8), br),
                    b=(rcx - int(br * 0.85), 410 + int(br * 0.8), br),
                    pack=(rcx - pw // 2, 90, pw, 60))
    if layout.mode == "stack":
        top, ah = H, ch - H
        cy = top + int(ah * 0.56)
        pr = min(int(ah * 0.40), 200)
        br = min(int(ah * 0.17), 80)
        return dict(dpad=(260, cy, pr),
                    a=(730 + int(br * 0.85), cy - int(br * 0.8), br),
                    b=(730 - int(br * 0.85), cy + int(br * 0.8), br),
                    pack=(420, top + int(ah * 0.12) - 32, 180, 64))
    return dict(dpad=(125, H - 130, 95),                         # overlay
                a=(W - 60, H - 150, 52),
                b=(W - 140, H - 72, 52),
                pack=(W // 2 - 65, H - 62, 130, 50))


def _dist(pos, c):
    return math.hypot(pos[0] - c[0], pos[1] - c[1])


class TouchControls:
    """Owns the on-screen buttons: hit-testing, finger tracking, drawing."""

    def __init__(self, layout):
        self.layout = layout
        self.geo = geometry(layout)
        self.alpha = 0.62 if layout.mode == "overlay" else 1.0
        self.fingers = {}            # finger id -> "dpad" | "a" | "b" | "pack"
        self.pressed = set()         # "a" / "b" / "pack" currently down (for drawing)
        self.dir = None
        self._rep_t = None           # None = no auto-repeat armed
        self._rep_scene = None
        self._img = None
        self.reset()

    # ---- state ---------------------------------------------------------------------------
    def reset(self):
        global _held
        self.fingers.clear()
        self.pressed.clear()
        self.dir = None
        self._rep_t = None
        _held = None

    def _set_dir(self, d, engine):
        global _held
        if d == self.dir:
            return
        self.dir = d
        _held = d
        if d:
            self._key(engine, _ARROW_KEYS[d])
            self._rep_t, self._rep_scene = REPEAT_DELAY, engine.top
            vibrate(6)
        else:
            self._rep_t = None

    @staticmethod
    def _key(engine, k):
        engine.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))

    # ---- hit testing ---------------------------------------------------------------------
    def _pick(self, pos):
        """Name of the control under `pos` (generous touch radius, nearest centre wins), else None."""
        best, best_ratio = None, 1.0
        for name in ("dpad", "a", "b"):
            cx, cy, r = self.geo[name]
            ratio = _dist(pos, (cx, cy)) / (r * (1.3 if name == "dpad" else 1.25))
            if ratio <= best_ratio:
                best, best_ratio = name, ratio
        px, py, pw, ph = self.geo["pack"]
        if px - 10 <= pos[0] <= px + pw + 10 and py - 10 <= pos[1] <= py + ph + 10:
            return "pack"
        return best

    def hit(self, pos):
        """True if a (mouse-style) point lies on a control: such clicks must not reach the game underneath."""
        return self.layout.mode == "overlay" and self._pick(pos) is not None

    def _dir_at(self, pos):
        cx, cy, r = self.geo["dpad"]
        dx, dy = pos[0] - cx, pos[1] - cy
        if dx * dx + dy * dy < (r * 0.22) ** 2:
            return None
        ax, ay = abs(dx), abs(dy)
        if self.dir in ("left", "right"):          # hysteresis: do not flicker along the diagonals
            horiz = not (ay > ax * 1.35)
        elif self.dir in ("up", "down"):
            horiz = ax > ay * 1.35
        else:
            horiz = ax >= ay
        if horiz:
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"

    # ---- events --------------------------------------------------------------------------
    def handle(self, e, engine, pos):
        """Process a finger event at canvas position `pos`. Returns True when it landed on a control."""
        fid = getattr(e, "finger_id", 0)
        if e.type == _FINGER[0]:                                        # down
            name = self._pick(pos)
            if name is None:
                return False
            self.fingers[fid] = name
            if name == "dpad":
                self._set_dir(self._dir_at(pos), engine)
            else:
                self.pressed.add(name)
                vibrate(10)
                self._key(engine, {"a": pygame.K_RETURN, "b": pygame.K_x, "pack": pygame.K_i}[name])
            return True
        name = self.fingers.get(fid)
        if name is None:
            return False
        if e.type == _FINGER[1]:                                        # move
            if name == "dpad":
                self._set_dir(self._dir_at(pos), engine)
        elif e.type == _FINGER[2]:                                      # up
            del self.fingers[fid]
            if name == "dpad":
                self._set_dir(None, engine)
            elif name not in self.fingers.values():
                self.pressed.discard(name)
        return True

    def update(self, dt, engine):
        if self._rep_t is None or not self.dir:
            return
        if engine.top is not self._rep_scene:        # a menu opened / closed under the thumb: stop repeating
            self._rep_t = None
            return
        self._rep_t -= dt
        if self._rep_t <= 0:
            self._rep_t = REPEAT_RATE
            self._key(engine, _ARROW_KEYS[self.dir])

    # ---- drawing -------------------------------------------------------------------------
    def _build(self):
        import ui                                   # late: needs fonts, so only when first drawn
        a = 255
        img = {}
        cx, cy, r = self.geo["dpad"]
        size = 2 * r + 6
        c = (size // 2, size // 2)

        def pad(active):
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(s, (18, 24, 44, 150), c, r)
            pygame.draw.circle(s, (190, 210, 255, 170), c, r, 3)
            pygame.draw.circle(s, (190, 210, 255, 90), c, int(r * 0.22), 2)
            for d, (vx, vy) in {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.items():
                mx, my = c[0] + vx * r * 0.62, c[1] + vy * r * 0.62
                k = r * 0.2
                px, py = -vy, vx                    # perpendicular
                tri = [(mx + vx * k, my + vy * k), (mx - vx * k + px * k, my - vy * k + py * k),
                       (mx - vx * k - px * k, my - vy * k - py * k)]
                if d == active:
                    pygame.draw.circle(s, (60, 110, 90, 200), (int(mx), int(my)), int(r * 0.26))
                pygame.draw.polygon(s, (125, 255, 176, a) if d == active else (230, 238, 255, 205), tri)
            return s

        img["dpad"] = {None: pad(None), **{d: pad(d) for d in _ARROW_KEYS}}
        for name, col, label in (("a", (209, 85, 47), "A"), ("b", (90, 138, 134), "B")):
            _, _, br = self.geo[name]
            row = {}
            for down in (False, True):
                s = pygame.Surface((2 * br + 6, 2 * br + 6), pygame.SRCALPHA)
                m = (br + 3, br + 3)
                shade = 1.25 if down else 1.0
                pygame.draw.circle(s, tuple(min(255, int(v * shade)) for v in col) + (200,), m, br)
                pygame.draw.circle(s, (240, 244, 255, 200), m, br, 3)
                t = ui.render_text(label, "display", int(br * 0.7), (255, 255, 255))
                s.blit(t, t.get_rect(center=m))
                row[down] = s
            img[name] = row
        px, py, pw, ph = self.geo["pack"]
        row = {}
        for down in (False, True):
            s = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pygame.draw.rect(s, (60, 80, 120, 215) if down else (23, 29, 48, 190), (0, 0, pw, ph), border_radius=ph // 3)
            pygame.draw.rect(s, (190, 210, 255, 190), (0, 0, pw, ph), 3, border_radius=ph // 3)
            t = ui.render_text("PACK", "display", max(10, int(ph * 0.3)), (240, 244, 255))
            s.blit(t, t.get_rect(center=(pw // 2, ph // 2)))
            row[down] = s
        img["pack"] = row
        if self.alpha < 1.0:                        # translucent overlay: bake the opacity in once
            for v in img.values():
                for s in (v.values() if isinstance(v, dict) else ()):
                    s.set_alpha(int(255 * self.alpha))
        self._img = img

    def draw(self, surf):
        if self._img is None:
            self._build()
        img = self._img
        parts = []
        cx, cy, r = self.geo["dpad"]
        parts.append((img["dpad"][self.dir], (cx - r - 3, cy - r - 3)))
        for name in ("a", "b"):
            bx, by, br = self.geo[name]
            parts.append((img[name][name in self.pressed], (bx - br - 3, by - br - 3)))
        px, py, _, _ = self.geo["pack"]
        parts.append((img["pack"]["pack" in self.pressed], (px, py)))
        for s, pos in parts:
            surf.blit(s, pos)
