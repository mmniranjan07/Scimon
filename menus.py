"""Modal scenes: the Pack (party + bag), the shop counter, the Sci-Database terminal and the repair menu.

All of them are translucent overlays (`opaque = False`) pushed on top of the overworld, driven purely by
events and update(dt) -- opening one never pauses or blocks the engine loop."""
import pygame

import assets
import audio
from data import CATALOG, ITEM_CATEGORIES, MODULES, SHOP_PRICES, STATUS_INFO, item_def, sell_price, type_rgb, hexc
from engine import Scene, StateId
from monsters import PARTY_LIMIT
from settings import CREAM, H, INK, ORANGE, TEAL_DARK, W
from ui import (Button, ButtonGrid, bar, dim, draw_button, hp_color, is_back, is_click, is_confirm, label_chip,
                nav_dir, panel, render_text, text, type_chip, status_chip, wrap_text)


def _icon(surf, species_id, center, size):
    img = assets.mon_image(species_id, size, size)
    surf.blit(img, img.get_rect(center=center))


def _item_chip(surf, d, rect):
    pygame.draw.rect(surf, hexc(d.color), rect, border_radius=4)
    pygame.draw.rect(surf, INK, rect, 2, border_radius=4)
    img = render_text(d.short, "display", 8, INK)
    surf.blit(img, img.get_rect(center=rect.center))


