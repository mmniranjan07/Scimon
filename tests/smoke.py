"""Headless smoke test: drives the real Engine with synthetic input and saves screenshots."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")  # never touch the real save
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
from engine import Engine, StateId
from scenes import TitleScene
import ui

OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/shots"
os.makedirs(OUT, exist_ok=True)
eng = Engine(); eng.push(TitleScene())

def key(k):
    eng.dispatch(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
def run(sec, dt=1/60):
    for _ in range(int(sec / dt)):
        eng.step(dt)
def shot(name):
    eng.render(); pygame.image.save(eng.screen, f"{OUT}/{name}.png")
def until(state, max_presses=80):
    """Click/confirm through whatever dialogue is up until the given scene is on top."""
    for _ in range(max_presses):
        if eng.top.state_id == state and not eng.transitioning:
            run(0.6); return
        key(pygame.K_RETURN); run(0.12)
    raise AssertionError(f"never reached {state}, stuck at {eng.top.state_id}")

run(0.5); shot("01_title")
key(pygame.K_RETURN); run(0.6)                    # title -> customize
key(pygame.K_RETURN); run(0.8)                    # start journey -> wake
run(1.0); shot("02_wake")
until(StateId.BRIEF)                              # dismiss the wake-up lines
run(0.8); shot("03_brief")
assert eng.top.state_id == StateId.BRIEF, eng.top
until(StateId.STARTER_SELECT)                     # Prof. Venn's animated briefing
run(0.6); shot("04_starter")
assert eng.top.state_id == StateId.STARTER_SELECT, eng.top
key(pygame.K_RIGHT); run(0.2); shot("04b_starter_pyro")
key(pygame.K_LEFT); key(pygame.K_RETURN); run(0.8)
run(0.5); shot("05_rival")
until(StateId.BATTLE)                             # Kael's challenge lines
run(0.8); shot("06_battle_intro")
assert eng.find(StateId.BATTLE), [s.state_id.name for s in eng.scenes]
print("OK flow reached rival battle; scenes:", [s.state_id.name for s in eng.scenes])
