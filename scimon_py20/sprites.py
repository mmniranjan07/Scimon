"""Sprite classes: the player, NPCs, the animated battle Scimon, the trainer silhouette and hit particles.

World characters are drawn procedurally on a 16-unit art grid (a port of V34's drawChar) and cached as
48 px Surfaces, so the pixel-art look stays crisp and costs one blit per frame. Every animation takes
`dt` seconds, so speed is identical at 30, 60 or 144 fps."""
import math
import random
import zlib

import pygame

import animation
import assets
from settings import CHAR_PX, CREATURE_HOVER, CREATURE_SHEETS, PX, TILE, WALK_TILES_PER_SEC, hexc

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _r(surf, color, x, y, w, h, scale=PX):
    pygame.draw.rect(surf, color, (x * scale, y * scale, w * scale, h * scale))


# --------------------------------------------------------------------------- world characters
# Characters are 32x32-px MPWSP01 frames (assets/mpw/ow/ow<n>.png, 4x4) drawn at 64 px wide (settings.CHAR_PX = 2), cropped to the artwork.
# The *hitbox* is the single 48x48 tile the character stands on; the sprite is anchored so its feet are on the
# bottom edge of that tile and the head overhangs the tile above (see Character.draw_pos).
JUMP_SPEED, JUMP_HEIGHT = 1.15, TILE * 0.55        # ledge hop: a little faster than walking, arc height in px

# who looks like whom: the ten MPWSP01 overworld sheets (assets/mpw/ow/ow1..ow10.png).  Anyone not listed gets a
# stable sheet derived from their id, so every NPC in every town has an MPW look.
MPW_CAST = {
    "player": 1, "venn": 7, "kael": 8, "ilo": 4, "jori": 2, "sella": 6, "lab-aide": 3, "mayor": 10, "cush": 9,
    "archivist": 3, "shopkeeper": 5, "farmer-wren": 10, "grower": 5, "player-mom": 6, "toma": 2, "reya": 9, "ranger": 4,
}
LOOKS = {"player": MPW_CAST["player"], "kael": MPW_CAST["kael"]}


def look_for(who):
    """Sheet number (1..10) for a character id."""
    n = MPW_CAST.get(who)
    return n if n else 2 + zlib.crc32(str(who).encode()) % 9


def look_animator(look):
    return animation.mpw_animator(int(look))


def character_frame(look, facing, mode, index):
    """Scaled surface for one frame by index (0-3); kept for callers that pick frames themselves."""
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
        return (self.rect.x + (TILE - self.image.get_width()) // 2,
                self.rect.bottom - self.image.get_height() - int(getattr(self, "lift", 0)))

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
        self.lift = 0.0                  # pixels the sprite is raised while hopping a ledge (shadow stays on the ground)
        self._jump = None                # (start position, total distance) while hopping

    def stand(self):
        self.mode = "idle"
        self.refresh()

    def place(self, tx, ty, facing):
        self.tile, self.target, self.moving = (tx, ty), (tx, ty), False
        self.lift, self._jump = 0.0, None
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

    def begin_jump(self, landing):
        """Hop south over a ledge onto `landing` (two tiles away): same glide as a step, plus an arc."""
        self.facing = "down"
        self.target = landing
        self.moving = True
        self._jump = (pygame.Vector2(self.pos), (pygame.Vector2(landing[0] * TILE, landing[1] * TILE) - self.pos).length())
        self.mode = "idle"

    def advance(self, dt):
        """Move toward the target. Returns (arrived, leftover_dt)."""
        if not self.moving:
            self.mode = "idle"
            self.anim_t += dt
            self.refresh()
            return False, dt
        spd = self.speed * (JUMP_SPEED if self._jump else 1.0)
        dist = spd * dt
        goal = pygame.Vector2(self.target[0] * TILE, self.target[1] * TILE)
        remaining = (goal - self.pos).length()
        if dist >= remaining:
            self.pos.update(goal)
            self.tile, self.moving = self.target, False
            self.anim_t += remaining / spd
            self.lift, self._jump = 0.0, None
            self.refresh()
            return True, (dist - remaining) / spd
        self.pos += (goal - self.pos).normalize() * dist
        self.anim_t += dt
        if self._jump:
            done = 1.0 - (goal - self.pos).length() / max(1.0, self._jump[1])
            self.lift = math.sin(math.pi * max(0.0, min(1.0, done))) * JUMP_HEIGHT
        self.refresh()
        return False, 0.0


