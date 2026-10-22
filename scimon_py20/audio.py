"""Tiny synthesized sound effects (port of V34's WebAudio blip generator). No audio files needed;
if no audio device exists the game just runs silent."""
import math
import random
from array import array

import pygame

RATE = 22050
_sounds = {}
_ready = False
muted = False


def init():
    global _ready
    try:
        pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
        _ready = True
    except pygame.error:
        _ready = False
        return False
    try:
        _build()
    except Exception:            # e.g. a browser without raw-buffer Sound support: just run silent
        _sounds.clear()
    return True


def _wave(kind, phase):
    if kind == "square":
        return 1.0 if (phase % 1.0) < 0.5 else -1.0
    if kind == "saw":
        return 2.0 * (phase % 1.0) - 1.0
    if kind == "noise":
        return random.uniform(-1, 1)
    return math.sin(phase * math.tau)


def _blip(notes):
    """notes: [(freq, dur, kind, start, gain)] mixed into one mono sound with exp decay per note."""
    total = max(s + d for _, d, _, s, _ in notes)
    n = int(total * RATE) + 1
    buf = [0.0] * n
    for freq, dur, kind, start, gain in notes:
        i0, cnt = int(start * RATE), int(dur * RATE)
        for i in range(cnt):
            if i0 + i >= n:
                break
            env = math.exp(-6.0 * i / max(1, cnt))
            buf[i0 + i] += _wave(kind, freq * i / RATE) * gain * env
    data = array("h", (max(-32767, min(32767, int(v * 32767 * 4))) for v in buf))
    return pygame.mixer.Sound(buffer=data.tobytes())


def _build():
    spec = {
        "hit": [(180, 0.12, "square", 0.0, 0.05), (120, 0.14, "square", 0.02, 0.04)],
        "faint": [(300, 0.5, "saw", 0.0, 0.05), (150, 0.5, "saw", 0.05, 0.04)],
        "capture": [(440, 0.08, "square", 0.0, 0.06), (660, 0.08, "square", 0.1, 0.06)],
        "heal": [(523, 0.09, "sine", 0.0, 0.05), (659, 0.09, "sine", 0.09, 0.05), (784, 0.12, "sine", 0.18, 0.05)],
        "xp": [(700, 0.05, "square", 0.0, 0.03), (900, 0.06, "square", 0.06, 0.03)],
        "select": [(520, 0.04, "square", 0.0, 0.03)],
        "move": [(330, 0.03, "square", 0.0, 0.02)],
        "door": [(220, 0.08, "sine", 0.0, 0.05), (330, 0.1, "sine", 0.07, 0.05)],
        "buy": [(660, 0.05, "square", 0.0, 0.04), (880, 0.08, "square", 0.05, 0.04)],
        "deny": [(150, 0.12, "square", 0.0, 0.05)],
    }
    for name, notes in spec.items():
        _sounds[name] = _blip(notes)


def play(name):
    if not _ready or muted:
        return
    snd = _sounds.get(name)
    if snd:
        snd.play()


def toggle_mute():
    global muted
    muted = not muted
    return muted
