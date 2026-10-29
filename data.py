"""SCI-MON static data: types, techniques, species, evolutions, habitats, items, shop prices.

The scimon_database.json package is the authoritative species catalog (109 families, 327 forms,
habitats, encounter policy); everything else (held items, key items, item categories, rarity,
the Corrupt Bandits) is merged from Version 34's lib/game/data.ts and scimon_py's data.py."""
import json
import os
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

# ---- the wider region's wild Scimons brought the full type chart with them: one full learnset pool per type ----
_t("cinderbite", "Cinder Bite", "Thermal", "physical", 45, 100, "Red-hot jaws clamp onto the target.",
   status="Overheated", status_chance=0.15)
_t("furnacevent", "Furnace Vent", "Thermal", "special", 65, 90, "A roaring blast from an overheated core.")
_t("heatsink", "Heat Sink", "Thermal", "status", 0, 100, "Absorbs ambient heat to push Power up.", buff_power=0.25)
_t("tidalslam", "Tidal Slam", "Hydro", "physical", 50, 95, "A wall of ballast water crashes down.")
_t("brineblast", "Brine Blast", "Hydro", "special", 45, 100, "Salted spray corrodes the target.",
   status="Deoxygenated", status_chance=0.2)
_t("riptide", "Riptide", "Hydro", "special", 60, 95, "A dragging undertow that pulls the target under.")
_t("thornvolley", "Thorn Volley", "Botanic", "physical", 45, 100, "Fires a spread of hardened thorns.")
_t("sapdrain", "Sap Drain", "Botanic", "special", 35, 100, "Saps nutrient fluid to repair the user.", drain=0.5)
_t("boulderbarge", "Boulder Barge", "Geologic", "physical", 55, 90, "A mass of compressed stone barrels forward.")
_t("quakestomp", "Quake Stomp", "Geologic", "physical", 65, 85, "A ground-shaking stomp from a heavy chassis.")
_t("shardguard", "Shard Guard", "Geologic", "status", 0, 100, "Raises mineral plating for a Power push.", buff_power=0.25)
_t("galecut", "Gale Cut", "Atmospheric", "physical", 45, 100, "Blade-thin wind shear lances out.")
_t("cyclone", "Cyclone", "Atmospheric", "special", 55, 95, "A tight vortex tears at the target's seams.")
_t("decompress", "Decompress", "Atmospheric", "status", 0, 90, "Drops the local pressure - systems starve.",
   status="Deoxygenated", status_chance=1)
_t("voltnet", "Volt Net", "Electric", "special", 50, 95, "A spreading mesh of live wire.",
   status="Electrified", status_chance=0.25)
_t("coilcrash", "Coil Crash", "Electric", "physical", 55, 95, "A magnetically accelerated body slam.")
_t("capacitance", "Capacitance", "Electric", "status", 0, 100, "Banks a charge to push Power up.", buff_power=0.25)
_t("frostbite", "Frostbite", "Cryo", "special", 45, 100, "Flash-freezes the target's joints.")
_t("permafrost", "Permafrost", "Cryo", "special", 60, 95, "A deep-cold wave that locks servos solid.")
_t("rimeedge", "Rime Edge", "Cryo", "physical", 50, 100, "A blade of hoarfrost, harder than steel.")
_t("alloybash", "Alloy Bash", "Metallic", "physical", 50, 100, "A hammer blow from layered alloy plating.")
_t("ferrofilament", "Ferro Filament", "Metallic", "special", 40, 100, "Wire filaments flay the target's coating.",
   status="Corroded", status_chance=0.2)
_t("platingcast", "Plating Cast", "Metallic", "status", 0, 100, "Casts fresh armour, stiffening every strike.", buff_power=0.2)
_t("acidburst", "Acid Burst", "Chemical", "special", 45, 100, "A jet of reactive solvent.",
   status="Corroded", status_chance=0.25)
_t("toxinspray", "Toxin Spray", "Chemical", "special", 55, 95, "An aerosol of corrosive catalysts.")
_t("catalyst", "Catalyst", "Chemical", "status", 0, 100, "Speeds every reaction - Power climbs.", buff_power=0.3)
_t("phaselance", "Phase Lance", "Quantum", "special", 50, 95, "A probability-focused energy lance.")
_t("entanglepulse", "Entangle Pulse", "Quantum", "status", 0, 85, "Tangles the target's states - logic wobbles.",
   status="Glitched", status_chance=0.75)
_t("superposition", "Superposition", "Quantum", "special", 65, 85, "Strikes from every state at once.")
_t("ionstorm", "Ion Storm", "Plasma", "special", 55, 95, "A supercharged ion front rolls over the target.",
   status="Electrified", status_chance=0.2)
