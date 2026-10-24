"""The Corrupt Bandits - the villain arc.

Cush, the friendly repair-franchise owner, is the secret mastermind: his nooks launder stolen Sci-Mon
through their own databases, and his bays build the black "Snatcher" modules that beat the professor's
Scanner.  One pair of black-clad thugs ambushes the player after each city:

  Act 1  Route 1, after the rival:  losing gets you blacked out, but the professor's new Scanner burns the
         Snatcher out - the theft fails either way.
  Act 2  Epidimy high street:      losing lets them take a RANDOM party Sci-Mon.  It sits in a shadow-box of
         Cush's own Sci-Database until the player recovers it from any nook terminal - the arc's quiet clue.
  Act 3  The Epidimy nook, after the Green Gym stamp: Cush is caught ordering the final Snatch.  His boss
         battle is re-offered on every re-entry until beaten; then he flees by repair-drone and Kael - his
         son - inherits the nooks, gives up his own dream, and rematches the player from time to time.

This module is pure data (no pygame): overworld.py drives the ambushes, scenes.py plays the cutscenes.
"""
from data import BANDIT_TEAMS, KAEL_RETEAM, KAEL_RETEAM2

RIVAL_NAME = "Kael"

# --------------------------------------------------------------------------- ambushes (one pair per city)
AMBUSHES = [
    dict(
        id="bandit1",
        area="route1",
        # the whole road width west of the Riven gate: leaving town northward cannot miss it
        triggers=[(x, 19) for x in range(9, 18)] + [(x, 20) for x in range(9, 18)],
        spots=[(11, 19), (12, 20)],
        leader="Bandit Rex",
        team=BANDIT_TEAMS["act1"],
        intro=[
            "???: Well, well. A baby researcher, all alone on Route 1.",
            "Corrupt Bandit: We're the CORRUPT BANDITS - and that Scanner of yours is coming with us.",
            "Corrupt Bandit: Hand over the Sci-Mon, or we crack its collar and take it!",
        ],
        win=[
            "Corrupt Bandit: Gah! Fine - we'll do this the hard way.",
            "The Bandit hurls a jet-black module - a Snatcher - at your Sci-Mon!",
            "Your Field Scanner screams a counter-signal. The Snatcher sparks and melts!",
            "Corrupt Bandit: The Boss won't forget this, kid.",
            "The Bandits vanish into the treeline.",
        ],
        lose=[
            "Corrupt Bandit: Ha! Easy pickings.",
            "The Bandit hurls a Snatcher at your exhausted Sci-Mon -",
            "- but your Field Scanner screams a counter-signal. The professor's new firmware burns it out!",
            "Corrupt Bandit: Tch. The Boss said the professor was upgrading the scanners. Retreat!",
            "Everything goes dark as you stagger back to town...",
        ],
    ),
    dict(
        id="bandit2",
        area="epidimy",
        # the high street east of the south-road junction: heading for the gym cannot miss it
        triggers=[(9, 14), (11, 14), (12, 14), (13, 14), (9, 15), (10, 15), (11, 15), (12, 15), (13, 15)],
        spots=[(11, 14), (12, 15)],
        leader="Bandit Volt",
        team=BANDIT_TEAMS["act2"],
        intro=[
            "???: That's the one. Fresh from Riven Town - the Boss wants its signal.",
            "Corrupt Bandit: CORRUPT BANDITS! Your Sci-Mon, or your teeth.",
            "Corrupt Bandit: New town, same mistake - nobody walks our high street for free.",
        ],
        win=[
            "Corrupt Bandit: Impossible! The Boss tuned this Snatcher himself!",
            "The Snatcher's black casing cracks against your Scanner's counter-signal...",
            "Corrupt Bandit: Enjoy it while it lasts. The Boss finishes his buster soon.",
            "The Bandits retreat toward the cave, dragging their modules behind them.",
        ],
        lose=[
            "Corrupt Bandit: Ha! The Boss's buster works. Your little beeper is dead weight now.",
            "The Snatcher locks on - and drags one of your Sci-Mon into its black hold!",
            "Corrupt Bandit: The Boss sends his regards.",
            "Everything goes dark... but a tracker blip still pulses somewhere in town.",
        ],
    ),
]

# --------------------------------------------------------------------------- Act 3: the reveal (Epidimy nook)
REVEAL_BUILDING = "epi-center"          # the finish is tied to Epidimy
REVEAL_STAMP = "green"                  # ...and it waits for the Green Gym stamp

REVEAL_LINES = [
    "You step into the nook. The repair bay door at the back hangs wide open.",
    "Cush: ...send the fourth Snatcher to the terrace, and this time jam the scanner FIRST.",
    "Cush: Oh. {name}. You're early.",
    "Cush: You want to know what the back room is? It's the warehouse, kid. THE warehouse.",
    "Cush: Every stolen Sci-Mon in two towns sits in MY database, sorted by collar ID. Mine.",
    "Cush: Who do you think taught the Bandits to crack the professor's Scanner? Who repairs their modules?",
    "Cush: Corrupt Bandits? Kid, I AM the Corrupt Bandits. The apron was the mask.",
    "Cush: And now that you've stamped every gym in the highland... you know too much. Let's talk shop.",
]

BOSS_NAME = "Cush"
BOSS_TEAM = BANDIT_TEAMS["boss"]        # [(nanolyte, 9), (florabot, 10)] - the Grim Florabot is his ace

BOSS_WIN_LINES = [
    "Cush: ...heh. Overclocked by a kid with a hand-me-down Scanner.",
    "Cush: A franchise is never one store, champ. This circuit has nine more nooks.",
    "A repair drone crashes through the skylight and hauls Cush away!",
    "He drops something on the counter - his own franchise ticket, void-stamped.",
]

KAEL_ARRIVAL = [
    "A voice barks from the doorway - Kael, out of breath, his fists shaking.",
    f"{RIVAL_NAME}: CUSH! You... you're the one who took Sci-Mon? Dad... DAD?!",
    f"{RIVAL_NAME}: I wanted to be the greatest Researcher alive so you'd finally watch a battle of mine...",
    f"{RIVAL_NAME}: Fine. FINE. The nooks are mine now. I'll keep them clean - that's the dream now, I guess.",
    f"{RIVAL_NAME}: But don't you dare disappear on me, {{name}}: I still owe you a battle. And I collect debts.",
]

# Kael's standing rematch dialogue (the existing rematch system: ask / win / post lines)
KAEL_REMATCH_ASK = [
    f"{RIVAL_NAME}: There you are. The nooks are spotless, the books are honest -",
    f"{RIVAL_NAME}: - which means I have time to wipe that champion smile off your face. Battle me!",
]
KAEL_REMATCH_POST_WIN = [
    f"{RIVAL_NAME}: Tch. Good battle. The nooks will make me sharp - keep training, {{name}}.",
    f"{RIVAL_NAME}: I'll be here. Somebody has to answer for my dad.",
]
KAEL_REMATCH_POST_LOSE = [
    f"{RIVAL_NAME}: HA! See? The nooks agree with me. Same time next week, {{name}}!",
]

# Act 2 hint Cush drops while a snatched Sci-Mon is still missing
SNATCH_HINT = "Cush: Odd - box eight keeps syncing itself at night. Machines, am I right?"

# the Sci-Database recovery scene (any nook terminal, while st.snatched is set)
RECOVERY_LINES = [
    "The Sci-Database chimes - one storage box is flagged with a broken lock symbol...",
    "It's YOUR Sci-Mon, held in a shadow-box of the Cush franchise database!",
    "The collar link re-syncs. {mon} is recovered!",
]
