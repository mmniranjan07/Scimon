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
        "captured": sorted(st.captured), "rival_species": st.rival_species,
        "intro_done": st.intro_done, "rival_beaten": st.rival_beaten,
        "opened_chests": sorted(str(k) for k in st.opened_chests),
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
    from data import SPECIES
    from monsters import Scimon
    try:
        d = json.loads(_read())
        if d.get("v") != VERSION:
            return False
        fields = {f.name for f in dataclasses.fields(Scimon)}

        def mons(rows):
            out = []
            for r in rows:
                if r["species_id"] in SPECIES:
                    out.append(Scimon(**{k: v for k, v in r.items() if k in fields}))
            return out
        st.reset()
        st.party, st.storage = mons(d["party"]), mons(d["storage"])
        st.items = {k: int(v) for k, v in d["items"].items()}
        st.credits = int(d["credits"])
        st.captured = set(d["captured"])
        st.rival_species = d.get("rival_species")
        st.intro_done = bool(d.get("intro_done"))
        st.rival_beaten = bool(d.get("rival_beaten"))
        st.opened_chests = set(d.get("opened_chests", []))
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
