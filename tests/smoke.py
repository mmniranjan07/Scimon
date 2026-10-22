"""Headless smoke test: drives the real Engine with synthetic input and saves screenshots."""
import os, sys, random
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

run(0.5); shot("01_title")
key(pygame.K_RETURN); run(0.6)
run(1.0); shot("02_wake")
for _ in range(4):
    key(pygame.K_RETURN); key(pygame.K_RETURN); run(0.1)
run(0.6); shot("03_starter")
assert eng.top.state_id == StateId.STARTER_SELECT, eng.top
key(pygame.K_RIGHT); run(0.2); shot("03b_starter_pyro")
key(pygame.K_LEFT); key(pygame.K_RETURN); run(0.6)
run(0.5); shot("04_rival")
for _ in range(5):
    key(pygame.K_RETURN); key(pygame.K_RETURN); run(0.1)
run(1.0)
assert eng.find(StateId.BATTLE), [s.state_id for s in eng.scenes]
run(0.8); shot("05_battle_intro")
print("OK flow reached rival battle; scenes:", [s.state_id.name for s in eng.scenes])