_t("plasmacutter", "Plasma Cutter", "Plasma", "physical", 50, 100, "A contained arc blade slices out.")
_t("fusionflare", "Fusion Flare", "Plasma", "special", 70, 90, "A brief, contained fusion burn.")
_t("lumenburst", "Lumen Burst", "Radiant", "special", 50, 100, "A burst of clean white light.")
_t("prismbeam", "Prism Beam", "Radiant", "special", 60, 95, "One beam split into a barrage of spectra.")
_t("suncloak", "Sun Cloak", "Radiant", "status", 0, 100, "Bathes in pure light, raising Power.", buff_power=0.25)
_t("duskwake", "Dusk Wake", "Shadow", "special", 50, 100, "A cold ripple of lightless static.")
_t("voidpincer", "Void Pincer", "Shadow", "physical", 55, 95, "Claws of compressed darkness.")
_t("nightleech", "Night Leech", "Shadow", "special", 40, 100, "Drains integrity through the dark.", drain=0.5)
_t("myceliumweb", "Mycelium Web", "Bio", "status", 0, 90, "A web of living filaments chokes the target.",
   status="Deoxygenated", status_chance=0.75)
_t("splicetalon", "Splice Talon", "Bio", "physical", 50, 100, "Genespliced claws rake out.")
_t("cellburst", "Cell Burst", "Bio", "special", 55, 95, "Overcharges its own cells in a burst.")
_t("servoslam", "Servo Slam", "Mechanical", "physical", 55, 95, "Every actuator fires at once.")
_t("wreckingarm", "Wrecking Arm", "Mechanical", "physical", 65, 85, "A full-force hydraulic wrecking swing.")
_t("swarmbite", "Swarm Bite", "Nano", "physical", 40, 100, "A million tiny jaws in one bite.",
   status="Nanite-Infected", status_chance=0.2)
_t("disassembler", "Disassembler", "Nano", "special", 55, 95, "Takes the target apart, screw by screw.",
   status="Corroded", status_chance=0.2)
_t("packetstorm", "Packet Storm", "Digital", "special", 50, 100, "A flood of malformed packets.")
_t("firewallbreaker", "Firewall Breaker", "Digital", "physical", 45, 100, "A ram-charge through any defence.")
_t("recompile", "Recompile", "Digital", "status", 0, 100, "Rewrites its own loops - Power climbs.", buff_power=0.3)
_t("starfall", "Starfall", "Cosmic", "special", 55, 95, "Calls down a scatter of burning dust.")
_t("voidlance", "Void Lance", "Cosmic", "physical", 50, 95, "A spear of hard vacuum.")
_t("nebulaglow", "Nebula Glow", "Cosmic", "special", 60, 90, "Wraps the target in a glowing stellar cloud.")

# Disc-only art (never appears in a learnset): each gym leader's secret technique, taught by their move disc.
_t("verdantstorm", "Verdant Storm", "Botanic", "special", 75, 90,
   "The Green Gym's secret art: a storm of razor leaves and choking pollen.",
   status="Deoxygenated", status_chance=0.2)


# --------------------------------------------------------------------------- species
# The scimon_database.json package (assets/scimon_database.json, mirrored in scimon_db_data.py for browser
# builds) is the authoritative catalog: 109 families, 327 forms, evolutions, habitats and the encounter
# policy.  All 268 previously registered IDs, dex numbers, names, stats and evolution thresholds are preserved
# inside it; the 59 first forms marked "proposed_new_art_stage" complete every family to three stages.
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
    family_id: str = ""
    stage_ordinal: int = 0           # 1 first / 2 middle / 3 final
    stage_role: str = ""
    normal_habitats: tuple = ()      # authoritative normal-encounter habitats (species_expanded.WILD_HOME successor)
    min_wild_level: int = 1
    max_wild_level: int = 100
    wild_unlock_phase: int = 0
    evolves_to: Optional[str] = None
    evolution_level: Optional[int] = None
    wild_enabled: bool = True
    source_registered: bool = True

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


def _s(*a, **k):
    s = Species(*a, **k)
    SPECIES[s.id] = s


