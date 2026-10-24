"""SCI-MON static data: types, techniques, species, items, shop prices.

Merged from Version 34's lib/game/data.ts (the complete catalogue: held items, key items,
item categories, rarity) and scimon_py's data.py (sprite file names)."""
from dataclasses import dataclass, field
from typing import Optional

from settings import hexc

# --------------------------------------------------------------------------- types
TYPE_COLORS = {
    "Thermal": "#e0592f", "Hydro": "#3d84c6", "Botanic": "#5aa63f", "Geologic": "#a98150",
    "Atmospheric": "#8fb8d6", "Electric": "#e8c33a", "Cryo": "#7fd0e0", "Metallic": "#9aa4ad",
    "Chemical": "#8e5bb0", "Quantum": "#5b5bd6", "Plasma": "#d6478f", "Radiant": "#f0d76a",
    "Shadow": "#4a4560", "Bio": "#57b06f", "Mechanical": "#8a8f98", "Nano": "#9b6bd6",
    "Cosmic": "#3a3f7a", "Digital": "#2fbfae",
}


def type_rgb(t):
    return hexc(TYPE_COLORS[t])


STRONG = {
    "Thermal": ["Botanic", "Metallic", "Cryo", "Nano", "Bio"],
    "Hydro": ["Thermal", "Geologic", "Plasma"],
    "Botanic": ["Hydro", "Geologic"],
    "Geologic": ["Thermal", "Electric", "Metallic", "Chemical"],
    "Atmospheric": ["Botanic", "Bio"],
    "Electric": ["Hydro", "Atmospheric", "Mechanical", "Metallic"],
    "Cryo": ["Hydro", "Botanic", "Atmospheric"],
    "Metallic": ["Cryo", "Geologic"],
    "Chemical": ["Metallic", "Bio"],
    "Quantum": ["Cosmic", "Digital"],
    "Plasma": ["Metallic", "Atmospheric", "Nano"],
    "Radiant": ["Shadow", "Bio"],
    "Shadow": ["Radiant", "Quantum", "Digital"],
    "Bio": ["Chemical", "Hydro"],
    "Mechanical": ["Geologic"],
    "Nano": ["Mechanical", "Metallic", "Bio"],
    "Cosmic": ["Quantum", "Radiant"],
    "Digital": ["Digital", "Nano", "Electric"],
}

WEAK = {
    "Thermal": ["Hydro", "Thermal", "Geologic"],
    "Hydro": ["Hydro", "Botanic", "Electric"],
    "Botanic": ["Thermal", "Botanic", "Metallic", "Atmospheric"],
    "Geologic": ["Botanic"],
    "Atmospheric": ["Electric"],
    "Electric": ["Geologic", "Electric"],
    "Cryo": ["Thermal", "Cryo", "Metallic"],
    "Metallic": ["Thermal", "Electric", "Chemical"],
    "Chemical": ["Chemical"],
    "Nano": ["Digital"],
    "Mechanical": ["Nano", "Metallic"],
    "Digital": ["Shadow"],
    "Bio": ["Thermal", "Radiant", "Atmospheric"],
    "Radiant": ["Shadow"],
}


def effectiveness(attack, defenders):
    mult = 1.0
    for d in defenders:
        if d in STRONG.get(attack, ()):
            mult *= 1.5
        elif d in WEAK.get(attack, ()):
            mult *= 0.6
    return mult


# --------------------------------------------------------------------------- status
# status id -> (abbr, colour, note)
STATUS_INFO = {
    "Overheated": ("OVH", "#e0592f", "Power up, integrity decays"),
    "Corroded": ("COR", "#8e5bb0", "Defense decays"),
    "Glitched": ("GLI", "#2fbfae", "Techniques may fail"),
    "Nanite-Infected": ("NAN", "#9b6bd6", "Stability decays"),
    "Deoxygenated": ("DOX", "#3d84c6", "Systems weakened"),
    "Electrified": ("ELC", "#e8c33a", "Movement disrupted"),
}


