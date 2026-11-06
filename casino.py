"""The Verdance Game Corner: a slot machine and a five-card-draw data-poker table, played with
Game Corner coins bought at the counter (FireRed's Coin Case economy -- coins are bought with
credits and can never be sold back).

The slot machine is FireRed's three-reeler with the skill stop: SPIN sets all three reels running,
then you stop each reel in turn with its STOP press -- the symbol each reel lands on is wherever
its strip actually is, so your timing is the game.  The poker table is standard Jacks-or-better
video poker: bet, deal, hold any cards, draw, and the paytable pays the multiplier x bet.

Both are translucent modal scenes over the casino interior, exactly like the shop."""
import random

import pygame

import audio
from data import CATALOG
from engine import Scene, StateId
from settings import CREAM, H, INK, ORANGE, SLOT_BETS, TEAL_DARK, W
from ui import Button, ButtonGrid, dim, is_back, is_click, is_confirm, panel, render_text, text

SUIT_COLOR = {"S": (40, 44, 52), "H": (208, 74, 62), "D": (222, 130, 48), "C": (54, 110, 62)}
SUIT_NAME = {"S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs"}
RANK_NAME = {"T": "10", "J": "Jack", "Q": "Queen", "K": "King", "A": "Ace"}

# --------------------------------------------------------------------------- slots
SYMBOL_COLORS = {"seven": (222, 168, 48), "bolt": (240, 200, 60), "star": (222, 130, 48),
                 "orb": (108, 170, 220), "leaf": (110, 180, 110), "cherry": (208, 74, 62)}
# the reel strip: 15 cells -- a rare seven, a few bolts and stars, lots of leaves; tuned to return
# about 99.5 coins per 100 bet (FireRed's slots are famous for hovering just under break-even)
STRIP = (["seven"] + ["bolt"] * 2 + ["star"] * 2 + ["orb"] * 3 + ["leaf"] * 5 + ["cherry"] * 2)
TRIPLE_PAYOUT = {"seven": 300, "bolt": 50, "star": 30, "orb": 12, "leaf": 6, "cherry": 4}
CHERRY_TWO, CHERRY_ONE = 2, 1

POKER_PAYOUT = [("Royal Flush", 250), ("Straight Flush", 50), ("Four of a Kind", 25), ("Full House", 9),
                ("Flush", 6), ("Straight", 4), ("Three of a Kind", 3), ("Two Pair", 2), ("Jacks or Better", 1)]


