"""Global game data singleton (party, storage, bag, credits, Sci-Dex) and every operation on it.

Port of V34's inventory section of engine.ts. Operations return (ok, message) so any UI -- the
pack, the in-world Sci-Database terminal, the shop -- reports results the same way."""
from data import (CATALOG, MODULES, ITEMS, SPECIES_COUNT, STARTING_CREDITS, sell_price, item_name, TECHNIQUES)
from monsters import PARTY_LIMIT, Scimon

BOX_COLS, BOX_ROWS = 6, 5
BOX_SIZE = BOX_COLS * BOX_ROWS
BOX_COUNT = 8                         # the Sci-Database always has this many boxes, empty or not

# The trainer profile's stamp case: one slot per gym in the league.  A gym leader hands over their stamp the
# first time they are beaten (their NPC carries `stamp`: worldmap._trainer(stamp=...) -> overworld awards it).
# Gyms that don't exist yet keep id=None so their slot shows as an undiscovered "???".
GYM_STAMPS = (
    dict(id="green", name="Green Stamp", gym="Green Gym", leader="Fern", color=(110, 190, 90)),
    dict(id=None, name="???", gym="???", leader="???", color=(150, 152, 150)),
    dict(id=None, name="???", gym="???", leader="???", color=(150, 152, 150)),
    dict(id=None, name="???", gym="???", leader="???", color=(150, 152, 150)),
    dict(id=None, name="???", gym="???", leader="???", color=(150, 152, 150)),
    dict(id=None, name="???", gym="???", leader="???", color=(150, 152, 150)),
    dict(id=None, name="???", gym="???", leader="???", color=(150, 152, 150)),
    dict(id=None, name="???", gym="???", leader="???", color=(150, 152, 150)),
)


def stamp_by_id(gym_id):
    return next((d for d in GYM_STAMPS if d["id"] == gym_id), None)


def playtime_str(seconds):
    """Compact clock, e.g. 3h 07m or 12m 05s."""
    s = int(seconds)
    if s >= 3600:
        return f"{s // 3600}h {s % 3600 // 60:02d}m"
    return f"{s // 60}m {s % 60:02d}s"


# Everything the player starts with, keyed by catalogue id (V34 INITIAL_ITEMS).
INITIAL_ITEMS = {
    "repaircell": 5, "nanorepair": 2, "stabilizer": 3,
    "standard": 15, "cryo": 3, "bio": 3,
    "thermalcore": 1, "plating": 1, "scanner": 1, "townpass": 1,
}


