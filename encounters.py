"""Wild encounter selection: the single authoritative selector per triggered wild encounter.

Policy (scimon_database.json -> data.ENCOUNTER_POLICY):
1. resolve the location's zone (habitat, level band) and the player's progression phase,
2. roll ONCE for the branch: 0.1% global migration, otherwise the normal habitat pool,
3. build that branch's eligible pool (progression-locked stages and invalid level intervals removed),
4. select the stage with the phase weights, normalized over the available nonzero-weight stages,
5. normal: family by canonical rarity weight in this habitat; migration: uniform family among all
   wild-enabled families carrying the selected stage -- starters included,
6. that family's selected-stage form, then a uniform valid level.

The 0.1% is per triggered wild encounter (not per species, per tile or per frame) and bypasses the
habitat restriction only: stage gates, wild-enabled locations, level bands and the game cap all hold.
A migrated Scimon keeps exactly the rolled species id -- no auto-evolution afterwards.
"""
import random

from data import ENCOUNTER_POLICY, FAMILIES, FAMILY_OF, PHASES, SPECIES

MIGRATION_PROBABILITY = ENCOUNTER_POLICY["global_migration_probability"]
LEVEL_CAP = ENCOUNTER_POLICY["level_cap"]

# ---------------------------------------------------------------------------
# Gym progression reference (FireRed gym-team levels mapped to the Scimon region).
# The ace is the highest-level creature on the leader's team.  The wild ceiling for a gym's
# progression region is the ace minus the configured gap.  These are upper limits, not mandatory
# encounter levels.  Gym 1 is the Green Gym (Fern, Botanic, Epidimy Town); gyms 2-8 are future
# content -- their progression records drive the zone level ceilings.
GYM_REFERENCE = {
    1: {"ace": 14, "gap": 4, "ceiling": 10, "leader": "Fern", "gym": "Green Gym",
        "team": [("petalug", 12), ("florabot", 14)]},
    2: {"ace": 21, "gap": 5, "ceiling": 16},
    3: {"ace": 24, "gap": 6, "ceiling": 18},
    4: {"ace": 29, "gap": 7, "ceiling": 22},
    5: {"ace": 43, "gap": 10, "ceiling": 33},
    6: {"ace": 43, "gap": 10, "ceiling": 33},
    7: {"ace": 47, "gap": 12, "ceiling": 35},
    8: {"ace": 50, "gap": 15, "ceiling": 35},
}
POSTGAME_WILD_CAP = 50
POSTGAME_STORY_FLAG = "boss_beaten"

_coverage_errors = []          # (zone_id, reason) -- drained by the debug overlay / tests


def coverage_errors():
    return list(_coverage_errors)


def phase_of(state):
    """Durable progression phase from the saved milestones only (never party level / playtime)."""
    stamps = getattr(state, "stamps", ())
    if "green" in stamps:
        if "boss_beaten" in getattr(state, "story", ()):
            return 2
        return 1
    return 0


def _stage_eligible(sid, phase, interval, cap):
    """A species is eligible for a wild slot when its stage is unlocked and a valid level exists."""
    sp = SPECIES[sid]
    if sp.wild_unlock_phase > phase:
        return False
    return interval is not None and interval[0] <= interval[1] and interval[1] <= cap


def _level_interval(sid, band, cap, gym_ceiling=None, migration_band=None):
    """The form's legal wild level interval for one encounter.

    effective_max = min(zone_band_max, gym_ceiling, 50, phase_cap, form_max_wild_level)
    effective_min = max(zone_band_min, form_min_wild_level)
    Forms whose minimum exceeds the effective maximum are excluded (no clamping up past the cap).
    """
    sp = SPECIES[sid]
    hi = min(band[1], sp.max_wild_level, cap)
    if gym_ceiling is not None:
        hi = min(hi, gym_ceiling)
    hi = min(hi, LEVEL_CAP)
    lo = max(band[0], sp.min_wild_level)
    if migration_band:
        lo = max(lo, migration_band[0])
        hi = min(hi, migration_band[1])
    if lo > hi:
        return None
    return (lo, hi)


def _weighted_family(pairs, rng):
    total = sum(w for _f, w in pairs)
    r = rng.random() * total
    for fid, w in pairs:
        r -= w
        if r <= 0:
            return fid
    return pairs[-1][0]


def _gym_ceiling(zone, state):
    """The zone's wild level ceiling: the gym-relative ceiling, or the postgame cap for postgame
    zones after the story milestone (the postgame ceiling also extends the zone band max upward
    so final forms become reachable)."""
    if zone.get("postgame") and POSTGAME_STORY_FLAG in getattr(state, "story", ()):
        return POSTGAME_WILD_CAP
    return GYM_REFERENCE.get(zone.get("gym_id", 1), {}).get("ceiling", LEVEL_CAP)