# --------------------------------------------------------------------------- techniques
@dataclass
class Technique:
    id: str
    name: str
    type: str
    category: str            # physical | special | status
    power: int
    accuracy: int
    desc: str = ""
    status: Optional[str] = None
    status_chance: float = 0.0
    drain: float = 0.0       # fraction of damage healed to the user
    buff_power: float = 0.0  # status move: raise the user's Power stage
    signature: bool = False


TECHNIQUES = {}


def _t(*a, **k):
    t = Technique(*a, **k)
    TECHNIQUES[t.id] = t


_t("sysram", "System Ram", "Mechanical", "physical", 30, 100, "A blunt chassis-first collision.")
_t("staticjab", "Static Jab", "Electric", "physical", 30, 100, "A quick charged strike.")
_t("leafcut", "Leaf Cutter", "Botanic", "physical", 35, 100, "Razor solar-panel edges slice the target.")
_t("biodrain", "Bio Drain", "Bio", "special", 40, 100, "Siphons energy, restoring the user.", drain=0.5)
_t("sporecloud", "Spore Cloud", "Botanic", "status", 0, 85, "Releases spores that starve the target's systems.",
   status="Deoxygenated", status_chance=1)
_t("photosurge", "Photosynthetic Surge", "Botanic", "special", 55, 95, "Converts light into a focused energy blast.")
_t("verdant", "Verdant Overload", "Bio", "special", 70, 95, "Florabot's signature: an overwhelming growth surge.",
   signature=True)
_t("embervent", "Ember Vent", "Thermal", "special", 35, 100, "Vents superheated exhaust.")
_t("thermalburst", "Thermal Burst", "Thermal", "special", 60, 95, "A controlled thermal discharge.",
   status="Overheated", status_chance=0.2)
_t("pistonpunch", "Piston Punch", "Mechanical", "physical", 40, 100, "A hydraulic-driven strike.")
_t("overclock", "Overclock", "Mechanical", "status", 0, 100, "Pushes the reactor to raise Power.", buff_power=0.3)
_t("magmasurge", "Magma Surge", "Thermal", "special", 70, 95, "Pyrodrive's signature: a molten eruption.",
   signature=True)
_t("waterjet", "Water Jet", "Hydro", "special", 35, 100, "A pressurized burst of coolant.")
_t("pressurewave", "Pressure Wave", "Hydro", "special", 55, 95, "A compressed shockwave of water.")
_t("dataspike", "Data Spike", "Digital", "special", 40, 100, "Injects corrupt packets.")
_t("glitchpulse", "Glitch Pulse", "Digital", "status", 0, 90, "Destabilizes the target's logic core.",
   status="Glitched", status_chance=1)
_t("overflow", "Overflow", "Digital", "special", 70, 95, "Aquabit's signature: a cascading buffer overflow.",
   signature=True)
_t("arcdis", "Arc Discharge", "Electric", "special", 45, 95, "Releases a branching arc of current.",
   status="Electrified", status_chance=0.2)
_t("magshock", "Magnetic Shock", "Electric", "special", 35, 100, "A pulse of magnetic force.")
_t("rocktoss", "Rock Toss", "Geologic", "physical", 40, 95, "Hurls hardened mineral plating.")
_t("naniteswarm", "Nanite Swarm", "Nano", "special", 40, 100, "Deploys microscopic machines that infest the target.",
   status="Nanite-Infected", status_chance=0.25)
# Disc-only art (never appears in a learnset): each gym leader's secret technique, taught by their move disc.
_t("verdantstorm", "Verdant Storm", "Botanic", "special", 75, 90,
   "The Green Gym's secret art: a storm of razor leaves and choking pollen.",
   status="Deoxygenated", status_chance=0.2)


# --------------------------------------------------------------------------- species
@dataclass
class Species:
    id: str
    dex: int
    name: str
    classification: str
    types: list
    base: tuple              # hp, power, defense, sp_power, sp_defense, speed, stability
    catch_rate: int
    xp_yield: int
    front: str
    back: Optional[str]
    learnset: list           # [(level, technique id)]
    ability: str
    desc: str
    rarity: str

    @property
    def b_hp(self): return self.base[0]
    @property
    def b_power(self): return self.base[1]
    @property
    def b_def(self): return self.base[2]
    @property
    def b_sp(self): return self.base[3]
    @property
    def b_spdef(self): return self.base[4]
    @property
    def b_speed(self): return self.base[5]
    @property
    def b_stab(self): return self.base[6]


