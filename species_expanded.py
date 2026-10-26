"""The wider region's wild Scimons: 100 curated species, built as plain tuples that data.py turns into Species
records (this module stays import-free and pure-data; data.py owns the Species class and the dex numbering).

Every entry: (id, name, classification, types, rarity, archetype, biome, home-note).  Stats are derived from the
archetype template scaled by rarity with a seeded per-species jitter; learnsets come from the species' type pool
(technique ids defined in data.py); the art comes from tools/build_scimon_art.py -> assets/scimon/<id>-front.png.

Biomes follow the field survey (routes.py / kanto.py):
  meadow/forest  - Botanic, Bio, Atmospheric, Chemical, Mechanical, Radiant, the classic commons
  water          - Hydro (+ deep-sea Cosmic/Shadow, warm-vent Thermal on volcanic shores)
  highland       - Cryo (Epidimy's snow country) + Radiant on the climb to the Plateau
  volcanic       - Thermal (Cinderfall's roads)
  cave           - Geologic, Metallic (+ warm-vent Thermal in Mt. Crescent)
  tunnel         - Metallic, Electric, Nano (Hollowgate's lantern line)
  city           - Electric, Plasma, Quantum, Nano, Digital (Aurum's grid routes)
  ghost          - Cosmic, Shadow (Dusklight's monuments) + deep sea
"""

# learnset pools per primary type (technique ids; signatures stay exclusive to their owners)
TYPE_MOVES = {
    "Thermal": ["embervent", "cinderbite", "thermalburst", "furnacevent", "heatsink"],
    "Hydro": ["waterjet", "tidalslam", "brineblast", "pressurewave", "riptide"],
    "Botanic": ["leafcut", "thornvolley", "sporecloud", "photosurge", "sapdrain"],
    "Geologic": ["rocktoss", "boulderbarge", "quakestomp", "shardguard"],
    "Atmospheric": ["galecut", "cyclone", "decompress", "pressurewave"],
    "Electric": ["staticjab", "magshock", "arcdis", "voltnet", "coilcrash", "capacitance"],
    "Cryo": ["frostbite", "rimeedge", "permafrost"],
    "Metallic": ["sysram", "alloybash", "ferrofilament", "platingcast"],
    "Chemical": ["acidburst", "toxinspray", "catalyst"],
    "Quantum": ["phaselance", "entanglepulse", "superposition"],
    "Plasma": ["plasmacutter", "ionstorm", "fusionflare"],
    "Radiant": ["lumenburst", "prismbeam", "suncloak"],
    "Shadow": ["duskwake", "voidpincer", "nightleech"],
    "Bio": ["biodrain", "myceliumweb", "splicetalon", "cellburst"],
    "Mechanical": ["sysram", "pistonpunch", "servoslam", "wreckingarm", "overclock"],
    "Nano": ["naniteswarm", "swarmbite", "disassembler", "dataspike"],
    "Digital": ["dataspike", "packetstorm", "glitchpulse", "firewallbreaker", "recompile"],
    "Cosmic": ["starfall", "voidlance", "nebulaglow"],
}

ARCHETYPES = {
    "bulwark":    (58, 40, 62, 36, 50, 24, 62),
    "sweeper":    (40, 58, 34, 56, 36, 60, 38),
    "tank":       (52, 52, 50, 44, 46, 34, 52),
    "swift":      (38, 44, 36, 46, 40, 66, 40),
    "specialist": (44, 50, 42, 58, 44, 44, 42),
}
RARITY_SCALE = {"common": 0.94, "uncommon": 1.0, "rare": 1.08}
RARITY_CATCH = {"common": 160, "uncommon": 130, "rare": 80}
RARITY_XP = {"common": 42, "uncommon": 50, "rare": 64}

CLASS_BY_TYPE = {
    "Thermal": "Vent Drone", "Hydro": "Tide Drone", "Botanic": "Flora Drone", "Geologic": "Terra Drone",
    "Atmospheric": "Sky Drone", "Electric": "Cell Drone", "Cryo": "Frost Drone", "Metallic": "Alloy Drone",
    "Chemical": "Reagent Drone", "Quantum": "Phase Drone", "Plasma": "Arc Drone", "Radiant": "Lumen Drone",
    "Shadow": "Shade Drone", "Bio": "Culture Drone", "Mechanical": "Chassis Drone", "Nano": "Swarm Drone",
    "Cosmic": "Orbit Drone", "Digital": "Packet Drone",
}