class GameState:
    """Mutable save-game-shaped container. One instance lives on the Engine (`engine.state`)."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.party = []                      # list[Scimon], max PARTY_LIMIT
        self.storage = []                    # Sci-Database
        self.items = {k: v for k, v in INITIAL_ITEMS.items()}
        self.credits = STARTING_CREDITS
        self.captured = set()                # species ids for the Sci-Dex
        self.rival_species = None
        self.intro_done = False
        self.rival_beaten = False
        self.opened_chests = set()           # keys of loot chests already opened (layered_room.Chest)
        self.visited_healers = set()         # healer ids the player has used: a wipe returns you to the nearest one
        self.visited_areas = set()           # areas the player has set foot in: a wipe never sends you forward
        self.beaten_trainers = set()         # trainer npc ids already defeated (no rematch, no more line of sight)
        self.location = {}                   # where the player stands: {"area"|"building", "tile": [x, y], "facing"}
        self.name = "Robin"                  # chosen on the New Game character-customization screen
        self.look = None                     # player look code (sprites.make_look); None = the default look
        self.stamps = set()                  # gym stamps earned (ids into GYM_STAMPS)
        self.playtime = 0.0                  # seconds of play, ticked by Engine.step

    # ---- trainer profile ------------------------------------------------------------------
    def award_stamp(self, gym_id):
        """Record a gym stamp the first time its leader is beaten. Returns the stamp def or None."""
        d = stamp_by_id(gym_id)
        if not d or gym_id in self.stamps:
            return None
        self.stamps.add(gym_id)
        return d


    # ---- bag ----------------------------------------------------------------------
    def qty(self, item_id):
        return self.items.get(item_id, 0)

    def add_item(self, item_id, n=1):
        if n > 0:
            self.items[item_id] = self.qty(item_id) + n

    def remove_item(self, item_id, n=1):
        have = self.qty(item_id)
        if have <= 0:
            return
        left = have - min(n, have)
        if left > 0:
            self.items[item_id] = left
        else:
            self.items.pop(item_id, None)

    def add_credits(self, delta):
        self.credits = max(0, self.credits + delta)

    def items_in_category(self, category):
        rows = [(i, q) for i, q in self.items.items() if q > 0 and CATALOG.get(i) and CATALOG[i].category == category]
        rows.sort(key=lambda r: CATALOG[r[0]].name)
        return rows

    # ---- battle <-> bag projection (V34 battleBag / battleModules / mergeBattleResult) ----
    def battle_bag(self):
        return dict(self.items_in_category("consumable"))

    def battle_modules(self):
        return dict(self.items_in_category("module"))

    def merge_battle_result(self, bag, modules):
        for i in [i for i in self.items if CATALOG.get(i) and CATALOG[i].category in ("consumable", "module")]:
            del self.items[i]
        for i, q in {**bag, **modules}.items():
            if q > 0:
                self.items[i] = q

    # ---- finding Sci-Mons -------------------------------------------------------------
    def find(self, uid):
        for m in self.party:
            if m.uid == uid:
                return m, "party"
        for m in self.storage:
            if m.uid == uid:
                return m, "storage"
        return None, None

    # ---- commerce ---------------------------------------------------------------------
    def buy(self, item_id, price, qty=1):
        cost = price * qty
        if self.credits < cost:
            return False, "Not enough credits!"
        self.add_credits(-cost)
        self.add_item(item_id, qty)
        return True, f"Bought {qty}x - \u00a2{cost}"

    def sell(self, item_id, qty=1):
        d = CATALOG.get(item_id)
        if d and d.permanent:
            return False, f"{d.name} can't be sold."
        n = min(qty, self.qty(item_id))
        if n <= 0:
            return False, "Nothing to sell."
        gain = sell_price(item_id) * n
        self.remove_item(item_id, n)
        self.add_credits(gain)
        return True, f"Sold {n}x - +\u00a2{gain}"

    # ---- party / healing ----------------------------------------------------------------
    def heal_party(self):
        for m in self.party:
            m.heal_full()

    def receive_scimon(self, mon):
        self.captured.add(mon.species_id)
        if len(self.party) < PARTY_LIMIT:
            self.party.append(mon)
            return f"{mon.name} joined your team!"
        self.storage.append(mon)
        return f"{mon.name} was stored in your Sci-Database."

    def reorder_party(self, frm, to):
        n = len(self.party)
        if frm == to or not (0 <= frm < n and 0 <= to < n):
            return False, ""
        mon = self.party.pop(frm)
        self.party.insert(to, mon)
        return True, ""

    def send_to_storage(self, uid, box=None):
        idx = next((i for i, m in enumerate(self.party) if m.uid == uid), -1)
        if idx < 0:
            return False, "Not in your party."
        if len(self.party) <= 1:
            return False, "You must keep at least one Sci-Mon."
        mon = self.party.pop(idx)
        pos = len(self.storage)
        if box is not None and box * BOX_SIZE < len(self.storage):
            cells = {i % BOX_SIZE for i in range(box * BOX_SIZE, min((box + 1) * BOX_SIZE, len(self.storage)))}
            pos = box * BOX_SIZE + next(c for c in range(BOX_SIZE) if c not in cells)
        self.storage.insert(pos, mon)
        return True, f"{mon.name} was sent to the Sci-Database."

    def withdraw(self, uid):
        idx = next((i for i, m in enumerate(self.storage) if m.uid == uid), -1)
        if idx < 0:
            return False, "Not in storage."
        if len(self.party) >= PARTY_LIMIT:
            return False, "Your party is full."
        mon = self.storage.pop(idx)
        self.party.append(mon)
        return True, f"{mon.name} joined your party."

    # ---- using / holding items ------------------------------------------------------------
    def use_item(self, item_id, uid):
        d = CATALOG.get(item_id)
        if not d:
            return False, "Unknown item."
        if self.qty(item_id) <= 0:
            return False, f"You're out of {d.name}."
        target, _ = self.find(uid)
        if not target:
            return False, "That Sci-Mon isn't available."
        if d.category != "consumable":
            return False, f"{d.name} can't be used that way."

        changed, notes = False, []
        if d.revive and target.hp <= 0:
            target.hp = max(1, int(target.max_hp * d.revive))
            target.status = None
            changed = True
            notes.append("came back online")
        if d.heal and target.hp > 0:
            if target.hp >= target.max_hp:
                if not changed:
                    return False, f"{target.name} is already at full integrity."
            else:
                before = target.hp
                target.hp = min(target.max_hp, target.hp + d.heal)
                changed = True
                notes.append(f"recovered {target.hp - before} HP")
        elif d.heal and target.hp <= 0:
            return False, f"{target.name} is offline - it needs reviving first."
        if d.restore_stability:
            if target.stability < target.max_stability or target.status is not None:
                target.stability, target.status = target.max_stability, None
                changed = True
                notes.append("stabilized")
            elif not changed:
                return False, f"{target.name} is already stable."
        if d.cure and target.status is not None:
            target.status = None
            changed = True
            notes.append("faults cleared")
        if not changed:
            return False, f"It would have no effect on {target.name}."
        self.remove_item(item_id, 1)
        return True, f"{target.name} {', '.join(notes)}."

    def give_held(self, item_id, uid):
        d = CATALOG.get(item_id)
        if not d:
            return False, "Unknown item."
        if d.category != "held":
            return False, f"{d.name} can't be held."
        if self.qty(item_id) <= 0:
            return False, f"You have no {d.name}."
        target, _ = self.find(uid)
        if not target:
            return False, "That Sci-Mon isn't available."
        if target.held_item == item_id:
            return False, f"{target.name} is already holding that."
        self.remove_item(item_id, 1)
        msg = f"{target.name} is now holding {d.name}."
        if target.held_item:
            old = CATALOG.get(target.held_item)
            self.add_item(target.held_item, 1)
            msg = f"Swapped {old.name if old else 'the old item'} for {d.name}."
        target.held_item = item_id
        return True, msg

    def take_held(self, uid):
        target, _ = self.find(uid)
        if not target:
            return False, "That Sci-Mon isn't available."
        if not target.held_item:
            return False, f"{target.name} isn't holding anything."
        d = CATALOG.get(target.held_item)
        self.add_item(target.held_item, 1)
        target.held_item = None
        return True, f"Took {d.name if d else 'the item'} from {target.name}."

    def teach_move(self, item_id, uid, forget=None):
        """Play a move disc on a party Sci-Mon. The disc's technique is disc-only: it never comes from a
        learnset or a level-up, so this is the only way a Sci-Mon ever learns it. `forget` names the move to
        replace when the target already knows four techniques (the Pack asks which one first)."""
        d = CATALOG.get(item_id)
        if not d or d.category != "disc" or not d.move:
            return False, "That isn't a move disc."
        if self.qty(item_id) <= 0:
            return False, f"You have no {d.name}."
        target, loc = self.find(uid)
        if not target or loc != "party":
            return False, "Discs can only be played on your party."
        tech = TECHNIQUES[d.move]
        if d.compat_types and not (set(target.types) & set(d.compat_types)):
            return False, f"{target.name} is not compatible with {tech.name}."
        if d.move in target.moves:
            return False, f"{target.name} already knows {tech.name}."
        if forget is not None:
            if forget not in target.moves:
                return False, "That isn't one of its techniques."
            target.moves[target.moves.index(forget)] = d.move
        elif len(target.moves) >= 4:
            return False, f"{target.name} already knows 4 techniques - forget one first."
        else:
            target.moves.append(d.move)
        self.remove_item(item_id, 1)
        return True, f"{target.name} learned {tech.name}!"

    def discard(self, item_id, qty=1):
        d = CATALOG.get(item_id)
        if not d:
            return False, "Unknown item."
        if d.permanent:
            return False, f"{d.name} can't be discarded."
        if self.qty(item_id) <= 0:
            return False, f"No {d.name} to discard."
        self.remove_item(item_id, qty)
        return True, f"Discarded {d.name}."

    @property
    def dex_progress(self):
        return len(self.captured), SPECIES_COUNT
