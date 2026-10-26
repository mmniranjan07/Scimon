"""Modal scenes: the Pack (party + bag), the shop counter, the Sci-Database terminal and the type guide.

All of them are translucent overlays (`opaque = False`) pushed on top of the overworld, driven purely by
events and update(dt) -- opening one never pauses or blocks the engine loop."""
import math

import pygame

import assets
import audio
from data import (CATALOG, ITEM_CATEGORIES, MODULES, PASSES, SHOP_PRICES, STATUS_INFO, TECHNIQUES, item_def,
                  sell_price, type_rgb, hexc, STRONG, TYPE_COLORS, WEAK)
from engine import Scene, StateId
from monsters import PARTY_LIMIT
from settings import CREAM, H, INK, ORANGE, TEAL_DARK, W
from sprites import LOOKS, character_frame
from state import BOX_SIZE, BOX_COUNT, GYM_STAMPS, playtime_str
from ui import (Button, ButtonGrid, bar, dim, draw_button, hp_color, is_back, is_click, is_confirm, label_chip,
                nav_dir, panel, render_text, text, type_chip, status_chip, wrap_text)


def _icon(surf, species_id, center, size):
    img = assets.mon_image(species_id, size, size)
    surf.blit(img, img.get_rect(center=center))


def _item_chip(surf, d, rect):
    """The item's pixel-art icon centred in `rect`; falls back to the coloured letter chip when no icon art exists."""
    ic = assets.item_icon(d.id, 2)
    if ic is None:
        pygame.draw.rect(surf, hexc(d.color), rect, border_radius=4)
        pygame.draw.rect(surf, INK, rect, 2, border_radius=4)
        img = render_text(d.short, "display", 8, INK)
        surf.blit(img, img.get_rect(center=rect.center))
        return
    surf.blit(ic, ic.get_rect(center=rect.center))