def _load_db():
    """The database JSON is the source of truth; scimon_db_data.py (generated from it) is the import-time
    fallback for browser builds, where assets are preloaded after the module imports."""
    here = os.path.dirname(os.path.abspath(__file__))
    for rel in (os.path.join("assets", "scimon_database.json"), "scimon_database.json"):
        try:
            with open(os.path.join(here, rel), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    try:
        import scimon_db_data
        return scimon_db_data.DB
    except Exception:
        raise ImportError("scimon database not found (assets/scimon_database.json / scimon_db_data.py)")


import json as _json
import os as _os

DB = _load_db()

# ---- types: colours and matchups come from the database (it completes the missing Quantum/Plasma/Shadow/Cosmic
# weakness lists the hand-written table was missing)
TYPE_COLORS = {t["id"]: t["color"] for t in DB["types"]}
STRONG = {t["id"]: list(t["strong_against"]) for t in DB["types"]}
WEAK = {t["id"]: list(t["weak_against"]) for t in DB["types"]}

# ---- techniques: identical ids/fields to the hand-written table (verified), kept in sync from the database
for _tr in DB["techniques"]:
    _t(**{k: v for k, v in _tr.items() if k in Technique.__dataclass_fields__})

# ---- families and the encounter policy
FAMILIES = {f["id"]: f for f in DB["families"]}
HABITATS = {h["id"]: h for h in DB["habitats"]}
ENCOUNTER_POLICY = DB["encounter_policy"]
PHASES = ENCOUNTER_POLICY["phases"]
MIGRATION_PROBABILITY = ENCOUNTER_POLICY["global_migration_probability"]
LEVEL_CAP = ENCOUNTER_POLICY["level_cap"]

STARTER_IDS = [f["id"] for f in DB["families"] if f.get("starter_gift_eligible")]

for _rec in DB["species"]:
    _learnset = [(int(_m["level"]), _m["technique_id"]) for _m in _rec.get("learnset", ())]
    _base = tuple(int(_rec["base_stats"][k]) for k in
                  ("hp", "power", "defense", "sp_power", "sp_defense", "speed", "stability"))
    _front = _rec.get("front_sprite") or ""
    _back = _rec.get("back_sprite") or None
    _s(_rec["id"], int(_rec["dex"]), _rec["name"], _rec.get("classification", ""), list(_rec["types"]), _base,
       int(_rec["catch_rate"]), int(_rec["xp_yield"]),
       _front.split("/")[-1] if _front else "", _back.split("/")[-1] if _back else None,
       _learnset, _rec.get("ability", ""), _rec.get("description", ""), _rec.get("rarity", "common"),
       family_id=_rec.get("family_id", ""), stage_ordinal=int(_rec.get("stage_ordinal", 0)),
       stage_role=_rec.get("stage_role", ""), normal_habitats=tuple(_rec.get("normal_habitats", ())),
       min_wild_level=int(_rec.get("minimum_wild_level", 1)), max_wild_level=int(_rec.get("maximum_wild_level", 100)),
       wild_unlock_phase=int(_rec.get("wild_unlock_phase", 0)), evolves_to=_rec.get("evolves_to"),
       evolution_level=_rec.get("evolution_level"), wild_enabled=bool(_rec.get("wild_enabled", True)),
       source_registered=bool(_rec.get("source_registered", True)))

# ---- display-name patch provenance (tools/apply_name_patch.py): each species' previous canonical
# name, kept so savegame.load() can migrate a stored default name while preserving real nicknames
PREVIOUS_NAMES = {rec["id"]: rec["previous_name"] for rec in DB["species"] if rec.get("previous_name")}

# ---- evolutions and chains straight from the database (the old CRC-seeded registration is gone)
EVOLUTIONS = {sid: (rec["evolves_to"], int(rec["evolution_level"]))
              for sid, rec in ((s["id"], s) for s in DB["species"]) if rec.get("evolves_to")}
CHAIN_OF = {}
FAMILY_OF = {}
for _f in DB["families"]:
    for _sid in _f["chain_ids"]:
        CHAIN_OF[_sid] = list(_f["chain_ids"])
        FAMILY_OF[_sid] = _f["id"]
WILD_HOME = {sid: FAMILIES[fid]["normal_habitats"][0] for sid, fid in FAMILY_OF.items()}

SPECIES_COUNT = len(SPECIES)


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

# --------------------------------------------------------------------------- fishing rods
_probe_desc = "A basic sampling probe. Casts into shallow water for young Scimons."
_field_desc = "A field-grade capture rod. Casts into deeper water for developed Scimons."
_deep_desc = "A deep-water sampling rig. Casts into the open sea for apex Scimons."
CATALOG["probe_rod"] = ItemDef("probe_rod", "Probe Rod", "PR", _probe_desc, "#3d84c6", "key", permanent=True)
CATALOG["field_rod"] = ItemDef("field_rod", "Field Rod", "FR", _field_desc, "#2fbfae", "key", permanent=True)
CATALOG["deep_rod"] = ItemDef("deep_rod", "Deep Rod", "DR", _deep_desc, "#5b5bd6", "key", permanent=True)
FISHING_RODS = ("probe_rod", "field_rod", "deep_rod")

# --------------------------------------------------------------------------- field ability modules
CATALOG["abl_aquaboard"] = ItemDef("abl_aquaboard", "Aquaboard Module", "AB",
                                   "A field module. Ride a Hydro-type Scimon across open water.",
                                   "#3d84c6", "key", permanent=True)
CATALOG["abl_aerolift"] = ItemDef("abl_aerolift", "Aerolift Module", "AL",
                                  "A field module. Fast-travel to visited rest points with an Atmospheric-type.",
                                  "#8fb8d6", "key", permanent=True)
CATALOG["abl_lumen"] = ItemDef("abl_lumen", "Lumen Module", "LM",
                               "A field module. Illuminate dark spaces with Radiant energy.",
                               "#f0d76a", "key", permanent=True)
CATALOG["abl_excavator"] = ItemDef("abl_excavator", "Excavator Module", "EX",
                                   "A field module. Burrow out of caves with a Geologic-type Scimon.",
                                   "#a98150", "key", permanent=True)

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