class NPC(Character):
    def __init__(self, d):
        super().__init__(d["x"], d["y"], look_for(d["id"]))
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
    """A battle-side creature: MPW idle animation (front view) or breathing (back view), attack animation + lunge,
    hit shake + flash, send-in pop, faint fade, ground shadow.

    Positioned by `midbottom` (the point where its feet touch the ground)."""

    def __init__(self, species_id, midbottom, max_size, back=False, appear=False):
        super().__init__()
        self.species_id, self.back = species_id, back
        self.base = assets.mon_image(species_id, *max_size, back=back)
        self.idle = [self.base] if back else assets.mon_anim(species_id, "idle", *max_size)
        self.attack_frames = None if back else assets.mon_anim(species_id, "attack", *max_size)
        self.midbottom = midbottom
        self.t = random.random() * 3
        self.shake_t = self.flash_t = self.atk_t = 0.0
        self.atk_dir = 1
        self.appear_t = 0.0 if appear else 1.0       # 0 -> 1 over APPEAR seconds
        self.fainted, self.fade = False, 1.0
        self.image = self.base
        self.rect = self.base.get_rect(midbottom=midbottom)

    APPEAR, SHAKE, FLASH, FAINT, ATTACK = 0.45, 0.36, 0.30, 0.5, 0.55

    def hit(self):
        self.shake_t, self.flash_t = self.SHAKE, self.FLASH

    def attack(self, direction=1):
        """Play the attack animation and lunge `direction` (+1 right, -1 left) towards the opponent."""
        self.atk_t, self.atk_dir = self.ATTACK, direction

    def send_in(self):
        self.appear_t, self.fainted, self.fade = 0.0, False, 1.0

    def faint(self):
        self.fainted = True

    def update(self, dt):
        self.t += dt
        self.shake_t = max(0.0, self.shake_t - dt)
        self.flash_t = max(0.0, self.flash_t - dt)
        self.atk_t = max(0.0, self.atk_t - dt)
        if self.appear_t < 1.0:
            self.appear_t = min(1.0, self.appear_t + dt / self.APPEAR)
        if self.fainted:
            self.fade = max(0.0, self.fade - dt / self.FAINT)

    def _frame(self):
        if self.atk_t > 0 and self.attack_frames:
            p = 1 - self.atk_t / self.ATTACK
            return self.attack_frames[min(len(self.attack_frames) - 1, int(p * len(self.attack_frames)))]
        return self.idle[int(self.t * 5) % len(self.idle)]

    def draw(self, surf):
        if self.fade <= 0:
            return
        frame = self._frame()
        idle = math.sin(self.t * (math.tau / 2.6))                     # slow breathing on top of the frame animation
        lift = max(0.0, idle) * 0.02 if len(self.idle) == 1 else 0.0
        sx, sy = (1 + 0.015 * max(0.0, idle), 1 - 0.015 * max(0.0, idle)) if len(self.idle) == 1 else (1, 1)
        e = 1 - (1 - self.appear_t) ** 3                              # ease-out for the send-in
        k = 0.4 + 0.6 * e
        w, h = frame.get_size()
        size = (max(1, int(w * sx * k)), max(1, int(h * sy * k)))
        img = pygame.transform.scale(frame, size) if size != (w, h) else frame.copy()
        shake = 0
        if self.shake_t > 0:                                           # shake-x: damped oscillation
            p = 1 - self.shake_t / self.SHAKE
            shake = math.sin(p * math.tau * 2.5) * 10 * (1 - p)
        if self.atk_t > 0:                                             # lunge towards the target and back
            shake += math.sin(math.pi * (1 - self.atk_t / self.ATTACK)) * 34 * self.atk_dir
        x = self.midbottom[0] + shake - size[0] / 2
        y = self.midbottom[1] - size[1] - h * lift + (1 - e) * 30 + (1 - self.fade) * 16
        self.rect = pygame.Rect(int(x), int(y), size[0], size[1])
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


# MPW attack effect sheet (assets/mpw/fx/attack<N>.png, 4 frames of 96x96) per technique type
FX_FOR_TYPE = {"Hydro": 3, "Cryo": 3, "Thermal": 4, "Plasma": 5, "Botanic": 6, "Bio": 6, "Electric": 7, "Digital": 7,
               "Nano": 1, "Atmospheric": 1}


class AttackFx:
    """One-shot MPW attack effect played over the target (drawn 3x, nearest neighbour)."""
    DURATION = 0.5

    def __init__(self, tech_type, center):
        n = FX_FOR_TYPE.get(tech_type, 2)
        sheet = assets.image(f"mpw/fx/attack{n}.png")
        self.frames = [pygame.transform.scale(sheet.subsurface((i * 96, 0, 96, 96)), (96 * 3, 96 * 3)) for i in range(4)]
        self.center, self.t = center, 0.0

    @property
    def alive(self):
        return self.t < self.DURATION

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        if not self.alive:
            return
        f = self.frames[min(3, int(self.t / self.DURATION * 4))]
        surf.blit(f, f.get_rect(center=self.center))


_trainer_cache = {}


def trainer_surface(scale=5):
    """Battle trainer: the rival's character sprite (front-facing idle frame) scaled up."""
    s = _trainer_cache.get(scale)
    if s is None:
        f = character_frame(LOOKS["kael"], "down", "idle", 0)
        s = pygame.transform.scale(f, (f.get_width() * scale // CHAR_PX, f.get_height() * scale // CHAR_PX))
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