# =========================================================================== the Pack
class InventoryScene(Scene):
    state_id = StateId.INVENTORY
    opaque = False

    PARTY_COLS, BAG_COLS = 3, 4

    def __init__(self, tab="party"):
        self.tab, self.cat, self.idx = tab, "consumable", 0
        self.pending = None           # item id waiting for a target Sci-Mon
        self.msg, self.msg_t, self.t = "", 0.0, 0.0
        self.rect = pygame.Rect(20, 16, W - 40, H - 32)
        self.slot_rects = []

    # ---- slot model -----------------------------------------------------------------
    def slots(self):
        st = self.engine.state
        if self.tab == "party":
            return [("mon", st.party[i] if i < len(st.party) else None) for i in range(PARTY_LIMIT)]
        stacks = st.items_in_category(self.cat)
        n = max(12, len(stacks))
        return [("item", stacks[i] if i < len(stacks) else None) for i in range(n)]

    @property
    def cols(self):
        return self.PARTY_COLS if self.tab == "party" else self.BAG_COLS

    def active(self):
        s = self.slots()
        return s[min(self.idx, len(s) - 1)]

    def say(self, msg, ok=True):
        if msg:
            self.msg, self.msg_t = msg, 2.4
            audio.play("heal" if ok else "deny")

    # ---- commands -----------------------------------------------------------------------
    def begin_target(self, item_id):
        d = item_def(item_id)
        if d and d.category in ("consumable", "held"):
            self.pending, self.tab, self.idx = item_id, "party", 0

    def apply_pending(self, mon):
        if not self.pending:
            return
        st = self.engine.state
        d = item_def(self.pending)
        ok, msg = st.give_held(self.pending, mon.uid) if d.category == "held" else st.use_item(self.pending, mon.uid)
        self.say(msg, ok)
        self.pending = None

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
                self.set_tab("bag" if self.tab == "party" else "party")
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
                {"close": lambda: self.engine.pop(self), "party": lambda: self.set_tab("party"),
                 "bag": lambda: self.set_tab("bag"), "use": self.activate, "discard": self.discard,
                 "take": self.take, "up": lambda: self.reorder(-1), "down": lambda: self.reorder(1),
                 "cancel": lambda: setattr(self, "pending", None)}.get(name, lambda: None)()
                if name.startswith("cat:"):
                    self.cat, self.idx = name[4:], 0
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
        text(surf, "PACK", (r.x + 28, r.y + 22), "display", 16, INK)
        for i, (key, label) in enumerate((("party", "Sci-Mon"), ("bag", "Bag"))):
            b = Button(label, (r.x + 140 + i * 130, r.y + 14, 120, 36))
            draw_button(surf, b, selected=self.tab == key, size=16)
            self._buttons[key] = b.rect
        text(surf, f"\u00a2 {st.credits}", (r.right - 90, r.y + 24), "display", 16, INK, anchor="topright")
        close = Button("X", (r.right - 70, r.y + 14, 48, 36))
        draw_button(surf, close, size=16)
        self._buttons["close"] = close.rect

        y0 = r.y + 64
        if self.pending:
            d = item_def(self.pending)
            banner = pygame.Rect(r.x + 24, y0, r.w - 48, 34)
            panel(surf, banner, "button_sel", blur=False, shadow=False)
            verb = "hold" if d.category == "held" else "receive"
            text(surf, f"Choose a Sci-Mon to {verb} {d.name}", (banner.x + 16, banner.centery), "display", 8, INK,
                 anchor="midleft")
            c = Button("Cancel", (banner.right - 110, banner.y + 3, 100, 28))
            draw_button(surf, c, size=8)
            self._buttons["cancel"] = c.rect
            y0 += 42

        left = pygame.Rect(r.x + 24, y0, 560, r.bottom - y0 - 46)
        right = pygame.Rect(left.right + 14, y0, r.right - left.right - 38, left.h)
        panel(surf, left, "inner", shadow=False)
        panel(surf, right, "inner", shadow=False)
        gy = left.y + 12
        if self.tab == "bag":
            x = left.x + 12
            for cid, label in ITEM_CATEGORIES:
                b = Button(label, (x, gy, 124, 30))
                draw_button(surf, b, selected=self.cat == cid, size=8)
                self._buttons["cat:" + cid] = b.rect
                x += 130
            gy += 40
        else:
            text(surf, f"Party {len(st.party)}/{PARTY_LIMIT}", (left.x + 14, gy), "display", 8, INK)
            gy += 26
        self._draw_grid(surf, pygame.Rect(left.x + 10, gy, left.w - 20, left.bottom - gy - 8))
        self._draw_detail(surf, right)
        if self.tab == "party" and not self.pending:
            text(surf, "Swap Sci-Mons at a Sci-Database terminal (Astrion Lab or Cush's Nook).",
                 (left.x + 14, left.bottom - 28), "body", 22, (70, 74, 70))
        hint = ("Tap to select   Use the buttons above to switch, take, reorder or discard   B closes"
                if getattr(self.engine, "touch_on", False) else
                "Arrows move  Enter select  Tab switch  Q/E category  T take  U/J reorder  Del discard  Esc close")
        text(surf, hint, (r.x + 28, r.bottom - 30), "body", 22, (70, 74, 70))
        if self.msg_t > 0:
            img = render_text(self.msg, "display", 8, (248, 246, 230))
            box = pygame.Rect(0, 0, img.get_width() + 40, 38)
            box.midbottom = (r.centerx, r.bottom - 52)
            panel(surf, box, "message")
            surf.blit(img, img.get_rect(center=box.center))

    def _draw_grid(self, surf, area):
        slots = self.slots()
        cols = self.cols
        cw, ch = (area.w - (cols - 1) * 8) // cols, 92 if self.tab == "party" else 78
        rows_vis = max(1, area.h // (ch + 8))
        first_row = max(0, self.idx // cols - rows_vis + 1)
        self.slot_rects = [pygame.Rect(-99, -99, 1, 1)] * len(slots)
        for i, (kind, v) in enumerate(slots):
            row = i // cols - first_row
            if row < 0 or row >= rows_vis:
                continue
            rect = pygame.Rect(area.x + (i % cols) * (cw + 8), area.y + row * (ch + 8), cw, ch)
            self.slot_rects[i] = rect
            panel(surf, rect, "button_sel" if i == self.idx else "button", blur=False, shadow=False)
            if kind == "item":
                if not v:
                    continue
                d = CATALOG[v[0]]
                _item_chip(surf, d, pygame.Rect(rect.centerx - 14, rect.y + 8, 28, 24))
                text(surf, d.name, (rect.centerx, rect.y + 40), "body", 22, INK, anchor="midtop")
                text(surf, f"x{v[1]}", (rect.centerx, rect.bottom - 6), "display", 8, INK, anchor="midbottom")
            elif v:
                _icon(surf, v.species_id, (rect.centerx, rect.y + 30), 46)
                text(surf, v.name, (rect.centerx, rect.y + 56), "body", 22, INK, anchor="midtop")
                ratio = v.hp / v.max_hp
                bar(surf, (rect.x + 10, rect.bottom - 12, rect.w - 20, 6), ratio, hp_color(ratio))

    def _draw_detail(self, surf, rect):
        kind, v = self.active()
        x, y = rect.x + 16, rect.y + 14
        if not v:
            text(surf, "Pick a slot to see its details.", rect.center, "body", 24, (100, 104, 100), anchor="center")
            return
        st = self.engine.state
        if kind == "item":
            d = CATALOG[v[0]]
            _item_chip(surf, d, pygame.Rect(x, y, 36, 30))
            text(surf, d.name, (x + 48, y), "display", 8, INK)
            text(surf, f"In bag: {v[1]}", (x + 48, y + 18), "body", 22, (90, 94, 90))
            ly = y + 54
            for ln in wrap_text(d.desc, "body", 26, rect.w - 32):
                text(surf, ln, (x, ly), "body", 26, INK)
                ly += 24
            by = rect.bottom - 14
            if d.category == "module":
                text(surf, "Thrown during battle to capture wild Sci-Mons.", (x, by - 20), "body", 22, (90, 94, 90))
            if not d.permanent:
                b = Button("Discard one", (x, by - 40, rect.w - 32, 34))
                draw_button(surf, b, size=8)
                self._buttons["discard"] = b.rect
                by -= 44
            else:
                text(surf, "Key items can't be discarded.", (x, by - 20), "body", 22, (90, 94, 90))
                by -= 24
            if d.category in ("consumable", "held"):
                b = Button("Give to a Sci-Mon" if d.category == "held" else "Use on a Sci-Mon",
                           (x, by - 40, rect.w - 32, 34), accent=True)
                draw_button(surf, b, selected=True, size=8)
                self._buttons["use"] = b.rect
            return
        mon = v
        _icon(surf, mon.species_id, (x + 28, y + 28), 56)
        text(surf, f"{mon.name}  L{mon.level}", (x + 70, y + 4), "display", 8, INK)
        cx = x + 70
        for t in mon.types:
            cx = type_chip(surf, t, cx, y + 26)
        ly = y + 66
        text(surf, f"HP {mon.hp}/{mon.max_hp}", (x, ly), "body", 24, INK)
        bar(surf, (x, ly + 22, rect.w - 32, 10), mon.hp / mon.max_hp, hp_color(mon.hp / mon.max_hp))
        ly += 40
        text(surf, f"Stability {mon.stability}/{mon.max_stability}", (x, ly), "body", 24, INK)
        ly += 24
        if mon.status:
            text(surf, f"{mon.status} - {STATUS_INFO[mon.status][2]}", (x, ly), "body", 22, hexc(STATUS_INFO[mon.status][1]))
            ly += 22
        for k, (lab, val) in enumerate((("Pow", mon.power), ("Def", mon.defense), ("SpP", mon.sp_power),
                                         ("SpD", mon.sp_defense), ("Spd", mon.speed))):
            text(surf, f"{lab} {val}", (x + (k % 2) * 130, ly + (k // 2) * 22), "body", 22, (70, 74, 70))
        ly += 70
        held = item_def(mon.held_item) if mon.held_item else None
        text(surf, f"Holding: {held.name if held else 'nothing'}", (x, ly), "body", 24, INK)
        by = rect.bottom - 14
        in_party = mon in st.party
        if in_party:
            i = st.party.index(mon)
            b1 = Button("Move up", (x, by - 34, (rect.w - 40) // 2, 34), enabled=i > 0)
            b2 = Button("Move down", (x + (rect.w - 40) // 2 + 8, by - 34, (rect.w - 40) // 2, 34), enabled=i < len(st.party) - 1)
            draw_button(surf, b1, size=8)
            draw_button(surf, b2, size=8)
            self._buttons["up"], self._buttons["down"] = b1.rect, b2.rect
            by -= 42
        if held:
            b = Button("Take held item", (x, by - 34, rect.w - 32, 34))
            draw_button(surf, b, size=8)
            self._buttons["take"] = b.rect
            by -= 42
        if self.pending:
            b = Button(f"Give to {mon.name}", (x, by - 34, rect.w - 32, 34), accent=True)
            draw_button(surf, b, selected=True, size=8)
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
                               right=f"x{owned}   \u00a2{price}"))
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
        text(surf, self.b.name, (r.x + 28, r.y + 22), "display", 16, INK)
        text(surf, f"\u00a2 {self.engine.state.credits}", (r.right - 28, r.y + 22), "display", 16, INK, anchor="topright")
        for i, (key, label) in enumerate((("buy", "Buy"), ("sell", "Sell"))):
            b = Button(label, (r.x + 24 + i * 208, r.y + 62, 200, 38))
            draw_button(surf, b, selected=self.tab == key, size=16)
        if not self.grid.buttons:
            text(surf, "Nothing to sell.", (r.x + 40, r.y + 140), "body", 32, (100, 104, 100))
        self.grid.draw(surf, size=16, kind="body" if False else "display")
        if self.msg_t > 0:
            text(surf, self.msg, (r.x + 28, r.bottom - 66), "display", 8, ORANGE)
        text(surf, "Up/Down choose   Enter confirm   Tab buy/sell   Esc leave", (r.centerx, r.bottom - 28),
             "body", 22, (70, 74, 70), anchor="center")


# =========================================================================== Sci-Database terminal
class DatabaseScene(Scene):
    state_id = StateId.DATABASE
    opaque = False

    def __init__(self):
        self.col, self.idx, self.msg, self.msg_t, self.t = 0, [0, 0], "", 0.0, 0.0
        self.rect = pygame.Rect(120, 50, W - 240, H - 100)
        self.rows = [[], []]

    def lists(self):
        st = self.engine.state
        return [st.party, st.storage]

    def handle_event(self, e):
        lists = self.lists()
        if is_back(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_i):
            self.engine.pop(self)
            return
        d = nav_dir(e)
        if d:
            if d[0]:
                self.col = max(0, min(1, self.col + d[0]))
            n = len(lists[self.col])
            self.idx[self.col] = max(0, min(max(0, n - 1), self.idx[self.col] + d[1]))
            return
        if is_confirm(e):
            self._act()
        elif is_click(e):
            for c in (0, 1):
                for i, rr in enumerate(self.rows[c]):
                    if rr.collidepoint(e.pos):
                        self.col, self.idx[c] = c, i
                        self._act()
                        return

    def _act(self):
        st, lst = self.engine.state, self.lists()[self.col]
        if not lst:
            return
        mon = lst[min(self.idx[self.col], len(lst) - 1)]
        ok, msg = st.send_to_storage(mon.uid) if self.col == 0 else st.withdraw(mon.uid)
        self.msg, self.msg_t = msg, 2.2
        audio.play("select" if ok else "deny")
        for c in (0, 1):
            self.idx[c] = max(0, min(self.idx[c], len(self.lists()[c]) - 1))

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)

    def draw(self, surf):
        dim(surf, 160)
        st, r = self.engine.state, self.rect
        panel(surf, r, "panel")
        text(surf, "SCI-DATABASE", (r.x + 28, r.y + 22), "display", 16, INK)
        text(surf, f"Party {len(st.party)}/{PARTY_LIMIT}", (r.right - 28, r.y + 24), "display", 8, INK, anchor="topright")
        colw = (r.w - 72) // 2
        for c, (title, lst, act) in enumerate((("Active party", st.party, "Store"), (f"Stored ({len(st.storage)})", st.storage, "Take"))):
            area = pygame.Rect(r.x + 28 + c * (colw + 16), r.y + 80, colw, r.h - 170)
            text(surf, title, (area.x, area.y - 22), "display", 8, (70, 74, 70))
            panel(surf, area, "inner", shadow=False)
            self.rows[c] = []
            if not lst:
                text(surf, "Nothing stored yet." if c else "", (area.x + 16, area.y + 16), "body", 26, (100, 104, 100))
            for i, m in enumerate(lst[:6]):
                row = pygame.Rect(area.x + 8, area.y + 8 + i * 62, area.w - 16, 56)
                self.rows[c].append(row)
                sel = (self.col == c and self.idx[c] == i)
                panel(surf, row, "button_sel" if sel else "button", blur=False, shadow=False)
                _icon(surf, m.species_id, (row.x + 30, row.centery), 44)
                text(surf, f"{m.name}  L{m.level}", (row.x + 62, row.y + 6), "body", 26, INK)
                ratio = m.hp / m.max_hp
                bar(surf, (row.x + 62, row.y + 34, row.w - 170, 9), ratio, hp_color(ratio))
                ok = (len(st.party) > 1) if c == 0 else (len(st.party) < PARTY_LIMIT)
                text(surf, act, (row.right - 16, row.centery), "display", 8, INK if ok else (150, 150, 140), anchor="midright")
            if c == 0 and len(st.party) <= 1:
                text(surf, "Keep at least one Sci-Mon with you.", (area.x + 12, area.bottom - 28), "body", 22, (100, 104, 100))
            if c == 1 and len(st.party) >= PARTY_LIMIT and st.storage:
                text(surf, "Store one first - your party is full.", (area.x + 12, area.bottom - 28), "body", 22, (100, 104, 100))
        if self.msg_t > 0:
            text(surf, self.msg, (r.x + 28, r.bottom - 76), "display", 8, ORANGE)
        text(surf, "Arrows move   Enter store/take   Esc log out", (r.centerx, r.bottom - 34), "body", 24, (70, 74, 70),
             anchor="center")


# =========================================================================== repair / service menu
class ServiceScene(Scene):
    """Cush's counter: free full repair, supplies, and the Sci-Database."""
    state_id = StateId.SERVICE
    opaque = False

    def __init__(self, building, on_repair):
        self.b, self.on_repair, self.t = building, on_repair, 0.0
        r = pygame.Rect(0, 0, 440, 78 + 58 * 4 + 28)
        r.center = (W // 2, H // 2)
        self.rect = r
        btns = []
        if building.repairs:
            btns.append(Button("Repair Scimons (free)", (r.x + 24, 0, r.w - 48, 46), tag="repair"))
        if building.shop:
            btns.append(Button("Buy supplies", (r.x + 24, 0, r.w - 48, 46), tag="shop"))
        if building.has_database:
            btns.append(Button("Access Sci-Database", (r.x + 24, 0, r.w - 48, 46), tag="db"))
        btns.append(Button("Leave", (r.x + 24, 0, r.w - 48, 46), tag="leave"))
        for i, b in enumerate(btns):
            b.rect.y = r.y + 70 + i * 58
        r.h = 70 + len(btns) * 58 + 22
        r.center = (W // 2, H // 2)
        for i, b in enumerate(btns):
            b.rect.y = r.y + 70 + i * 58
        self.grid = ButtonGrid(btns, cols=1)

    def handle_event(self, e):
        res = self.grid.handle(e)
        if not res:
            return
        kind, b = res
        if kind == "back" or (kind == "activate" and b.tag == "leave"):
            self.engine.pop(self)
        elif kind == "activate":
            self.engine.pop(self)
            if b.tag == "repair":
                self.on_repair()
            elif b.tag == "shop":
                self.engine.push(ShopScene(self.b))
            elif b.tag == "db":
                self.engine.push(DatabaseScene())

    def update(self, dt):
        self.t += dt
        self.grid.update(dt)

    def draw(self, surf):
        dim(surf, 130)
        panel(surf, self.rect, "panel")
        text(surf, self.b.name, (self.rect.x + 28, self.rect.y + 26), "display", 16, INK)
        self.grid.draw(surf, size=16)
