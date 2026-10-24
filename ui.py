"""UI toolkit: frosted-glass panels, pixel-font text rendering, the typewriter dialogue box, HP bars,
type/status chips and a keyboard + mouse menu grid.

Everything animated here advances with delta time (`dt`, seconds) so it behaves identically at any
frame rate. Nothing in this module ever blocks -- widgets are plain objects that scenes update()
and draw() every frame."""
import math

import pygame

import assets
from data import STATUS_INFO, TYPE_COLORS
from settings import (CREAM, CREAM_2, EXP_BLUE, HP_GREEN, HP_RED, HP_YELLOW, INK, ORANGE, SHADE, STAB_BLUE,
                      TEAL_DARK, W, H, hexc)

# --------------------------------------------------------------------------- input helpers
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_x, pygame.K_BACKSPACE)
_NAV = {pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
        pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1)}


def is_confirm(e):
    return e.type == pygame.KEYDOWN and e.key in CONFIRM_KEYS


def is_back(e):
    return e.type == pygame.KEYDOWN and e.key in BACK_KEYS


def nav_dir(e):
    """(dx, dy) for an arrow/WASD key press, else None."""
    if e.type != pygame.KEYDOWN:
        return None
    return _NAV.get(e.key)


def is_click(e):
    return e.type == pygame.MOUSEBUTTONDOWN and e.button == 1


# --------------------------------------------------------------------------- text
_text_cache = {}


def render_text(s, kind="body", size=28, color=INK):
    key = (s, kind, size, color)
    img = _text_cache.get(key)
    if img is None:
        if len(_text_cache) > 1500:      # bounded cache: rebuild from scratch rather than leak
            _text_cache.clear()
        img = assets.font(kind, size).render(s, True, color)
        _text_cache[key] = img
    return img


def text(surf, s, pos, kind="body", size=28, color=INK, anchor="topleft", shadow=None, alpha=None):
    """Draw `s` at pos. anchor is any pygame.Rect attribute name (topleft, center, midtop, topright...)."""
    img = render_text(str(s), kind, size, color)
    r = img.get_rect()
    setattr(r, anchor, (int(pos[0]), int(pos[1])))
    if shadow:
        surf.blit(render_text(str(s), kind, size, shadow), r.move(max(1, size // 14), max(1, size // 14)))
    if alpha is not None and alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, r)
    return r


def wrap_text(s, kind, size, width):
    """Greedy word wrap using the real font metrics."""
    f = assets.font(kind, size)
    lines, cur = [], ""
    for word in s.split(" "):
        test = (cur + " " + word).strip()
        if f.size(test)[0] <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


# --------------------------------------------------------------------------- frosted-glass panels
# kind -> (top rgba, bottom rgba, border rgba, corner radius, blur factor, text colour)
PANEL_KINDS = {
    "panel": ((243, 239, 214, 238), (226, 219, 185, 214), (255, 255, 255, 120), 16, 8),
    "message": ((95, 145, 141, 225), (58, 99, 95, 205), (255, 255, 255, 90), 18, 8),
    "inner": ((255, 255, 255, 52), (255, 255, 255, 36), (255, 255, 255, 80), 12, 0),
    "button": ((243, 239, 214, 225), (224, 217, 182, 170), (255, 255, 255, 120), 12, 0),
    "button_sel": ((250, 246, 226, 240), (232, 226, 193, 200), (209, 85, 47, 255), 12, 0),
    "button_accent": ((226, 108, 70, 240), (190, 74, 40, 230), (255, 255, 255, 110), 12, 0),
    "chip": ((243, 239, 214, 220), (224, 217, 182, 190), (255, 255, 255, 110), 10, 0),
}

_mask_cache, _overlay_cache, _shadow_cache = {}, {}, {}


def _rounded_mask(w, h, r):
    key = (w, h, r)
    m = _mask_cache.get(key)
    if m is None:
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, w, h), border_radius=r)
        _mask_cache[key] = m
    return m


def _gradient(w, h, top, bottom):
    g = pygame.Surface((1, 2), pygame.SRCALPHA)
    g.set_at((0, 0), top)
    g.set_at((0, 1), bottom)
    return pygame.transform.smoothscale(g, (w, h))