SPECIES = {}


def _s(*a):
    s = Species(*a)
    SPECIES[s.id] = s


_s("florabot", 1, "Florabot", "Ecological Drone", ["Botanic", "Bio"], (50, 42, 52, 50, 55, 40, 55), 45, 64,
   "florabot-front.png", "florabot-back.png",
   [(1, "sysram"), (1, "leafcut"), (6, "biodrain"), (10, "sporecloud"), (14, "photosurge"), (20, "verdant")],
   "Photosynthesis", "An ecological maintenance robot. Curious and friendly, it excels at defense and disruption.", "rare")
_s("pyrodrive", 2, "Pyrodrive", "Thermal Engine", ["Thermal", "Mechanical"], (48, 60, 45, 52, 40, 50, 45), 45, 64,
   "pyrodrive-front.png", "pyrodrive-back.png",
   [(1, "sysram"), (1, "embervent"), (6, "pistonpunch"), (10, "thermalburst"), (14, "overclock"), (20, "magmasurge")],
   "Overdrive", "A high-temperature engineering machine. Energetic and aggressive, it hits extremely hard.", "rare")
_s("aquabit", 3, "Aquabit", "Research Drone", ["Hydro", "Digital"], (44, 40, 42, 58, 46, 62, 48), 45, 64,
   "aquabit-front.png", "aquabit-back.png",
   [(1, "sysram"), (1, "waterjet"), (6, "dataspike"), (10, "pressurewave"), (14, "glitchpulse"), (20, "overflow")],
   "Coolant Flow", "A playful aquatic research drone. Fast and clever, it overwhelms foes with special techniques.", "rare")
_s("sporelet", 11, "Sporelet", "Fungal Nanobot", ["Botanic"], (40, 34, 40, 38, 40, 30, 45), 160, 40,
   "sporelet-front.png", None, [(1, "leafcut"), (4, "sporecloud"), (8, "biodrain")],
   "Spore Vent", "A tiny fungus-inspired nanobot that drifts through meadows dispersing spores.", "common")
_s("cindermite", 12, "Cindermite", "Ember Drone", ["Thermal"], (36, 45, 32, 42, 30, 52, 38), 150, 44,
   "cindermite-front.png", None, [(1, "embervent"), (5, "sysram"), (9, "thermalburst")],
   "Ember Body", "A skittish ember drone whose chassis glows with residual heat.", "common")
_s("dewbit", 13, "Dewbit", "Droplet Drone", ["Hydro"], (42, 32, 40, 44, 42, 40, 46), 160, 42,
   "dewbit-front.png", None, [(1, "waterjet"), (5, "sysram"), (9, "pressurewave")],
   "Condensation", "A gentle droplet-shaped drone that patrols streams and puddles.", "common")
_s("sparkit", 14, "Sparkit", "Cell Bot", ["Electric"], (34, 36, 34, 46, 34, 55, 40), 150, 44,
   "sparkit-front.png", None, [(1, "staticjab"), (4, "magshock"), (8, "arcdis")],
   "Static Charge", "A restless battery-cell bot that crackles with stored current.", "uncommon")
_s("pebblon", 15, "Pebblon", "Rock Crawler", ["Geologic"], (52, 46, 58, 30, 40, 22, 60), 140, 50,
   "pebblon-front.png", None, [(1, "rocktoss"), (1, "sysram"), (8, "pistonpunch")],
   "Sturdy Plating", "A slow, heavily-armored crawler that grinds minerals from the earth.", "uncommon")
_s("nanolyte", 16, "Nanolyte", "Microbot Swarm", ["Nano", "Digital"], (38, 40, 36, 48, 40, 48, 30), 120, 52,
   "nanolyte-front.png", None, [(1, "naniteswarm"), (1, "dataspike"), (8, "glitchpulse")],
   "Swarm Logic", "A rare cluster of nanobots bound by an unstable shared consciousness.", "rare")

