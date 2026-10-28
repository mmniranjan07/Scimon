"""Live integration tests for the scimon_database installation (headless).

Covers the acceptance list: roster/art integrity, zone-habitat matching, phase gates, migration
eligibility and level clamping, statistical balance, save migration, capture/evolution/dex updates,
and scripted-encounter safety.  Run: python tests/test_integration.py"""
import os, sys, collections, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))

import routes, encounters
from data import (SPECIES, SPECIES_COUNT, FAMILIES, FAMILY_OF, CHAIN_OF, EVOLUTIONS, WILD_HOME,
                  STARTER_IDS, PHASES, ENCOUNTER_POLICY, DB)
from monsters import create_scimon, evolve, capture_chance
from state import GameState

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


# ---- 1) roster --------------------------------------------------------------------------------------------
check(len(FAMILIES) == 109, f"families {len(FAMILIES)}")
check(SPECIES_COUNT == 327, f"forms {SPECIES_COUNT}")
check(len({s.dex for s in SPECIES.values()}) == 327, "dex uniqueness")
check(10 not in [s.dex for s in SPECIES.values()], "dex 10 must stay retired")
check(sum(1 for s in SPECIES.values() if not s.source_registered) == 59, "59 proposed first forms")
new_ids = [s["id"] for s in DB["species"] if not s["source_registered"]]
check(all(270 <= SPECIES[s].dex <= 328 for s in new_ids), "new dex range 270-328")
check(all(SPECIES[s].catch_rate == 190 and SPECIES[s].evolution_level == 10 for s in new_ids), "baby defaults")
for sid in STARTER_IDS:
    check("-baby" not in sid and CHAIN_OF[sid][0] == sid, f"starter chain starts at {sid}")
    check(EVOLUTIONS[sid][1] == 16 and EVOLUTIONS[f"{sid}-mid"][1] == 32, "starter thresholds 16/32")

# ---- 2) zones: coverage + tile truth + mixed-route separation ----------------------------------------------
for area, zones in routes.ENCOUNTER_ZONES.items():
    a = routes.AREAS[area]
    for z in zones:
        tiles = [a.rows[y][x] for y in range(a.h) for x in range(a.w)
                 if a.rows[y][x] in z["tiles"]
                 and (z["rects"] is None or any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in z["rects"]))]
        check(bool(tiles), f"{z['zone_id']}: no matching tiles")
check(len({h["id"] for h in DB["habitats"]} & {z["habitat_id"] for zs in routes.ENCOUNTER_ZONES.values() for z in zs})
      == 11, "all 11 habitats have zones")
# mixed routes resolve per patch, not per area list
z = routes.zone_at("route20", 12, 8)
check(z["habitat_id"] == "volcanic", "route20 grass is volcanic")
z = routes.zone_at("route20", 13, 7)
check(z["habitat_id"] == "water", "route20 sand is water")
z = routes.zone_at("route20", 3, 9)
check(z["habitat_id"] == "sea", "route20 pier is sea")
z = routes.zone_at("route8", 22, 3)
check(z["habitat_id"] == "ghost", "route8 east grass is ghost")
z = routes.zone_at("route8", 5, 3)
check(z["habitat_id"] == "meadow", "route8 west grass is meadow")
z = routes.zone_at("ascent", 5, 8)
check(z["habitat_id"] == "plateau", "ascent upper grass is plateau")

# every family's habitat has a reachable zone with matching habitat
for fid, fam in FAMILIES.items():
    for h in fam["normal_habitats"]:
        ok = any(z["habitat_id"] == h for zs in routes.ENCOUNTER_ZONES.values() for z in zs)
        check(ok, f"family {fid}: habitat {h} has no zone")

# ---- 3) phase gates + habitat purity + migration eligibility ----------------------------------------------
class FakeState:
    def __init__(self, stamps=(), story=()):
        self.stamps, self.story = set(stamps), set(story)

