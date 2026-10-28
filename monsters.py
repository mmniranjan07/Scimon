"""Sci-Mon creature model and the pure battle formulas (damage, capture, XP, enemy AI).

Port of V34's lib/game/engine.ts creature section, including held-item effects."""
import itertools
import random
from dataclasses import dataclass, field
from typing import Optional

from data import SPECIES, TECHNIQUES, MODULES, CATALOG, EVOLUTIONS, effectiveness

PARTY_LIMIT = 6
_uid = itertools.count(1)


def xp_for_level(level):
    return 15 * level + 10


def _stat(base, level):
    return base * level // 50 + 5


def _hp(base, level):
    return base * level // 50 + level + 10


def _stability(base, level):
    return base * level // 50 + 10


def learnable_moves(species_id, level):
    learned = [t for (lv, t) in SPECIES[species_id].learnset if lv <= level]
    unique = []
    for t in learned:
        if t not in unique:
            unique.append(t)
    return unique[-4:]


@dataclass
class Scimon:
    species_id: str
    level: int
    uid: str = ""
    name: str = ""
    xp: int = 0
    xp_to_next: int = 0
    types: list = field(default_factory=list)
    max_hp: int = 0
    hp: int = 0
    max_stability: int = 0
    stability: int = 0
    power: int = 0
    defense: int = 0
    sp_power: int = 0
    sp_defense: int = 0
    speed: int = 0
    moves: list = field(default_factory=list)
    status: Optional[str] = None
    power_stage: int = 0
    held_item: Optional[str] = None

    @property
    def species(self):
        return SPECIES[self.species_id]

    def recalc_stats(self, keep_hp_ratio=False):
        sp, lv = self.species, self.level
        ratio = self.hp / self.max_hp if (keep_hp_ratio and self.max_hp) else 1.0
        self.max_hp = _hp(sp.b_hp, lv)
        self.max_stability = _stability(sp.b_stab, lv)
        self.power = _stat(sp.b_power, lv)
        self.defense = _stat(sp.b_def, lv)
        self.sp_power = _stat(sp.b_sp, lv)
        self.sp_defense = _stat(sp.b_spdef, lv)
        self.speed = _stat(sp.b_speed, lv)
        self.hp = max(1, round(self.max_hp * ratio)) if keep_hp_ratio else self.max_hp
        self.xp_to_next = xp_for_level(lv)

    def level_up_to(self, level):
        """Apply a new level while keeping the HP *ratio* (V34 levelUpTo)."""
        self.level = level
        self.recalc_stats(keep_hp_ratio=True)

    def heal_full(self):
        self.hp, self.stability = self.max_hp, self.max_stability
        self.status, self.power_stage = None, 0


def create_scimon(species_id, level):
    sp = SPECIES[species_id]
    m = Scimon(species_id=species_id, level=level, uid=f"s{next(_uid)}_{random.randrange(36**5):05x}",
               name=sp.name, types=list(sp.types))
    m.recalc_stats()
    m.stability = m.max_stability
    m.moves = learnable_moves(species_id, level)
    return m


# --------------------------------------------------------------------------- formulas
def calc_damage(att, dfn, tech, defending=False):
    """Returns (damage, effectiveness, crit)."""
    if tech.power <= 0:
        return 0, 1.0, False
    phys = tech.category == "physical"
    atk = att.power if phys else att.sp_power
    dfe = dfn.defense if phys else dfn.sp_defense
    if att.power_stage > 0:
        atk = int(atk * (1 + 0.3 * att.power_stage))
    if att.status == "Overheated":
        atk = int(atk * 1.2)
    if dfn.status == "Corroded" and phys:
        dfe = int(dfe * 0.7)
    held = CATALOG.get(att.held_item) if att.held_item else None
    if held and held.power_boost and tech.type == held.power_boost[0]:
        atk = int(atk * held.power_boost[1])
    dheld = CATALOG.get(dfn.held_item) if dfn.held_item else None
    if dheld and dheld.def_boost:
        dfe = int(dfe * dheld.def_boost)
    eff = effectiveness(tech.type, dfn.types)
    if eff == 0:
        return 0, 0.0, False
    stab = 1.25 if tech.type in att.types else 1.0
    crit = random.random() < 0.0625
    base = ((2 * att.level) / 5 + 2) * tech.power * (atk / dfe) / 50 + 2
    dmg = base * stab * eff * (1.5 if crit else 1.0) * (0.5 if defending else 1.0) * (0.85 + random.random() * 0.15)
    return max(1, int(dmg)), eff, crit


def eff_text(eff):
    if eff == 0:
        return "It has no effect..."
    if eff > 1.4:
        return "A critical scientific advantage!"
    if eff < 1:
        return "It's not very effective..."
    return None


def xp_gain(enemy):
    return max(1, SPECIES[enemy.species_id].xp_yield * enemy.level // 7)


def capture_chance(enemy, module_id):
    sp = SPECIES[enemy.species_id]
    mod = MODULES[module_id]
    hp_factor = (3 * enemy.max_hp - 2 * enemy.hp) / (3 * enemy.max_hp)
    stab_factor = 1 + (1 - enemy.stability / enemy.max_stability) * 0.6
    status_bonus = 1.4 if enemy.status else 1.0
    if mod.match_type and mod.match_type in enemy.types:
        module_bonus = mod.mult
    elif mod.match_type:
        module_bonus = 0.9
    else:
        module_bonus = 1.0
    level_factor = min(1.3, max(0.7, 1 + (10 - enemy.level) * 0.02))
    raw = hp_factor * (sp.catch_rate / 200) * stab_factor * status_bonus * module_bonus * level_factor
    return min(0.95, max(0.03, raw))


def choose_enemy_move(enemy, player):
    damaging = [m for m in enemy.moves if TECHNIQUES[m].power > 0]
    if not damaging:
        return random.choice(enemy.moves)
    if random.random() < 0.3:
        return random.choice(enemy.moves)

    def score(m):
        t = TECHNIQUES[m]
        return t.power * effectiveness(t.type, player.types) * (1.25 if t.type in enemy.types else 1.0)

    return max(damaging, key=score)


# --------------------------------------------------------------------------- evolution
def evolve(mon):
    """Transform `mon` into its evolved species (keeping level, HP ratio, uid and any nickname).  Returns
    (old name, new name) or None when there is nothing pending at this level."""
    evo = EVOLUTIONS.get(mon.species_id)
    if not evo or mon.level < evo[1]:
        return None
    target, _lv = evo
    old_species_id = mon.species_id
    old_name = mon.name
    sp = SPECIES[target]
    ratio = mon.hp / mon.max_hp if mon.max_hp else 1.0
    mon.species_id = target
    mon.types = list(sp.types)
    # keep nicknames: only rename when the current name is the current species' own name
    mon.name = sp.name if mon.name == SPECIES[old_species_id].name else mon.name
    known = set(mon.moves)
    for lv, tech in sp.learnset:
        if lv <= mon.level and tech not in known:
            known.add(tech)
            if len(mon.moves) < 4:
                mon.moves.append(tech)
    mon.recalc_stats(keep_hp_ratio=True)
    return old_name, sp.name


def check_evolutions(party):
    """Run every pending evolution across the party (after a battle's level-ups).  Returns a list of
    (mon, "old name", "new name") in party order."""
    done = []
    for mon in party:
        while True:
            res = evolve(mon)
            if not res:
                break
            done.append((mon, res[0], res[1]))
    return done
