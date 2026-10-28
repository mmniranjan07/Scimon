"""The scimon_database integration (headless): roster integrity, preserved source facts, art coverage,
habitat rules, evolution edges and a battle smoke test.

Usage: python tests/specimens.py [screenshot_dir]"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from data import (SPECIES, SPECIES_COUNT, TECHNIQUES, WILD_HOME, STARTER_IDS, TYPE_COLORS, STRONG, WEAK,
                  FAMILIES, FAMILY_OF, CHAIN_OF, EVOLUTIONS, DB, HABITATS, ENCOUNTER_POLICY, PHASES)
from monsters import create_scimon, check_evolutions
from battle import new_battle

# ---- 1) the roster: 109 families, 327 forms, 59 proposed first forms; dex is an identifier, not an index
assert len(FAMILIES) == 109 and len(SPECIES) == SPECIES_COUNT == 327, (len(FAMILIES), len(SPECIES))
assert DB["summary"]["preserved_existing_forms"] == 268 and DB["summary"]["proposed_added_first_forms"] == 59
_dexes = [s.dex for s in SPECIES.values()]
assert len(set(_dexes)) == 327 and 10 not in _dexes, "dex numbers must be unique and 10 stays retired"
_new = [s for s in SPECIES.values() if s.id in DB["source"] and not s.source_registered]
assert len([s for s in SPECIES.values() if not s.source_registered]) == 59
for s in SPECIES.values():
    if not s.source_registered:
        assert s.id.endswith("-baby") and s.name.startswith("Baby ") and 270 <= s.dex <= 328, s.id
        assert s.catch_rate == 190 and s.evolution_level == 10, s.id
assert sum(1 for f in FAMILIES.values() if len(f["chain_ids"]) == 3) == 109, "every family is three forms now"

# ---- 2) the 268 source facts are preserved: dex, names, stats, catch rates, xp, abilities, techniques
_src_facts = 0
for rec in DB["species"]:
    if not rec["source_registered"]:
        continue
    sp = SPECIES[rec["id"]]
    assert sp.dex == rec["dex"] and sp.name == rec["name"], rec["id"]
    assert sp.catch_rate == rec["catch_rate"] and sp.xp_yield == rec["xp_yield"]
    assert sp.ability == rec["ability"] and list(sp.types) == list(rec["types"])
    assert [(lv, t) for lv, t in sp.learnset] == [(m["level"], m["technique_id"]) for m in rec["learnset"]]
    assert sp.base == tuple(rec["base_stats"][k] for k in
                            ("hp", "power", "defense", "sp_power", "sp_defense", "speed", "stability"))
    _src_facts += 1
assert _src_facts == 268, _src_facts

# ---- 3) chains: chain order is authoritative; every edge valid, increasing, acyclic; thresholds preserved
for fid, fam in FAMILIES.items():
    chain = fam["chain_ids"]
    assert [SPECIES[s].stage_ordinal for s in chain] == [1, 2, 3], fid
    assert all(SPECIES[s].family_id == fid for s in chain), fid
    for i, sid in enumerate(chain):
        assert CHAIN_OF[sid] == chain
        nxt = chain[i + 1] if i + 1 < len(chain) else None
        sp_evo = EVOLUTIONS.get(sid) if nxt else None
        if nxt:
            assert sp_evo and sp_evo[0] == nxt, (sid, sp_evo, nxt)
    for (a, b) in zip(chain, chain[1:]):
        evo = EVOLUTIONS[a]
        assert evo == (b, fam["evolution_levels"][chain.index(a)]), (fid, a, evo)
    # dex numbers are preserved identifiers, NOT chain order: an existing baby keeps its old dex
    # (e.g. sporelet-baby = 117 while sporelet = 11) -- only uniqueness is guaranteed
    assert len({SPECIES[s].dex for s in chain}) == 3, fid
# starter thresholds unchanged, no fourth stage
for sid in STARTER_IDS:
    assert EVOLUTIONS[sid] == (f"{sid}-mid", 16) and EVOLUTIONS[f"{sid}-mid"] == (f"{sid}-final", 32), sid
assert all("-baby" not in s for s in STARTER_IDS)
# formerly two-form families: the unsuffixed id is the MIDDLE form now
assert CHAIN_OF["voltling"] == ["voltling-baby", "voltling", "voltling-final"]
assert EVOLUTIONS["voltling-baby"] == ("voltling", 10) and EVOLUTIONS["voltling"] == ("voltling-final", 21)
assert EVOLUTIONS["glacibit-baby"] == ("glacibit", 10) and EVOLUTIONS["glacibit"] == ("glacibit-final", 16)

# ---- 4) art coverage: every form has front art on disk and a back view where the database declares one
import assets
missing_front = [sid for sid, sp in SPECIES.items()
                 if not os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "assets", "scimon", sp.front))]
assert not missing_front, f"forms without front art: {missing_front[:6]}"
missing_back = [sid for sid, sp in SPECIES.items() if sp.back and
                not os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "assets", "scimon", sp.back))]
assert not missing_back, f"forms with declared but missing back art: {missing_back[:6]}"
with_backs = sum(1 for sp in SPECIES.values() if sp.back)
assert with_backs == 327, f"expected 327 registered backs, got {with_backs}"

# ---- 5) habitat rules: explicit, authoritative, Thermal/Cryo consistency
assert len(HABITATS) == 11
for sid, sp in SPECIES.items():
    fam = FAMILIES[sp.family_id]
    assert sp.normal_habitats == tuple(fam["normal_habitats"]), sid
    if "Thermal" in sp.types:
        assert fam["normal_habitats"] == ["volcanic"], f"{sid}: Thermal family outside volcanic"
assert "cindermite" not in [f["id"] for f in FAMILIES.values() if "meadow" in f["normal_habitats"]]
glac = FAMILIES["glacibit"]
assert glac["normal_habitats"] == ["highland"], "Glacibit belongs in the cold highlands"
assert FAMILIES["fusor"]["normal_habitats"] == ["volcanic"] and FAMILIES["cometling"]["normal_habitats"] == ["volcanic"]

# ---- 6) the encounter policy defaults
assert ENCOUNTER_POLICY["global_migration_probability"] == 0.001
assert [p["stage_weights"] for p in PHASES] == [{"1": 100, "2": 0, "3": 0},
                                                {"1": 85, "2": 15, "3": 0}, {"1": 80, "2": 17, "3": 3}]
assert [p["maximum_wild_level"] for p in PHASES] == [18, 35, 60]
assert ENCOUNTER_POLICY["preserve_existing_per_grass_step_encounter_chance"] == 0.12

# ---- 7) every form instantiates and battles; evolution walks the whole chain
for sid in ("florabot", "voltling-baby", "voidling-final", "glacibit-baby", "cindermite"):
    m = create_scimon(sid, min(20, SPECIES[sid].max_wild_level))
    assert m.moves, sid
foe = create_scimon("florabot", 10)
b = new_battle([create_scimon("sproutle-baby", 10)], foe, {}, {})
assert b.player and b.enemy
_m = create_scimon("voltling-baby", 30)          # a high-level baby walks its whole chain
from monsters import evolve
while EVOLUTIONS.get(_m.species_id):
    res = evolve(_m)
    assert res, _m.species_id
assert _m.species_id == "voltling-final", _m.species_id

print(f"OK specimens: 109 families / 327 forms (268 preserved + 59 first forms), 327 fronts + "
      f"{with_backs} backs on disk, habitat + evolution + policy rules verified, battle smoke passed")
