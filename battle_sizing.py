"""Centralized battle-sprite sizing for every Scimon form.

One configuration drives how large a creature reads in battle:

- STAGE_FACTORS      evolution-chain position (from the database's stage_ordinal, never filename
                     suffixes) -> share of the family reference size.  First 60%, middle 80%, final 100%.
- REFERENCE_BODY     the on-screen body size (px) of a 100% final form; FAMILY_REFERENCE overrides it
                     per family for unusually large/small species lines.
- SPECIES_SCALE      documented per-species corrections on top (compact bugs, oversized starters...).
- BODY_PROBE         morphological-opening radius (as a fraction of the art's larger dimension): the
                     opening removes thin features -- wings, tails, antennae, flames, orbital rings --
                     so the scale is driven by the creature's BODY, not its decorations.  Appendages
                     stay visible: the whole artwork is scaled by the body-derived factor.
- MAX_ENEMY/PLAYER   the layout caps of each battle side; full art is clamped inside them so nothing
                     overlaps the HUD, menus or the opposing creature.
- HOVER / HOVER_FAMILIES  floating creatures rise above the ground baseline (their shadow stays put).

Everything is measured on the artwork's nontransparent bounds (the canvases are pre-trimmed by the
importers), scaled with nearest neighbour (pixel art) and cached per (species, view).
"""
import os

import numpy as np
import pygame
from scipy import ndimage

import assets
from data import SPECIES

# --------------------------------------------------------------------------- configuration
STAGE_FACTORS = {1: 0.60, 2: 0.80, 3: 1.00}
REFERENCE_BODY = 150.0                  # px: body size of a 100% (final) form
DEFAULT_FAMILY_REFERENCE = REFERENCE_BODY
FAMILY_REFERENCE = {
    # unusually large / small lines read best with their own reference:
    # "gearhulk": 165.0,
}
PERSPECTIVE_BACK = 1.0                  # player-side (back view) perspective multiplier
SPECIES_SCALE = {
    # compact bug: Enzymite must read smaller than the equivalent-stage Zephyrit
    "enzymite": 0.85, "enzymite-baby": 0.85, "enzymite-final": 0.85,
    # first-stage Pyrodrive must be a compact starter like Florabot / Aquabit
    "pyrodrive": 0.88,
}
BODY_PROBE = (0.045, 2, 9)              # opening radius = clamp(frac * art max dim, min, max)
MAX_ENEMY = (250, 220)                  # enemy side layout caps (battle.py's box)
MAX_PLAYER = (300, 260)                 # player side layout caps (back view, nearer camera)
HOVER_FAMILIES = {                      # floating lines rise above the ground baseline
    "aerochit": 16, "cumulob": 20, "vapomite": 18, "zephyrit": 14, "galepod": 16,
    "vortexling": 18, "stratowing": 20, "wavicle": 18, "phaseling": 16, "entanglit": 12,
    "gloombat": 18, "mosswing": 14, "prismoth": 16, "ionling": 16, "arcwisp": 18,
    "coronalet": 12, "orbitling": 20, "starlit": 14, "nebulon": 16, "wraithex": 18,
    "duskling": 10, "umbralet": 12, "noctulite": 14, "voidling": 12, "shadefam": 0,
    "mistfin": 12, "puddlit": 10, "droplite": 12, "solvexel": 12, "snovite": 10, "icelyte": 10,
    "solburst": 12, "gleamlet": 12, "lumibot": 10, "nanolyte": 10, "joulebot": 0,
}
HOVER_SPECIES = {}                      # per-species override (px)
# ---------------------------------------------------------------------------

_measure_cache = {}
_surface_cache = {}


def _disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r


def _measure(key, surface):
    """(full bbox, body bbox) from the nontransparent pixels.  The body is the largest mass that
    survives a morphological opening: thin decorations (wings, tails, flames, antennae) vanish,
    the torso stays.  Cached per source path."""
    if key in _measure_cache:
        return _measure_cache[key]
    a = pygame.surfarray.array_alpha(surface).transpose(1, 0)     # -> (h, w)
    mask = a > 16
    ys, xs = np.nonzero(mask)
    full = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    w, h = full[2] - full[0], full[3] - full[1]
    r = int(min(max(BODY_PROBE[0] * max(w, h), BODY_PROBE[1]), BODY_PROBE[2]))
    eroded = ndimage.binary_erosion(mask, structure=_disk(r))
    if eroded.any():
        lab, n = ndimage.label(eroded, structure=np.ones((3, 3)))
        if n > 1:
            # the torso is the thick mass nearest the artwork's centre: flames, tails and wings
            # sit at the edges, so "largest blob" alone can pick a decoration
            cx, cy = full[0] + w / 2, full[1] + h / 2
            best, best_d = None, 1e9
            for k in range(1, n + 1):
                ky, kx = np.nonzero(lab == k)
                d = np.hypot(kx.mean() - cx, ky.mean() - cy)
                if d < best_d:
                    best, best_d = k, d
            core = lab == best
        else:
            core = eroded
        body = ndimage.binary_dilation(core, structure=_disk(r)) & mask
        bys, bxs = np.nonzero(body)
        body_box = (bxs.min(), bys.min(), bxs.max() + 1, bxs.max() + 1)
    else:
        body_box = full
    _measure_cache[key] = (full, body_box)
    return _measure_cache[key]


def hover_of(species_id):
    """How far above the ground baseline this creature hovers (0 = grounded, feet on the floor)."""
    sp = SPECIES[species_id]
    if species_id in HOVER_SPECIES:
        return HOVER_SPECIES[species_id]
    return HOVER_FAMILIES.get(sp.family_id, 0)


def battle_surface(species_id, back=False):
    """The battle-ready Surface for one form and view: trimmed, body-normalized by evolution stage,
    nearest-neighbour scaled, clamped to the side's layout caps.  Cached per (species, view)."""
    key = (species_id, back)
    if key in _surface_cache:
        return _surface_cache[key]
    sp = SPECIES[species_id]
    rel = sp.back if (back and sp.back) else sp.front
    key = f"scimon/{rel}"
    src = assets.image(key)
    (fx0, fy0, fx1, fy1), (bx0, by0, bx1, by1) = _measure(key, src)
    body = max(bx1 - bx0, by1 - by0)
    fam_ref = FAMILY_REFERENCE.get(sp.family_id, DEFAULT_FAMILY_REFERENCE)
    target = STAGE_FACTORS.get(sp.stage_ordinal, 1.0) * fam_ref * SPECIES_SCALE.get(species_id, 1.0)
    if back:
        target *= PERSPECTIVE_BACK
    k = target / body if body else 1.0
    w = (fx1 - fx0) * k
    h = (fy1 - fy0) * k
    caps = MAX_PLAYER if back else MAX_ENEMY
    if w > caps[0] or h > caps[1]:
        kc = min(caps[0] / w, caps[1] / h)
        w, h = w * kc, h * kc
    sized = pygame.transform.scale(src.subsurface((fx0, fy0, fx1 - fx0, fy1 - fy0)),
                                   (max(1, int(w)), max(1, int(h))))
    _surface_cache[key] = sized
    return sized
