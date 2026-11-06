"""Scimon field abilities and fishing system.

Replaces FireRed's HM system with scientific-ability unlocks that are:
- Distributed like FireRed's HMs: each one is handed over at the same kind of story
  milestone (a dex-requirement gift, a gym-leader award, a postgame item on the ground)
- Once unlocked, usable from the overworld without teaching a move (F = Aerolift,
  G = Excavator, confirm facing water = fish / board)
- Tracked durably in the save (like FireRed's gym badges gating HM usage)

FireRed mapping:  Lumen = HM05 Flash (Oak's aide, 10-dex requirement) - Prof. Venn, 10 dex
entries.  Aerolift = HM02 Fly (a route gate) - Leader Fern after the Green Stamp.
Aquaboard = HM03 Surf (mid/post-game milestone) - the boss-victory aftermath.
Excavator = HM04 Strength (a fetch sidequest) - the Route 4 supply chest.
Hydroclimb = HM07 Waterfall (an item ball on the ground in a postgame place) - the Ascent
Road.  Rods are geographic tiers like FireRed's (Epidimy -> Route 12 -> Route 20), and
fishing needs only a rod - never the Aquaboard.

Fishing replaces FireRed's rod system: three rod tiers catch water-habitat families at
different level ranges, with the gym ceiling applied.  Fishing uses its own encounter
tables (separate from walking encounters), so some deep-water species are only catchable
by fishing with the right rod.
"""
import random

import pygame

from engine import Scene, StateId
from settings import INK, H, W
from ui import dim, is_back, panel, text

# --------------------------------------------------------------------------- abilities
ABILITIES = {
    "aquaboard": {
        "name": "Aquaboard",
        "desc": "Ride a Hydro-type Scimon across open water.",
        "req_type": "Hydro",
        "gym_hint": "Cush's field module, activated after the Corrupt Bandits fell.",
    },
    "aerolift": {
        "name": "Aerolift",
        "desc": "Fast-travel to any visited rest point with an Atmospheric-type Scimon.",
        "req_type": "Atmospheric",
        "gym_hint": "Leader Fern's award for earning the Green Stamp.",
    },
    "lumen": {
        "name": "Lumen Flare",
        "desc": "Illuminate dark spaces with Radiant energy.",
        "req_type": "Radiant",
        "gym_hint": "Prof. Venn's gift for logging ten dex entries.",
    },
    "excavator": {
        "name": "Excavator",
        "desc": "Burrow out of caves with a Geologic-type Scimon.",
        "req_type": "Geologic",
        "gym_hint": "Found in the Route 4 supply chest.",
    },
    "hydroclimb": {
        "name": "Hydroclimb",
        "desc": "Scale rushing water with a Hydro-type Scimon.",
        "req_type": "Hydro",
        "gym_hint": "An item ball lying on the Ascent Road.",
    },
}

# ability id -> the key item that carries it (an `abl_*` module in the Pack's key folder).
# The Pack item is the durable proof of the unlock; sync_from_items re-derives the ability
# from the item, so any grant path (NPC handover, chest, boss aftermath) unlocks for free.
ABILITY_ITEM = {
    "aquaboard": "abl_aquaboard",
    "aerolift": "abl_aerolift",
    "lumen": "abl_lumen",
    "excavator": "abl_excavator",
    "hydroclimb": "abl_hydroclimb",
}


def sync_from_items(state):
    """Unlock every field ability whose module item the player holds (idempotent; returns
    the ability ids newly unlocked, in ABILITIES order, so callers can toast them)."""
    out = []
    for ability_id, item_id in ABILITY_ITEM.items():
        if getattr(state, "qty", lambda _i: 0)(item_id) > 0 and state.unlock_ability(ability_id):
            out.append(ability_id)
    return out


def gate_met(state, gate):
    """Grant gates for NPC handovers, mirroring FireRed's HM conditions.
    `gate` is None or a string: "flag:<story flag>" (a story milestone such as
    boss_beaten), "dex:<n>" (n distinct Sci-Mon captured -- FireRed's 10-dex Flash) or
    "stamps:<n>" (n gym stamps earned -- the bike-shop style milestone)."""
    if not gate:
        return True
    kind, _, val = gate.partition(":")
    if kind == "flag":
        return val in getattr(state, "story", ())
    if kind == "dex":
        return len(getattr(state, "captured", ()) or ()) >= int(val)
    if kind == "stamps":
        return len(getattr(state, "stamps", ()) or ()) >= int(val)
    return True

# --------------------------------------------------------------------------- fishing rods
# Keyed by the catalogue ids (data.py FISHING_RODS tuple): probe / field / deep.  Each tier's level
# range decides which evolution stages it can hook (lower rods catch first forms, higher rods the rest).
FISHING_RODS = {
    "probe_rod": {"name": "Probe Rod", "levels": (2, 8),
                  "desc": "A basic sampling probe. Casts into shallow water for young Scimons."},
    "field_rod": {"name": "Field Rod", "levels": (10, 20),
                  "desc": "A field-grade capture rod. Casts into deeper water for developed Scimons."},
    "deep_rod": {"name": "Deep Rod", "levels": (20, 35),
                 "desc": "A deep-water sampling rig. Casts into the open sea for apex Scimons."},
}
ROD_TIER = {"probe_rod": 1, "field_rod": 2, "deep_rod": 3}   # maps rod -> evolution stage to target

