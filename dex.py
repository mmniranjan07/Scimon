"""The Sci-Dex catalog: every registered Scimon family and form, browsable with seen/caught state.

Opened from the Sci-Database terminal (D).  Family-grouped grid on the left (dex order within a
family, families in dex order of their first form), full detail panel on the right: types, stage,
evolution chain with numeric levels, normal habitat, wild-stage unlock hint and the front/back art
(F flips).  Unseen forms show as silhouettes; seen but uncaught forms hide their description."""
import pygame

import assets
import audio
from data import FAMILIES, FAMILY_OF, SPECIES, TYPE_COLORS
from engine import Scene, StateId
from settings import H, INK, W
from ui import dim, is_back, panel, text

CELL = 78
COLS = 6
DETAIL_W = 330
STAGE_NAMES = {1: "first form", 2: "middle form", 3: "final form"}
PHASE_HINT = {0: "wild from the start", 1: "wild after the Green Stamp",
              2: "wild after the Green Stamp and the bandit boss"}


def _family_order():
    """Families in dex order of their first form; every species of the family keeps chain order."""
    fams = sorted(FAMILIES.values(), key=lambda f: min(SPECIES[s].dex for s in f["chain_ids"]))
    out = []
    for f in fams:
        out.extend(sorted(f["chain_ids"], key=lambda s: SPECIES[s].dex))
    return out


_ORDER = _family_order()


def _wrap(s, n):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