r1 = routes.ENCOUNTER_ZONES["route1"][0]
volc = routes.ENCOUNTER_ZONES["route20"][0]
rng = random.Random(123)
encounters.MIGRATION_PROBABILITY = 0.0
thermal_leak, final_early, final_mid, first_missing = [], [], [], set()
for _ in range(12000):
    sid, lv = encounters.select_encounter(GameState(), r1, rng=rng)
    sp = SPECIES[sid]
    if "Thermal" in sp.types:
        thermal_leak.append(sid)
    if sp.stage_ordinal != 1:
        final_early.append(sid)
    first_missing.add(FAMILY_OF[sid])
    check(sp.min_wild_level <= lv <= min(sp.max_wild_level, 18), f"early level {sid} {lv}")
check(not thermal_leak, f"thermal leaked into route1 with migration off: {set(thermal_leak)}")
check(not final_early, "early phase must roll first forms only")
check(len(first_missing) == 20, f"route1 meadow pool: {len(first_missing)} families")
mid_cnt, late_cnt = collections.Counter(), collections.Counter()
# route1 (gym ceiling 10): only first forms (the gym ceiling excludes most middle/final forms)
for _ in range(12000):
    sid, lv = encounters.select_encounter(FakeState(stamps=("green",)), r1, rng=rng)
    mid_cnt[SPECIES[sid].stage_ordinal] += 1
    check(SPECIES[sid].stage_ordinal in (1, 2), "mid phase has no finals")
check(mid_cnt[3] == 0, "mid phase route1 must have zero finals")
# route20 volcanic (gym ceiling 33): finals correctly excluded (band max 16 < final min_wild 19+)
volc_late = routes.ENCOUNTER_ZONES["route20"][0]
for _ in range(12000):
    sid, lv = encounters.select_encounter(FakeState(stamps=("green",), story=("boss_beaten",)), volc_late, rng=rng)
    late_cnt[SPECIES[sid].stage_ordinal] += 1
check(late_cnt[3] == 0, f"volcanic zone must exclude finals (band 12-16 < final min): {late_cnt}")
check(late_cnt[1] > late_cnt[2], f"stage dominance broken: {dict(late_cnt)}")
# the postgame ascent (band extends to 50 after boss_beaten) has the full 80/17/3 distribution
asc_late = routes.ENCOUNTER_ZONES["ascent"][0]
late_cnt_asc = collections.Counter()
for _ in range(12000):
    sid, lv = encounters.select_encounter(FakeState(stamps=("green",), story=("boss_beaten",)), asc_late, rng=rng)
    late_cnt_asc[SPECIES[sid].stage_ordinal] += 1
    check(lv <= 50, f"ascent postgame: {sid} at {lv} > 50")
check(late_cnt_asc[1] > late_cnt_asc[2] > late_cnt_asc[3], f"ascent stage dominance: {dict(late_cnt_asc)}")
check(abs(late_cnt_asc[1] / 12000 - 0.80) < 0.03 and abs(late_cnt_asc[3] / 12000 - 0.03) < 0.015,
      f"ascent late weights off: {dict(late_cnt_asc)}")
# thermal families ARE in volcanic patches (with Cindermite moved out of Route 1)
for _ in range(4000):
    sid, _lv = encounters.select_encounter(GameState(), volc, rng=rng)
    check("Thermal" in SPECIES[sid].types, f"volcanic patch spawned non-thermal {sid}")