def draw_symbol(surf, sym, rect):
    """One reel symbol drawn as a coloured chip with a simple vector glyph (no font glyph risk)."""
    pygame.draw.rect(surf, (26, 30, 36), rect, border_radius=6)
    pygame.draw.rect(surf, SYMBOL_COLORS[sym], rect.inflate(-6, -6), border_radius=5)
    c = rect.center
    col = (26, 30, 36)
    if sym == "seven":
        text(surf, "7", c, "ui_b", rect.h // 2, col, anchor="center")
    elif sym == "bolt":
        pygame.draw.polygon(surf, col, [(c[0] + rect.w // 5, c[1] - rect.h // 3), (c[0] - rect.w // 8, c[1] + rect.h // 16),
                                        (c[0] + rect.w // 16, c[1] + rect.h // 16), (c[0] - rect.w // 5, c[1] + rect.h // 3),
                                        (c[0] + rect.w // 10, c[1] - rect.h // 32), (c[0] - rect.w // 40, c[1] - rect.h // 32)])
    elif sym == "star":
        pts = []
        for i in range(10):
            r = rect.h // 3 if i % 2 == 0 else rect.h // 7
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
        pygame.draw.polygon(surf, col, pts)
    elif sym == "orb":
        pygame.draw.circle(surf, col, c, rect.h // 3)
        pygame.draw.circle(surf, SYMBOL_COLORS[sym], (c[0] - rect.h // 8, c[1] - rect.h // 8), rect.h // 8)
    elif sym == "leaf":
        pygame.draw.ellipse(surf, col, rect.inflate(-rect.w // 2, -rect.h // 2))
        pygame.draw.line(surf, SYMBOL_COLORS[sym], (c[0] - rect.w // 6, c[1] + rect.h // 4),
                         (c[0] + rect.w // 6, c[1] - rect.h // 4), 2)
    else:                                               # cherry: two berries on a stem
        r = rect.h // 7
        pygame.draw.line(surf, col, (c[0], c[1] - rect.h // 4), (c[0] - r, c[1]), 2)
        pygame.draw.line(surf, col, (c[0], c[1] - rect.h // 4), (c[0] + r, c[1] + r // 2), 2)
        pygame.draw.circle(surf, col, (c[0] - r, c[1] + r), r)
        pygame.draw.circle(surf, col, (c[0] + r, c[1] + int(1.5 * r)), r)


def score_reels(syms, bet):
    """The slot payout: triples by symbol, then cherries count as a consolation pair/single."""
    if syms[0] == syms[1] == syms[2]:
        mult = TRIPLE_PAYOUT[syms[0]]
        label = "JACKPOT!" if syms[0] == "seven" else f"TRIPLE {syms[0].upper()}!"
        return mult * bet, label
    n = syms.count("cherry")
    if n == 2:
        return CHERRY_TWO * bet, "Two cherries!"
    if n == 1:
        return CHERRY_ONE * bet, "A cherry - bet returned."
    return 0, ""


# --------------------------------------------------------------------------- poker


def new_deck():
    deck = [r + s for r in "23456789TJQKA" for s in "SHDC"]
    random.shuffle(deck)
    return deck


def score_hand(cards):
    """Standard Jacks-or-better evaluation.  Returns (hand name, multiplier) -- ("", 0) for nothing."""
    ranks = sorted("23456789TJQKA".index(c[0]) for c in cards)
    suits = {c[1] for c in cards}
    groups = sorted((ranks.count(r), r) for r in set(ranks))
    flush = len(suits) == 1
    straight = ranks == list(range(ranks[0], ranks[0] + 5)) or ranks == [0, 1, 2, 3, 12]  # A-2-3-4-5
    if flush and straight:
        return ("Royal Flush", 250) if ranks == [8, 9, 10, 11, 12] else ("Straight Flush", 50)
    if groups[-1][0] == 4:
        return "Four of a Kind", 25
    if groups[-1][0] == 3 and groups[-2][0] == 2:
        return "Full House", 9
    if flush:
        return "Flush", 6
    if straight:
        return "Straight", 4
    if groups[-1][0] == 3:
        return "Three of a Kind", 3
    if groups[-1][0] == 2 and groups[-2][0] == 2:
        return "Two Pair", 2
    if groups[-1][0] == 2 and groups[-1][1] >= 9:       # Jacks (index 9) or better
        return "Jacks or Better", 1
    return "", 0


def card_label(card):
    """A card's display strings: ('10', 'hearts') style."""
    r, s = card[0], card[1]
    return RANK_NAME.get(r, r), SUIT_NAME[s]


# =========================================================================== scenes


class _CasinoScene(Scene):
    """Shared chrome: the coin purse, the bet cycle and the coin counter." config."""
    state_id = StateId.CASINO
    opaque = False
    title = "GAME CORNER"

    def __init__(self):
        self.rect = pygame.Rect(120, 40, W - 240, H - 80)
        self.msg, self.msg_t = "Welcome! Coins cost 10 credits each.", 3.0
        self.t = 0.0

    def say(self, msg, ok=True):
        self.msg, self.msg_t = msg, 2.6 if ok else 2.0

    def cycle_bet(self, d):
        self.bet_idx = (self.bet_idx + d) % len(SLOT_BETS)
        audio.play("select")

    def coins(self):
        return self.engine.state.coins

    def draw_footer(self, surf):
        st = self.engine.state
        r = self.rect
        text(surf, f"COINS {st.coins}", (r.x + 26, r.bottom - 40), "ui_b", 15, (222, 168, 48))
        text(surf, f"\u00a2 {st.credits}", (r.right - 26, r.bottom - 40), "ui_b", 15, INK, anchor="topright")
        if self.msg_t > 0:
            col = ORANGE if "Not enough" in self.msg or "out of coins" in self.msg else CREAM
            text(surf, self.msg, (r.centerx, r.bottom - 12), "ui", 13, col, anchor="midbottom")

    def draw_header(self, surf, subtitle):
        r = self.rect
        panel(surf, r, "panel")
        text(surf, self.title, (r.x + 26, r.y + 18), "ui_b", 18, INK)
        text(surf, subtitle, (r.centerx, r.y + 22), "ui", 14, (110, 114, 118), anchor="midtop")


class SlotScene(_CasinoScene):
    """The three-reeler: bet, SPIN, stop each reel in turn; the strip decides, your timing argues."""

    def __init__(self):
        super().__init__()
        self.bet_idx = 0
        self.phase = "idle"            # idle | spin | done
        self.pos = [random.randrange(len(STRIP)) for _ in range(3)]   # strip positions (cell units)
        self.vel = [0.0, 0.0, 0.0]
        self.stopped = [True] * 3
        self.result = None             # (coins won, label)
        self.speed = 0.0
        self.grid = ButtonGrid([], cols=4)
        self._rebuild()

    def bet(self):
        return SLOT_BETS[self.bet_idx]

    def _rebuild(self):
        r = self.rect
        btns = [
            Button(f"BET {self.bet()}", (r.x + 26, r.bottom - 92, 120, 38), tag="bet", enabled=self.phase != "spin"),
            Button("SPIN", (r.x + 156, r.bottom - 92, 120, 38), accent=self.phase == "idle", tag="spin",
                   enabled=self.phase == "idle"),
            Button("STOP", (r.x + 286, r.bottom - 92, 120, 38), tag="stop", enabled=self.phase == "spin"),
            Button("BUY 10 COINS", (r.x + 416, r.bottom - 92, 170, 38), tag="coins", enabled=self.phase != "spin"),
            Button("LEAVE", (r.right - 116, r.bottom - 92, 90, 38), tag="back"),
        ]
        self.grid.set_buttons(btns)

    def on_enter(self):
        self._rebuild()

    def spin(self):
        st = self.engine.state
        if st.coins < self.bet():
            self.say("Not enough coins! Buy some at the counter.", False)
            audio.play("deny")
            return
        st.coins -= self.bet()
        self.phase, self.result = "spin", None
        self.stopped = [False, False, False]
        self.speed = random.uniform(14.0, 16.0)
        self.vel = [self.speed, self.speed * 1.15, self.speed * 1.3]
        audio.play("select")
        self.say(f"Bet {self.bet()} - stop each reel!", True)
        self._rebuild()

    def stop_one(self):
        for i in range(3):
            if not self.stopped[i]:
                self.stopped[i] = True
                self.pos[i] = round(self.pos[i]) % len(STRIP)
                audio.play("select")
                if all(self.stopped):
                    self._settle()
                return

    def _settle(self):
        self.phase = "done"
        st = self.engine.state
        syms = [STRIP[p] for p in self.pos]
        won, label = score_reels(syms, self.bet())
        if won:
            st.coins += won
            audio.play("jackpot" if won >= self.bet() * 40 else "win")
            self.say(f"{label} You win {won} coins!" if won > self.bet() else f"{label}", True)
        elif "cherry" not in syms:
            audio.play("deny")
            self.say("No luck this time.", False)
        self.result = (won, label)
        self._rebuild()

    def buy_coins(self):
        ok, msg = self.engine.state.buy_coins(10)
        self.say(msg, ok)
        audio.play("buy" if ok else "deny")

    def handle_event(self, e):
        if is_back(e):
            self.engine.pop(self)
            return
        if self.phase == "spin" and (is_confirm(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE)):
            self.stop_one()
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_LEFT, pygame.K_a):
                self.cycle_bet(-1)
                self._rebuild()
                return
            if e.key in (pygame.K_RIGHT, pygame.K_d):
                self.cycle_bet(1)
                self._rebuild()
                return
            if e.key == pygame.K_SPACE and self.phase != "spin":
                self.spin() if self.phase == "idle" else None
                return
        res = self.grid.handle(e)
        if not res:
            return
        kind, b = res
        if kind == "back":
            self.engine.pop(self)
        elif kind == "activate":
            {"bet": lambda: (self.cycle_bet(1), self._rebuild()), "spin": self.spin, "stop": self.stop_one,
             "coins": self.buy_coins}[b.tag]()

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        self.grid.update(dt)
        if self.phase == "spin":
            tick = False
            for i in range(3):
                if not self.stopped[i]:
                    self.pos[i] = (self.pos[i] + self.vel[i] * dt) % len(STRIP)
                    self.vel[i] *= 0.995 ** (dt * 60.0)        # reels bleed speed while they run
                    tick = True
            if tick:
                self._tick_t = getattr(self, "_tick_t", 0.0) + dt
                if self._tick_t > 0.07:
                    self._tick_t = 0.0
                    audio.play("reel")
            left = [i for i in range(3) if not self.stopped[i]]
            if left and min(self.vel[i] for i in left) < 3.0:  # a reel nobody stopped coasts to a halt
                self.stop_one()

    def draw(self, surf):
        dim(surf, 150)
        r = self.rect
        self.draw_header(surf, "Slot Machine - line up three of a kind")
        cw, ch, gap = 110, 150, 24
        row_w = cw * 3 + gap * 2
        x0, y0 = r.centerx - row_w // 2, r.y + 90
        for i in range(3):
            rect = pygame.Rect(x0 + i * (cw + gap), y0, cw, ch)
            panel(surf, rect, "inner", blur=False, shadow=False)
            if self.stopped[i]:
                cell = pygame.Rect(0, 0, cw - 16, ch - 16)
                cell.center = rect.center
                draw_symbol(surf, STRIP[self.pos[i]], cell)
                col = (110, 180, 110) if self.stopped[i] else (200, 200, 200)
            else:
                # while spinning: draw three strip cells scrolling through the window
                clip = surf.get_clip()
                surf.set_clip(rect.inflate(-8, -8))
                for k, off in ((0, -1.0), (1, 0.0), (2, 1.0)):
                    cell = pygame.Rect(0, 0, cw - 16, ch - 16)
                    cell.center = (rect.centerx, rect.centery + int(off * (ch - 8)))
                    draw_symbol(surf, STRIP[int(round(self.pos[i] + off)) % len(STRIP)], cell)
                surf.set_clip(clip)
                col = (222, 130, 48)
            if self.phase == "spin" and not self.stopped[i]:
                text(surf, "SPINNING", (rect.centerx, rect.bottom + 14), "ui", 11, col, anchor="midtop")
            elif self.phase != "idle":
                text(surf, "STOPPED" if self.stopped[i] else "READY", (rect.centerx, rect.bottom + 14), "ui", 11,
                     (90, 94, 90), anchor="midtop")
        y = y0 + ch + 44
        text(surf, "PAYS  7-7-7 x300   BOLT x50   STAR x30   ORB x12   LEAF x6   2 CHERRY x2   1 CHERRY x1",
             (r.centerx, y), "ui", 11, (110, 114, 118), anchor="midtop")
        for b in self.grid.buttons:
            from ui import draw_button
            draw_button(surf, b, size=13, kind="ui")
        self.draw_footer(surf)


class PokerScene(_CasinoScene):
    """Five-card draw, Jacks or better: bet, DEAL, hold your winners, DRAW, collect."""

    def __init__(self):
        super().__init__()
        self.bet_idx = 1
        self.phase = "bet"             # bet | draw | result
        self.hand = []
        self.hold = [False] * 5
        self.deck = []
        self.result = None             # (hand name, coins won)
        self.grid = ButtonGrid([], cols=5)
        self._rebuild()

    def bet(self):
        return SLOT_BETS[self.bet_idx]

    def _rebuild(self):
        r = self.rect
        btns = [
            Button(f"BET {self.bet()}", (r.x + 26, r.bottom - 92, 120, 38), tag="bet", enabled=self.phase != "draw"),
            Button("DEAL", (r.x + 156, r.bottom - 92, 120, 38), accent=self.phase == "bet", tag="deal",
                   enabled=self.phase == "bet"),
            Button("DRAW", (r.x + 286, r.bottom - 92, 120, 38), accent=self.phase == "draw", tag="draw",
                   enabled=self.phase == "draw"),
            Button("BUY 10 COINS", (r.x + 416, r.bottom - 92, 170, 38), tag="coins", enabled=self.phase != "draw"),
            Button("LEAVE", (r.right - 116, r.bottom - 92, 90, 38), tag="back"),
        ]
        self.grid.set_buttons(btns)

    def on_enter(self):
        self._rebuild()

    def deal(self):
        st = self.engine.state
        if st.coins < self.bet():
            self.say("Not enough coins! Buy some at the counter.", False)
            audio.play("deny")
            return
        st.coins -= self.bet()
        self.deck = new_deck()
        self.hand = [self.deck.pop() for _ in range(5)]
        self.hold = [False] * 5
        self.phase, self.result = "draw", None
        audio.play("select")
        self.say("Hold the cards you keep (click or SPACE), then DRAW.")
        self._rebuild()

    def toggle(self, i):
        if self.phase == "draw":
            self.hold[i] = not self.hold[i]
            audio.play("select")

    def draw_cards(self):
        for i in range(5):
            if not self.hold[i]:
                self.hand[i] = self.deck.pop()
        self.phase = "result"
        name, mult = score_hand(self.hand)
        won = mult * self.bet()
        st = self.engine.state
        if won:
            st.coins += won
            audio.play("jackpot" if mult >= 25 else "win")
            self.say(f"{name}! You win {won} coins!", True)
        else:
            audio.play("deny")
            self.say("No hand. Better luck on the draw.", False)
        self.result = (name, won)
        self._rebuild()

    def buy_coins(self):
        ok, msg = self.engine.state.buy_coins(10)
        self.say(msg, ok)
        audio.play("buy" if ok else "deny")

    def handle_event(self, e):
        if is_back(e):
            self.engine.pop(self)
            return
        if e.type == pygame.KEYDOWN and self.phase == "draw":
            for i, key in enumerate((pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)):
                if e.key == key:
                    self.toggle(i)
                    return
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and self.phase == "draw":
            for i, rect in enumerate(self._card_rects()):
                if rect.collidepoint(e.pos):
                    self.toggle(i)
                    return
        if is_confirm(e) and self.phase == "draw":
            self.draw_cards()
            return
        res = self.grid.handle(e)
        if not res:
            return
        kind, b = res
        if kind == "back":
            self.engine.pop(self)
        elif kind == "activate":
            {"bet": lambda: (self.cycle_bet(1), self._rebuild()), "deal": self.deal,
             "draw": self.draw_cards, "coins": self.buy_coins}[b.tag]()

    def _card_rects(self):
        r = self.rect
        cw, ch, gap = 120, 168, 18
        x0, y0 = r.centerx - (cw * 5 + gap * 4) // 2, r.y + 96
        return [pygame.Rect(x0 + i * (cw + gap), y0, cw, ch) for i in range(5)]

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        self.grid.update(dt)

    def draw(self, surf):
        dim(surf, 150)
        r = self.rect
        self.draw_header(surf, "Data Poker - five-card draw, Jacks or better")
        for i, rect in enumerate(self._card_rects()):
            held = self.hold[i]
            panel(surf, rect, "inner" if not held else "chip", blur=False, shadow=False)
            if self.hand and i < len(self.hand):
                rank, suit = card_label(self.hand[i])
                col = SUIT_COLOR[self.hand[i][1]]
                text(surf, rank, (rect.x + 12, rect.y + 10), "ui_b", 22, col)
                text(surf, {"S": "S", "H": "H", "D": "D", "C": "C"}[self.hand[i][1]], (rect.x + 12, rect.y + 38),
                     "ui_b", 16, col)
                big = {"S": "S", "H": "H", "D": "D", "C": "C"}[self.hand[i][1]]
                text(surf, big, (rect.right - 14, rect.bottom - 12), "ui_b", 40, col, anchor="bottomright")
                if held:
                    text(surf, "HOLD", rect.center, "ui_b", 15, (222, 168, 48), anchor="center")
            else:
                text(surf, "-", rect.center, "ui_b", 30, (160, 164, 168), anchor="center")
            if self.phase == "draw":
                text(surf, f"{i + 1}", (rect.centerx, rect.bottom + 14), "ui", 11, (90, 94, 90), anchor="midtop")
        # the paytable, the row for the current bet highlighted
        y0 = r.y + 96
        px = r.right - 190
        text(surf, "HAND            x", (px, y0 - 20), "ui_b", 12, INK, anchor="topleft")
        for k, (name, mult) in enumerate(POKER_PAYOUT):
            cur = self.result and self.result[0] == name
            text(surf, name.ljust(15) + str(mult), (px, y0 + k * 18), "ui", 12,
                 (222, 168, 48) if cur else ((90, 94, 90) if self.phase == "bet" else (110, 114, 118)),
                 anchor="topleft")
        for b in self.grid.buttons:
            from ui import draw_button
            draw_button(surf, b, size=13, kind="ui")
        self.draw_footer(surf)
