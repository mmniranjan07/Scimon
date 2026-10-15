"""Sprite classes: the player, NPCs, the animated battle Scimon, the trainer silhouette and hit particles.

World characters are drawn procedurally on a 16-unit art grid (a port of V34's drawChar) and cached as
48 px Surfaces, so the pixel-art look stays crisp and costs one blit per frame. Every animation takes
`dt` seconds, so speed is identical at 30, 60 or 144 fps."""
import math
import random

import pygame

import assets
from settings import PX, TILE, WALK_TILES_PER_SEC, hexc

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _r(surf, color, x, y, w, h, scale=PX):
    pygame.draw.rect(surf, color, (x * scale, y * scale, w * scale, h * scale))


# --------------------------------------------------------------------------- world characters
# Characters are 16x32-px frames (assets/characters/<body>_<hue>.png, 24 columns x 7 rows) drawn at 48x96.
# The *hitbox* is the single 48x48 tile the character stands on; the sprite is anchored so its feet are on the
# bottom edge of that tile and the head overhangs the tile above (see Character.draw_pos).
FRAME_W, FRAME_H = 16, 32
DIR_COL = {"right": 0, "up": 6, "left": 12, "down": 18}       # first of 6 frames per facing
IDLE_ROW, WALK_ROW = 1, 2
WALK_FPS, IDLE_FPS = 16.0, 4.0

# who looks like whom: body sheet + hue variant (4 bodies, recoloured, for the whole cast)
LOOKS = {
    "player": ("adam", 0), "venn": ("bob", 0), "kael": ("alex", 230), "ilo": ("bob", 110), "jori": ("adam", 110),
    "sella": ("amelia", 50), "lab-aide": ("amelia", 170), "mayor": ("bob", 290), "cush": ("amelia", 290),
    "archivist": ("amelia", 230), "shopkeeper": ("alex", 50), "farmer-wren": ("adam", 170), "grower": ("bob", 50),
    "player-mom": ("amelia", 0), "toma": ("alex", 0), "reya": ("amelia", 110),
}
_frame_cache = {}


def character_frame(look, facing, mode, index):
    """48x96 surface for one frame. `look` = (body, hue); mode = 'walk' | 'idle'; index = animation frame 0-5."""
    key = (look, facing, mode, index % 6)
    f = _frame_cache.get(key)
    if f is None:
        body, hue = look
        rel = f"characters/{body}_{hue}.png"
        sheet = assets.image(rel)
        row = WALK_ROW if mode == "walk" else IDLE_ROW
        x = (DIR_COL[facing] + index % 6) * FRAME_W
        sub = sheet.subsurface((x, row * FRAME_H, FRAME_W, FRAME_H))
        f = pygame.transform.scale(sub, (FRAME_W * PX, FRAME_H * PX))
        _frame_cache[key] = f
    return f


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
        self.image = character_frame(look, facing, "idle", 0)

    @property
    def sort_y(self):
        return self.rect.bottom

    @property
    def draw_pos(self):
        """Top-left of the sprite in world pixels: feet on the hitbox's bottom edge, head overhanging upward."""
        return self.rect.x + (TILE - self.image.get_width()) // 2, self.rect.bottom - self.image.get_height()

    def refresh(self):
        fps = WALK_FPS if self.mode == "walk" else IDLE_FPS
        self.image = character_frame(self.look, self.facing, self.mode, int(self.anim_t * fps))
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
        super().__init__(d["x"], d["y"], LOOKS.get(d["id"], ("bob", 0)))
        self.id, self.name, self.lines = d["id"], d["name"], d["lines"]
        self.heals, self.service = d.get("heals", False), d.get("service")

    def face(self, direction):
        self.facing = direction
        self.refresh()

    def update(self, dt):
        self.anim_t += dt                              # idle animation (breathing / blink) from the sheet
        self.refresh()


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