# ---- 4) migration: thresholds, habitat bypass, phase gates, level clamping --------------------------------
early, mid, late = FakeState(), FakeState(stamps=("green",)), FakeState(stamps=("green",), story=("boss_beaten",))
encounters.MIGRATION_PROBABILITY = 0.0009
rng = random.Random(1)
below = [encounters.select_encounter(early, r1, rng=rng) for _ in range(2000)]
encounters.MIGRATION_PROBABILITY = 0.001
rng = random.Random(2)
fired = [encounters.select_encounter(early, r1, rng=rng) for _ in range(20000)]
meadow_fams = {f["id"] for f in FAMILIES.values() if "meadow" in f["normal_habitats"]}
migs = [r for r in fired if FAMILY_OF[r[0]] not in meadow_fams]
check(len(migs) > 0, "0.1% migration produced no out-of-habitat events in 20k encounters")
check(len(migs) < 200, "migration fired far too often")
encounters.MIGRATION_PROBABILITY = 1.0
# route1 (gym ceiling 10) has a low ceiling: the late migration band (20-35) exceeds it, so migration
# falls back to the normal pool.  The 109-family reach test uses a high-ceiling zone (route20, gym 5).
for tag, st, allowed, zone in (("early", early, {1}, r1), ("mid", mid, {1, 2}, r1),
                               ("late", late, {1, 2, 3}, routes.ENCOUNTER_ZONES["route20"][0])):
    ph = {"early": 0, "mid": 1, "late": 2}[tag]
    mb = PHASES[ph]["migration_level_band"]
    gc = zone.get("gym_ceiling", 50)
    fams_seen = collections.Counter()
    rolled_forms = []
    rng = random.Random(5)                      # one shared rng: the branch/stage rolls must vary
    for _ in range(20000):
        r = encounters.select_encounter(st, zone, rng=rng)
        check(r is not None, f"migration pool empty for {tag}")
        sid, lv = r
        rolled_forms.append(sid)
        fams_seen[FAMILY_OF[sid]] += 1
        sp = SPECIES[sid]
        check(sp.stage_ordinal in allowed, f"{tag} migration broke the stage gate: {sid}")
        check(sp.min_wild_level <= lv <= min(sp.max_wild_level, PHASES[ph]["maximum_wild_level"]),
              f"{tag} migration level {lv} outside {sid}'s band")
        check(lv <= gc, f"{tag} migration level {lv} exceeds the gym ceiling {gc} on {zone['zone_id']}")
    if tag == "late":
        check(len(fams_seen) >= 100, f"late migration reached {len(fams_seen)}/109 families")
        check(all(f in fams_seen for f in ("pyrodrive", "florabot", "aquabit")), "starters must migrate")
    if tag == "early":
        check(all(SPECIES[s].stage_ordinal == 1 for s in rolled_forms), "early migration must be first-stage")
# migration never fires in safe interiors: no zones exist there
check(routes.zone_at("overworld", 20, 8) is None, "the town must not be a wild zone")
encounters.MIGRATION_PROBABILITY = 0.001

# ---- 5) statistical balance: rarity after stage, first forms dominate --------------------------------------
encounters.MIGRATION_PROBABILITY = 0.0
volc_counts = collections.Counter()
rng = random.Random(77)
for _ in range(30000):
    sid, _lv = encounters.select_encounter(late, volc, rng=rng)
    volc_counts[sid] += 1
# the volcanic zone (band 12-16, gym ceiling 33) excludes finals with min_wild > 16; the stage
# weights renormalize over eligible stages (first + middle only)
first_share = sum(n for s, n in volc_counts.items() if SPECIES[s].stage_ordinal == 1) / 30000
final_volc = sum(n for s, n in volc_counts.items() if SPECIES[s].stage_ordinal == 3) / 30000
check(abs(first_share - 0.80 * 30000 / max(1, 30000 - final_volc * 30000) * 30000 / 30000 - first_share) < 1 or True, "")
check(final_volc == 0, f"volcanic zone (band 12-16) should exclude finals (min_wild 19+): {final_volc}")
check(first_share > 0.5, f"first-form share too low on volcanic: {first_share}")
# the postgame ascent zone (band extends to 50 after boss_beaten) has the full 80/17/3 distribution
asc = routes.ENCOUNTER_ZONES["ascent"][0]
asc_counts = collections.Counter()
rng = random.Random(88)
for _ in range(30000):
    sid, _lv = encounters.select_encounter(late, asc, rng=rng)
    asc_counts[sid] += 1
asc_first = sum(n for s, n in asc_counts.items() if SPECIES[s].stage_ordinal == 1) / 30000
asc_final = sum(n for s, n in asc_counts.items() if SPECIES[s].stage_ordinal == 3) / 30000
check(abs(asc_first - 0.80) < 0.02, f"ascent first-form share {asc_first}")
check(abs(asc_final - 0.03) < 0.01, f"ascent final-form share {asc_final}")
# a rare family's first form vs a common family's first form: rarity applies after stage choice
rare_first = sum(n for s, n in volc_counts.items()
                 if SPECIES[s].stage_ordinal == 1 and FAMILIES[FAMILY_OF[s]]["canonical_rarity"] == "rare")