STARTER_IDS = ["florabot", "pyrodrive", "aquabit"]
SPECIES_COUNT = len(SPECIES)

# (species, weight, min level, max level)
ROUTE_ENCOUNTERS = [
    ("sporelet", 30, 2, 5), ("dewbit", 25, 2, 5), ("cindermite", 20, 3, 5),
    ("sparkit", 13, 3, 6), ("pebblon", 8, 4, 6), ("nanolyte", 4, 4, 6),
]


# --------------------------------------------------------------------------- items
@dataclass
class Module:
    id: str
    name: str
    short: str
    mult: float
    match_type: Optional[str]
    color: str


MODULES = {
    "standard": Module("standard", "Standard Module", "STD", 1.0, None, "#d15a34"),
    "cryo": Module("cryo", "Cryo Module", "CRY", 1.7, "Thermal", "#7fd0e0"),
    "magnetic": Module("magnetic", "Magnetic Module", "MAG", 1.7, "Metallic", "#9aa4ad"),
    "bio": Module("bio", "Bio Capsule", "BIO", 1.7, "Bio", "#57b06f"),
}


@dataclass
class HealItem:
    id: str
    name: str
    short: str
    heal: int = 0
    restore_stability: bool = False
    cure: bool = False
    color: str = "#e05a72"


ITEMS = {
    "repaircell": HealItem("repaircell", "Repair Cell", "RC", heal=25),
    "nanorepair": HealItem("nanorepair", "Nano Repair", "NR", heal=60),
    "stabilizer": HealItem("stabilizer", "Stabilizer", "ST", restore_stability=True, cure=True, color="#5b5bd6"),
}

STARTING_CREDITS = 1500

SHOP_PRICES = {
    "repaircell": 200, "nanorepair": 600, "stabilizer": 300,
    "standard": 200, "cryo": 600, "magnetic": 600, "bio": 600,
}


def sell_price(item_id):
    """Stores buy back at half the catalogue price."""
    return SHOP_PRICES.get(item_id, 100) // 2


# --------------------------------------------------------------------------- unified catalogue
ITEM_CATEGORIES = [("consumable", "Supplies"), ("module", "Modules"), ("held", "Equipment"), ("disc", "Discs"),
                   ("key", "Key Items")]


@dataclass
class ItemDef:
    id: str
    name: str
    short: str
    desc: str
    color: str
    category: str                      # consumable | module | held | key
    permanent: bool = False            # key items can't be sold or discarded
    heal: int = 0
    cure: bool = False
    restore_stability: bool = False
    revive: float = 0.0
    power_boost: Optional[tuple] = None   # (type, multiplier) for the holder's techniques
    def_boost: float = 0.0                # multiplier on the holder's defense
    move: Optional[str] = None            # move discs: the technique the disc teaches
    compat_types: tuple = ()              # move discs: Sci-Mon types that can learn it


_DESC = {
    "repaircell": "A basic patch kit. Restores 25 HP to a single Sci-Mon.",
    "nanorepair": "Dense repair swarm. Restores 60 HP to a single Sci-Mon.",
    "stabilizer": "Resets a Sci-Mon's Stability and clears any status fault.",
    "standard": "General-purpose containment module. No type affinity.",
    "cryo": "Containment module tuned for Thermal-class Sci-Mons.",
    "magnetic": "Containment module tuned for Metallic-class Sci-Mons.",
    "bio": "Containment capsule tuned for Bio-class Sci-Mons.",
}

CATALOG = {}
for _i in ITEMS.values():
    CATALOG[_i.id] = ItemDef(_i.id, _i.name, _i.short, _DESC.get(_i.id, "A field supply item."), _i.color,
                             "consumable", heal=_i.heal, cure=_i.cure, restore_stability=_i.restore_stability)
for _m in MODULES.values():
    CATALOG[_m.id] = ItemDef(_m.id, _m.name, _m.short, _DESC.get(_m.id, "A containment module."), _m.color, "module")


