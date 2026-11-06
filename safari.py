"""The Vespera Safari Reserve: FireRed's Safari Zone, scaled down (200 credits, 20 Safari Modules,
400 steps).  Inside the reserve you do not battle: every encounter opens a safari battle where the
only options are BALL / BAIT / ROCK / RUN, and the wild Scimon may flee after every action.

The math below is FireRed's, taken verbatim from the pokefirered decomp and only re-seeded from the
game's own 0-200 catch_rate scale:
  - battle_main.c HandleAction_ThrowBait / HandleAction_ThrowRock / HandleAction_WatchesCarefully
    (the bait/rock counters and the catch-factor swings, the decay while watching),
  - battle_script_commands.c Cmd_handleballthrow (the Safari Ball catch roll),
  - battle_ai_script_commands.c Cmd_if_random_safari_flee (the escape roll after every action).

The pure helpers here are headless (no pygame): battle.py drives them from SafariBattleScene and
overworld.py drives the step budget from _on_step."""
import math
import random
from dataclasses import dataclass

from settings import SAFARI_BALLS, SAFARI_COST, SAFARI_FLEE_BASE, SAFARI_STEPS

# --------------------------------------------------------------------------- session


def enter(st):
    """Open a session on the game state (the warden has already charged the fee)."""
    st.safari = {"balls": SAFARI_BALLS, "steps": SAFARI_STEPS}


def end(st):
    """Close the session (the gate, or the PA escort): leftover modules are handed back."""
    st.safari = None


def on_step(st):
    """One overworld step inside the reserve.  Returns a PA line to toast, or "time_up" when the
    budget ran out (the caller escorts the player to the gate), else None."""
    if not st.safari:
        return None
    s = st.safari
    s["steps"] = max(0, s["steps"] - 1)
    left = s["steps"]
    if left == SAFARI_STEPS // 2:
        return "PA: Half of your visit is over. Please explore with care."
    if left == 100:
        return "PA: One hundred steps remaining. Please start heading back."
    if left == 10:
        return "PA: Ten steps remaining. Please come to the gate at once."
    if left <= 0:
        return "time_up"
    if s["balls"] == 1:
        return "PA: Attention! You just used your last Safari Module!"
    return None


# --------------------------------------------------------------------------- species factors
# FireRed stores a per-species safari flee rate (25-125 for the Kanto reserve); Scimon species only
# carry catch_rate (0-200), so the escape rate is derived from it: commons stay, skittish rares go.

def _frlg_catch_rate(sp):
    """Scimon's 0-200 catch_rate rescaled to FireRed's 0-255 ball-catch-rate scale."""
    return sp.catch_rate * 255 // 200


def _frlg_flee_rate(sp):
    """A derived 0-255 safari flee rate: the rarer the species, the jumpier (SAFARI_FLEE_BASE sets
    how fast skittishness rises; 4 lands the whole dex inside FireRed's observed 25-125 band)."""
    return max(0, (200 - sp.catch_rate) * SAFARI_FLEE_BASE // 8)


def catch_factor(sp):
    """battle_main.c:2284 -- catchFactor = catchRate * 100 / 1275 (never below 1)."""
    return max(1, _frlg_catch_rate(sp) * 100 // 1275)


def escape_factor(sp):
    """battle_main.c:2285-2287 -- escapeFactor = fleeRate * 100 / 1275, minimum 2."""
    f = _frlg_flee_rate(sp) * 100 // 1275
    return 2 if f <= 1 else f


# --------------------------------------------------------------------------- the field state


@dataclass
class SafariField:
    """One safari encounter's live state (FireRed's gBattleStruct safari fields)."""
    catch_factor: int
    escape_factor: int
    bait_counter: int = 0
    rock_counter: int = 0

    @classmethod
    def for_species(cls, sp):
        return cls(catch_factor=catch_factor(sp), escape_factor=escape_factor(sp))

    def reset_factor(self, sp):                       # the rock wears off: back to the species' base
        self.catch_factor = catch_factor(sp)


# --------------------------------------------------------------------------- actions


def throw_bait(f):
    """battle_main.c:4380-4395: the mon eats for 2-6 turns (cap 6), rocks stop working, and the
    catch factor halves with a floor of 3."""
    f.bait_counter = min(6, f.bait_counter + random.randrange(5) + 2)
    f.rock_counter = 0
    f.catch_factor >>= 1
    if f.catch_factor <= 2:
        f.catch_factor = 3


def throw_rock(f):
    """battle_main.c:4396-4411: the mon is angry for 2-6 turns (cap 6), bait is wasted, and the
    catch factor doubles with a cap of 20."""
    f.rock_counter = min(6, f.rock_counter + random.randrange(5) + 2)
    f.bait_counter = 0
    f.catch_factor <<= 1
    if f.catch_factor > 20:
        f.catch_factor = 20


def watch(f, sp):
    """battle_main.c:4333-4368 -- the mon's own action after every player action: the rock/bait
    counters tick down and it reacts.  Returns the reaction: watching | eating | angry."""
    if f.rock_counter:
        f.rock_counter -= 1
        if f.rock_counter == 0:
            f.reset_factor(sp)
            return "watching"
        return "angry"
    if f.bait_counter:
        f.bait_counter -= 1
        return "watching" if f.bait_counter == 0 else "eating"
    return "watching"


def roll_flee(f):
    """battle_ai_script_commands.c Cmd_if_random_safari_flee: the escape roll after every player
    action.  Angry mons flee twice as hard (cap 20), eating mons barely at all (floor 1); the final
    chance is factor * 5 percent."""
    if f.rock_counter:
        flee = min(20, f.escape_factor * 2)
    elif f.bait_counter:
        flee = max(1, f.escape_factor // 4)
    else:
        flee = f.escape_factor
    return random.randrange(100) < flee * 5


def roll_catch(f, mon):
    """battle_script_commands.c Cmd_handleballthrow with the Safari Ball (bonus 15), verbatim: the
    odds come from the doubled catch factor at full HP, then the four-shake test decides."""
    catch_rate = f.catch_factor * 1275 // 100
    odds = (catch_rate * 15 // 10) * (mon.max_hp * 3 - mon.hp * 2) // (3 * mon.max_hp)
    if odds > 254:
        return True, 3
    odds = math.isqrt(math.isqrt(16711680 // odds))
    odds = 1048560 // odds
    shakes = 0
    while shakes < 3 and random.randrange(65536) < odds:
        shakes += 1
    return shakes == 3, shakes