def _overlay(w, h, kind, border_override=None):
    key = (w, h, kind)
    s = _overlay_cache.get(key)
    if s is None:
        top, bot, border, r, _ = PANEL_KINDS[kind]
        s = _gradient(w, h, top, bot)
        s.blit(_rounded_mask(w, h, r), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(s, border, (0, 0, w, h), 2 if kind == "button_sel" else 1, border_radius=r)
        if kind != "inner":      # soft top highlight, like V34's inset 1px white
            pygame.draw.line(s, (255, 255, 255, 70), (r, 1), (w - r, 1))
        _overlay_cache[key] = s
    return s


def _shadow(w, h, r):
    key = (w, h, r)
    s = _shadow_cache.get(key)
    if s is None:
        pad = 14
        small = pygame.Surface((w // 4 + 8, h // 4 + 8), pygame.SRCALPHA)
        pygame.draw.rect(small, (0, 0, 0, 120), (4, 4, w // 4, h // 4), border_radius=max(1, r // 4))
        s = pygame.transform.smoothscale(small, (w + 32, h + 32))
        _shadow_cache[key] = s
    return s


def _blur(sub):
    w, h = sub.get_size()
    small = pygame.transform.smoothscale(sub, (max(1, w // 8), max(1, h // 8)))
    return pygame.transform.smoothscale(small, (w, h))


def panel(surf, rect, kind="panel", blur=None, shadow=True):
    """Draw a frosted-glass panel: soft shadow, blurred backdrop, tinted gradient, border, highlight."""
    rect = pygame.Rect(rect)
    w, h = rect.size
    if w < 4 or h < 4:
        return
    r = PANEL_KINDS[kind][3]
    do_blur = PANEL_KINDS[kind][4] > 0 if blur is None else blur
    if shadow and kind in ("panel", "message"):
        surf.blit(_shadow(w, h, r), (rect.x - 16, rect.y - 6))
    if do_blur:
        clip = rect.clip(surf.get_rect())
        if clip.w > 4 and clip.h > 4:
            bg = _blur(surf.subsurface(clip)).convert_alpha()
            bg.blit(_rounded_mask(w, h, r).subsurface((clip.x - rect.x, clip.y - rect.y, clip.w, clip.h)), (0, 0),
                    special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(bg, clip.topleft)
    surf.blit(_overlay(w, h, kind), rect.topleft)


# --------------------------------------------------------------------------- bars and chips
def hp_color(ratio):
    return HP_GREEN if ratio > 0.5 else HP_YELLOW if ratio > 0.2 else HP_RED


def bar(surf, rect, ratio, color, segmented=False):
    """Rounded track + fill (V34 .bar-track/.bar-fill)."""
    rect = pygame.Rect(rect)
    ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surf, (28, 32, 36), rect, border_radius=rect.h // 2)
    if ratio > 0:
        fill = pygame.Rect(rect.x + 1, rect.y + 1, max(rect.h - 2, int((rect.w - 2) * ratio)), rect.h - 2)
        pygame.draw.rect(surf, color, fill, border_radius=max(1, fill.h // 2))
        if segmented:        # V34 EXP bar: repeating 4px/2px stripes
            for x in range(fill.x, fill.right, 6):
                pygame.draw.line(surf, (42, 144, 204), (x + 4, fill.y), (x + 4, fill.bottom - 1), 2)
        pygame.draw.line(surf, (255, 255, 255, 90), (fill.x + 2, fill.y), (fill.right - 3, fill.y))
    pygame.draw.rect(surf, (255, 255, 255), rect, 1, border_radius=rect.h // 2)


def label_chip(surf, label, pos, bg, size=8, fg=(255, 255, 255)):
    img = render_text(label, "display", size, fg)
    r = pygame.Rect(pos[0], pos[1], img.get_width() + 10, img.get_height() + 8)
    pygame.draw.rect(surf, bg, r, border_radius=4)
    pygame.draw.rect(surf, (0, 0, 0, 80), r, 1, border_radius=4)
    surf.blit(img, (r.x + 5, r.y + 4))
    return r


def type_chip(surf, t, x, y, size=8):
    r = label_chip(surf, t.upper(), (x, y), hexc(TYPE_COLORS[t]), size)
    return r.right + 4


def status_chip(surf, status, x, y, size=8):
    if not status:
        return x
    abbr, col, _ = STATUS_INFO[status]
    r = label_chip(surf, abbr, (x, y), hexc(col), size)
    return r.right + 4


# --------------------------------------------------------------------------- typewriter + dialogue
class TypeWriter:
    """Reveals text over time. `update(dt)` advances; `skip()` finishes the line instantly."""

    def __init__(self, s="", cps=60.0):
        self.cps = cps
        self.set(s)

    def set(self, s):
        self.full, self.t = s, 0.0

    @property
    def count(self):
        return min(len(self.full), int(self.t * self.cps))

    @property
    def done(self):
        return self.count >= len(self.full)

    def update(self, dt):
        if not self.done:
            self.t += dt

    def skip(self):
        self.t = len(self.full) / self.cps + 1

    @property
    def visible(self):
        return self.full[:self.count]


class DialogueBox:
    """The V34 'message + caret' box. First confirm completes the line, the next advances.
    `advance()` returns True when the last line has been dismissed."""

    def __init__(self, lines=None, rect=None, size=32, kind="message", cps=70.0):
        self.rect = pygame.Rect(rect or (24, H - 168, W - 48, 144))
        self.size, self.kind = size, kind
        self.tw = TypeWriter(cps=cps)
        self.lines, self.i, self.t = [], 0, 0.0
        if lines:
            self.set_lines(lines)

    def set_lines(self, lines):
        self.lines, self.i, self.t = list(lines), 0, 0.0
        self.tw.set(self.lines[0] if self.lines else "")

    @property
    def line(self):
        return self.lines[self.i] if self.lines else ""

    @property
    def waiting(self):
        return self.tw.done

    def advance(self):
        if not self.tw.done:
            self.tw.skip()
            return False
        if self.i + 1 < len(self.lines):
            self.i += 1
            self.tw.set(self.lines[self.i])
            return False
        return True

    def update(self, dt):
        self.t += dt
        self.tw.update(dt)

    def draw(self, surf, speaker_color=None):
        panel(surf, self.rect, self.kind)
        fg = (248, 246, 230) if self.kind == "message" else INK
        shadow = (20, 40, 38) if self.kind == "message" else None
        # wrap using the *full* line so words don't jump between lines while typing
        full_lines = wrap_text(self.line, "body", self.size, self.rect.w - 64)
        shown, y = self.tw.count, self.rect.y + 24
        for ln in full_lines:
            part = ln[:max(0, shown)]
            if part:
                text(surf, part, (self.rect.x + 32, y), "body", self.size, fg, shadow=shadow)
            shown -= len(ln) + 1
            y += int(self.size * 1.05)
        if self.tw.done:
            blink = int(self.t * 2.5) % 2 == 0
            if blink:
                cx, cy = self.rect.right - 38, self.rect.bottom - 30
                pygame.draw.polygon(surf, ORANGE, [(cx - 8, cy - 5), (cx + 8, cy - 5), (cx, cy + 7)])


# --------------------------------------------------------------------------- menu grid
class Button:
    def __init__(self, label, rect, enabled=True, accent=False, tag=None, sub=None, color=None, right=None, icon=None):
        self.label, self.rect, self.enabled, self.accent = label, pygame.Rect(rect), enabled, accent
        self.tag, self.sub, self.color, self.right = tag, sub, color, right
        self.icon = icon                      # MPW UI icon name (assets/mpw/ui/<icon>.png), drawn at the left edge


# MPW UI icons: options1-4 have a highlighted twin options5-8 (white outline) used while the button is selected
ICON_SELECTED = {"options1": "options5", "options2": "options6", "options3": "options7", "options4": "options8"}


def icon_chip(surf, icon, pos, bg, scale=2):
    """Colour chip carrying an MPW bar icon (heart, spark ...), the pixel-art replacement for the HP / STB / EXP text chips."""
    img = assets.ui_icon(icon, scale)
    r = pygame.Rect(pos[0], pos[1], img.get_width() + 10, img.get_height() + 4)
    pygame.draw.rect(surf, bg, r, border_radius=4)
    pygame.draw.rect(surf, (0, 0, 0, 80), r, 1, border_radius=4)
    surf.blit(img, (r.x + 5, r.y + 2))
    return r


class ButtonGrid:
    """A grid of Buttons with arrow/WASD navigation, mouse hover/click and disabled-state handling.

    handle(e) returns ("activate", button) / ("back", None) / None. Disabled buttons can be highlighted
    but not activated (so the player can still read why they're unavailable)."""

    def __init__(self, buttons, cols=1, allow_back=True):
        self.buttons, self.cols, self.allow_back = buttons, max(1, cols), allow_back
        self.idx = 0
        self.t = 0.0

    def set_buttons(self, buttons, keep=False):
        self.buttons = buttons
        self.idx = min(self.idx, max(0, len(buttons) - 1)) if keep else 0

    @property
    def current(self):
        return self.buttons[self.idx] if self.buttons else None

    def update(self, dt):
        self.t += dt

    def handle(self, e):
        if not self.buttons:
            return ("back", None) if (self.allow_back and is_back(e)) else None
        d = nav_dir(e)
        if d:
            dx, dy = d
            n = self.idx + (dx if dx else dy * self.cols)
            if dx and (n // self.cols != self.idx // self.cols):
                n = self.idx           # don't wrap left/right across rows
            if 0 <= n < len(self.buttons):
                self.idx = n
            return None
        if is_confirm(e):
            b = self.current
            return ("activate", b) if b and b.enabled else ("deny", b)
        if self.allow_back and is_back(e):
            return ("back", None)
        if e.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(e.pos):
                    self.idx = i
        if is_click(e):
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(e.pos):
                    self.idx = i
                    return ("activate", b) if b.enabled else ("deny", b)
        return None

    def draw(self, surf, size=24, kind="display"):
        for i, b in enumerate(self.buttons):
            draw_button(surf, b, selected=(i == self.idx), size=size, kind=kind, t=self.t)


def draw_button(surf, b, selected=False, size=24, kind="display", t=0.0):
    pk = "button_accent" if (b.accent and b.enabled) else "button_sel" if selected else "button"
    panel(surf, b.rect, pk, blur=False, shadow=False)
    if selected and b.accent and b.enabled:
        pygame.draw.rect(surf, (255, 255, 255), b.rect, 2, border_radius=12)
    color = (255, 255, 255) if (b.accent and b.enabled) else INK
    if not b.enabled:
        color = (120, 120, 112)
    img = render_text(b.label, kind, size, color)
    list_row = b.right is not None or b.sub is not None
    if b.icon:                                                            # icon at the left, label after it
        ic = assets.item_icon(b.icon, 2)                                  # item / disc / module icon when one exists
        if ic is None:
            name = ICON_SELECTED.get(b.icon, b.icon) if selected else b.icon
            ic = assets.ui_icon(name, 2)
        if not b.enabled:
            ic = ic.copy()
            ic.set_alpha(110)
        surf.blit(ic, (b.rect.x + 12, b.rect.centery - ic.get_height() // 2))
        if b.right is not None:
            surf.blit(img, (b.rect.x + 22 + ic.get_width() + 6, b.rect.centery - img.get_height() // 2))
        else:
            surf.blit(img, img.get_rect(center=(b.rect.centerx + 14, b.rect.centery)))
    elif b.sub:
        y = b.rect.y + max(6, (b.rect.h - img.get_height() - 16) // 2)
        surf.blit(img, (b.rect.x + 16, y))
        chip = render_text(b.sub, "display", 8, (255, 255, 255))
        pygame.draw.rect(surf, b.color or (90, 90, 90), (b.rect.x + 16, y + img.get_height() + 5,
                                                         chip.get_width() + 10, 16), border_radius=3)
        surf.blit(chip, (b.rect.x + 21, y + img.get_height() + 9))
    elif b.right is not None:
        surf.blit(img, (b.rect.x + 22, b.rect.centery - img.get_height() // 2))
    else:
        surf.blit(img, img.get_rect(center=b.rect.center))
    if b.right is not None:
        r_img = render_text(str(b.right), kind, size, color)
        surf.blit(r_img, (b.rect.right - 16 - r_img.get_width(), b.rect.centery - r_img.get_height() // 2))
    if selected and list_row:
        cx, cy = b.rect.x + 8 + int(math.sin(t * 8) * 2), b.rect.centery
        pygame.draw.polygon(surf, ORANGE, [(cx, cy - 6), (cx, cy + 6), (cx + 7, cy)])


# --------------------------------------------------------------------------- toast + overlays
class Toast:
    """Top-centre message that slides in and fades out; driven by dt."""

    def __init__(self):
        self.msg, self.t, self.total = "", 0.0, 1.0

    def show(self, msg, seconds=2.6):
        self.msg, self.t, self.total = msg, seconds, seconds

    def update(self, dt):
        self.t = max(0.0, self.t - dt)

    def draw(self, surf):
        if self.t <= 0 or not self.msg:
            return
        elapsed = self.total - self.t
        slide = 1.0 - min(1.0, elapsed / 0.22)           # 1 -> 0 as it drops in
        out = min(1.0, self.t / 0.25)                    # fade over the last quarter second
        img = render_text(self.msg, "display", 8, (248, 246, 230))
        r = pygame.Rect(0, 0, img.get_width() + 44, 44)
        r.midtop = (W // 2, 12 - int(slide * 50) - int((1 - out) * 50))     # drops in, lifts away at the end
        panel(surf, r, "message")
        surf.blit(img, img.get_rect(center=r.center))


def dim(surf, alpha=140):
    s = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    s.fill((0, 0, 0, alpha))
    surf.blit(s, (0, 0))


def fade(surf, alpha, color=(0, 0, 0)):
    if alpha <= 0:
        return
    s = pygame.Surface(surf.get_size())
    s.fill(color)
    s.set_alpha(int(255 * min(1.0, alpha)))
    surf.blit(s, (0, 0))


def circuit_backdrop(surf, t, base=TEAL_DARK, line=(80, 130, 125), step=32):
    """Faint scrolling circuit grid (title / starter screens)."""
    surf.fill(base)
    off = int(t * 12) % step
    for x in range(-step + off, W + step, step):
        pygame.draw.line(surf, line, (x, 0), (x, H))
    for y in range(-step + off, H + step, step):
        pygame.draw.line(surf, line, (0, y), (W, y))
    # slow vignette
    v = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.rect(v, (0, 0, 0, 0), (0, 0, W, H))
    for i in range(6):
        pygame.draw.rect(v, (0, 0, 0, 14), (i * 10, i * 10, W - i * 20, H - i * 20), 10)
    surf.blit(v, (0, 0))
