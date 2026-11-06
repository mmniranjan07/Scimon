"""The Day-Care (Route 5): FireRed's breeding system on SCI-MON's habitat-pairing model.

Two Scimons deposited with Keeper Sorrel bank every overworld step as EXP (FireRed's rule: steps ==
EXP points, applied level-by-level at withdrawal for 100 credits + 100 per level gained).  While both
slots are filled and no egg is pending, every EGG_ROLL_STEPS steps rolls against the pair's
compatibility score; a win leaves an egg with Sorrel.  Party eggs tick their hatch counter down each
step and hatch into the family's first stage at level EGG_HATCH_LEVEL.

Pairing (SCI-MON has no genders, so habitats stand in for egg groups):
  either Scimon is a first-stage baby  -> infertile (Gen 3's undiscovered group)
  same family                          -> 50  "The two seem to get along."
  different families, shared habitat   -> 20  "The two don't seem to like each other much."
  otherwise                            ->  0  "The two prefer to play with other Scimons than each other."
"""
import random

from data import CHAIN_OF, FAMILY_OF, LEVEL_CAP, SPECIES
from monsters import create_scimon, hatch_cycles, xp_for_level
from settings import DAYCARE_LEVEL_COST, DAYCARE_SLOTS, EGG_HATCH_LEVEL, EGG_ROLL_STEPS, HATCH_CYCLE_STEPS

COMPAT_TEXT = {
    50: "The two seem to get along.",
    20: "The two don't seem to like each other much.",
    0: "The two prefer to play with other Scimons than each other.",
}


def compat_score(mon_a, mon_b):
    """The pair's compatibility score (0, 20 or 50): the egg-roll chance in percent."""
    if mon_a.species.stage_role == "first" or mon_b.species.stage_role == "first":
        return 0                                   # babies don't breed (Gen 3's undiscovered group)
    if FAMILY_OF.get(mon_a.species_id) == FAMILY_OF.get(mon_b.species_id):
        return 50                                  # same family
    if set(mon_a.species.normal_habitats) & set(mon_b.species.normal_habitats):
        return 20                                  # same habitat, different families
    return 0


def compat_text(mon_a, mon_b):
    return COMPAT_TEXT[compat_score(mon_a, mon_b)]


def can_deposit(st):
    """FRLG's deposit guards: keep at least one healthy, non-egg Scimon in the party."""
    if not any(m.hp > 0 and not m.is_egg for m in st.party):
        return False, "You have no Scimon able to battle!"
    if len([m for m in st.party if not m.is_egg]) <= 1:
        return False, "You have to keep at least one Scimon with you!"
    if len(st.daycare) >= DAYCARE_SLOTS:
        return False, "The Day-Care is full."
    return True, ""


def deposit(st, uid):
    """Copy a party Scimon into a Day-Care slot (its PP restored, steps zeroed, FireRed's deposit)."""
    ok, msg = can_deposit(st)
    if not ok:
        return False, msg
    mon = next((m for m in st.party if m.uid == uid), None)
    if not mon or mon.is_egg:
        return False, "That Scimon isn't available."
    mon.restore_energy()
    st.party.remove(mon)
    st.daycare.append({"mon": mon, "steps": 0})
    return True, f"{mon.name} was left with the Day-Care."


def _apply_daycare_exp(mon, steps):
    """FireRed's ApplyDaycareExperience: EXP += banked steps, applied level-by-level.  New learnset
    techniques replace the first technique when the moveset is full (no prompt, FireRed's daycare rule).
    Returns levels gained."""
    work, level = mon.xp + steps, mon.level
    while work >= xp_for_level(level) and level < LEVEL_CAP:
        work -= xp_for_level(level)
        level += 1
        for lv, tech in SPECIES[mon.species_id].learnset:
            if lv == level and tech not in mon.moves:
                if len(mon.moves) >= 4:
                    mon.moves.pop(0)
                mon.moves.append(tech)
    mon.xp, mon.xp_to_next = work, xp_for_level(level)
    mon.level_up_to(level)


def levels_gained(slot):
    """(level before, level after) for a deposited Scimon, counting its banked steps as EXP (FRLG)."""
    mon, steps = slot["mon"], slot["steps"]
    work, level = mon.xp + steps, mon.level
    while work >= xp_for_level(level) and level < LEVEL_CAP:
        work -= xp_for_level(level)
        level += 1
    return mon.level, level