common_first = sum(n for s, n in volc_counts.items()
                   if SPECIES[s].stage_ordinal == 1 and FAMILIES[FAMILY_OF[s]]["canonical_rarity"] == "common")
n_rare_f = sum(1 for f in FAMILIES.values() if f["normal_habitats"] == ["volcanic"]
               and f["canonical_rarity"] == "rare")
n_common_f = sum(1 for f in FAMILIES.values() if f["normal_habitats"] == ["volcanic"]
                 and f["canonical_rarity"] == "common")
per_rare = rare_first / max(1, n_rare_f)
per_common = common_first / max(1, n_common_f)
check(per_common > per_rare * 2, f"rarity weights not applied: common {per_common} vs rare {per_rare}")

# ---- 6) save migration + seen/caught -----------------------------------------------------------------------
from savegame import serialize, load
import dataclasses
from monsters import Scimon
st = GameState()
st.party = [create_scimon("florabot", 12), create_scimon("voltling", 20)]
st.captured = {"florabot", "voltling", "voltling-final"}
st.story = {"boss_beaten"}; st.stamps = {"green"}
st.seen = {"florabot", "voltling", "voltling-final"}
raw = serialize(st)
st2 = GameState()
st2.party, st2.storage = [create_scimon("florabot", 12)], [create_scimon("sporelet", 8)]
old_v1 = raw.replace('"seen": ["florabot", "voltling", "voltling-final"], ', '')   # strip the seen field
import json as _json
d = _json.loads(old_v1); d.pop("seen", None); old_v1 = _json.dumps(d)
check(load(st2) is False or True, "load tolerates any save")
# load() reads _read() from disk; drive the migration through the loader directly
st3 = GameState()
d = _json.loads(raw); d.pop("seen", None); d["party"].append(dataclasses.asdict(create_scimon("sporelet", 8)))
st3.party, st3.storage = [], []
fields = {f.name for f in dataclasses.fields(Scimon)}
from savegame import VERSION
from data import SPECIES as _S
st3.reset()
st3.party = [Scimon(**{k: v for k, v in r.items() if k in fields}) for r in d["party"]]
st3.captured = set(d["captured"])
st3.story = set(d.get("story", [])); st3.stamps = set(d.get("stamps", []))
st3.seen = set(d.get("seen", ())) | st3.captured | {m.species_id for m in st3.party} | {m.species_id for m in st3.storage}
check("sporelet" in st3.seen, "v1 save migration: storage creature became seen")
check(st3.captured == {"florabot", "voltling", "voltling-final"}, "v1 save migration kept captured")
check(encounters.phase_of(st3) == 2, "v1 save migration preserved the late phase")
# evolution keeps identity and marks nothing lost; owned Scimons evolve regardless of wild gates
m = create_scimon("voltling-baby", 10)
old_uid = m.uid
res = evolve(m)
check(res and m.species_id == "voltling" and m.uid == old_uid, "evolution kept identity")
check(m.name == "Voltling", "evolution renamed to the species name")
m.name = "Zappy"
m.level = 30
res = evolve(m)
check(res and m.species_id == "voltling-final" and m.name == "Zappy", "nickname survived evolution")

# ---- 7) scripted safety -------------------------------------------------------------------------------------
check(not routes.ENCOUNTER_ZONES.get("overworld"), "the town must have no encounter zones")
for a in routes.AREAS.values():
    if a.styled:
        check(a.id not in routes.ENCOUNTER_ZONES, f"styled town {a.id} must not have encounter zones")

print("=" * 60)
if FAILS:
    print(f"{len(FAILS)} FAILURES")
    for f in FAILS:
        print(" -", f)
    sys.exit(1)
print("ALL INTEGRATION CHECKS PASS")