HOME_NOTES = {
    "meadow": "nests in the open meadows of the region",
    "forest": "drifts through Mossmere's old growth",
    "water": "rides the sea routes' tide-grass beds",
    "highland": "hunts above the snow line of the Epidimy climb",
    "volcanic": "basks on Cinderfall's warm shores",
    "cave": "clatters about the caves and crater walls",
    "tunnel": "lives along Hollowgate's lantern line",
    "city": "swarms the grid roads around Aurum City",
    "ghost": "haunts the monuments around Dusklight Town",
    "sea": "circles the deep wrecks off the sea lanes",
    "plateau": "shelters on the Ascent Road's high meadow",
}

# (id, name, types, rarity, archetype, biome) -- primary type drives the learnset pool; a secondary type widens
# the dex record and battle typing only.
SPECIES_TABLE = [
    # ---- meadow & forest grass biomes (35)
    ("vinelatch", "Vinelatch", ["Botanic"], "common", "bulwark", "forest"),
    ("sproutle", "Sproutle", ["Botanic"], "common", "swift", "meadow"),
    ("thistledrone", "Thistledrone", ["Botanic"], "uncommon", "specialist", "forest"),
    ("petalug", "Petalug", ["Botanic"], "common", "tank", "forest"),
    ("cactopod", "Cactopod", ["Botanic", "Chemical"], "uncommon", "bulwark", "meadow"),
    ("bloomxell", "Bloomxell", ["Botanic", "Radiant"], "rare", "specialist", "forest"),
    ("mosswing", "Mosswing", ["Botanic", "Atmospheric"], "common", "swift", "forest"),
    ("splicewisp", "Splicewisp", ["Bio"], "uncommon", "swift", "meadow"),
    ("mycelid", "Mycelid", ["Bio"], "common", "bulwark", "forest"),
    ("enzymite", "Enzymite", ["Bio", "Chemical"], "common", "specialist", "meadow"),
    ("organitron", "Organitron", ["Bio", "Mechanical"], "rare", "tank", "meadow"),
    ("cellling", "Cellling", ["Bio"], "common", "sweeper", "meadow"),
    ("visceroid", "Visceroid", ["Bio", "Shadow"], "rare", "bulwark", "meadow"),
    ("zephyrit", "Zephyrit", ["Atmospheric"], "common", "swift", "meadow"),
    ("galepod", "Galepod", ["Atmospheric"], "uncommon", "sweeper", "forest"),
    ("cumulob", "Cumulob", ["Atmospheric", "Hydro"], "common", "tank", "meadow"),
    ("aerochit", "Aerochit", ["Atmospheric"], "common", "swift", "meadow"),
    ("vortexling", "Vortexling", ["Atmospheric", "Quantum"], "rare", "sweeper", "forest"),
    ("stratowing", "Stratowing", ["Atmospheric"], "uncommon", "specialist", "plateau"),
    ("reagentot", "Reagentot", ["Chemical"], "common", "tank", "meadow"),
    ("toxigerm", "Toxigerm", ["Chemical", "Bio"], "common", "specialist", "meadow"),
    ("vapomite", "Vapomite", ["Chemical", "Atmospheric"], "uncommon", "swift", "meadow"),
    ("sludgebot", "Sludgebot", ["Chemical"], "uncommon", "bulwark", "meadow"),
    ("solvexel", "Solvexel", ["Hydro", "Chemical"], "rare", "specialist", "water"),
    ("catalyxt", "Catalyxt", ["Chemical"], "rare", "sweeper", "meadow"),
    ("cogmite", "Cogmite", ["Mechanical"], "common", "tank", "meadow"),
    ("gearhulk", "Gearhulk", ["Mechanical", "Geologic"], "uncommon", "bulwark", "meadow"),
    ("riveton", "Riveton", ["Mechanical"], "common", "bulwark", "tunnel"),
    ("springbit", "Springbit", ["Mechanical"], "common", "swift", "meadow"),
    ("crankling", "Crankling", ["Mechanical"], "uncommon", "specialist", "tunnel"),
    ("automit", "Automit", ["Mechanical", "Digital"], "rare", "tank", "city"),
    ("lumibot", "Lumibot", ["Radiant"], "uncommon", "specialist", "plateau"),
    ("prismoth", "Prismoth", ["Radiant", "Atmospheric"], "rare", "swift", "plateau"),
    ("gleamlet", "Gleamlet", ["Radiant"], "common", "swift", "meadow"),
    ("solburst", "Solburst", ["Radiant", "Plasma"], "rare", "sweeper", "meadow"),
    # ---- water & ice (14)
    ("droplite", "Droplite", ["Hydro"], "common", "swift", "water"),
    ("tidefin", "Tidefin", ["Hydro"], "common", "sweeper", "water"),
    ("brineling", "Brineling", ["Hydro", "Chemical"], "common", "specialist", "water"),
    ("kelpbot", "Kelpbot", ["Hydro", "Botanic"], "uncommon", "bulwark", "water"),
    ("mistfin", "Mistfin", ["Hydro", "Atmospheric"], "common", "swift", "water"),
    ("puddlit", "Puddlit", ["Hydro"], "common", "tank", "water"),
    ("coralbit", "Coralbit", ["Hydro", "Geologic"], "uncommon", "bulwark", "water"),
    ("abyssling", "Abyssling", ["Hydro", "Shadow"], "rare", "sweeper", "sea"),
    ("frostrit", "Frostrit", ["Cryo"], "common", "swift", "highland"),
    ("glacibit", "Glacibit", ["Cryo", "Hydro"], "uncommon", "tank", "water"),
    ("icelyte", "Icelyte", ["Cryo", "Radiant"], "rare", "specialist", "highland"),
    ("rimelet", "Rimelet", ["Cryo"], "common", "bulwark", "highland"),
    ("chillmite", "Chillmite", ["Cryo"], "common", "swift", "highland"),
    ("snovite", "Snovite", ["Cryo", "Atmospheric"], "uncommon", "sweeper", "highland"),
    # ---- volcanic (7)
    ("emberling", "Emberling", ["Thermal"], "common", "swift", "volcanic"),
    ("slagmite", "Slagmite", ["Thermal", "Geologic"], "uncommon", "bulwark", "volcanic"),
    ("magmite", "Magmite", ["Thermal"], "common", "tank", "volcanic"),
    ("flarebit", "Flarebit", ["Thermal"], "uncommon", "sweeper", "volcanic"),
    ("ashling", "Ashling", ["Thermal", "Atmospheric"], "common", "specialist", "volcanic"),
    ("scorchit", "Scorchit", ["Thermal"], "uncommon", "sweeper", "volcanic"),
    ("larvaburn", "Larvaburn", ["Thermal", "Bio"], "rare", "specialist", "volcanic"),
    # ---- caves (12)
    ("boulderon", "Boulderon", ["Geologic"], "uncommon", "bulwark", "cave"),
    ("shalebit", "Shalebit", ["Geologic"], "common", "tank", "cave"),
    ("cragling", "Cragling", ["Geologic"], "common", "bulwark", "cave"),
    ("quartzot", "Quartzot", ["Geologic", "Radiant"], "rare", "specialist", "cave"),
    ("gravelmut", "Gravelmut", ["Geologic", "Metallic"], "uncommon", "tank", "cave"),
    ("terrabot", "Terrabot", ["Geologic"], "uncommon", "bulwark", "cave"),
    ("basaltot", "Basaltot", ["Geologic", "Thermal"], "rare", "tank", "volcanic"),
    ("ferrite", "Ferrite", ["Metallic"], "common", "tank", "cave"),
    ("alloyling", "Alloyling", ["Metallic"], "common", "specialist", "tunnel"),
    ("chromelet", "Chromelet", ["Metallic", "Radiant"], "rare", "swift", "cave"),
    ("steelot", "Steelot", ["Metallic"], "uncommon", "bulwark", "tunnel"),
    ("ingotot", "Ingotot", ["Metallic", "Geologic"], "uncommon", "tank", "cave"),
    # ---- the power grid (5)
    ("voltling", "Voltling", ["Electric"], "common", "swift", "city"),
    ("amperit", "Amperit", ["Electric"], "common", "specialist", "tunnel"),
    ("ohmite", "Ohmite", ["Electric"], "uncommon", "tank", "city"),
    ("faradot", "Faradot", ["Electric", "Metallic"], "uncommon", "sweeper", "city"),
    ("joulebot", "Joulebot", ["Electric"], "rare", "sweeper", "tunnel"),
    # ---- the big-city grid roads (16)
    ("ionling", "Ionling", ["Plasma"], "common", "swift", "city"),
    ("arcwisp", "Arcwisp", ["Plasma", "Electric"], "uncommon", "sweeper", "city"),
    ("fusor", "Fusor", ["Plasma", "Thermal"], "rare", "specialist", "city"),
    ("coronalet", "Coronalet", ["Plasma", "Radiant"], "rare", "swift", "city"),
    ("qubit", "Qubit", ["Quantum"], "common", "swift", "city"),
    ("entanglit", "Entanglit", ["Quantum"], "uncommon", "specialist", "city"),
    ("phaseling", "Phaseling", ["Quantum", "Shadow"], "rare", "sweeper", "city"),
    ("wavicle", "Wavicle", ["Quantum", "Atmospheric"], "rare", "swift", "plateau"),
    ("nanoclit", "Nanoclit", ["Nano"], "common", "swift", "city"),
    ("micromite", "Micromite", ["Nano", "Mechanical"], "common", "tank", "city"),
    ("swarmlet", "Swarmlet", ["Nano"], "uncommon", "sweeper", "tunnel"),
    ("assembit", "Assembit", ["Nano", "Mechanical"], "rare", "specialist", "city"),
    ("biteling", "Biteling", ["Digital"], "common", "swift", "city"),
    ("codeling", "Codeling", ["Digital"], "common", "specialist", "city"),
    ("pixelot", "Pixelot", ["Digital", "Radiant"], "uncommon", "sweeper", "city"),
    ("packetot", "Packetot", ["Digital"], "rare", "tank", "city"),
    # ---- ghost houses & the deep (11)
    ("starlit", "Starlit", ["Cosmic"], "common", "swift", "ghost"),
    ("cometling", "Cometling", ["Cosmic", "Thermal"], "uncommon", "sweeper", "sea"),
    ("nebulon", "Nebulon", ["Cosmic"], "uncommon", "specialist", "ghost"),
    ("orbitling", "Orbitling", ["Cosmic", "Metallic"], "rare", "tank", "ghost"),
    ("voidling", "Voidling", ["Cosmic", "Shadow"], "rare", "sweeper", "sea"),
    ("duskling", "Duskling", ["Shadow"], "common", "swift", "ghost"),
    ("gloombat", "Gloombat", ["Shadow", "Atmospheric"], "common", "swift", "ghost"),
    ("umbralet", "Umbralet", ["Shadow"], "uncommon", "specialist", "ghost"),
    ("shadebot", "Shadebot", ["Shadow", "Mechanical"], "uncommon", "tank", "ghost"),
    ("wraithex", "Wraithex", ["Shadow", "Cosmic"], "rare", "sweeper", "ghost"),
    ("noctulite", "Noctulite", ["Shadow", "Radiant"], "rare", "specialist", "sea"),
]

