"""Save / load the player's progress.

Browser (pygbag): stored in the browser's localStorage, so it survives closing the tab and coming back later
(same browser + same site address).  Desktop: stored as JSON in ~/.scimon/save.json.
Nothing here can crash the game: every failure just means "no save"."""
import dataclasses
import json
import os
import sys

KEY = "scimon_save_v1"
VERSION = 1
_WEB = sys.platform == "emscripten"
_FILE = os.path.join(os.path.expanduser("~"), ".scimon", "save.json")


def _read():
    if os.environ.get("SCIMON_NO_SAVE"):       # tests / previews must never touch the player's real save
        return None
    try:
        if _WEB:
            import platform
            raw = platform.window.localStorage.getItem(KEY)
            return str(raw) if raw else None
        with open(_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _write(raw):
    if os.environ.get("SCIMON_NO_SAVE"):       # tests / previews must never touch the player's real save
        return False
    try:
        if _WEB:
            import platform
            platform.window.localStorage.setItem(KEY, raw)
        else:
            os.makedirs(os.path.dirname(_FILE), exist_ok=True)
            with open(_FILE, "w", encoding="utf-8") as f:
                f.write(raw)
        return True
    except Exception:
        return False


def serialize(st):
    return json.dumps({
        "v": VERSION,
        "party": [dataclasses.asdict(m) for m in st.party],
        "storage": [dataclasses.asdict(m) for m in st.storage],
        "items": st.items, "credits": st.credits,
        "captured": sorted(st.captured), "seen": sorted(getattr(st, "seen", ())), "rival_species": st.rival_species,
        "intro_done": st.intro_done, "rival_beaten": st.rival_beaten,
        "opened_chests": sorted(str(k) for k in st.opened_chests),
        "visited_healers": sorted(str(k) for k in getattr(st, "visited_healers", ())),
        "visited_areas": sorted(str(k) for k in getattr(st, "visited_areas", ())),
        "beaten_trainers": sorted(str(k) for k in getattr(st, "beaten_trainers", ())),
        "stamps": sorted(str(k) for k in getattr(st, "stamps", ())),
        "story": sorted(str(k) for k in getattr(st, "story", ())),
        "abilities": sorted(str(k) for k in getattr(st, "abilities", ())),
        "snatched": dataclasses.asdict(st.snatched) if getattr(st, "snatched", None) else None,
        "playtime": round(float(getattr(st, "playtime", 0.0)), 1),
        "location": getattr(st, "location", None) if isinstance(getattr(st, "location", None), dict) else {},
        "name": getattr(st, "name", "Robin"), "look": getattr(st, "look", None),
    }, sort_keys=True)


def has_save():
    raw = _read()
    if not raw:
        return False
    try:
        return json.loads(raw).get("v") == VERSION and bool(json.loads(raw).get("party"))
    except Exception:
        return False


def save(st, last=None):
    """Write the save if something changed since `last` (the previous string). Returns the string written."""
    if not st.party:                       # nothing worth saving before a starter is chosen
        return last
    raw = serialize(st)
    if raw != last and _write(raw):
        return raw
    return last


def load(st):
    """Fill `st` from the save. Returns True on success; on any problem `st` is left reset."""
    from data import SPECIES, PREVIOUS_NAMES
    from monsters import Scimon
    from state import stamp_by_id

    def fix_name(m):
        # display-name migration: saves written before the named-sprite patch stored the species'
        # default name on the creature.  Rename it ONLY when it still equals that species' previous
        # canonical name -- anything else is a player nickname and stays untouched.
        prev = PREVIOUS_NAMES.get(m.species_id)
        if prev and m.name == prev:
            m.name = SPECIES[m.species_id].name
        return m

    try:
        d = json.loads(_read())
        if d.get("v") != VERSION:
            return False
        fields = {f.name for f in dataclasses.fields(Scimon)}

        def mons(rows):
            out = []
            for r in rows:
                if r["species_id"] in SPECIES:
                    out.append(fix_name(Scimon(**{k: v for k, v in r.items() if k in fields})))
            return out
        st.reset()
        st.party, st.storage = mons(d["party"]), mons(d["storage"])
        st.items = {k: int(v) for k, v in d["items"].items()}
        st.credits = int(d["credits"])
        st.captured = set(d["captured"])
        # version-1 migration: saves written before the dex "seen" set initialize it from every
        # creature the player already owns (caught + party + storage), never losing state
        st.seen = set(d.get("seen", ())) | st.captured | {m.species_id for m in st.party} \
            | {m.species_id for m in st.storage}
        st.rival_species = d.get("rival_species")
        st.intro_done = bool(d.get("intro_done"))
        st.rival_beaten = bool(d.get("rival_beaten"))
        st.opened_chests = set(d.get("opened_chests", []))
        st.visited_healers = set(d.get("visited_healers", []))
        st.visited_areas = set(d.get("visited_areas", []))
        st.beaten_trainers = set(d.get("beaten_trainers", []))
        st.stamps = {s for s in d.get("stamps", []) if stamp_by_id(s)}
        st.story = set(d.get("story", []))
        st.abilities = set(d.get("abilities", []))
        sn = d.get("snatched")
        st.snatched = fix_name(Scimon(**{k: v for k, v in sn.items() if k in fields})) \
            if sn and sn.get("species_id") in SPECIES else None
        if st.snatched:
            st.seen.add(st.snatched.species_id)
        st.playtime = float(d.get("playtime", 0.0) or 0.0)
        loc = d.get("location")
        st.location = loc if isinstance(loc, dict) else {}
        st.name = str(d.get("name") or "Robin")[:12]
        st.look = d.get("look")
        return bool(st.party)
    except Exception:
        st.reset()
        return False


def delete():
    try:
        if _WEB:
            import platform
            platform.window.localStorage.removeItem(KEY)
        elif os.path.exists(_FILE):
            os.remove(_FILE)
    except Exception:
        pass
