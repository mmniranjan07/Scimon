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

# ---- the wider region's wild Scimons (species_expanded.py: 100 curated entries; stats and learnsets derive
# from the species' archetype and type pool, the art from tools/build_scimon_art.py) -------------------------------
from species_expanded import expanded_species

WILD_HOME = {}                         # species id -> home biome (routes.py builds the encounter tables from it)
for _i, _row in enumerate(expanded_species(), 17):
    WILD_HOME[_row[0]] = _row[13]
    _s(_row[0], _i, _row[1], _row[2], _row[3], _row[4], _row[5], _row[6], _row[7], _row[8], _row[9], _row[10],
       _row[11], _row[12])

# --------------------------------------------------------------------------- evolutions
# Every Sci-Mon evolves.  The three starters climb a full three-stage line (dex 4-9); wild lines have either two
# stages (base -> final) or three (baby -> base -> final) -- the seeded split is ~40% three-stage.  Stage stats
# derive from the base species' archetype (babies smaller and easier to catch, finals larger and rarer), and every
# stage inherits its line's habitat (WILD_HOME) so the biome rule holds for the whole family.
EVOLUTIONS = {}                        # species id -> (target id, level)
CHAIN_OF = {}                          # every member id -> [stage ids, first..last]
CURATED_STARTER_STAGES = [
    # (base, mid name, mid level, final name, final level)
    ("florabot", "Floravine", 16, "Floratitan", 32),
    ("pyrodrive", "Pyroblaze", 16, "Pyrodrake", 32),
    ("aquabit", "Aquafin", 16, "Aquarex", 32),
]
_FINAL_SUFFIXES = ("Prime", "Rex", "Max", "Nova", "King", "Zero")
_next_dex = [4]                        # the reserved dex slots 4-9 go to the starters' evolved stages


def _build_evolutions():
    _seen_names = {s.name for s in SPECIES.values()}
    wild_ids = [s.id for s in SPECIES.values()
                if s.id not in STARTER_IDS and not (s.id.endswith("-mid") or s.id.endswith("-final")
                                                     or s.id.endswith("-baby"))]

    def baby_name(base):
        stem = base[:-2] if len(base) > 6 else base
        for cand in (stem + "ling", stem + "let", stem + "iling"):
            if cand not in _seen_names and not cand.endswith("lling"):
                return cand
        return base + " Jr"

    def final_name(base):
        for cand in (base + " " + suf for suf in _FINAL_SUFFIXES):
            if cand not in _seen_names:
                return cand
        return base + " Prime II"

    # ---- starters: curated three-stage lines, dex 4-9
    for base, mid_name, mid_lv, final_name_, final_lv in CURATED_STARTER_STAGES:
        sp = SPECIES[base]
        chain = [base]
        for sid, name, lv, scale in ((f"{base}-mid", mid_name, mid_lv, 1.28),
                                     (f"{base}-final", final_name_, final_lv, 1.55)):
            b = tuple(max(20, round(v * scale)) for v in sp.base)
            _s(sid, _next_dex[0], name, sp.classification, list(sp.types), b,
               45, int(sp.xp_yield * 1.5), f"{sid}-front.png", None,
               list(sp.learnset), sp.ability,
               f"The evolved form of {sp.name}. {sp.desc}", sp.rarity)
            _next_dex[0] += 1
            EVOLUTIONS[chain[-1]] = (sid, lv)
            chain.append(sid)
            _seen_names.add(name)
        for member in chain:
            CHAIN_OF[member] = list(chain)

    # ---- wild lines: seeded two/three-stage split (dex 117+)
    _next_dex[0] = max(_next_dex[0], 117)
    for base in wild_ids:
        sp = SPECIES[base]
        r = __import__("zlib").crc32(("evo:" + base).encode())
        three = (r % 100) < 40
        chain = [base]
        if three:                                       # a baby pre-stage before the known species
            bid = f"{base}-baby"
            b = tuple(max(20, round(v * 0.62)) for v in sp.base)
            bn = baby_name(sp.name)
            first_move = sp.learnset[0][1]
            _s(bid, _next_dex[0], bn, sp.classification, list(sp.types), b,
               190, max(20, int(sp.xp_yield * 0.6)), f"{bid}-front.png", None,
               [(1, first_move), (1, "sysram") if first_move != "sysram" else (1, first_move)],
               sp.ability, f"A young {sp.name}. {sp.desc}", "common")
            _next_dex[0] += 1
            EVOLUTIONS[bid] = (base, 10 + r % 5)
            chain.insert(0, bid)
            _seen_names.add(bn)
        fid = f"{base}-final"
        f = tuple(max(20, round(v * (1.4 if three else 1.45))) for v in sp.base)
        fn = final_name(sp.name)
        _s(fid, _next_dex[0], fn, sp.classification, list(sp.types), f,
           max(35, sp.catch_rate // 3), int(sp.xp_yield * 1.6),
           f"{fid}-front.png", None,
           list(sp.learnset) + [(26, sp.learnset[-1][1]), (32, sp.learnset[min(2, len(sp.learnset) - 1)][1])],
           sp.ability, f"The final form of {sp.name}. {sp.desc}", "rare")
        _next_dex[0] += 1
        EVOLUTIONS[chain[-1]] = (fid, (24 + r % 10) if three else (14 + r % 9))
        chain.append(fid)
        _seen_names.add(fn)
        for member in chain:
            CHAIN_OF[member] = list(chain)

    # stages inherit the line's habitat (the base species' biome)
    for sid, chain in CHAIN_OF.items():
        if sid not in WILD_HOME:
            home_chain = [c for c in chain if c in WILD_HOME]
            WILD_HOME[sid] = WILD_HOME[home_chain[0]] if home_chain else "meadow"


_build_evolutions()

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