ABILITIES = ["Photosynthesis", "Overdrive", "Coolant Flow", "Spore Vent", "Ember Body", "Condensation",
             "Static Charge", "Sturdy Plating", "Swarm Logic", "Heat Sink", "Buoyant Core", "Gyro Balance",
             "Regenerative Weave", "Grid Tether", "Deep Cycle", "Silent Run", "Night Optics", "Vacuum Seal"]


def expanded_species():
    """Yield tuples shaped exactly like data.py's _s(...) species records (dex is assigned by the caller)."""
    import zlib

    def rng(seed):
        r = zlib.crc32(str(seed).encode())
        return r

    out = []
    for (sid, name, types, rarity, archetype, biome) in SPECIES_TABLE:
        r = rng(sid)
        scale = RARITY_SCALE[rarity]
        base = tuple(max(20, round(v * scale + ((r >> (3 * i)) % 9) - 4)) for i, v in enumerate(ARCHETYPES[archetype]))
        pool = TYPE_MOVES[types[0]]
        n_moves = 5 if rarity == "rare" else (4 if rarity == "uncommon" else 3)
        learnset = [] if pool[0] == "sysram" else [(1, "sysram")]
        learnset.append((1, pool[0]))
        for i in range(1, min(n_moves, len(pool))):
            learnset.append((1 + i * 4, pool[i]))
        front = f"{sid}-front.png"
        note = HOME_NOTES[biome]
        desc = (f"This {CLASS_BY_TYPE[types[0]].lower()} {note}. "
                f"{archetype.capitalize()} chassis, {types[0].lower()}-tuned systems.")
        ability = ABILITIES[(r >> 5) % len(ABILITIES)]
        out.append((sid, name, CLASS_BY_TYPE[types[0]], types, base,
                    RARITY_CATCH[rarity] + (r >> 2) % 21 - 10, RARITY_XP[rarity] + (r >> 4) % 9 - 4,
                    front, None, learnset, ability, desc, rarity, biome))
    return out
