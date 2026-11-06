"""Sci-Mon creature model and the pure battle formulas (damage, capture, XP, enemy AI).

Port of V34's lib/game/engine.ts creature section, including held-item effects, the Phase-A stat
stages / the energy system, and the battle-ability specs from data.BATTLE_ABILITIES."""
import itertools
import random
from dataclasses import dataclass, field
from typing import Optional

from data import (SPECIES, TECHNIQUES, MODULES, CATALOG, EVOLUTIONS, effectiveness, ability_spec,
                  STAGE_MIN, STAGE_MAX, stage_mult, IV_STATS, IV_MAX, EV_PER_STAT_CAP, EV_TOTAL_CAP,
                  YIELD_STATS)

PARTY_LIMIT = 6
_uid = itertools.count(1)


def xp_for_level(level):
    return 15 * level + 10


def _stat(base, level):
    return base * level // 50 + 5


def _hp(base, level):
    return base * level // 50 + level + 10


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
    max_energy: int = 0                        # the energy reserve's size (grows with level/evolution)
    power: int = 0
    defense: int = 0
    sp_power: int = 0
    sp_defense: int = 0
    speed: int = 0
    moves: list = field(default_factory=list)
    status: Optional[str] = None
    status_timer: int = 0                          # Suspended: standby turns remaining
    stages: dict = field(default_factory=dict)     # stat -> -3..+3 stage (missing key = 0)
    energy: int = 0                                # remaining energy: every technique drains its cost
    held_item: Optional[str] = None
    sturdy_used: bool = False                      # Sturdy Plating fires once per battle
    ivs: dict = field(default_factory=dict)        # stat -> Individual Value 0-31 (born talent, never changes)
    evs: dict = field(default_factory=dict)        # stat -> Effort Value (battle training; caps 255/stat, 510 total)
    bonus: dict = field(default_factory=dict)      # retired vitamin field: migrated into evs on load
    choice_lock: Optional[str] = None              # Choice Band / Logic Clip: the one technique it may use
    is_egg: bool = False                           # a Day-Care egg: hatches after walking hatch_left steps
    hatch_left: int = 0                            # remaining hatch counter in steps (cycles x HATCH_CYCLE_STEPS)

    @property
    def species(self):
        return SPECIES[self.species_id]

    @property
    def ability(self):
        return self.species.ability

    def stage(self, stat):
        return max(STAGE_MIN, min(STAGE_MAX, int(self.stages.get(stat, 0))))

    def set_stage(self, stat, value):
        """Clamped stage write; returns the new stage so callers can report it."""
        clamped = max(STAGE_MIN, min(STAGE_MAX, int(value)))
        self.stages[stat] = clamped
        return clamped

    def reset_stages(self):
        self.stages = {}

    @property
    def power_stage(self):
        return self.stage("power")                 # compat for the pre-stage-era reads

    def move_cost(self, tech_id):
        """The energy this technique drains per use (stronger techniques cost more)."""
        return TECHNIQUES[tech_id].energy

    def can_pay(self, tech_id):
        return self.energy >= self.move_cost(tech_id)

    def spend_energy(self, tech_id, n=1):
        """Drain one use's energy (Pressure-class abilities drain double)."""
        self.energy = max(0, self.energy - self.move_cost(tech_id) * n)

    def restore_energy(self):
        """An Energy Cell (or Cush's Nook): the reserves back to full."""
        self.energy = self.max_energy

    def has_energy(self):
        """True while at least one known technique is still affordable (else Struggle)."""
        return any(self.can_pay(m) for m in self.moves)

    def recalc_stats(self, keep_hp_ratio=False):
        """Gen 3's stat formula: stat = (2*base + IV + EV/4) * level / 100 (+5, or +level+10 for HP).
        With no IVs and no effort this collapses to the original V34 formula, so old saves keep their
        stats until the migration grants their IVs."""
        sp, lv = self.species, self.level
        ratio = self.hp / self.max_hp if (keep_hp_ratio and self.max_hp) else 1.0
        iv, ev = (self.ivs or {}), (self.evs or {})

        def trained(base, stat):
            return 2 * base + int(iv.get(stat, 0)) + int(ev.get(stat, 0)) // 4
        self.max_hp = trained(sp.b_hp, "hp") * lv // 100 + lv + 10
        # the energy reserves scale with the species' reserve organ (base[6]), so they grow with
        # level and jump when the Scimon evolves into a higher-bodied form
        self.max_energy = sp.b_energy * lv // 50 + 15 + lv
        self.energy = min(self.energy, self.max_energy)
        self.power = trained(sp.b_power, "power") * lv // 100 + 5
        self.defense = trained(sp.b_def, "defense") * lv // 100 + 5
        self.sp_power = trained(sp.b_sp, "sp_power") * lv // 100 + 5
        self.sp_defense = trained(sp.b_spdef, "sp_defense") * lv // 100 + 5
        self.speed = trained(sp.b_speed, "speed") * lv // 100 + 5
        self.hp = max(1, round(self.max_hp * ratio)) if keep_hp_ratio else self.max_hp
        self.xp_to_next = xp_for_level(lv)

    def level_up_to(self, level):
        """Apply a new level while keeping the HP *ratio* (V34 levelUpTo)."""
        self.level = level
        self.recalc_stats(keep_hp_ratio=True)

    def heal_full(self):
        self.hp = self.max_hp
        self.status, self.stages = None, {}
        self.energy = self.max_energy               # a Nook visit recharges the reserves too