def withdraw_cost(slot):
    before, after = levels_gained(slot)
    return DAYCARE_LEVEL_COST + DAYCARE_LEVEL_COST * (after - before), after - before


def withdraw(st, idx):
    """Take a deposited Scimon back: pay 100 + 100 per level gained, apply the banked EXP level-by-level."""
    if not (0 <= idx < len(st.daycare)):
        return False, "That slot is empty."
    slot = st.daycare[idx]
    cost, gained = withdraw_cost(slot)
    if st.credits < cost:
        return False, f"You don't have the {cost} credits for the Day-Care."
    if len(st.party) >= 6:
        return False, "Your party is full."
    mon = slot["mon"]
    st.credits -= cost
    _apply_daycare_exp(mon, slot["steps"])
    st.daycare.pop(idx)
    st.party.append(mon)
    msg = f"{mon.name} came back" + (f" and grew {gained} level{'s' if gained != 1 else ''}!" if gained else "!")
    return True, msg + (f"  (-{cost} credits)" if cost else "")


def _egg_of(species_id, parents):
    """An egg of exactly `species_id`: random 0-31 IVs with INHERITED_IVS copied from the parents, the
    level-1 moveset plus shared parent techniques the child's learnset carries (Gen 3's egg rules)."""
    from data import IV_STATS
    from settings import INHERITED_IVS
    egg = create_scimon(species_id, EGG_HATCH_LEVEL)
    egg.name = "Egg"
    egg.is_egg = True
    egg.hatch_left = hatch_cycles(species_id) * HATCH_CYCLE_STEPS
    for stat in random.sample(list(IV_STATS), INHERITED_IVS):
        egg.ivs[stat] = int(random.choice(parents).ivs.get(stat, egg.ivs[stat]))
    egg.recalc_stats()
    egg.energy = egg.max_energy
    known = set(egg.moves)
    shared = set(parents[0].moves) & set(parents[1].moves) if len(parents) >= 2 else set()
    for tech in shared:
        if tech not in known and len(egg.moves) < 4 \
                and any(t == tech for _lv, t in SPECIES[species_id].learnset):
            egg.moves.append(tech)
            known.add(tech)
    return egg


def on_step(st, rng=None):
    """One overworld step in the wider world: bank Day-Care steps, roll for an egg, tick party eggs.
    Returns a list of messages to toast (egg produced, egg hatched...)."""
    rng = rng or random
    out = []
    for slot in st.daycare:
        slot["steps"] += 1
    # egg production: only while both slots are filled and nothing is pending (FRLG's roll window)
    if len(st.daycare) >= DAYCARE_SLOTS and not st.daycare_egg:
        if st.daycare[1]["steps"] % EGG_ROLL_STEPS == 0:
            score = compat_score(st.daycare[0]["mon"], st.daycare[1]["mon"])
            if score > 0 and rng.randrange(100) < score:
                mother = rng.choice([s["mon"] for s in st.daycare])
                st.daycare_egg = CHAIN_OF[mother.species_id][0]
                out.append("The Day-Care keeper found an egg! (Go claim it at the Day-Care.)")
    # hatching: party eggs count steps down (FRLG's ShouldEggHatch, scaled)
    for mon in list(st.party):
        if mon.is_egg:
            mon.hatch_left -= 1
            if mon.hatch_left <= 0:
                out.append(_hatch(st, mon))
    return out


def _hatch(st, mon):
    """An egg hatches in place: it becomes its species' first stage at EGG_HATCH_LEVEL."""
    fresh = create_scimon(mon.species_id, EGG_HATCH_LEVEL)
    fresh.uid, fresh.ivs = mon.uid, mon.ivs          # keep identity + the inherited IVs
    idx = st.party.index(mon)
    st.party[idx] = fresh
    st.captured.add(fresh.species_id)
    st.seen.add(fresh.species_id)
    return f"Congratulations! The Egg hatched into {fresh.name}!"


def take_egg(st):
    """Accept the egg waiting at the Day-Care (requires a free party slot; FRLG's hand-out)."""
    if not st.daycare_egg:
        return False, "There is no egg waiting."
    if len(st.party) >= 6:
        return False, "Your party is full - make room first."
    parents = [s["mon"] for s in st.daycare] or [create_scimon(st.daycare_egg, 5)]
    egg = _egg_of(st.daycare_egg, parents)
    st.party.append(egg)
    st.captured.add(egg.species_id)
    st.seen.add(egg.species_id)
    st.daycare_egg = None
    return True, "You received the Egg! Walk with it and it will hatch."
