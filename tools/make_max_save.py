"""Build a ready-to-play save: six level-99 Scimons (the three starter finals plus three powerhouse
finals), perfect IVs, a full supply belt, a fat wallet and a completed Sci-Dex.  The story itself
stays untouched (no stamps, no beaten trainers, no arc flags) so everything still plays in order --
it is just steamrolled.  Run again any time to regenerate:

    python tools/make_max_save.py

Overwrites ~/.scimon/save.json (the game's real save slot)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import savegame
from data import SPECIES
from monsters import IV_MAX, IV_STATS, create_scimon
from state import GameState
from worldmap import PLAYER_START

TEAM = ("florabot-final", "pyrodrive-final", "aquabit-final",          # the three starter finals
        "joulebot-final", "vortexling-final", "quartzot-final")        # Dynamorilla, Cyclonaga, Piezoceros
LEVEL = 99
CREDITS = 100_000
COINS = 500

# every field module: F (Aerolift), the board/flare/burrow/climb all usable from the first step
FIELD_ABILITIES = ("aquaboard", "aerolift", "lumen", "excavator", "hydroclimb")

SUPPLIES = {                                                           # the belt, generously stocked
    "repaircell": 30, "nanorepair": 30, "stabilizer": 20, "chargecell": 20,
    "repel": 10, "superrepel": 10,
    "standard": 10, "cryo": 10, "magnetic": 10, "bio": 10,             # capture modules
    "abl_aquaboard": 1, "abl_aerolift": 1, "abl_lumen": 1, "abl_excavator": 1, "abl_hydroclimb": 1,
}


def build_state():
    st = GameState()
    st.name = "Robin"
    for sid in TEAM:
        mon = create_scimon(sid, LEVEL)
        mon.ivs = {s: IV_MAX for s in IV_STATS}                        # perfect talent
        mon.recalc_stats()
        mon.energy = mon.max_energy                                    # the reserves top off too
        st.party.append(mon)
    st.captured = set(SPECIES)                                         # the completed Sci-Dex
    st.seen = set(SPECIES)
    st.items = dict(SUPPLIES)
    st.abilities = set(FIELD_ABILITIES)                                # Aerolift + friends, all unlocked
    st.credits = CREDITS
    st.coins = COINS
    st.intro_done = True                                               # skip the wake / briefing / starter
    st.rival_species = "aquabit"
    st.location = {"area": "overworld", "tile": list(PLAYER_START), "facing": "down"}
    st.visited_areas.add("overworld")
    return st


def main():
    st = build_state()
    assert len(st.party) == 6 and all(m.level == LEVEL for m in st.party)
    ok = bool(savegame.save(st))
    print(("WROTE" if ok else "FAILED TO WRITE") + f" {savegame._FILE}")
    for m in st.party:
        print(f"  {m.name:12s} Lv{m.level}  {'/'.join(m.types):22s} {m.moves}")
    print(f"  credits {st.credits}, coins {st.coins}, dex {len(st.captured)}/{len(SPECIES)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