def create_scimon(species_id, level):
    sp = SPECIES[species_id]
    m = Scimon(species_id=species_id, level=level, uid=f"s{next(_uid)}_{random.randrange(36**5):05x}",
               name=sp.name, types=list(sp.types))
    m.ivs = {s: random.randint(0, IV_MAX) for s in IV_STATS}   # born talent: unique per Scimon (Gen 3)
    m.recalc_stats()
    m.energy = m.max_energy
    m.moves = learnable_moves(species_id, level)
    return m


# --------------------------------------------------------------------------- the Day-Care egg
def hatch_cycles(species_id):
    """Steps-to-hatch budget in cycles: rarer families take longer (FireRed's per-species egg cycles)."""
    return {"common": 3, "uncommon": 4, "rare": 5}.get(SPECIES[species_id].rarity, 3)


# --------------------------------------------------------------------------- effort (EVs)
def ev_yield(species_id):
    """The effort a defeated Scimon grants (Gen 3's EV yields): 1 / 2 / 3 points in the species' highest
    base stat by stage (first / middle / final; anything unmarked counts as first).  Stability never
    yields, exactly like Gen 3 keeps its yields on the six battle stats."""
    sp = SPECIES[species_id]
    top = max(range(len(YIELD_STATS)), key=lambda i: (sp.base[i], -i))
    n = {1: 1, 2: 2, 3: 3}.get(int(sp.stage_ordinal), 1)
    return ((YIELD_STATS[top], n),)


def grant_evs(mon, yields):
    """Apply effort yields under Gen 3's caps (255 per stat, 510 in total).  Returns True when anything
    changed, so battle playback only queues an event for Scimons that actually trained."""
    changed = False
    for stat, n in yields:
        cur = int(mon.evs.get(stat, 0))
        room_stat = EV_PER_STAT_CAP - cur
        room_total = EV_TOTAL_CAP - sum(int(v) for v in mon.evs.values())
        gain = max(0, min(int(n), room_stat, room_total))
        if gain:
            mon.evs[stat] = cur + gain
            changed = True
    return changed


# --------------------------------------------------------------------------- formulas
def calc_damage(att, dfn, tech, defending=False):
    """Returns (damage, effectiveness, crit).  Stat stages and battle abilities are applied here."""
    if tech.power <= 0:
        return 0, 1.0, False
    phys = tech.category == "physical"
    atk = att.power if phys else att.sp_power
    dfe = dfn.defense if phys else dfn.sp_defense
    atk = int(atk * stage_mult(att.stage("power")))
    dfe = int(dfe * stage_mult(dfn.stage("defense" if phys else "sp_defense")))
    if att.status == "Overheated":
        atk = int(atk * 1.2)
    if dfn.status == "Corroded" and phys:
        dfe = int(dfe * 0.7)
    a_ab, d_ab = ability_spec(att), ability_spec(dfn)
    if a_ab:
        if a_ab.get("low_hp_power") and att.hp * 3 <= att.max_hp:
            atk = int(atk * a_ab["low_hp_power"])
        if a_ab.get("status_power") and att.status:
            atk = int(atk * a_ab["status_power"])
    if d_ab and d_ab.get("def_boost"):
        dfe = int(dfe * d_ab["def_boost"])
    held = CATALOG.get(att.held_item) if att.held_item else None
    if held and held.power_boost and tech.type == held.power_boost[0]:
        atk = int(atk * held.power_boost[1])
    if held and held.choice_boost and tech.category == held.choice_boost[0]:
        atk = int(atk * held.choice_boost[1])
    dheld = CATALOG.get(dfn.held_item) if dfn.held_item else None
    if dheld and dheld.def_boost:
        dfe = int(dfe * dheld.def_boost)
    eff = effectiveness(tech.type, dfn.types)
    if eff == 0:
        return 0, 0.0, False
    stab = 1.25 if tech.type in att.types else 1.0
    crit_mult = (a_ab.get("crit_mult", 1) if a_ab else 1) * (held.crit_boost if held else 1)
    crit = random.random() < 0.0625 * crit_mult
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
    status_bonus = 1.4 if enemy.status else 1.0
    if mod.match_type and mod.match_type in enemy.types:
        module_bonus = mod.mult
    elif mod.match_type:
        module_bonus = 0.9
    else:
        module_bonus = 1.0
    level_factor = min(1.3, max(0.7, 1 + (10 - enemy.level) * 0.02))
    raw = hp_factor * (sp.catch_rate / 200) * status_bonus * module_bonus * level_factor
    return min(0.95, max(0.03, raw))


