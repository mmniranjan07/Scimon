"""Headless Game Corner test: the coin economy (credits -> coins, no sell-back), the slot machine's
strip/payout balance (enumerated return rate in the house band), the poker hand evaluator (every hand
class, plus the A-low wheel) and both scenes' full interaction flows on a live engine."""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy"); os.environ.setdefault("SCIMON_NO_SAVE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init(); pygame.display.set_mode((960, 640))
random.seed(31)

import casino
from casino import STRIP, TRIPLE_PAYOUT, score_reels, score_hand, new_deck, card_label
from settings import COIN_PRICE, SLOT_BETS
from state import GameState

# ---- 1. the coin purse ------------------------------------------------------------------------------
st = GameState()
st.credits = 1000
ok, msg = st.buy_coins(10)
assert ok and st.coins == 10 and st.credits == 1000 - 10 * COIN_PRICE, (st.coins, st.credits)
st.credits = 5
ok, _ = st.buy_coins(1)
assert not ok and st.coins == 10, "coins must cost credits"

# ---- 2. the slot strip: enumerated return rate -------------------------------------------------------
ev = sum(score_reels((a, b, c), 1)[0] for a in STRIP for b in STRIP for c in STRIP) / len(STRIP) ** 3
assert 0.85 <= ev <= 1.10, f"slot return {ev:.3f} outside the house band"
assert score_reels(("seven", "seven", "seven"), 10)[0] == 3000
assert score_reels(("bolt", "bolt", "bolt"), 3)[0] == 150
assert score_reels(("cherry", "cherry", "leaf"), 3)[0] == 6
assert score_reels(("cherry", "leaf", "leaf"), 3)[0] == 3
assert score_reels(("leaf", "leaf", "orb"), 3)[0] == 0

# ---- 3. the poker evaluator ---------------------------------------------------------------------------
assert score_hand(["TS", "JS", "QS", "KS", "AS"]) == ("Royal Flush", 250)
assert score_hand(["9H", "TH", "JH", "QH", "KH"]) == ("Straight Flush", 50)
assert score_hand(["5H", "5D", "5S", "5C", "2H"]) == ("Four of a Kind", 25)
assert score_hand(["5H", "5D", "5S", "2C", "2H"]) == ("Full House", 9)
assert score_hand(["2H", "4H", "7H", "9H", "KH"]) == ("Flush", 6)
assert score_hand(["2H", "3S", "4D", "5C", "AH"]) == ("Straight", 4)      # the wheel
assert score_hand(["2H", "3H", "4S", "5D", "6C"]) == ("Straight", 4)
assert score_hand(["JH", "JS", "4D", "7C", "9H"]) == ("Jacks or Better", 1)
assert score_hand(["TH", "TS", "4D", "7C", "9H"]) == ("", 0)              # tens do not pay
assert score_hand(["2H", "2S", "7D", "7C", "9H"]) == ("Two Pair", 2)
assert score_hand(["2H", "4H", "7S", "9D", "KH"]) == ("", 0)
assert len(new_deck()) == 52 and len(set(new_deck())) == 52
assert card_label("TH") == ("10", "hearts") and card_label("AS") == ("Ace", "spades")

# ---- 4. both scenes live: full flows on an engine -----------------------------------------------------
import engine as eng
engine = eng.Engine(headless=True)
engine.state = st
st.credits = 1000
st.coins = 0

# slots: buy coins, set the bet, spin, stop all three reels
slot = casino.SlotScene()
slot.engine = engine
slot.on_enter()
ok, msg = st.buy_coins(10)
assert st.coins == 10 and st.credits == 1000 - 10 * COIN_PRICE
slot.spin()
assert slot.phase == "spin" and st.coins == 9, "spin must charge the bet"
for _ in range(3):
    slot.stop_one()
assert slot.phase == "done" and all(slot.stopped)
won = slot.result[0]
assert st.coins == 9 + won, (st.coins, won)
symbols = tuple(STRIP[p] for p in slot.pos)
assert won == score_reels(symbols, 1)[0]
slot.spin()
slot.stop_one()
for _ in range(6):
    slot.update(99.0)                   # nobody stops the rest: the reels coast to a halt themselves
assert slot.phase == "done", "unstopped reels must auto-stop"
won2 = slot.result[0]
assert st.coins == 9 + won - 1 + won2

# poker: deal, hold two cards, draw, collect
poker = casino.PokerScene()
poker.engine = engine
poker.on_enter()
poker.bet_idx = 0
poker.deal()
assert poker.phase == "draw" and len(poker.hand) == 5 and st.coins == 8 + won + won2 - 1
keep = poker.hand[:2]
poker.hold = [True, True, False, False, False]
poker.draw_cards()
assert poker.phase == "result" and poker.hand[:2] == keep and poker.hand[2:] != []
name, mult = score_hand(poker.hand)
assert poker.result == (name, mult * 1)
assert st.coins == 7 + won + won2 + mult

# the scenes dismiss (LEAVE) without breaking the engine
slot.engine.pop(slot)
poker.engine.pop(poker)
assert engine.top is not slot and engine.top is not poker

print("OK casino: coins, slot balance + skill stop + auto-stop, poker hands + draw flow, scene flows")