# =========================================================================== the Pack
class InventoryScene(Scene):
    state_id = StateId.INVENTORY
    opaque = False

    PARTY_COLS, BAG_COLS = 3, 4

    def __init__(self, tab="party"):
        self.tab, self.cat, self.idx = tab, "consumable", 0
        self.pending = None           # item id waiting for a target Sci-Mon
        self.forgetting, self.forget_idx = None, 0   # (item id, uid): choose which of 4 moves the disc replaces
        self.msg, self.msg_t, self.t = "", 0.0, 0.0
        self.rect = pygame.Rect(20, 16, W - 40, H - 32)
        self.slot_rects = []

    # ---- slot model -----------------------------------------------------------------
    def slots(self):
        st = self.engine.state
        if self.tab == "party":
            return [("mon", st.party[i] if i < len(st.party) else None) for i in range(PARTY_LIMIT)]
        if self.tab == "profile":
            return []
        stacks = st.items_in_category(self.cat)
        if self.cat == "key":                     # the PASSES folder leads the Key Items grid
            passes = [s for s in stacks if s[0] in PASSES]
            rest = [s for s in stacks if s[0] not in PASSES]
            rows = -(-len(passes) // self.BAG_COLS)
            passes += [None] * (rows * self.BAG_COLS - len(passes))
            rest += [None] * max(0, 8 - len(rest))
            return [("item", s) for s in passes + rest]
        n = max(12, len(stacks))
        return [("item", stacks[i] if i < len(stacks) else None) for i in range(n)]

    @property
    def cols(self):
        return self.PARTY_COLS if self.tab == "party" else self.BAG_COLS

    def active(self):
        s = self.slots()
        return s[min(self.idx, len(s) - 1)] if s else ("none", None)

    def say(self, msg, ok=True):
        if msg:
            self.msg, self.msg_t = msg, 2.4
            audio.play("heal" if ok else "deny")

    # ---- commands -----------------------------------------------------------------------
    def begin_target(self, item_id):
        d = item_def(item_id)
        if d and d.category in ("consumable", "held", "disc"):
            self.pending, self.tab, self.idx = item_id, "party", 0

    def apply_pending(self, mon):
        if not self.pending:
            return
        st = self.engine.state
        d = item_def(self.pending)
        if d.category == "held":
            ok, msg = st.give_held(self.pending, mon.uid)
        elif d.category == "disc":
            if d.move not in mon.moves and len(mon.moves) >= 4 and \
                    (not d.compat_types or set(mon.types) & set(d.compat_types)):
                self.forgetting, self.pending, self.forget_idx = (self.pending, mon.uid), None, 0
                audio.play("select")
                return
            ok, msg = st.teach_move(self.pending, mon.uid)
        else:
            ok, msg = st.use_item(self.pending, mon.uid)
        self.say(msg, ok)
        self.pending = None

    def cancel_forget(self):
        self.forgetting, self.forget_idx = None, 0
        audio.play("deny")

    def pick_forget(self):
        """Swap the disc's move for the highlighted technique (the disc is consumed only on success)."""
        if not self.forgetting:
            return
        item_id, uid = self.forgetting
        mon, _ = self.engine.state.find(uid)
        if not mon:
            self.cancel_forget()
            return
        ok, msg = self.engine.state.teach_move(item_id, uid, forget=mon.moves[self.forget_idx % len(mon.moves)])
        self.say(msg, ok)
        self.forgetting = None

    def activate(self):
        kind, v = self.active()
        if kind == "mon":
            if v and self.pending:
                self.apply_pending(v)
        elif v:
            self.begin_target(v[0])

    def discard(self):
        kind, v = self.active()
        if kind == "item" and v:
            ok, msg = self.engine.state.discard(v[0], 1)
            self.say(msg, ok)

    def take(self):
        kind, v = self.active()
        if kind == "mon" and v:
            ok, msg = self.engine.state.take_held(v.uid)
            self.say(msg, ok)

    def reorder(self, delta):
        kind, v = self.active()
        if kind == "mon" and v:
            i = self.engine.state.party.index(v)
            ok, _ = self.engine.state.reorder_party(i, i + delta)
            if ok:
                self.idx = i + delta
                audio.play("select")

    def set_tab(self, tab):
        if tab != self.tab:
            self.tab, self.idx = tab, 0
            audio.play("select")

    def cycle_cat(self, d):
        ids = [c[0] for c in ITEM_CATEGORIES]
        self.cat = ids[(ids.index(self.cat) + d) % len(ids)]
        self.idx = 0
        audio.play("select")

    # ---- events -------------------------------------------------------------------------
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            k = e.key
            if self.forgetting:
                if k in (pygame.K_ESCAPE, pygame.K_x, pygame.K_BACKSPACE):
                    self.cancel_forget()
                    return
                mon, _ = self.engine.state.find(self.forgetting[1])
                n = len(mon.moves) if mon else 0
                if k in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                    self.forget_idx = (self.forget_idx - 1) % max(1, n)
                    audio.play("select")
                    return
                if k in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                    self.forget_idx = (self.forget_idx + 1) % max(1, n)
                    audio.play("select")
                    return
                if is_confirm(e):
                    self.pick_forget()
                return                     # modal: swallow everything else while the forget prompt is up
            if k in (pygame.K_ESCAPE, pygame.K_x, pygame.K_BACKSPACE):
                if self.pending:
                    self.pending = None
                else:
                    self.engine.pop(self)
                return
            if k == pygame.K_i:
                self.engine.pop(self)
                return
            if k == pygame.K_TAB:
                order = ("party", "bag", "profile")
                self.set_tab(order[(order.index(self.tab) + 1) % len(order)])
                return
            if k == pygame.K_q and self.tab == "bag":
                self.cycle_cat(-1)
                return
            if k == pygame.K_e and self.tab == "bag":
                self.cycle_cat(1)
                return
            if k == pygame.K_t:
                self.take()
                return
            if k == pygame.K_u:
                self.reorder(-1)
                return
            if k == pygame.K_j:
                self.reorder(1)
                return
            if k in (pygame.K_DELETE, pygame.K_r):
                self.discard()
                return
        d = nav_dir(e)
        if d:
            n = self.idx + (d[0] if d[0] else d[1] * self.cols)
            if d[0] and n // self.cols != self.idx // self.cols:
                n = self.idx
            if 0 <= n < len(self.slots()):
                self.idx = n
            return
        if is_confirm(e):
            self.activate()
        elif is_click(e):
            self._click(e.pos)
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.slot_rects):
                if r.collidepoint(e.pos):
                    self.idx = i

    def _click(self, pos):
        for name, r in getattr(self, "_buttons", {}).items():
            if r.collidepoint(pos):
                if name.startswith("forget:"):
                    self.forget_idx = int(name[7:])
                    self.pick_forget()
                    return
                if name == "cancel_forget":
                    self.cancel_forget()
                    return
                {"close": lambda: self.engine.pop(self), "party": lambda: self.set_tab("party"),
                 "bag": lambda: self.set_tab("bag"), "profile": lambda: self.set_tab("profile"),
                 "use": self.activate, "discard": self.discard,
                 "take": self.take, "up": lambda: self.reorder(-1), "down": lambda: self.reorder(1),
                 "cancel": lambda: setattr(self, "pending", None)}.get(name, lambda: None)()
                if name.startswith("cat:"):
                    self.cat, self.idx = name[4:], 0
                return
        if self.forgetting:                    # clicks outside the prompt buttons don't reach the grid
            return
        for i, r in enumerate(self.slot_rects):
            if r.collidepoint(pos):
                self.idx = i
                self.activate()
                return

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)

    # ---- drawing ------------------------------------------------------------------------
    def draw(self, surf):
        st = self.engine.state
        dim(surf, 175)
        panel(surf, self.rect, "panel")
        self._buttons = {}
        r = self.rect
        text(surf, "PACK", (r.x + 28, r.y + 22), "ui_b", 18, INK)
        for i, (key, label) in enumerate((("party", "Sci-Mon"), ("bag", "Bag"), ("profile", "Profile"))):
            b = Button(label, (r.x + 140 + i * 130, r.y + 14, 120, 36))
            draw_button(surf, b, selected=self.tab == key, size=15, kind="ui")
            self._buttons[key] = b.rect
        text(surf, f"\u00a2 {st.credits}", (r.right - 90, r.y + 24), "ui_b", 15, INK, anchor="topright")
        close = Button("X", (r.right - 70, r.y + 14, 48, 36))
        draw_button(surf, close, size=15, kind="ui_b")
        self._buttons["close"] = close.rect

        y0 = r.y + 64
        if self.pending:
            d = item_def(self.pending)
            banner = pygame.Rect(r.x + 24, y0, r.w - 48, 34)
            panel(surf, banner, "button_sel", blur=False, shadow=False)
            verb = {"held": "hold", "disc": "teach"}.get(d.category, "receive")
            text(surf, f"Choose a Sci-Mon to {verb} {d.name}", (banner.x + 16, banner.centery), "ui_b", 13, INK,
                 anchor="midleft")
            c = Button("Cancel", (banner.right - 110, banner.y + 3, 100, 28))
            draw_button(surf, c, size=13, kind="ui")
            self._buttons["cancel"] = c.rect
            y0 += 42

        lw = 300 if self.tab == "profile" else 560
        left = pygame.Rect(r.x + 24, y0, lw, r.bottom - y0 - 46)
        right = pygame.Rect(left.right + 14, y0, r.right - left.right - 38, left.h)
        panel(surf, left, "inner", shadow=False)
        panel(surf, right, "inner", shadow=False)
        if self.tab == "profile":
            self._draw_profile(surf, left, right)
        else:
            self._draw_pack(surf, left, right)
            if self.forgetting:
                self._draw_forget(surf)
        if self.msg_t > 0:
            img = render_text(self.msg, "ui_b", 13, (248, 246, 230))
            box = pygame.Rect(0, 0, img.get_width() + 40, 38)
            box.midbottom = (r.centerx, r.bottom - 52)
            panel(surf, box, "message")
            surf.blit(img, img.get_rect(center=box.center))

    def _draw_pack(self, surf, left, right):
        st = self.engine.state
        r = self.rect
        gy = left.y + 12
        if self.tab == "bag":
            x = left.x + 12
            for cid, label in ITEM_CATEGORIES:
                b = Button(label, (x, gy, 100, 30))
                draw_button(surf, b, selected=self.cat == cid, size=12, kind="ui")
                self._buttons["cat:" + cid] = b.rect
                x += 108
            gy += 40
        else:
            text(surf, f"Party {len(st.party)}/{PARTY_LIMIT}", (left.x + 14, gy), "ui_b", 13, INK)
            gy += 26
        self._draw_grid(surf, pygame.Rect(left.x + 10, gy, left.w - 20, left.bottom - gy - 8))
        self._draw_detail(surf, right)
        if self.tab == "party" and not self.pending:
            text(surf, "Swap Sci-Mons at a Sci-Database terminal.",
                 (left.x + 14, left.bottom - 28), "ui", 13, (70, 74, 70))
        hint = ("Tap to select   Use the buttons above to switch, take, reorder or discard   B closes"
                if getattr(self.engine, "touch_on", False) else
                "Arrows move   Enter select   Tab switch   Q/E category   T take   U/J reorder   Del discard   Esc close")
        text(surf, hint, (r.x + 28, r.bottom - 30), "ui", 13, (70, 74, 70))

    def _draw_forget(self, surf):
        """Move-disc overlay: the target knows 4 techniques, so pick the one the disc's move replaces."""
        st = self.engine.state
        item_id, uid = self.forgetting
        mon, _ = st.find(uid)
        d = item_def(item_id)
        if not mon or not d:
            self.forgetting = None
            return
        box = pygame.Rect(0, 0, 460, 60 + len(mon.moves) * 48 + 58)
        box.center = (self.rect.centerx, self.rect.centery)
        panel(surf, box, "panel")
        tech = TECHNIQUES[d.move]
        text(surf, f"Teach {tech.name} to {mon.name}?", (box.x + 24, box.y + 18), "ui_b", 14, INK)
        text(surf, "Pick the technique to forget.", (box.x + 24, box.y + 42), "ui", 13, (90, 94, 90))
        self._buttons.pop("use", None)
        for i, mv in enumerate(mon.moves):
            b = Button(TECHNIQUES[mv].name, (box.x + 24, box.y + 62 + i * 48, box.w - 48, 40))
            draw_button(surf, b, selected=self.forget_idx % len(mon.moves) == i, size=14, kind="ui")
            self._buttons[f"forget:{i}"] = b.rect
        c = Button("Cancel", (box.x + 24, box.bottom - 46, 120, 34))
        draw_button(surf, c, size=13, kind="ui")
        self._buttons["cancel_forget"] = c.rect

    def _draw_profile(self, surf, left, right):
        """Trainer card: look, money, time played | the gym stamp case (8 slots) and the current team."""
        st = self.engine.state
        x, y = left.x + 16, left.y + 14
        text(surf, "TRAINER", (x, y), "display", 8, INK)
        look = st.look if st.look is not None else LOOKS["player"]
        img = pygame.transform.scale_by(character_frame(look, "down", "idle", 0), 2)
        surf.blit(img, img.get_rect(midtop=(left.centerx, y + 34)))
        text(surf, st.name, (left.centerx, y + 238), "ui_b", 18, INK, anchor="midtop")
        text(surf, "Sci-Mon Researcher", (left.centerx, y + 268), "ui", 13, (90, 94, 90), anchor="midtop")
        panel(surf, pygame.Rect(x, y + 292, left.w - 32, 2), "inner", blur=False, shadow=False)
        for i, (label, val) in enumerate((("Credits", f"\u00a2 {st.credits}"), ("Played", playtime_str(st.playtime)),
                                          ("Stamps", f"{len(st.stamps)}/{len(GYM_STAMPS)}"))):
            ry = y + 310 + i * 34
            text(surf, label, (x + 4, ry), "ui", 14, (90, 94, 90))
            text(surf, val, (left.right - 20, ry), "ui_b", 13, INK, anchor="topright")

        rx, ry = right.x + 16, right.y + 14
        text(surf, "GYM STAMPS", (rx, ry), "ui_b", 13, TEAL_DARK)
        text(surf, f"{len(st.stamps)}/{len(GYM_STAMPS)} earned", (right.right - 20, ry), "ui", 13, (90, 94, 90),
             anchor="topright")
        cw, gap, ch = 118, 12, 118
        for i, d in enumerate(GYM_STAMPS):
            slot = pygame.Rect(rx + (i % 4) * (cw + gap), ry + 30 + (i // 4) * (ch + 12), cw, ch)
            earned = bool(d["id"] and d["id"] in st.stamps)
            panel(surf, slot, "button" if earned else "inner", blur=False, shadow=False)
            self._stamp_badge(surf, (slot.centerx, slot.y + 44), 34, d["color"],
                              (d["leader"][:1] or "?") if earned else "?", earned)
            text(surf, d["gym"] if earned else "???", (slot.centerx, slot.bottom - 18), "ui", 12,
                 INK if earned else (130, 132, 130), anchor="midbottom")

        ty = ry + 30 + 2 * (ch + 12) + 8
        text(surf, "CURRENT TEAM", (rx, ty), "ui_b", 13, TEAL_DARK)
        tw, tgap = 78, 8
        for i in range(PARTY_LIMIT):
            slot = pygame.Rect(rx + i * (tw + tgap), ty + 24, tw, 92)
            m = st.party[i] if i < len(st.party) else None
            panel(surf, slot, "button" if m else "inner", blur=False, shadow=False)
            if m:
                _icon(surf, m.species_id, (slot.centerx, slot.y + 30), 46)
                text(surf, m.name, (slot.centerx, slot.y + 58), "ui", 12, INK, anchor="midtop")
                text(surf, f"L{m.level}", (slot.centerx, slot.bottom - 4), "ui", 12, (70, 74, 70),
                     anchor="midbottom")
        if not st.party:
            text(surf, "No Sci-Mon yet.", (rx + tw * 3 + tgap * 2, ty + 70), "ui", 13, (100, 104, 100),
                 anchor="center")

    def _stamp_badge(self, surf, center, r, color, letter, earned):
        """A gym leader's stamp: scalloped rosette; undiscovered slots show a dashed outline."""
        cx, cy = center
        if not earned:
            for a in range(0, 12):
                start = a * 30 + 4
                pygame.draw.arc(surf, (150, 152, 150), (cx - r, cy - r, r * 2, r * 2), start * math.pi / 180,
                                (start + 22) * math.pi / 180, 3)
            return
        rim = tuple(c * 2 // 3 for c in color)
        lit = tuple(min(255, c + 45) for c in color)
        for i in range(12):                                  # scalloped edge
            a = math.tau * i / 12
            pygame.draw.circle(surf, rim, (round(cx + math.cos(a) * r), round(cy + math.sin(a) * r)), r // 4)
        pygame.draw.circle(surf, rim, (cx, cy), r)
        pygame.draw.circle(surf, color, (cx, cy), r - 4)
        pygame.draw.circle(surf, lit, (cx, cy), r - 13)
        img = render_text(letter, "display", 16, (255, 255, 255))
        surf.blit(img, img.get_rect(center=(cx, cy)))

    def _draw_grid(self, surf, area):
        slots = self.slots()
        cols = self.cols
        cw, ch = (area.w - (cols - 1) * 8) // cols, 92 if self.tab == "party" else 78
        split = 0                                  # the PASSES folder: leading full rows of pass items
        if self.tab == "bag" and self.cat == "key":
            split = sum(1 for s in slots if s[0] == "item" and s[1] and CATALOG[s[1][0]].id in PASSES)
        head = 22 if split else 0
        rows_vis = max(1, (area.h - head) // (ch + 8))
        first_row = max(0, self.idx // cols - rows_vis + 1)
        self.slot_rects = [pygame.Rect(-99, -99, 1, 1)] * len(slots)
        if split:
            pygame.draw.rect(surf, (232, 195, 58),
                             pygame.Rect(area.x, area.y + 14, area.w, (split // cols) * (ch + 8) - 4), 2, border_radius=8)
            text(surf, "PASSES", (area.x + 8, area.y), "ui_b", 12, (150, 122, 22))
        for i, (kind, v) in enumerate(slots):
            row = i // cols - first_row
            if row < 0 or row >= rows_vis:
                continue
            rect = pygame.Rect(area.x + (i % cols) * (cw + 8), area.y + head + row * (ch + 8), cw, ch)
            self.slot_rects[i] = rect
            panel(surf, rect, "button_sel" if i == self.idx else "button", blur=False, shadow=False)
            if kind == "item":
                if not v:
                    continue
                d = CATALOG[v[0]]
                _item_chip(surf, d, pygame.Rect(rect.centerx - 16, rect.y + 5, 32, 32))
                nm = 13 if assets.font("ui_b", 13).size(d.name)[0] <= rect.w - 8 else 11
                text(surf, d.name, (rect.centerx, rect.y + 40), "ui_b", nm, INK, anchor="midtop")
                text(surf, f"x{v[1]}", (rect.centerx, rect.bottom - 6), "ui", 12, (90, 94, 90), anchor="midbottom")
            elif v:
                _icon(surf, v.species_id, (rect.centerx, rect.y + 30), 46)
                text(surf, v.name, (rect.centerx, rect.y + 56), "ui_b", 13, INK, anchor="midtop")
                ratio = v.hp / v.max_hp
                bar(surf, (rect.x + 10, rect.bottom - 12, rect.w - 20, 6), ratio, hp_color(ratio))

    def _draw_detail(self, surf, rect):
        kind, v = self.active()
        x, y = rect.x + 16, rect.y + 14
        if not v:
            text(surf, "Pick a slot to see its details.", rect.center, "ui", 14, (100, 104, 100), anchor="center")
            return
        st = self.engine.state
        if kind == "item":
            d = CATALOG[v[0]]
            _item_chip(surf, d, pygame.Rect(x, y, 32, 32))
            text(surf, d.name, (x + 48, y), "ui_b", 14, INK)
            text(surf, f"In bag: {v[1]}", (x + 48, y + 22), "ui", 13, (90, 94, 90))
            ly = y + 54
            for ln in wrap_text(d.desc, "ui", 14, rect.w - 32):
                text(surf, ln, (x, ly), "ui", 14, INK)
                ly += 20
            by = rect.bottom - 14
            if d.category == "module":
                lines = wrap_text("Thrown during battle to capture wild Sci-Mons.", "ui", 13, rect.w - 32)
                for j, ln in enumerate(lines):
                    text(surf, ln, (x, by - 20 - j * 20), "ui", 13, (90, 94, 90))
                by -= 20 * len(lines)
            if not d.permanent:
                b = Button("Discard one", (x, by - 40, rect.w - 32, 34))
                draw_button(surf, b, size=13, kind="ui")
                self._buttons["discard"] = b.rect
                by -= 44
            else:
                text(surf, "Key items can't be discarded.", (x, by - 20), "ui", 13, (90, 94, 90))
                by -= 24
            if d.category in ("consumable", "held", "disc"):
                label = {"held": "Give to a Sci-Mon", "disc": "Teach to a Sci-Mon"}.get(d.category, "Use on a Sci-Mon")
                b = Button(label, (x, by - 40, rect.w - 32, 34), accent=True)
                draw_button(surf, b, selected=True, size=14, kind="ui_b")
                self._buttons["use"] = b.rect
            return
        mon = v
        _icon(surf, mon.species_id, (x + 28, y + 28), 56)
        text(surf, f"{mon.name}  L{mon.level}", (x + 70, y + 4), "ui_b", 14, INK)
        cx = x + 70
        for t in mon.types:
            cx = type_chip(surf, t, cx, y + 26)
        ly = y + 66
        text(surf, f"HP {mon.hp}/{mon.max_hp}", (x, ly), "ui_b", 13, INK)
        bar(surf, (x, ly + 22, rect.w - 32, 10), mon.hp / mon.max_hp, hp_color(mon.hp / mon.max_hp))
        ly += 40
        text(surf, f"Stability {mon.stability}/{mon.max_stability}", (x, ly), "ui", 13, (70, 74, 70))
        ly += 22
        if mon.status:
            text(surf, f"{mon.status} - {STATUS_INFO[mon.status][2]}", (x, ly), "ui", 13, hexc(STATUS_INFO[mon.status][1]))
            ly += 20
        for k, (lab, val) in enumerate((("Pow", mon.power), ("Def", mon.defense), ("SpP", mon.sp_power),
                                         ("SpD", mon.sp_defense), ("Spd", mon.speed))):
            text(surf, f"{lab} {val}", (x + (k % 2) * 130, ly + (k // 2) * 20), "ui", 13, (70, 74, 70))
        ly += 64
        held = item_def(mon.held_item) if mon.held_item else None
        text(surf, f"Holding: {held.name if held else 'nothing'}", (x, ly), "ui", 13, INK)
        by = rect.bottom - 14
        in_party = mon in st.party
        if in_party:
            i = st.party.index(mon)
            b1 = Button("Move up", (x, by - 34, (rect.w - 40) // 2, 34), enabled=i > 0)
            b2 = Button("Move down", (x + (rect.w - 40) // 2 + 8, by - 34, (rect.w - 40) // 2, 34), enabled=i < len(st.party) - 1)
            draw_button(surf, b1, size=13, kind="ui")
            draw_button(surf, b2, size=13, kind="ui")
            self._buttons["up"], self._buttons["down"] = b1.rect, b2.rect
            by -= 42
        if held:
            b = Button("Take held item", (x, by - 34, rect.w - 32, 34))
            draw_button(surf, b, size=13, kind="ui")
            self._buttons["take"] = b.rect
            by -= 42
        if self.pending:
            b = Button(f"Give to {mon.name}", (x, by - 34, rect.w - 32, 34), accent=True)
            draw_button(surf, b, selected=True, size=14, kind="ui_b")
            self._buttons["use"] = b.rect


# =========================================================================== shop
class ShopScene(Scene):
    state_id = StateId.SHOP
    opaque = False

    def __init__(self, building):
        self.b = building
        self.tab, self.msg, self.msg_t, self.t = "buy", "", 0.0, 0.0
        self.rect = pygame.Rect(150, 50, W - 300, H - 100)
        self.grid = ButtonGrid([], cols=1)
        self._rebuild()

    def rows(self):
        st = self.engine.state if self.engine else None
        if self.tab == "buy":
            return [(i, p, st.qty(i) if st else 0) for i, p in self.b.shop]
        if not st:
            return []
        out = []
        for cat in ("consumable", "module"):
            out += [(i, sell_price(i), q) for i, q in st.items_in_category(cat)]
        return out

    def _rebuild(self, keep=False):
        r = self.rect
        btns = []
        for k, (iid, price, owned) in enumerate(self.rows()):
            ok = (self.engine.state.credits >= price) if self.tab == "buy" and self.engine else owned > 0
            btns.append(Button(CATALOG[iid].name, (r.x + 24, r.y + 120 + k * 46, r.w - 48, 40), enabled=ok, tag=iid,
                               icon=iid, right=f"x{owned}   \u00a2{price}"))
        self.grid.set_buttons(btns, keep=keep)

    def on_enter(self):
        self._rebuild()

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
            self.tab = "sell" if self.tab == "buy" else "buy"
            self._rebuild()
            audio.play("select")
            return
        if is_click(e):
            for name, rr in (("buy", pygame.Rect(self.rect.x + 24, self.rect.y + 62, 200, 38)),
                             ("sell", pygame.Rect(self.rect.x + 232, self.rect.y + 62, 200, 38))):
                if rr.collidepoint(e.pos):
                    self.tab = name
                    self._rebuild()
                    return
        res = self.grid.handle(e)
        if not res:
            return
        kind, b = res
        if kind == "back":
            self.engine.pop(self)
        elif kind == "deny":
            self.say("Not enough credits!" if self.tab == "buy" else "Nothing to sell.", False)
        elif kind == "activate":
            st = self.engine.state
            if self.tab == "buy":
                ok, msg = st.buy(b.tag, dict(self.b.shop)[b.tag])
            else:
                ok, msg = st.sell(b.tag)
            self.say(msg, ok)
            audio.play("buy" if ok else "deny")
            self._rebuild(keep=True)

    def say(self, msg, ok):
        self.msg, self.msg_t = msg, 2.0

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        self.grid.update(dt)

    def draw(self, surf):
        dim(surf, 150)
        r = self.rect
        panel(surf, r, "panel")
        text(surf, self.b.name, (r.x + 28, r.y + 22), "ui_b", 18, INK)
        text(surf, f"\u00a2 {self.engine.state.credits}", (r.right - 28, r.y + 24), "ui_b", 15, INK, anchor="topright")
        for i, (key, label) in enumerate((("buy", "Buy"), ("sell", "Sell"))):
            b = Button(label, (r.x + 24 + i * 208, r.y + 62, 200, 38))
            draw_button(surf, b, selected=self.tab == key, size=15, kind="ui")
        if not self.grid.buttons:
            text(surf, "Nothing to sell.", (r.x + 40, r.y + 140), "ui", 15, (100, 104, 100))
        self.grid.draw(surf, size=15, kind="ui")
        if self.msg_t > 0:
            img = render_text(self.msg, "ui_b", 13, (248, 246, 230))
            box = pygame.Rect(0, 0, img.get_width() + 40, 38)
            box.midbottom = (r.centerx, r.bottom - 52)
            panel(surf, box, "message")
            surf.blit(img, img.get_rect(center=box.center))
        text(surf, "Up/Down choose   Enter confirm   Tab buy/sell   Esc leave", (r.centerx, r.bottom - 28),
             "ui", 13, (70, 74, 70), anchor="center")


# =========================================================================== Sci-Database terminal
# Party-and-boxes layout: Current Party on the left, a 6x5 storage box in the middle, and a detail panel with the
# species' stat hexagon on the right.  Behaviour is unchanged: Enter / click stores a party member or takes a stored
# one (the game still insists on keeping one Sci-Mon with you and on a party of at most PARTY_LIMIT).
BOX_COLS, BOX_ROWS = 6, 5
STAT_LABELS = ("HP", "ATTACK", "DEFENSE", "SPEED", "SP. DEF", "SP. ATK")
STAT_ORDER = (0, 1, 2, 5, 4, 3)          # clockwise from the top, as indexes into Species.base
STAT_MAX = 70.0
RARITY_COLORS = {"common": ((150, 150, 138), (255, 255, 255)), "uncommon": ((96, 170, 110), (255, 255, 255)),
                 "rare": ((232, 195, 58), INK)}


def _verdict(sp):
    total = sum(sp.base[:6])
    return "Amazing stats!" if total >= 285 else "Great stats!" if total >= 245 else \
        "Solid stats!" if total >= 225 else "Humble stats."


def _hex_pt(cx, cy, i, r):
    a = math.radians(-90 + 60 * i)
    return cx + math.cos(a) * r, cy + math.sin(a) * r


class DatabaseScene(Scene):
    state_id = StateId.DATABASE
    opaque = False

    def __init__(self):
        self.focus = "party"                 # "party" | "box"
        self.pidx, self.cell, self.box = 0, 0, 0
        self.back = False                    # F flips the preview to the back view
        self.msg, self.msg_t, self.t = "", 0.0, 0.0
        self.rect = pygame.Rect(20, 16, W - 40, H - 32)
        self.disp = [0.0] * 6                # animated hexagon values
        self.party_rects, self.cell_rects, self._buttons = [], [], {}

    # ---- model --------------------------------------------------------------------------------
    def boxes(self):
        return max(BOX_COUNT, -(-len(self.engine.state.storage) // BOX_SIZE))

    def selected(self):
        st = self.engine.state
        if self.focus == "party":
            return st.party[self.pidx] if self.pidx < len(st.party) else None
        i = self.box * BOX_SIZE + self.cell
        return st.storage[i] if i < len(st.storage) else None

    def _can_act(self, mon):
        st = self.engine.state
        if not mon:
            return False, ""
        if self.focus == "party":
            return (True, "Store in box") if len(st.party) > 1 else (False, "Keep one Sci-Mon with you")
        return (True, "Take to party") if len(st.party) < PARTY_LIMIT else (False, "Party full - store one first")

    def _act(self):
        st, mon = self.engine.state, self.selected()
        if not mon:
            return
        ok, msg = st.send_to_storage(mon.uid, self.box) if self.focus == "party" else st.withdraw(mon.uid)
        self.msg, self.msg_t = msg, 2.2
        audio.play("select" if ok else "deny")
        self.box = min(self.box, self.boxes() - 1)

    def _flip_box(self, d):
        n = self.boxes()
        if n > 1:
            self.box = (self.box + d) % n
            audio.play("select")

    def _move(self, dx, dy):
        if self.focus == "party":
            if dx > 0:
                self.focus = "box"
            else:
                self.pidx = max(0, min(PARTY_LIMIT - 1, self.pidx + dy))
            return
        col, row = self.cell % BOX_COLS, self.cell // BOX_COLS
        if dx < 0 and col == 0:
            self.focus, self.pidx = "party", min(row, PARTY_LIMIT - 1)
            return
        col = max(0, min(BOX_COLS - 1, col + dx))
        row = max(0, min(BOX_ROWS - 1, row + dy))
        self.cell = row * BOX_COLS + col

    # ---- input --------------------------------------------------------------------------------
    def _hit(self, pos):
        for i, r in enumerate(self.party_rects):
            if r.collidepoint(pos):
                return "party", i
        for i, r in enumerate(self.cell_rects):
            if r.collidepoint(pos):
                return "box", i
        return None

    def _point_at(self, hit):
        kind, i = hit
        if kind == "party":
            self.focus, self.pidx = "party", i
        else:
            self.focus, self.cell = "box", i

    def handle_event(self, e):
        if is_back(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_i):
            self.engine.pop(self)
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_q, pygame.K_PAGEUP):
                self._flip_box(-1)
                return
            if e.key in (pygame.K_e, pygame.K_PAGEDOWN):
                self._flip_box(1)
                return
            if e.key == pygame.K_f:
                self.back = not self.back
                return
        d = nav_dir(e)
        if d:
            self._move(*d)
            return
        if is_confirm(e):
            self._act()
        elif is_click(e):
            for name, r in self._buttons.items():
                if r.collidepoint(e.pos):
                    {"close": lambda: self.engine.pop(self), "prev": lambda: self._flip_box(-1),
                     "next": lambda: self._flip_box(1), "act": self._act}[name]()
                    return
            hit = self._hit(e.pos)
            if hit:                              # first tap selects (so touch players can read the entry), second acts
                same = (hit == ("party", self.pidx)) if hit[0] == "party" and self.focus == "party" else \
                       (hit == ("box", self.cell)) if hit[0] == "box" and self.focus == "box" else False
                self._point_at(hit)
                if same:
                    self._act()
        elif e.type == pygame.MOUSEMOTION:
            hit = self._hit(e.pos)
            if hit:
                self._point_at(hit)

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        mon = self.selected()
        target = [mon.species.base[k] for k in STAT_ORDER] if mon else [0.0] * 6
        k = 1 - math.exp(-14 * dt)
        self.disp = [a + (b - a) * k for a, b in zip(self.disp, target)]

    # ---- drawing ------------------------------------------------------------------------------
    def draw(self, surf):
        dim(surf, 175)
        st, r = self.engine.state, self.rect
        panel(surf, r, "panel")
        self._buttons = {}
        text(surf, "SCI-DATABASE", (r.x + 28, r.y + 22), "display", 16, INK)
        tab = Button("Party and Boxes", (r.x + 270, r.y + 14, 200, 36))
        draw_button(surf, tab, selected=True, size=8)
        text(surf, f"Party {len(st.party)}/{PARTY_LIMIT}   Stored {len(st.storage)}", (r.right - 90, r.y + 24),
             "display", 8, INK, anchor="topright")
        close = Button("X", (r.right - 70, r.y + 14, 48, 36))
        draw_button(surf, close, size=16)
        self._buttons["close"] = close.rect

        y0, bh = r.y + 64, r.h - 64 - 46
        left = pygame.Rect(r.x + 24, y0, 188, bh)
        mid = pygame.Rect(left.right + 12, y0, 360, bh)
        right = pygame.Rect(mid.right + 12, y0, r.right - 24 - (mid.right + 12), bh)
        for a in (left, mid, right):
            panel(surf, a, "inner", shadow=False)
        mon = self.selected()
        self._draw_party(surf, left)
        self._draw_box(surf, mid)
        self._draw_preview(surf, pygame.Rect(mid.x + 12, mid.y + 332, mid.w - 24, mid.bottom - mid.y - 332 - 10), mon)
        self._draw_detail(surf, right, mon)

        hint = ("Tap a slot to select, tap again to store or take   < > change box   F flip   B closes"
                if getattr(self.engine, "touch_on", False) else
                "Arrows move   Enter store/take   Q/E change box   F flip view   Esc log out")
        text(surf, hint, (r.x + 28, r.bottom - 30), "body", 22, (70, 74, 70))
        if self.msg_t > 0:
            img = render_text(self.msg, "display", 8, (248, 246, 230))
            box = pygame.Rect(0, 0, img.get_width() + 40, 38)
            box.midbottom = (r.centerx, r.bottom - 52)
            panel(surf, box, "message")
            surf.blit(img, img.get_rect(center=box.center))

    def _draw_party(self, surf, area):
        st = self.engine.state
        head = pygame.Rect(area.x + 8, area.y + 8, area.w - 16, 30)
        panel(surf, head, "button", blur=False, shadow=False)
        text(surf, "Current Party", head.center, "display", 8, INK, anchor="center")
        self.party_rects = []
        for i in range(PARTY_LIMIT):
            row = pygame.Rect(area.x + 8, area.y + 46 + i * 72, area.w - 16, 66)
            self.party_rects.append(row)
            m = st.party[i] if i < len(st.party) else None
            sel = self.focus == "party" and self.pidx == i
            panel(surf, row, ("button_sel" if sel else "button") if m else "inner", blur=False, shadow=False)
            if not m:
                continue
            _icon(surf, m.species_id, (row.x + 30, row.centery), 46)
            text(surf, m.name, (row.x + 58, row.y + 8), "body", 24, INK)
            text(surf, f"L{m.level}", (row.x + 58, row.y + 32), "display", 8, (70, 74, 70))
            ratio = m.hp / m.max_hp
            bar(surf, (row.x + 58, row.bottom - 14, row.w - 70, 7), ratio, hp_color(ratio))

    def _draw_box(self, surf, area):
        st = self.engine.state
        n = self.boxes()
        hy = area.y + 8
        for name, label, x in (("prev", "<", area.x + 12), ("next", ">", area.right - 52)):
            b = Button(label, (x, hy, 40, 32), enabled=n > 1)
            draw_button(surf, b, size=16)
            self._buttons[name] = b.rect
        head = pygame.Rect(area.x + 58, hy, area.w - 116, 32)
        panel(surf, head, "button", blur=False, shadow=False)
        text(surf, f"Box {self.box + 1}/{n}", head.center, "display", 8, INK, anchor="center")
        cs, gap = 51, 5
        gx = area.x + (area.w - (BOX_COLS * cs + (BOX_COLS - 1) * gap)) // 2
        gy = area.y + 52
        self.cell_rects, tip = [], None
        for i in range(BOX_SIZE):
            rect = pygame.Rect(gx + (i % BOX_COLS) * (cs + gap), gy + (i // BOX_COLS) * (cs + gap), cs, cs)
            self.cell_rects.append(rect)
            si = self.box * BOX_SIZE + i
            m = st.storage[si] if si < len(st.storage) else None
            sel = self.focus == "box" and self.cell == i
            panel(surf, rect, ("button_sel" if sel else "button") if m else "inner", blur=False, shadow=False)
            if m:
                _icon(surf, m.species_id, rect.center, cs - 12)
            if sel:
                pygame.draw.rect(surf, ORANGE, rect.inflate(6, 6), 3, border_radius=13)
                if m:
                    tip = (m, rect)
        if tip:                                          # name tag over the cursor, like the box view it is modelled on
            m, rect = tip
            img = render_text(f"{m.name}  L{m.level}", "display", 8, INK)
            tag = pygame.Rect(0, 0, img.get_width() + 22, 24)
            tag.midbottom = (rect.centerx, rect.y - 6)
            if rect.y < area.y + 60:                     # top row: hang the tag below so it doesn't cover the box title
                tag.midtop = (rect.centerx, rect.bottom + 6)
            tag.clamp_ip(area.inflate(-8, 0))
            panel(surf, tag, "button_sel", blur=False, shadow=False)
            surf.blit(img, img.get_rect(center=tag.center))

    def _draw_preview(self, surf, area, mon):
        panel(surf, area, "inner", shadow=False)
        can, label = self._can_act(mon)
        btn = Button(label or "Empty slot", (area.x + 10, area.bottom - 40, area.w - 20, 30), enabled=can, accent=can)
        draw_button(surf, btn, selected=can, size=8)
        self._buttons["act"] = btn.rect if mon else pygame.Rect(-99, -99, 1, 1)
        top = pygame.Rect(area.x, area.y, area.w, area.h - 46)
        if not mon:
            text(surf, "Nothing here.", top.center, "body", 26, (100, 104, 100), anchor="center")
            return
        shadow = pygame.Surface((90, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 55), shadow.get_rect())
        surf.blit(shadow, shadow.get_rect(midbottom=(area.x + 70, top.bottom - 6)))
        back = self.back and mon.species.back
        img = assets.mon_image(mon.species_id, 96, 92, back=bool(back))
        bob = math.sin(self.t * 2.6) * 3
        surf.blit(img, img.get_rect(midbottom=(area.x + 70, top.bottom - 10 + bob)))
        x = area.x + 140
        text(surf, f"{mon.name}  L{mon.level}", (x, top.y + 8), "display", 8, INK)
        ratio = mon.hp / mon.max_hp
        text(surf, f"HP {mon.hp}/{mon.max_hp}", (x, top.y + 24), "body", 22, INK)
        bar(surf, (x, top.y + 43, area.right - x - 12, 8), ratio, hp_color(ratio))
        text(surf, f"Stability {mon.stability}/{mon.max_stability}", (x, top.y + 54), "body", 22, INK)
        bar(surf, (x, top.y + 73, area.right - x - 12, 8), mon.stability / max(1, mon.max_stability), (91, 143, 214))
        held = item_def(mon.held_item) if mon.held_item else None
        line = f"{mon.status} - {STATUS_INFO[mon.status][2]}" if mon.status else f"Holding: {held.name if held else 'nothing'}"
        text(surf, line, (x, top.y + 84), "body", 22, hexc(STATUS_INFO[mon.status][1]) if mon.status else (70, 74, 70))

    def _draw_detail(self, surf, area, mon):
        if not mon:
            text(surf, "Empty slot", (area.centerx, area.centery - 12), "display", 8, INK, anchor="center")
            for k, ln in enumerate(wrap_text("Pick a Sci-Mon to read its entry.", "body", 24, area.w - 48)):
                text(surf, ln, (area.centerx, area.centery + 14 + k * 22), "body", 24, (100, 104, 100), anchor="center")
            return
        sp = mon.species
        pad = 8
        banner = pygame.Rect(area.x + pad, area.y + pad, area.w - 2 * pad, 36)
        pygame.draw.rect(surf, type_rgb(sp.types[0]), banner, border_radius=8)
        pygame.draw.rect(surf, INK, banner, 2, border_radius=8)
        no = render_text(f"No.{sp.dex:03d}", "display", 8, (255, 255, 255))
        size = 16 if render_text(sp.name.upper(), "display", 16, INK).get_width() < banner.w - no.get_width() - 40 else 8
        text(surf, sp.name.upper(), (banner.x + 12, banner.centery), "display", size, (255, 255, 255),
             anchor="midleft", shadow=INK)
        surf.blit(no, no.get_rect(midright=(banner.right - 12, banner.centery)))
        cx = area.x + pad + 2
        for t in sp.types:
            cx = type_chip(surf, t, cx, area.y + 54)
        bg, fg = RARITY_COLORS.get(sp.rarity, RARITY_COLORS["common"])
        rimg = render_text(sp.rarity.upper(), "display", 8, fg)
        rr = pygame.Rect(0, area.y + 54, rimg.get_width() + 10, rimg.get_height() + 8)
        rr.right = area.right - pad
        pygame.draw.rect(surf, bg, rr, border_radius=4)
        pygame.draw.rect(surf, (0, 0, 0, 80), rr, 1, border_radius=4)
        surf.blit(rimg, (rr.x + 5, rr.y + 4))
        self._draw_hexagon(surf, (area.centerx, area.y + 172), 60, sp)

        ky = area.y + 288
        for lab, val in (("CLASS", sp.classification), ("ABILITY", sp.ability), ("TOTAL", str(sum(sp.base[:6])))):
            text(surf, lab, (area.x + 14, ky + 6), "display", 8, TEAL_DARK)
            text(surf, val, (area.x + 92, ky), "body", 26, INK)
            ky += 24
        pygame.draw.line(surf, (255, 255, 255, 90), (area.x + 10, ky + 2), (area.right - 10, ky + 2))
        ly = ky + 10
        for ln in wrap_text(sp.desc, "body", 22, area.w - 28)[:4]:
            text(surf, ln, (area.x + 14, ly), "body", 22, (70, 74, 70))
            ly += 19
        text(surf, _verdict(sp), (area.centerx, area.bottom - 14), "display", 8, ORANGE, anchor="midbottom")

    def _draw_hexagon(self, surf, c, rad, sp):
        cx, cy = c
        for f in (1.0, 0.66, 0.33):
            pygame.draw.polygon(surf, (150, 146, 118), [_hex_pt(cx, cy, i, rad * f) for i in range(6)], 1)
        for i in range(6):
            pygame.draw.line(surf, (150, 146, 118), (cx, cy), _hex_pt(cx, cy, i, rad))
        pts = [_hex_pt(cx, cy, i, rad * max(0.04, min(1.0, v / STAT_MAX))) for i, v in enumerate(self.disp)]
        size = rad * 2 + 8
        layer = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        off = (size - cx, size - cy)
        pygame.draw.polygon(layer, (209, 85, 47, 105), [(x + off[0], y + off[1]) for x, y in pts])
        surf.blit(layer, (-off[0], -off[1]))
        pygame.draw.polygon(surf, ORANGE, pts, 3)
        for p in pts:
            pygame.draw.circle(surf, INK, (int(p[0]), int(p[1])), 3)
        for i, lab in enumerate(STAT_LABELS):
            val = sp.base[STAT_ORDER[i]]
            x, y = _hex_pt(cx, cy, i, rad + 14)
            if i == 0:
                text(surf, lab, (x, y - 12), "display", 8, TEAL_DARK, anchor="midbottom")
                text(surf, val, (x, y - 11), "display", 8, ORANGE, anchor="midtop")
            elif i == 3:
                text(surf, lab, (x, y + 6), "display", 8, TEAL_DARK, anchor="midtop")
                text(surf, val, (x, y + 18), "display", 8, ORANGE, anchor="midtop")
            else:
                anc = "midleft" if i < 3 else "midright"
                text(surf, lab, (x, y - 7), "display", 8, TEAL_DARK, anchor=anc)
                text(surf, val, (x, y + 7), "display", 8, ORANGE, anchor=anc)


# =========================================================================== type & disc guide
class HelpScene(Scene):
    """Field guide: every Scimon type with its strong / weak matchups, plus the discs, capture modules
    and held cells that are tuned for each type."""
    state_id = StateId.HELP
    opaque = False
    COLS = 3

    def __init__(self):
        self.t, self.idx = 0.0, 0
        self.types = list(TYPE_COLORS)
        self.rect = pygame.Rect(20, 16, W - 40, H - 32)
        cw = max(assets.font("display", 8).size(t.upper())[0] for t in self.types) + 30
        self.grid = pygame.Rect(self.rect.x + 24, self.rect.y + 64,
                                self.COLS * cw + (self.COLS - 1) * 10, 6 * 36 + 5 * 10)
        self.detail = pygame.Rect(self.grid.right + 16, self.grid.y, self.rect.right - 24 - (self.grid.right + 16),
                                  self.grid.h)
        self.gear = pygame.Rect(self.rect.x + 24, self.grid.bottom + 14, self.rect.w - 48,
                                self.rect.bottom - 52 - (self.grid.bottom + 14))
        self.chip_rects, self._buttons = [], {}

    # ---- events -------------------------------------------------------------------------
    def handle_event(self, e):
        if is_back(e):
            self.engine.pop(self)
            return
        d = nav_dir(e)
        if d:
            i = self.idx + (d[0] if d[0] else d[1] * self.COLS)
            if d[0] and i // self.COLS != self.idx // self.COLS:
                i = self.idx
            if 0 <= i < len(self.types):
                self.idx = i
                audio.play("move")
            return
        if is_click(e):
            if any(r.collidepoint(e.pos) for r in self._buttons.values()):
                self.engine.pop(self)
                return
            for i, r in self.chip_rects:
                if r.collidepoint(e.pos):
                    self.idx = i
                    audio.play("move")
                    return

    def update(self, dt):
        self.t += dt

    # ---- helpers ------------------------------------------------------------------------
    def _chips(self, surf, types, x, y, max_x):
        """Type chips wrapped inside max_x; returns the y below the last row."""
        if not types:
            return text(surf, "-", (x, y), "ui", 13, (150, 160, 156)).bottom + 8
        cx, cy = x, y
        fh = assets.font("display", 8).get_height()
        for t in types:
            img = render_text(t.upper(), "display", 8, (255, 255, 255))
            if cx + img.get_width() + 10 > max_x and cx > x:
                cx, cy = x, cy + fh + 10
            r = label_chip(surf, t.upper(), (cx, cy), hexc(TYPE_COLORS[t]), 8)
            cx = r.right + 6
        return cy + fh + 10

    # ---- drawing ------------------------------------------------------------------------
    def _draw_grid(self, surf):
        panel(surf, self.grid, "inner", shadow=False)
        cw = (self.grid.w - (self.COLS - 1) * 10) // self.COLS
        self.chip_rects = []
        for i, t in enumerate(self.types):
            cr = pygame.Rect(self.grid.x + (i % self.COLS) * (cw + 10), self.grid.y + (i // self.COLS) * 46, cw, 36)
            self.chip_rects.append((i, cr))
            pygame.draw.rect(surf, hexc(TYPE_COLORS[t]), cr, border_radius=5)
            pygame.draw.rect(surf, (0, 0, 0, 70), cr, 1, border_radius=5)
            img = render_text(t.upper(), "display", 8, (255, 255, 255))
            surf.blit(img, img.get_rect(midleft=(cr.x + 10, cr.centery)))
            if i == self.idx:
                pygame.draw.rect(surf, ORANGE, cr, 3, border_radius=5)

    def _draw_detail(self, surf):
        t = self.types[self.idx]
        panel(surf, self.detail, "inner", shadow=False)
        x, y = self.detail.x + 16, self.detail.y + 14
        text(surf, t.upper(), (x, y), "ui_b", 18, hexc(TYPE_COLORS[t]))
        y += 36
        rows = (("STRONG VS - DEALS 1.5x", STRONG.get(t, [])),
                ("WEAK VS - DEALS 0.6x", WEAK.get(t, [])),
                ("WEAK TO - TAKES 1.5x", [a for a in self.types if t in STRONG.get(a, [])]),
                ("RESISTS - TAKES 0.6x", [a for a in self.types if t in WEAK.get(a, [])]))
        for label, lst in rows:
            text(surf, label, (x, y), "ui_b", 12, TEAL_DARK)
            y = self._chips(surf, lst, x, y + 18, self.detail.right - 16) + 6

    def _draw_gear(self, surf):
        panel(surf, self.gear, "inner", shadow=False)
        ch = assets.font("display", 8).get_height() + 8       # chip height, for mid-row alignment
        x, y = self.gear.x + 16, self.gear.y + 12
        text(surf, "MOVE DISCS - A GYM LEADER'S SIGNATURE TECHNIQUE:", (x, y), "ui_b", 12, TEAL_DARK)
        y += 20
        for d in [c for c in CATALOG.values() if c.category == "disc"]:
            tech = TECHNIQUES[d.move]
            ic = assets.item_icon(d.id, 1)
            if ic:
                surf.blit(ic, (x, y - 8))
            x2 = text(surf, f"{d.name}: {tech.name} ({tech.type} {tech.power} POW) - give it to a",
                      (x + (ic.get_width() + 8 if ic else 0), y), "ui", 14, INK, anchor="midleft").right + 8
            for ct in d.compat_types:
                x2 = label_chip(surf, ct.upper(), (x2, y - ch // 2), hexc(TYPE_COLORS[ct]), 8).right + 6
            y += 28
        y += 8
        text(surf, "CAPTURE MODULES - THROW IN BATTLE TO CATCH; A MATCHED TYPE IS 1.7x MORE LIKELY TO STICK:",
             (x, y), "ui_b", 12, TEAL_DARK)
        y += 20
        x2 = x
        for m in MODULES.values():
            name = m.name.replace(" Module", "").replace(" Capsule", "")
            ic = assets.item_icon(m.id, 1)
            if ic:
                surf.blit(ic, (x2, y - 8))
            x2 = text(surf, name + ":", (x2 + (ic.get_width() + 6 if ic else 0), y), "ui", 14, INK,
                      anchor="midleft").right + 6
            if m.match_type:
                x2 = label_chip(surf, m.match_type.upper(), (x2, y - ch // 2), hexc(TYPE_COLORS[m.match_type]), 8).right + 14
            else:
                x2 = text(surf, "any type", (x2, y), "ui", 14, (110, 116, 110), anchor="midleft").right + 14
        y += 28
        text(surf, "HELD CELLS - THE HOLDER'S TECHNIQUES OF THAT TYPE GET +20%:", (x, y), "ui_b", 12, TEAL_DARK)
        y += 20
        x2 = x
        for d in [c for c in CATALOG.values() if c.category == "held" and c.power_boost]:
            ic = assets.item_icon(d.id, 1)
            if ic:
                surf.blit(ic, (x2, y - 8))
            x2 = text(surf, d.name + ":", (x2 + (ic.get_width() + 6 if ic else 0), y), "ui", 14, INK,
                      anchor="midleft").right + 6
            x2 = label_chip(surf, d.power_boost[0].upper(), (x2, y - ch // 2), hexc(TYPE_COLORS[d.power_boost[0]]), 8).right + 14

    def draw(self, surf):
        dim(surf, 175)
        panel(surf, self.rect, "panel")
        r = self.rect
        text(surf, "TYPE & DISC GUIDE", (r.x + 28, r.y + 22), "ui_b", 18, INK)
        text(surf, "Tap a type to see its matchups", (r.centerx, r.y + 30), "ui", 13, (110, 116, 110),
             anchor="center")
        close = Button("X", (r.right - 70, r.y + 14, 48, 36))
        draw_button(surf, close, size=15, kind="ui_b")
        self._buttons = {"close": close.rect}
        self._draw_grid(surf)
        self._draw_detail(surf)
        self._draw_gear(surf)
        text(surf, "Tip: weaken a wild Scimon (low HP, a status fault) before throwing a module.",
             (r.x + 28, r.bottom - 30), "ui", 13, (110, 116, 110))
