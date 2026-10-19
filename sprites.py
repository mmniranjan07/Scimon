"""Sprite classes: the player, NPCs, the animated battle Scimon, the trainer silhouette and hit particles.

World characters are drawn procedurally on a 16-unit art grid (a port of V34's drawChar) and cached as
48 px Surfaces, so the pixel-art look stays crisp and costs one blit per frame. Every animation takes
`dt` seconds, so speed is identical at 30, 60 or 144 fps."""
import math
import random

import pygame

import animation
import assets
from settings import (CREATURE_HOVER, CREATURE_SHEETS, PLAYER_SHEET, PX, USE_RPGDB_CAST, SHEET_LAYOUT, TILE, WALK_TILES_PER_SEC, hexc)

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _r(surf, color, x, y, w, h, scale=PX):
    pygame.draw.rect(surf, color, (x * scale, y * scale, w * scale, h * scale))


# --------------------------------------------------------------------------- world characters
# Characters are 16x32-px frames (assets/characters/<body>_<hue>.png, 24 columns x 7 rows) drawn at 48x96.
# The *hitbox* is the single 48x48 tile the character stands on; the sprite is anchored so its feet are on the
# bottom edge of that tile and the head overhangs the tile above (see Character.draw_pos).
FRAME_W, FRAME_H = SHEET_LAYOUT["frame"]
WALK_FPS, IDLE_FPS = SHEET_LAYOUT["fps"]["walk"], SHEET_LAYOUT["fps"]["idle"]

# who looks like whom: body sheet + hue variant (4 bodies, recoloured, for the whole cast)
LOOKS = {
    "player": ("adam", 0), "venn": ("bob", 0), "kael": ("alex", 230), "ilo": ("bob", 110), "jori": ("adam", 110),
    "sella": ("amelia", 50), "lab-aide": ("amelia", 170), "mayor": ("bob", 290), "cush": ("amelia", 290),
    "archivist": ("amelia", 230), "shopkeeper": ("alex", 50), "farmer-wren": ("adam", 170), "grower": ("bob", 50),
    "player-mom": ("amelia", 0), "toma": ("alex", 0), "reya": ("amelia", 110),
}


# Cast -> RPG DB character number (0-11, left to right on the source sheet; 0-3 old style, 4-11 new style).
# Edit freely; a number whose sheet file is missing is skipped and that person keeps the original look.
RPGDB_CAST = {
    "player": 5, "venn": 3, "kael": 10, "ilo": 0, "jori": 4, "sella": 11, "lab-aide": 1, "mayor": 2, "cush": 6,
    "archivist": 9, "shopkeeper": 7, "farmer-wren": 8, "grower": 0, "player-mom": 11, "toma": 10, "reya": 1,
    "ranger": 4,
}
DEFAULT_LOOK = ("bob", 0)                      # anyone not listed in LOOKS
if USE_RPGDB_CAST:
    for _who, _n in RPGDB_CAST.items():
        if assets.has(f"characters/rpgdb{_n}_0.png"):
            LOOKS[_who] = (f"rpgdb{_n}", 0)
    if assets.has("characters/rpgdb8_0.png"):
        DEFAULT_LOOK = ("rpgdb8", 0)


def look_animator(look):
    """SheetAnimator for a (body, hue) look.  The player's look can be replaced by settings.PLAYER_SHEET (any sheet
    following settings.SHEET_LAYOUT); a missing file silently falls back to the default body."""
    body, hue = look
    rel = f"characters/{body}_{hue}.png"
    if look == LOOKS["player"] and PLAYER_SHEET and assets.has(PLAYER_SHEET):
        rel = PLAYER_SHEET
    elif not assets.has(rel):                    # a look whose sheet is missing falls back to the default body
        rel = "characters/adam_0.png"
    return animation.sheet_animator(rel)


def character_frame(look, facing, mode, index):
    """48x96 surface for one frame by index (0-5); kept for callers that pick frames themselves."""
    return look_animator(look).frame_index(mode, facing, index)


