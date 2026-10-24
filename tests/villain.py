"""The Corrupt Bandits arc (headless): Act-1 win + loss, Act-2 snatch + database recovery, the reveal in the
Epidimy nook, the boss (loss re-offers it, win ends it), and Kael's inheritance + rematches.
Usage: python tests/villain.py [screenshot_dir]"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
from overworld import OverworldScene
from monsters import create_scimon
import villain

OUT = sys.argv[1] if len(sys.argv) > 1 else None
if OUT: os.makedirs(OUT, exist_ok=True)
eng = Engine(); ovs = eng.push(OverworldScene()); st = eng.state; eng.step(0.1)
st.rival_species = "aquabit"                               # the story is past the intro

def key(k):
    eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")); eng.step(0.05)

def battle_auto():
    """Mash through a battle: confirm messages, Fight -> the hardest-hitting technique, forced switches take the
    first able mon."""
    from data import TECHNIQUES, effectiveness
    for _ in range(600):
        eng.step(0.05)
        top = eng.top
        if top.state_id != StateId.BATTLE:
            return True
        if top.menu == "message":
            key(pygame.K_RETURN); key(pygame.K_RETURN)
        elif top.menu == "main":
            key(pygame.K_RETURN)
        elif top.menu == "fight":
            best, bi = -1, 0
            for i, btn in enumerate(top.grid.buttons):
                t = next((t for t in TECHNIQUES.values() if t.name == btn.label), None)
                if t and t.category != "status":
                    score = t.power * effectiveness(t.type, top.bs.enemy.types) * t.accuracy / 100
                    if score > best:
                        best, bi = score, i
            cols = max(1, top.grid.cols)
            cr, cc = divmod(top.grid.idx, cols)
            tr, tc = divmod(bi, cols)
            for _ in range(max(0, tr - cr)):
                key(pygame.K_DOWN)
            for _ in range(max(0, cr - tr)):
                key(pygame.K_UP)
            for _ in range(max(0, tc - cc)):
                key(pygame.K_RIGHT)
            for _ in range(max(0, cc - tc)):
                key(pygame.K_LEFT)
            key(pygame.K_RETURN)
        elif top.menu == "switch":
            for _ in range(len(top.grid.buttons)):
                if top.grid.current.enabled: break
                key(pygame.K_DOWN)
            key(pygame.K_RETURN)
        else:
            key(pygame.K_ESCAPE)
    return False

def dismiss(n=40):
    """Press through dialogue; auto-play any battle that appears (its cutscene chains right after)."""
    for _ in range(n):
        if eng.top is ovs and not eng.transitioning:
            return
        if eng.top.state_id == StateId.BATTLE:
            assert battle_auto(), "a battle did not end"
            continue
        key(pygame.K_RETURN); eng.step(0.08)

def settle():
    """Press through whatever is left on top after dismiss (cutscenes land here)."""
    if eng.top is not ovs:
        dismiss()

def goto(area, tile):
    ovs.building = None
    ovs.map = ovs._get_map(None, area)
    ovs._load_npcs()
    ovs.player.place(*tile, "down")
    eng.step(0.1)

def shot(n):
    if OUT: eng.render(); pygame.image.save(eng.screen, f"{OUT}/{n}.png")

# ---- Act 1: the win branch - snatch fails anyway, flag set, no ticket yet
st.party = [create_scimon("florabot", 9), create_scimon("dewbit", 8)]
goto("route1", (10, 19))
ovs._check_ambush()
assert eng.top.state_id == StateId.DIALOGUE, eng.top
assert any(n.id.startswith("bandit") for n in ovs.npcs), "thugs did not stage"
shot("v1_ambush")
dismiss()                                                  # intro -> fade -> battle -> win cutscene
settle()
assert "bandit1" in st.story and not st.snatched and st.qty("banditticket") == 0
assert not any(n.id.startswith("bandit") for n in ovs.npcs), "thugs did not leave"
print("act1 win: snatch failed, flag set")

# ---- Act 1 loss: blackout, the scanner still saves the Sci-Mon
st.story.discard("bandit1")
st.party = [create_scimon("sporelet", 2)]
goto("route1", (10, 19))
ovs._check_ambush()
dismiss()
settle()
assert "bandit1" in st.story and not st.snatched and len(st.party) == 1
print("act1 loss: blackout, scanner jammed the snatch")

# ---- Act 2 loss: a RANDOM party Sci-Mon is taken
st.party = [create_scimon("sporelet", 2), create_scimon("sporelet", 2)]
goto("epidimy", (9, 15))
ovs._check_ambush()
assert eng.top.state_id == StateId.DIALOGUE
dismiss()
settle()
assert "bandit2" in st.story and st.snatched is not None, (st.story, st.snatched)
assert len(st.party) == 1 and st.snatched.uid != st.party[0].uid
assert st.qty("banditticket") == 1, "the Bandits' ticket should have dropped"
taken = st.snatched
print("act2 loss:", taken.name, "was taken")

# ---- recovery: the Sci-Database terminal inside Cush's own nook
cush = next(b for b in __import__("worldmap").BUILDINGS if b.id == "cush")
ovs.building = cush; ovs.map = ovs._get_map(cush); ovs._load_npcs()
ovs.player.place(9, 4, "up")
ovs.interact(); eng.step(0.1)
assert not st.snatched and "snatch_done" in st.story
assert taken.name in [m.name for m in st.party] + [m.name for m in st.storage]
dismiss()
print("recovery: the stolen Sci-Mon came home from Cush's database")

# ---- Act 3: the reveal (gated on the Green Gym stamp), then a forced boss loss
st.stamps.add("green")
st.party = [create_scimon("sporelet", 2)]                  # force the first boss loss
epi_center = next(b for b in __import__("epidimy").BUILDINGS if b.id == "epi-center")
ovs.building = None
ovs.enter_building(epi_center); eng.step(0.4)
assert "exposed" in st.story
dismiss()                                                  # reveal lines -> boss battle -> loss -> blackout
assert "boss_beaten" not in st.story
print("act3: reveal staged, boss survived the first attempt")

# ---- the boss remains: re-entry re-offers it, and this time the player wins with a full team
st.party = [create_scimon(s, lv) for s, lv in
            (("florabot", 14), ("dewbit", 13), ("sparkit", 13), ("pebblon", 13), ("cindermite", 13), ("sporelet", 14))]
ovs.enter_building(epi_center); eng.step(0.4)
assert eng.top.state_id == StateId.DIALOGUE, eng.top       # "Back so soon?" -> re-offer
dismiss()                                                  # -> boss battle -> win -> aftermath
settle()
assert "boss_beaten" in st.story and st.qty("mastersticket") == 1 and st.qty("banditticket") == 0
assert any(d.get("id") == "kael-nook" for d in ovs.map.npc_defs), "Kael did not take the counter"
shot("v2_aftermath")
print("act3: boss beaten, Kael inherited the nooks")

# ---- Kael: talk = challenge, the rematch ask offers a repair choice (retries: an auto-fight can lose)
for _ in range(4):
    st.party = [create_scimon("florabot", 16), create_scimon("dewbit", 15)]   # fresh team every attempt
    ovs.player.place(5, 6, "up"); eng.step(0.1)
    ovs.interact(); eng.step(0.1)
    assert eng.top.state_id == StateId.DIALOGUE
    dismiss()                                              # the confrontation lines -> battle -> post lines
    settle()
    if "kael-nook" in st.beaten_trainers:
        break
assert "kael-nook" in st.beaten_trainers, "Kael was not beaten in four attempts"
ovs.player.place(5, 6, "up"); ovs.interact(); eng.step(0.1)
assert eng.top.state_id == StateId.DIALOGUE and eng.top.choices
labels = [lab for lab, _ in eng.top.choices]
assert labels == ["BATTLE!", "REPAIR", "NOT NOW"], labels
key(pygame.K_LEFT); key(pygame.K_RETURN); eng.step(0.2)    # choose REPAIR (middle choice)
assert all(m.hp == m.max_hp for m in st.party), "Kael's repair did not heal"
print("kael: fights at the counter, rematches, and still repairs")
print("VILLAIN-ARC-OK")