class DexScene(Scene):
    state_id = StateId.DATABASE
    opaque = False

    def __init__(self):
        self.idx = 0
        self.scroll = 0
        self.back = False
        self.t = 0.0
        self.cells = {}

    # ---- model -------------------------------------------------------------------------------
    @property
    def entries(self):
        return _ORDER

    def _seen(self, st, sid):
        return sid in getattr(st, "seen", ()) or sid in st.captured

    def _caught(self, st, sid):
        return sid in st.captured

    # ---- input --------------------------------------------------------------------------------
    def handle_event(self, e):
        if is_back(e) or (e.type == pygame.KEYDOWN and e.key in (pygame.K_i, pygame.K_d)):
            self.engine.pop(self)
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_f:
                self.back = not self.back
                audio.play("select")
                return
            if e.key in (pygame.K_PAGEUP, pygame.K_q):
                self.scroll = max(0, self.scroll - 4)
                return
            if e.key in (pygame.K_PAGEDOWN, pygame.K_e):
                self.scroll = min(max(0, len(self.entries) - 8), self.scroll + 4)
                return
            d = {pygame.K_LEFT: (1, 0), pygame.K_RIGHT: (-1, 0),
                 pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}.get(e.key)
            # the grid is filled right-to-left (dex order), so left advances the dex
            if d:
                i = self.idx - d[0] + d[1] * COLS
                self.idx = max(0, min(len(self.entries) - 1, i))
                self._follow()
                audio.play("select")
                return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for sid, r in self.cells.items():
                if r.collidepoint(e.pos):
                    self.idx = self.entries.index(sid)
                    audio.play("select")
            return

    def _follow(self):
        row = self.idx // COLS
        if row < self.scroll:
            self.scroll = row
        if row >= self.scroll + 7:
            self.scroll = row - 6

    def update(self, dt):
        self.t += dt

    # ---- draw ---------------------------------------------------------------------------------
    def draw(self, surf):
        st = self.engine.state
        dim(surf, 165)
        grid = pygame.Rect(16, 16, W - DETAIL_W - 48, H - 32)
        panel(surf, grid)
        det = pygame.Rect(W - DETAIL_W - 16, 16, DETAIL_W, H - 32)
        panel(surf, det)
        clip = surf.get_clip()
        surf.set_clip(grid.inflate(-16, -20))
        self.cells = {}
        for i, sid in enumerate(self.entries):
            row, col = divmod(i, COLS)
            row -= self.scroll
            if row < 0 or row > 7:
                continue
            r = pygame.Rect(grid.x + 12 + (COLS - 1 - col) * CELL, grid.y + 12 + row * CELL, CELL - 6, CELL - 6)
            self.cells[sid] = r
            self._draw_cell(surf, st, sid, r)
        surf.set_clip(clip)
        self._draw_detail(surf, st, det)
        text(surf, f"{sum(1 for s in self.entries if self._caught(st, s))}/{len(self.entries)} registered · "
                   f"{len(getattr(st, 'seen', ()))} seen · F: flip art · Esc: back",
             (grid.x + 12, grid.bottom - 24), "ui", 13, (190, 200, 195))

    def _draw_cell(self, surf, st, sid, r):
        seen, caught = self._seen(st, sid), self._caught(st, sid)
        pygame.draw.rect(surf, (36, 52, 50) if caught else ((30, 38, 40) if seen else (24, 30, 32)), r,
                         border_radius=6)
        pygame.draw.rect(surf, (232, 195, 58) if caught else ((90, 110, 105) if seen else (52, 58, 60)),
                         r, 2, border_radius=6)
        if not seen:
            text(surf, "?", (r.centerx, r.centery - 10), "ui_b", 26, (70, 80, 82), anchor="midtop")
            return
        try:
            img = assets.mon_image(sid, r.width - 10, r.height - 10)
            surf.blit(img, img.get_rect(center=r.center))
        except Exception:
            pass
        if caught:
            pygame.draw.circle(surf, (232, 195, 58), (r.right - 9, r.top + 9), 4)

    def _draw_detail(self, surf, st, det):
        sid = self.entries[self.idx]
        sp = SPECIES[sid]
        seen, caught = self._seen(st, sid), self._caught(st, sid)
        fam = FAMILIES[FAMILY_OF[sid]]
        x, y = det.x + 16, det.y + 14
        text(surf, f"№ {sp.dex:03d}", (x, y), "ui", 13, (150, 160, 158))
        y += 22
        name = sp.name if seen else "???"
        text(surf, name, (x, y), "ui_b", 21, (232, 195, 58) if caught else (200, 205, 200))
        y += 30
        for i, t in enumerate(sp.types):
            chip = pygame.Rect(x + i * 92, y, 86, 20)
            pygame.draw.rect(surf, TYPE_COLORS.get(t, "#888888"), chip, border_radius=10)
            text(surf, t, (chip.x + 8, chip.y + 3), "ui", 12, (15, 18, 16))
        y += 30
        art = pygame.Rect(det.centerx - 90, y, 180, 140)
        pygame.draw.rect(surf, (18, 24, 26), art, border_radius=8)
        if seen:
            try:
                img = assets.mon_image(sid, art.width - 10, art.height - 10, back=self.back)
                surf.blit(img, img.get_rect(center=art.center))
            except Exception:
                pass
        else:
            text(surf, "?", (art.centerx, art.centery - 16), "ui_b", 40, (60, 70, 72), anchor="midtop")
        y = art.bottom + 10
        text(surf, f"{fam['name']} family · {STAGE_NAMES.get(sp.stage_ordinal, sp.stage_role)}",
             (x, y), "ui", 13, (170, 180, 176))
        y += 22
        chain = fam["chain_ids"]
        parts = []
        for i, member in enumerate(chain):
            known = self._seen(st, member)
            parts.append(SPECIES[member].name if known else "???")
            if i < len(chain) - 1:
                parts.append(f" -Lv{fam['evolution_levels'][i]}-> ")
        for chunk in _wrap("".join(parts), 36):
            text(surf, chunk, (x, y), "ui", 13, (200, 205, 200))
            y += 18
        y += 4
        text(surf, f"Habitat: {', '.join(fam['normal_habitats'])}", (x, y), "ui", 13, (150, 190, 165))
        y += 20
        if caught:
            text(surf, "Registered in the Sci-Database", (x, y), "ui", 13, (120, 200, 140))
        else:
            text(surf, PHASE_HINT.get(sp.wild_unlock_phase, "wild"), (x, y), "ui", 13, (232, 195, 58))
        y += 22
        if caught:
            for chunk in _wrap(sp.desc, 40)[:4]:
                text(surf, chunk, (x, y), "ui", 12, (185, 192, 188))
                y += 16
        else:
            text(surf, "Catch one to register its entry." if seen else "Not encountered yet.",
                 (x, y), "ui", 12, (150, 158, 155))