class Character(pygame.sprite.Sprite):
    """Base for anything standing on the tile grid. `rect` is its 48x48 hitbox in world pixels; `image` is the
    taller 48x96 sprite, drawn with its bottom edge on the hitbox bottom (use draw_pos / draw_rect)."""

    def __init__(self, tx, ty, look, facing="down"):
        super().__init__()
        self.tile = (tx, ty)
        self.pos = pygame.Vector2(tx * TILE, ty * TILE)
        self.look, self.facing = look, facing
        self.mode, self.anim_t = "idle", random.random() * 3
        self.rect = pygame.Rect(self.pos.x, self.pos.y, TILE, TILE)
        self.anim = look_animator(look)
        self.image = self.anim.frame("idle", facing, 0)

    @property
    def sort_y(self):
        return self.rect.bottom

    @property
    def draw_pos(self):
        """Top-left of the sprite in world pixels: feet on the hitbox's bottom edge, head overhanging upward."""
        return self.rect.x + (TILE - self.image.get_width()) // 2, self.rect.bottom - self.image.get_height()

    def refresh(self):
        self.image = self.anim.frame(self.mode, self.facing, self.anim_t)       # Animation.frame_at(t): fps per mode
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))


class Player(Character):
    """The researcher. Moves one tile at a time (Pokemon-style): a step is a straight-line glide to the
    next tile centre at WALK_TILES_PER_SEC, with leftover frame time carried into the next step so
    holding a key gives perfectly smooth, frame-rate independent walking."""

    def __init__(self, tx, ty):
        super().__init__(tx, ty, LOOKS["player"])
        self.moving = False
        self.target = (tx, ty)
        self.speed = WALK_TILES_PER_SEC * TILE

    def stand(self):
        self.mode = "idle"
        self.refresh()

    def place(self, tx, ty, facing):
        self.tile, self.target, self.moving = (tx, ty), (tx, ty), False
        self.pos.update(tx * TILE, ty * TILE)
        self.facing, self.mode, self.anim_t = facing, "idle", 0.0
        self.refresh()

    def begin_step(self, direction):
        """Face `direction` and start gliding to the neighbouring tile (caller already checked collision)."""
        self.facing = direction
        dx, dy = DIRS[direction]
        self.target = (self.tile[0] + dx, self.tile[1] + dy)
        self.moving = True
        if self.mode != "walk":
            self.mode, self.anim_t = "walk", 0.0

    def advance(self, dt):
        """Move toward the target. Returns (arrived, leftover_dt)."""
        if not self.moving:
            self.mode = "idle"
            self.anim_t += dt
            self.refresh()
            return False, dt
        dist = self.speed * dt
        goal = pygame.Vector2(self.target[0] * TILE, self.target[1] * TILE)
        remaining = (goal - self.pos).length()
        if dist >= remaining:
            self.pos.update(goal)
            self.tile, self.moving = self.target, False
            self.anim_t += remaining / self.speed
            self.refresh()
            return True, (dist - remaining) / self.speed
        self.pos += (goal - self.pos).normalize() * dist
        self.anim_t += dt
        self.refresh()
        return False, 0.0


class NPC(Character):
    def __init__(self, d):
        super().__init__(d["x"], d["y"], LOOKS.get(d["id"], DEFAULT_LOOK))
        self.id, self.name, self.lines = d["id"], d["name"], d["lines"]
        self.heals, self.service = d.get("heals", False), d.get("service")

    def face(self, direction):
        self.facing = direction
        self.refresh()

    def update(self, dt):
        self.anim_t += dt                              # idle animation (breathing / blink) from the sheet
        self.refresh()


# --------------------------------------------------------------------------- overworld Sci-Mon
_hover_cache = {}