# --------------------------------------------------------------------------- fishing pools
# Fishing catches water/sea habitat families.  Each rod tier targets a different evolution
# stage (first / middle / final), so higher-tier rods catch higher-stage forms.
# The gym ceiling and the 50 cap are applied at encounter time, not here.


def fishing_pool(habitat):
    """All water/sea families in this habitat (any stage) — the rod's level range does the filtering."""
    from data import FAMILIES, SPECIES
    out = []
    for fid, fam in FAMILIES.items():
        if habitat not in fam.get("normal_habitats", ()):
            continue
        for sid in fam["chain_ids"]:
            out.append(sid)
    return out


def fishing_encounter(state, area, rod_id, rng=None, gym_ceiling=None):
    """One fishing encounter -> (species_id, level) or None.

    The rod's level range determines which forms are eligible: lower rods catch first forms
    at low levels, higher rods catch middle/final forms at higher levels.  The gym ceiling,
    the 50 cap and the phase cap all apply.  No stage filter: the level range does the
    filtering.  Areas without a registered water zone (styled towns like Epidimy) still
    fish the plain water/sea pool, so every rod works wherever water glitters."""
    from encounters import PHASES, POSTGAME_WILD_CAP, phase_of
    rng = rng if rng is not None else random
    from data import SPECIES
    zone = _water_zone(area)
    rod = FISHING_RODS.get(rod_id)
    if rod is None:
        return None
    lo, hi = rod["levels"]
    gc = gym_ceiling if gym_ceiling is not None else (zone.get("gym_ceiling") if zone else None) \
        or POSTGAME_WILD_CAP
    phase_cap = min(PHASES[phase_of(state)]["maximum_wild_level"], POSTGAME_WILD_CAP) if state else POSTGAME_WILD_CAP
    effective_max = min(hi, gc, phase_cap)
    effective_min = max(lo, 2)

    species_pool = []
    zone_hab = zone.get("habitat_id", "water") if zone else "water"
    for hab in (zone_hab, "water", "sea"):
        for sid in fishing_pool(hab):
            sp = SPECIES[sid]
            if sp.min_wild_level <= effective_max and sp.max_wild_level >= effective_min:
                if sid not in species_pool:
                    species_pool.append(sid)
    if not species_pool:
        return None
    sid = rng.choice(species_pool)
    sp = SPECIES[sid]
    lv_lo = max(sp.min_wild_level, effective_min)
    lv_hi = min(sp.max_wild_level, effective_max)
    if lv_lo > lv_hi:
        return None
    return sid, rng.randint(lv_lo, lv_hi)


def _water_zone(area):
    """The water/sea zone for an area (fishing uses water/sea families regardless of the walking zone)."""
    from routes import ENCOUNTER_ZONES
    for z in ENCOUNTER_ZONES.get(area, ()):
        if z["habitat_id"] in ("water", "sea"):
            return z
    return None


def has_ability(state, ability_id):
    return ability_id in getattr(state, "abilities", ())


def has_req_type(state, ability_id):
    """The player's party has at least one Scimon of the ability's required type."""
    ab = ABILITIES.get(ability_id)
    if not ab:
        return False
    for mon in getattr(state, "party", ()):
        if ab["req_type"] in mon.types:
            return True
    return False


def can_use(state, ability_id):
    """The ability is unlocked AND the party has a Scimon of the required type."""
    return has_ability(state, ability_id) and has_req_type(state, ability_id)


class FlyMenu(Scene):
    """A modal scene for the Aerolift ability: pick a visited rest point and fast-travel there."""

    state_id = StateId.DATABASE
    opaque = False

    def __init__(self, targets, on_pick):
        self.targets = targets
        self.on_pick = on_pick
        self.idx = 0
        self.rect = pygame.Rect(W // 2 - 200, H // 2 - 120, 400, min(len(targets), 8) * 36 + 80)

    def handle_event(self, e):
        import pygame as _p
        if is_back(e) or e.type == pygame.KEYDOWN and e.key == _p.K_f:
            self.engine.pop(self)
            return
        if e.type == pygame.KEYDOWN:
            if e.key == _p.K_UP:
                self.idx = max(0, self.idx - 1)
            elif e.key == _p.K_DOWN:
                self.idx = min(len(self.targets) - 1, self.idx + 1)
            elif e.key == _p.K_RETURN:
                name, area, tile = self.targets[self.idx]
                self.engine.pop(self)
                self.on_pick(area, tile)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, _t in enumerate(self.targets):
                r = pygame.Rect(self.rect.x + 20, self.rect.y + 52 + i * 36, self.rect.w - 40, 32)
                if r.collidepoint(e.pos):
                    name, area, tile = self.targets[i]
                    self.engine.pop(self)
                    self.on_pick(area, tile)

    def update(self, dt):
        self.t = getattr(self, 't', 0) + 0.016

    def draw(self, surf):
        dim(surf, 150)
        panel(surf, self.rect)
        text(surf, "AEROLIFT", (self.rect.x + 20, self.rect.y + 16), "ui_b", 16, INK)
        for i, (name, _area, _tile) in enumerate(self.targets):
            r = pygame.Rect(self.rect.x + 20, self.rect.y + 52 + i * 36, self.rect.w - 40, 32)
            c = (232, 195, 58) if i == self.idx else (180, 185, 180)
            pygame.draw.rect(surf, (40, 46, 48) if i == self.idx else (28, 32, 34), r, border_radius=6)
            text(surf, name, (r.x + 10, r.y + 6), "ui", 14, c)