def _held(id, name, short, color, desc, **kw):
    CATALOG[id] = ItemDef(id, name, short, desc, color, "held", **kw)


def _disc(id, name, short, color, move, compat_types):
    """A gym leader's move disc: teaches its technique once to a compatible Sci-Mon (state.teach_move)."""
    t = TECHNIQUES[move]
    types = " or ".join(compat_types)
    CATALOG[id] = ItemDef(id, name, short, f"A move disc from a gym leader. Teaches {t.name} to a compatible "
                                           f"Sci-Mon ({types}). This move can't be learned any other way.",
                          color, "disc", permanent=True, move=move, compat_types=tuple(compat_types))


_disc("verdantdisc", "Verdant Disc", "VS", "#5aa63f", "verdantstorm", ("Botanic", "Bio"))


_held("thermalcore", "Thermal Core", "TC", "#e0592f",
      "An item to be held. Raises the power of the holder's Thermal techniques by 20%.", power_boost=("Thermal", 1.2))
_held("hydrocell", "Hydro Cell", "HC", "#3d84c6",
      "An item to be held. Raises the power of the holder's Hydro techniques by 20%.", power_boost=("Hydro", 1.2))
_held("biotrellis", "Bio Trellis", "BT", "#5aa63f",
      "An item to be held. Raises the power of the holder's Botanic techniques by 20%.", power_boost=("Botanic", 1.2))
_held("plating", "Reinforced Plating", "RP", "#9aa4ad",
      "An item to be held. Raises the holder's Defense and Sp. Defense by 15%.", def_boost=1.15)

CATALOG["scanner"] = ItemDef("scanner", "Field Scanner", "FS",
                             "Standard issue for Astrion researchers. Logs every Sci-Mon you encounter.",
                             "#2fbfae", "key", permanent=True)
CATALOG["townpass"] = ItemDef("townpass", "Riven Town Pass", "TP",
                              "Grants a researcher free access to Riven Town's civic facilities.",
                              "#e8c33a", "key", permanent=True)
CATALOG["epipass"] = ItemDef("epipass", "Epidimy Town Pass", "EP",
                             "Grants a researcher free access to Epidimy's civic facilities.",
                             "#57b06f", "key", permanent=True)

# key items that live in the Pack's PASSES folder, sorted ahead of the other key items
PASSES = ("townpass", "epipass")

# --------------------------------------------------------------------------- the Corrupt Bandits (story)
# Items the villain arc hands out.  The Shadow Module is never obtainable - it appears in cutscenes only.
CATALOG["shadowmodule"] = ItemDef("shadowmodule", "Shadow Module", "SH",
                                  "A jet-black containment module, factory-stamped with a scratched-out logo. Its "
                                  "firmware hums with something corrupted.", "#26262e", "key", permanent=True)
CATALOG["banditticket"] = ItemDef("banditticket", "Bandit Repair Ticket", "BT",
                                  "A repair ticket stamped with the Cush franchise logo - found on a Corrupt Bandit. "
                                  "Why would a Bandit carry one of these?", "#8a8f98", "key", permanent=True)
CATALOG["mastersticket"] = ItemDef("mastersticket", "Mastermind's Ticket", "MT",
                                   "Cush's own franchise ticket, void-stamped the moment he fled. A memento of the "
                                   "Corrupt Bandits' fall.", "#d1552f", "key", permanent=True)

# the Corrupt Bandits' teams (id -> [(species, level), ...]) and Kael's post-reveal rematch team
BANDIT_TEAMS = {
    "act1": [("cindermite", 3), ("dewbit", 4)],
    "act2": [("sparkit", 6), ("pebblon", 7)],
    "boss": [("nanolyte", 9), ("florabot", 10)],
}
KAEL_RETEAM = {"florabot": ("aquabit", 8), "pyrodrive": ("florabot", 8), "aquabit": ("pyrodrive", 8)}
KAEL_RETEAM2 = ("sporelet", 9)


def item_def(item_id):
    return CATALOG.get(item_id)


def item_name(item_id):
    d = CATALOG.get(item_id)
    return d.name if d else item_id