def _zone_band(zone, state):
    """The effective zone band: for postgame zones after the story milestone, the band max
    extends to the postgame ceiling so final forms (min_wild_level 19+) become reachable."""
    band = zone["band"]
    if zone.get("postgame") and POSTGAME_STORY_FLAG in getattr(state, "story", ()):
        return (band[0], POSTGAME_WILD_CAP)
    return band


def select_encounter(state, zone, rng=None):
    """One triggered wild encounter -> (species_id, level) or None.  `zone` is a routes.py zone dict
    (habitat_id, band, gym_ceiling, wild_enabled); `rng` is injectable for seeded tests."""
    rng = rng if rng is not None else random
    if zone is None or not zone.get("wild_enabled", True):
        return None
    phase = phase_of(state)
    phase_def = PHASES[phase]
    cap = min(int(phase_def["maximum_wild_level"]), POSTGAME_WILD_CAP)
    stage_weights = {int(k): w for k, w in phase_def["stage_weights"].items()}
    habitat = zone["habitat_id"]
    band = _zone_band(zone, state)
    gym_ceiling = _gym_ceiling(zone, state)
    migration_band = tuple(phase_def.get("migration_level_band", ()))

    migration = rng.random() < MIGRATION_PROBABILITY

    if migration:
        # global migration: any wild-enabled family with an unlocked, level-valid stage, habitat ignored.
        # Levels use the migration band intersected with the form's hard interval, the phase cap, and
        # the CURRENT location's gym ceiling -- migration bypasses habitat only.
        by_stage = {s: [] for s in stage_weights}
        for fid, fam in FAMILIES.items():
            if not (fam.get("wild_enabled", True) and fam.get("global_migration_enabled", True)):
                continue
            for sid in fam["chain_ids"]:
                stage = SPECIES[sid].stage_ordinal
                interval = _level_interval(sid, (0, LEVEL_CAP), cap, gym_ceiling, migration_band)
                if interval and _stage_eligible(sid, phase, interval, cap):
                    by_stage[stage].append(sid)
        weights = {s: w for s, w in stage_weights.items() if by_stage.get(s)}
        if not weights:
            _coverage_errors.append((zone["zone_id"], "empty migration pool"))
            return _normal_pool(state, zone, rng, cap, gym_ceiling)
        total_w = sum(weights.values())
        r = rng.random() * total_w
        stage = next(s for s in sorted(weights) for _ in [0] if (r := r - weights[s]) <= 0)
        sid = rng.choice(by_stage[stage])
        lo, hi = _level_interval(sid, (0, LEVEL_CAP), cap, gym_ceiling, migration_band)
        return sid, rng.randint(lo, hi)

    return _normal_pool(state, zone, rng, cap, gym_ceiling)


def _normal_pool(state, zone, rng, cap=None, gym_ceiling=None):
    """The normal habitat branch: the zone's habitat decides the family pool (one form per family per
    stage).  Returns (species_id, level) or None when the zone has no eligible pool at all."""
    if cap is None:
        phase = phase_of(state)
        cap = min(int(PHASES[phase]["maximum_wild_level"]), POSTGAME_WILD_CAP)
    if gym_ceiling is None:
        gym_ceiling = _gym_ceiling(zone, state)
    phase = phase_of(state)
    phase_def = PHASES[phase]
    stage_weights = {int(k): w for k, w in phase_def["stage_weights"].items()}
    habitat = zone["habitat_id"]
    band = _zone_band(zone, state)
    by_stage = {s: [] for s in stage_weights}
    for fid, fam in FAMILIES.items():
        if habitat not in fam.get("normal_habitats", ()) or not fam.get("wild_enabled", True):
            continue
        for stage_in_chain, sid in enumerate(fam["chain_ids"], 1):
            stage = SPECIES[sid].stage_ordinal
            interval = _level_interval(sid, band, cap, gym_ceiling)
            if interval and _stage_eligible(sid, phase, interval, cap):
                by_stage[stage].append(fid)
    weights = {s: w for s, w in stage_weights.items() if by_stage.get(s)}
    if not weights:
        _coverage_errors.append((zone["zone_id"], f"no normal pool in habitat {habitat}"))
        return None
    total_w = sum(weights.values())
    r = rng.random() * total_w
    stage = next(s for s in sorted(weights) for _ in [0] if (r := r - weights[s]) <= 0)
    fam_id = _weighted_family([(fid, FAMILIES[fid]["normal_family_weight"]) for fid in by_stage[stage]], rng)
    sid = FAMILIES[fam_id]["chain_ids"][stage - 1]
    lo, hi = _level_interval(sid, band, cap, gym_ceiling)
    return sid, rng.randint(lo, hi)