def _status_immune(mon, status_id):
    from data import BATTLE_ABILITIES
    spec = BATTLE_ABILITIES.get(mon.ability)
    return bool(spec and status_id in spec.get("status_immune", ()))


def choose_enemy_move(enemy, player):
    """The enemy's technique choice: damage moves score power x effectiveness x STAB, status moves score
    by their tactical value (buff early, inflict on a clean target, skip what would fail), with a 20%
    random fallback so it never plays fully predictively.  Falls back to Struggle out of energy."""
    from data import STATUS_INFO
    moves = list(enemy.moves)
    usable = [m for m in moves if enemy.can_pay(m)]
    if not usable:
        return "struggle"
    reasonable = [m for m in usable if not TECHNIQUES[m].status
                  or (not player.status and not _status_immune(player, TECHNIQUES[m].status)
                      and enemy.energy >= 2 * enemy.move_cost(m))]      # never waste low reserves on status
    if random.random() < 0.2:
        return random.choice(reasonable or usable)

    best, best_score = None, -1.0
    for m in usable:
        t = TECHNIQUES[m]
        if t.power > 0:
            score = t.power * effectiveness(t.type, player.types) * (1.25 if t.type in enemy.types else 1.0)
        elif t.status:
            if player.status or _status_immune(player, t.status) \
                    or enemy.energy < 2 * enemy.move_cost(m):      # keep the reserves for a real shot
                continue
            score = 60.0
        elif t.buffs:
            if all(enemy.stage(s) >= 2 for s in t.buffs):
                continue
            score = 45.0 + 5.0 * sum(max(0, 2 - enemy.stage(s)) for s in t.buffs)
        elif t.debuffs:
            if all(player.stage(s) <= -2 for s in t.debuffs):
                continue
            score = 45.0 + 5.0 * sum(max(0, player.stage(s) + 2) for s in t.debuffs)
        else:
            score = 10.0
        if score > best_score:
            best, best_score = m, score
    if best is None:
        best = max((m for m in usable if TECHNIQUES[m].power > 0), default=usable[0],
                   key=lambda m: TECHNIQUES[m].power * effectiveness(TECHNIQUES[m].type, player.types))
    return best


# --------------------------------------------------------------------------- evolution
def evolve(mon):
    """Transform `mon` into its evolved species (keeping level, HP ratio, uid and any nickname).  Returns
    (old name, new name, [techniques the full moveset could not take -- prompt the player, FireRed-style])
    or None when there is nothing pending at this level."""
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
    pending = []
    for lv, tech in sp.learnset:
        if lv <= mon.level and tech not in known:
            known.add(tech)
            if len(mon.moves) < 4:
                mon.moves.append(tech)
            else:
                pending.append(tech)
    mon.recalc_stats(keep_hp_ratio=True)
    return old_name, sp.name, pending


def check_evolutions(party):
    """Run every pending evolution across the party (after a battle's level-ups).  Returns a list of
    (mon, "old name", "new name", [techniques the full moveset could not take]) in party order."""
    done = []
    for mon in party:
        while True:
            res = evolve(mon)
            if not res:
                break
            done.append((mon, res[0], res[1], res[2]))
    return done