def _hover_animation(species_id, size=54):
    """Hover cycle for an overworld Sci-Mon: the creature bobs up and down while its ground shadow shrinks as it
    rises.  All frames are pre-rendered once (same canvas size), so per-frame cost is a single blit.
    If settings.CREATURE_SHEETS names an idle sheet for the species, its frames are used instead of one still."""
    got = _hover_cache.get(species_id)
    if got:
        return got
    cfg = CREATURE_SHEETS.get(species_id)
    sheet = assets.image_or_none(cfg["sheet"]) if cfg else None
    if sheet is not None:
        fw, fh = cfg["frame"]
        src = animation.strip_frames(sheet, fw, fh, cfg.get("frames"))
        k = min(size / fw, size / fh)
        src = [pygame.transform.scale(f, (max(1, int(fw * k)), max(1, int(fh * k)))) for f in src]
        n, fps = len(src), cfg.get("fps", 6)
    else:
        src = [assets.mon_image(species_id, size, size)]
        n = 24
        fps = n / CREATURE_HOVER["period"]
    h = max(f.get_height() for f in src)
    w = max(f.get_width() for f in src)
    amp = max(3, round(h * CREATURE_HOVER["amplitude"]))
    hover = animation.Hover(amp, period=1.0, phase=-math.pi / 2)       # phase 0 at frame 0 (on the ground)
    shadow_h = 8
    canvas_h = h + amp + shadow_h
    frames = []
    for i in range(n):
        t = i / n
        lift = hover.lift(t)
        f = pygame.Surface((w, canvas_h), pygame.SRCALPHA)
        sw = int(w * 0.7 * (1 - 0.3 * lift))
        shadow = pygame.Surface((sw, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (10, 10, 14, int(110 - 40 * lift)), shadow.get_rect())
        f.blit(shadow, ((w - sw) // 2, canvas_h - shadow_h))
        img = src[i % len(src)]
        f.blit(img, ((w - img.get_width()) // 2, canvas_h - shadow_h - img.get_height() + round(hover.offset(t)) - 2))
        frames.append(f)
    got = _hover_cache[species_id] = animation.Animation(frames, fps=fps)
    return got


class CreatureSprite:
    """A Sci-Mon floating on a tile of the overworld / a room.  Depth-sorted like any prop (`image`, `x`, `y`,
    `sort_y`), animated through update(dt), solid on its own tile (rooms mark that in their collision grid)."""

    def __init__(self, species_id, tx, ty):
        self.species_id, self.tile = species_id, (tx, ty)
        self.anim = _hover_animation(species_id)
        self.t = random.random() * self.anim.duration
        img = self.anim.frames[0]
        bottom = (ty + 1) * TILE
        self.x, self.y = tx * TILE + (TILE - img.get_width()) // 2, bottom - img.get_height()
        self.sort_y = bottom

    @property
    def image(self):
        return self.anim.frame_at(self.t)

    def update(self, dt):
        self.t += dt


# --------------------------------------------------------------------------- battle sprites
class ScimonSprite(pygame.sprite.Sprite):
    """A battle-side creature: idle breathing, hit shake + flash, send-in pop, faint fade, ground shadow.

    Positioned by `midbottom` (the point where its feet touch the platform)."""

    def __init__(self, species_id, midbottom, max_size, back=False, appear=False):
        super().__init__()
        self.species_id, self.back = species_id, back
        self.base = assets.mon_image(species_id, *max_size, back=back)
        self.midbottom = midbottom
        self.t = random.random() * 3
        self.shake_t = self.flash_t = 0.0
        self.appear_t = 0.0 if appear else 1.0       # 0 -> 1 over APPEAR seconds
        self.fainted, self.fade = False, 1.0
        self.image = self.base
        self.rect = self.base.get_rect(midbottom=midbottom)

    APPEAR, SHAKE, FLASH, FAINT = 0.45, 0.36, 0.30, 0.5

    def hit(self):
        self.shake_t, self.flash_t = self.SHAKE, self.FLASH

    def send_in(self):
        self.appear_t, self.fainted, self.fade = 0.0, False, 1.0

    def faint(self):
        self.fainted = True

    def update(self, dt):
        self.t += dt
        self.shake_t = max(0.0, self.shake_t - dt)
        self.flash_t = max(0.0, self.flash_t - dt)
        if self.appear_t < 1.0:
            self.appear_t = min(1.0, self.appear_t + dt / self.APPEAR)
        if self.fainted:
            self.fade = max(0.0, self.fade - dt / self.FAINT)

    def draw(self, surf):
        if self.fade <= 0:
            return
        idle = math.sin(self.t * (math.tau / 2.6))                     # scimon-idle keyframes (2.6 s)
        lift = max(0.0, idle) * 0.03
        sx, sy = 1 + 0.015 * max(0.0, idle), 1 - 0.015 * max(0.0, idle)
        e = 1 - (1 - self.appear_t) ** 3                              # ease-out for the send-in
        k = 0.4 + 0.6 * e
        w, h = self.base.get_size()
        size = (max(1, int(w * sx * k)), max(1, int(h * sy * k)))
        img = pygame.transform.scale(self.base, size) if size != (w, h) else self.base.copy()
        shake = 0
        if self.shake_t > 0:                                           # shake-x: damped oscillation
            p = 1 - self.shake_t / self.SHAKE
            shake = math.sin(p * math.tau * 2.5) * 10 * (1 - p)
        x = self.midbottom[0] + shake - size[0] / 2
        y = self.midbottom[1] - size[1] - h * lift + (1 - e) * 30 + (1 - self.fade) * 16
        # contact shadow, pulsing with the idle cycle
        sw = int(w * 0.62 * (1 - 0.14 * max(0.0, idle)) * k)
        shadow = pygame.Surface((sw, max(6, sw // 4)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (10, 10, 14, int(95 * self.fade * e)), shadow.get_rect())
        surf.blit(shadow, shadow.get_rect(midtop=(self.midbottom[0] + shake, self.midbottom[1] - shadow.get_height() // 2)))
        alpha = 255 * self.fade * e
        if self.flash_t > 0:                                           # anim-flash: opacity dip + brightness spike
            p = 1 - self.flash_t / self.FLASH
            pulse = math.sin(p * math.pi)
            alpha *= 1 - 0.75 * pulse
            img.fill((int(150 * pulse),) * 3 + (0,), special_flags=pygame.BLEND_RGB_ADD)
        img.set_alpha(int(alpha))
        surf.blit(img, (x, y))


_trainer_cache = {}


def trainer_surface(scale=5):
    """Battle trainer: the rival's character sprite (front-facing idle frame) scaled up."""
    s = _trainer_cache.get(scale)
    if s is None:
        f = character_frame(LOOKS["kael"], "down", "idle", 0)
        s = pygame.transform.scale(f, (f.get_width() * scale // PX, f.get_height() * scale // PX))
        _trainer_cache[scale] = s
    return s


class TrainerSprite(pygame.sprite.Sprite):
    def __init__(self, midbottom, scale=5):
        super().__init__()
        self.base, self.midbottom, self.t = trainer_surface(scale), midbottom, 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        bob = max(0.0, math.sin(self.t * (math.tau / 2.6))) * 0.03
        w, h = self.base.get_size()
        pygame.draw.ellipse(surf, (10, 10, 14, 60), (self.midbottom[0] - w * 0.4, self.midbottom[1] - 5, w * 0.8, 12))
        surf.blit(self.base, (self.midbottom[0] - w / 2, self.midbottom[1] - h - h * bob))


# --------------------------------------------------------------------------- particles
class ImpactBurst:
    """Short pixel particle burst for hits (V34 ImpactBurst: 12 particles, gravity, ~0.33 s life)."""

    COLORS = [(248, 246, 230), (240, 192, 32), (224, 72, 56)]

    def __init__(self):
        self.parts = []     # [x, y, vx, vy, life]

    def trigger(self, center):
        for _ in range(12):
            a = random.random() * math.tau
            sp = (1.3 + random.random() * 2.4) * 60 * 1.6
            self.parts.append([center[0], center[1], math.cos(a) * sp, math.sin(a) * sp - 1.2 * 60 * 1.6, 1.0])

    def update(self, dt):
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 0.16 * 3600 * 1.6 * dt * 0.5     # gravity
            p[4] -= 3.0 * dt                          # life: 1 -> 0 in ~0.33 s
        self.parts = [p for p in self.parts if p[4] > 0]

    def draw(self, surf):
        for x, y, _, _, life in self.parts:
            c = self.COLORS[int(life * 11) % 3]
            s = pygame.Surface((7, 7), pygame.SRCALPHA)
            s.fill(c + (int(255 * max(0.0, life)),))
            surf.blit(s, (x - 3, y - 3))
