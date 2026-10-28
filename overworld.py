"""The exploration state: Riven Town plus every interior, with grid movement, NPC talk, shops, repair, the
Sci-Database terminal, doors and tall-grass encounters. Port of V34's overworld.tsx game logic."""
import math
import random

import pygame

import audio
import abilities
import encounters
import villain
from battle import BG_FOR_AREA, BattleScene, new_battle
from data import KAEL_RETEAM2, SPECIES_COUNT, item_def
from engine import Scene, StateId
from map import Camera, TileMap
from menus import DatabaseScene, HelpScene, InventoryScene, ShopScene
from monsters import PARTY_LIMIT, check_evolutions, create_scimon
from routes import AREAS, HEALERS, LINKS, ROUTE1_START, TOWN, building_at, travel_cost, zone_at
from sprites import black_look

_contact = None


def _contact_shadow():
    """One cached soft ellipse shared by every character: grounds the sprites without per-frame surface churn."""
    global _contact
    if _contact is None:
        _contact = pygame.Surface((34, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(_contact, (10, 22, 18, 70), _contact.get_rect())
    return _contact
from scenes import DialogueScene
from settings import ENCOUNTER_CHANCE, H, INK, TILE, W
from sprites import DIRS, NPC, Player, look_animator, look_for
import touch
from ui import is_click, is_confirm, label_chip, panel, render_text, text
from worldmap import PLAYER_START, building_at_door, BUILDINGS


def pick_encounter(state, area, tile):
    """One triggered wild encounter at a concrete tile of an outdoor area: the tile's zone (routes.zone_at)
    decides the habitat; encounters.select_encounter applies the branch/stage/family/level policy.  A tile
    outside every zone (or a zone with no eligible pool) yields None -- there is no legacy fallback."""
    zone = zone_at(area, *tile) if (area and tile) else None
    return encounters.select_encounter(state, zone)


_OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
LOS_RANGE = 3                             # trainers spot the player up to this many tiles ahead
BUILDINGS_ALL = {b.id: b for b in BUILDINGS}          # town + Epidimy interiors, for the saved location
for _a in AREAS.values():
    BUILDINGS_ALL.update({b.id: b for b in _a.buildings})
AREA_STARTS = {TOWN: PLAYER_START, **{a.id: a.start for a in AREAS.values()}}   # safe fallback spots


class OverworldScene(Scene):
    state_id = StateId.OVERWORLD
    background_update = True

    def __init__(self):
        self.maps = {}
        self.map = self._get_map(None)
        self.building = None
        self.player = Player(*PLAYER_START)
        self.camera = Camera()
        self.npcs = pygame.sprite.Group()
        self.t = 0.0
        self._load_npcs()
        self.approacher = None            # trainer currently walking up to the player
        self._fighting = None             # trainer npc whose battle is in progress
        self.pack_rect = pygame.Rect(0, 0, 0, 0)
        self.help_rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self):
        look = getattr(self.engine.state, "look", None) if self.engine is not None else None
        if look and look != self.player.look:             # apply the look chosen on the customization screen
            self.player.look = look
            self.player.anim = look_animator(look)
            self.player.refresh()
        self._restore_location()                          # CONTINUE: back to the saved spot

    # ---- saved location ------------------------------------------------------------------
    def _sync_location(self):
        """Keep GameState.location current so the autosave stores where the player stands."""
        where = {"building": self.building.id} if self.building else {"area": getattr(self.map, "area", TOWN)}
        where.update(tile=list(self.player.tile), facing=self.player.facing)
        st = self.engine.state
        st.location = where
        st.visited_areas.add(self.building.area if self.building else getattr(self.map, "area", TOWN))

    def _free(self, tx, ty):
        """A tile the player may be restored onto: inside the map, walkable, nobody standing there."""
        return (not self.map.is_solid(tx, ty)) and self.npc_at(tx, ty) is None

    def _restore_location(self):
        """CONTINUE: put the player back where the save found them (bad data falls back to the town start)."""
        loc = getattr(self.engine.state, "location", None) or {}
        tile = loc.get("tile")
        tile = (int(tile[0]), int(tile[1])) if isinstance(tile, (list, tuple)) and len(tile) == 2 else None
        facing = loc.get("facing") if loc.get("facing") in DIRS else None
        b = BUILDINGS_ALL.get(loc.get("building")) if isinstance(loc.get("building"), str) else None
        if b is not None:                                 # resume inside a building
            self.building = b
            self.map = self._get_map(b)
            self._load_npcs()
            spot = tile if tile and self._free(*tile) else b.interior.spawn
            self.player.place(*spot, facing or "up")
            self.map.sync_state(self.engine.state)
        else:
            area = loc.get("area") if loc.get("area") in AREAS or loc.get("area") == TOWN else TOWN
            self.map = self._get_map(None, area)
            self._load_npcs()
            spot = tile if tile and self._free(*tile) else AREA_STARTS.get(area, PLAYER_START)
            self.player.place(*spot, facing or "down")
            self.map.sync_state(self.engine.state)        # outdoor loot chests reopen/save correctly
        self._sync_location()

    # ---- maps ------------------------------------------------------------------------
    def _get_map(self, b, area=TOWN):
        """The town (default), a route (`area`), or a building's interior (`b`); each is built once and cached."""
        key = b.id if b else area
        if key not in self.maps:
            if b:
                self.maps[key] = TileMap.interior(b)
            else:
                self.maps[key] = TileMap.overworld() if area == TOWN else TileMap.route(area)
        return self.maps[key]

    def _load_npcs(self):
        self.npcs.empty()
        st = self.engine.state if self.engine is not None else None
        if st and "boss_beaten" in getattr(st, "story", set()) and self.building and self.building.repairs:
            self.map.npc_defs = [self._kael_def(d) if d.get("service") == "repair" else d for d in self.map.npc_defs]
        for d in self.map.npc_defs:
            n = NPC(d)
            if n.trainer_battle and n.aside and n.id in self.engine.state.beaten_trainers:
                n.place(*n.aside)                          # a beaten gate guard waits out of the corridor
            self.npcs.add(n)

    def _npc_rects(self):
        return [pygame.Rect(n.tile[0] * TILE, n.tile[1] * TILE, TILE, TILE) for n in self.npcs]

    def npc_at(self, x, y):
        return next((n for n in self.npcs if n.tile == (x, y)), None)

    def enter_building(self, b):
        if b.repairs:                                     # walked into a healer's nook: remember it for blackouts
            self.engine.state.visited_healers.add(b.id)

        def apply():
            self.building = b
            self.map = self._get_map(b)
            self._load_npcs()
            self.player.place(*b.interior.spawn, "up")
            self.map.sync_state(self.engine.state)
            self._sync_location()
            st = self.engine.state
            if b.id == villain.REVEAL_BUILDING:
                if self._reveal_ready():
                    self._start_reveal()              # the finish is staged in the Epidimy nook
                elif "exposed" in st.story and "boss_beaten" not in st.story:
                    self.engine.push(DialogueScene(
                        ["Cush: Back so soon? The back room is open, kid - let's finish this.",
                         "Cush: Send out your Sci-Mon!"], on_done=self._start_boss_battle))
        audio.play("door")
        self.engine.fade_to(apply)

    def exit_building(self):
        b = self.building

        def apply():
            self.building = None
            self.map = self._get_map(None, b.area)           # back to the outdoor map the door is on (town or Epidimy)
            self._load_npcs()
            self.player.place(*b.entry_return, "down")
            self._sync_location()
        audio.play("door")
        self.engine.fade_to(apply)

    def travel(self, link):
        """Walk from one outdoor area to another (town <-> Route 1 <-> the wider network) through a link tile."""
        area, (tx, ty), facing = link

        def apply():
            self.map = self._get_map(None, area)
            self._load_npcs()
            self.player.place(tx, ty, facing)
            self.map.sync_state(self.engine.state)        # outdoor loot chests reopen where they were left
            self._sync_location()
        self.engine.fade_to(apply)

    # ---- interaction -------------------------------------------------------------------
    def interact(self):
        p, m = self.player, self.map
        dx, dy = DIRS[p.facing]
        fx, fy = p.tile[0] + dx, p.tile[1] + dy
        if m.is_terminal(fx, fy) and self.building:
            if self.engine.state.snatched:
                self._recover_snatched()                  # the Bandits' haul sits in Cush's own database
                return
            self.engine.push(DatabaseScene())
            return
        sign = m.sign_at(fx, fy) if not self.building else None      # signposts (the plaza's, Route 1's)
        if sign:
            audio.play("select")
            self.engine.push(DialogueScene(list(sign)))
            return
        obj = m.interactable_at(fx, fy)                              # loot chests etc.
        if obj:
            lines = obj.interact(self.engine.state)
            if lines:
                audio.play("select")
                self.engine.push(DialogueScene(lines))
                return
        npc = self.npc_at(fx, fy)
        if not npc and m.is_counter(fx, fy):
            bx, by = fx + dx, fy + dy
            npc = self.npc_at(bx, by) or (self.npc_at(bx, by - 1) or self.npc_at(bx, by + 1) if dx else
                                          self.npc_at(bx - 1, by) or self.npc_at(bx + 1, by))
        if npc:
            npc.face(_OPPOSITE[p.facing])
            audio.play("select")
            if npc.trainer_battle and npc.id in self.engine.state.beaten_trainers:
                if npc.rematch:                           # a beaten rematchable trainer offers a new battle
                    self._offer_rematch(npc)
                else:
                    self.engine.push(DialogueScene(list(npc.post) or list(npc.lines)))
            elif npc.trainer_battle:
                self._challenge(npc)                      # challenge by talking (gated leaders refuse here)
            elif npc.service and not self._pass_ok():
                need = getattr(self.building, "pass_item", "townpass") if self.building else "townpass"
                d = item_def(need)
                self.engine.push(DialogueScene([          # pass barrier: Mart / Cush serve pass holders only
                    f"{npc.name}: Terribly sorry - services here are for {d.name} holders only.",
                    f"{npc.name}: The Town Hall issues them. Do visit the Mayor!"]))
            else:
                st = self.engine.state
                lines = list(npc.lines)
                if npc.service == "repair" and st.snatched:
                    lines.append(villain.SNATCH_HINT)     # a quiet clue while a Sci-Mon is still missing
                if npc.gives and not st.qty(npc.gives):   # first talk: the hall hands over the Town Pass
                    lines += [f"{npc.name}: Oh, one more thing - every researcher needs a Town Pass.",
                              f"{npc.name}: Here you go. This opens all of the town's services for you."]
                self.engine.push(DialogueScene(lines, on_done=lambda n=npc: self._after_talk(n)))

    def _pass_ok(self):
        """Mart / repair counters are pass-gated where the town asks for one: the building's `pass_item`
        (Riven -> townpass, Epidimy -> epipass); towns of the wider network serve every traveler."""
        need = getattr(self.building, "pass_item", None) if self.building else \
            ("epipass" if getattr(self.map, "area", TOWN) == "epidimy" else "townpass")
        return True if not need else bool(self.engine.state.qty(need))

    def _offer_rematch(self, n):
        ask = list(n.rematch_ask) or [f"{n.name}: Another battle, {self.engine.state.name}?"]
        choices = [("BATTLE!", lambda nn=n: self._trainer_battle(nn)), ("NOT NOW", None)]
        if getattr(n, "service", None) == "repair":       # the nook's new owner still repairs, even mid-rivalry
            choices.insert(1, ("REPAIR", self._repair))
        self.engine.push(DialogueScene(ask, choices=choices))

    def _after_talk(self, npc):
        st = self.engine.state
        if npc.gives and not st.qty(npc.gives):
            st.add_item(npc.gives, 1)
            audio.play("heal")
            self.engine.toast.show(f"{item_def(npc.gives).name} added to your Key Items.", 2.6)
        if npc.heals:
            st.heal_party()
            audio.play("heal")
            self.engine.toast.show("Scimons restored!", 1.8)
            if not self.building:                         # outdoor healer (Prof. Venn): talking counts as a visit
                st.visited_healers.add(npc.id)
        b = self.building
        if not b:
            return
        if npc.service == "shop":
            self.engine.push(ShopScene(b))
        elif npc.service == "repair":
            ask = [f"{npc.name}: Shall I repair your Sci-Mons? Free of charge!"]
            self.engine.push(DialogueScene(ask, choices=[("YES, PLEASE!", self._repair), ("NO, THANKS", None)]))

    def _repair(self):
        self.engine.state.heal_party()
        audio.play("heal")
        self.engine.toast.show("All Scimons fully restored!", 2.0)

    def open_pack(self):
        self.engine.push(InventoryScene())

    # ---- battles ----------------------------------------------------------------------------
    def start_wild_battle(self, species_id, level):
        st = self.engine.state
        enemy = create_scimon(species_id, level)
        b = new_battle(st.party, enemy, st.battle_bag(), st.battle_modules())
        scene = BattleScene(b, self.end_wild_battle, bg=BG_FOR_AREA.get(getattr(self.map, "area", "overworld"), 1))
        audio.play("capture")
        self.engine.fade_to(lambda: self.engine.push(scene), color=(255, 255, 255))

    def _evolution_lines(self):
        """Apply pending evolutions after a battle's level-ups; returns the announcement lines."""
        lines = []
        for mon, old, new in check_evolutions(self.engine.state.party):
            self.engine.state.mark_seen(mon.species_id)   # the dex records the newly obtained form
            lines += [f"{old} is evolving!", f"Congratulations! Your {old} evolved into {new}!"]
            audio.play("heal")
        return lines

    def end_wild_battle(self, res):
        st = self.engine.state
        st.merge_battle_result(res["bag"], res["modules"])
        st.party = res["party"]
        out = res["outcome"]
        if out == "lose":
            st.heal_party()
            healer = self._nearest_visited_healer()
            if healer:                                    # a wipe sends you back to the last healer you used (or the nearest one behind you)
                self._blackout_to(healer)
            else:
                self.engine.toast.show("Your team was knocked offline... systems restored.", 3.0)
        elif out == "caught" and res["caught"]:
            self.engine.toast.show(st.receive_scimon(res["caught"]), 2.6)
            if len(st.captured) >= SPECIES_COUNT:
                self.engine.toast.show("You completed the Sci-Dex! Congratulations, Researcher!", 4.0)
        evo = self._evolution_lines()
        if evo:
            self.engine.push(DialogueScene(evo))

    def _nearest_visited_healer(self):
        """The healer the player has used that is closest to where they stand now.  Failsafes keep a wipe from
        stranding the player or skipping them ahead: if they never used a healer, the nearest one in an area
        they have already been through is returned (never one up ahead); a fresh save falls back to the start
        town, which is always behind the player."""
        st = self.engine.state
        candidates = [h for h in HEALERS if h["id"] in st.visited_healers]
        if not candidates:
            candidates = [h for h in HEALERS if h["area"] in st.visited_areas]
        if not candidates:
            candidates = [h for h in HEALERS if h["area"] == TOWN] or HEALERS
        area = self.building.area if self.building else getattr(self.map, "area", TOWN)
        tile = self.player.tile

        def cost(h):
            c = travel_cost(area, tile, h["area"], h["tile"])
            return (math.inf if c is None else c, h["id"])
        return min(candidates, key=cost)

    def _blackout_to(self, healer):
        """Set the player down by the healer.  Runs inside the battle-exit fade, so the swap is never seen."""
        self.building = None
        self.map = self._get_map(None, healer["area"])
        self._load_npcs()
        self.player.place(*healer["tile"], healer["facing"])
        self.map.sync_state(self.engine.state)
        self._sync_location()
        self.engine.toast.show(f"Your team was knocked offline... You hurried back to {healer['name']}.", 3.2)

    # ---- trainers: idle scan, line of sight, approach ------------------------------------------
    def _trainers_think(self, dt):
        """Undefeated trainers turn their heads at random; the player stepping into the 3-tile line of
        sight freezes them in place while the trainer walks up and starts a battle."""
        if self.approacher or self.engine.transitioning or self.engine.top is not self:
            return
        for n in self.npcs:
            if not n.trainer_battle or n.id in self.engine.state.beaten_trainers:
                continue
            if [r for r in n.requires if r not in self.engine.state.beaten_trainers]:
                continue              # gated (the gym leader behind her coaches): she waits, she doesn't scan
            n.scan_t -= dt
            if n.scan_t <= 0:
                n.scan_t = random.uniform(1.4, 2.8)
                n.face(random.choice(("up", "down", "left", "right")))
            if self._spotted(n):
                audio.play("select")
                self.approacher = n
                return

    def _spotted(self, n):
        """True when the player stands in the trainer's line of sight (walls and other people block it)."""
        dx, dy = DIRS[n.facing]
        for step in range(1, LOS_RANGE + 1):
            tx, ty = n.tile[0] + dx * step, n.tile[1] + dy * step
            if (tx, ty) == self.player.tile:
                return True
            if self.map.is_solid(tx, ty) or self.npc_at(tx, ty):
                return False
        return False

    def _approach_step(self, dt):
        """Walk the spotting trainer toward the frozen player, then start the confrontation dialogue."""
        n = self.approacher
        if n is None or n.moving or self.player.moving or self.engine.transitioning or self.engine.top is not self:
            return
        dx, dy = self.player.tile[0] - n.tile[0], self.player.tile[1] - n.tile[1]
        dist = abs(dx) + abs(dy)
        if dist <= 1:                                     # side by side: face each other and talk
            n.face("right" if dx > 0 else "left" if dx < 0 else "down" if dy > 0 else "up")
            self.player.facing = _OPPOSITE[n.facing]
            self.player.refresh()
            self._confront(n)
            return
        d = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) and dx else ("down" if dy > 0 else "up")
        tx, ty = n.tile[0] + DIRS[d][0], n.tile[1] + DIRS[d][1]
        if self.map.is_solid(tx, ty) or self.npc_at(tx, ty):
            self.approacher = None                        # can't get closer (shouldn't happen within 3 tiles)
            return
        n.begin_step(d)

    def _confront(self, n):
        self._challenge(n)

    def _challenge(self, n):
        """Challenge a trainer (spotted or talked to): while `requires` isn't cleared the trainer refuses
        (gym leader behind her coaches), otherwise the intro dialogue leads into the battle."""
        missing = [r for r in n.requires if r not in self.engine.state.beaten_trainers]
        audio.play("select")
        if missing:
            self.approacher = None           # never trap the player in a refusal loop
            lines = list(n.locked_lines) or [f"{n.name}: Not yet! Beat my gym trainers first - all of them."]
            self.engine.push(DialogueScene(lines))
            return
        self.engine.push(DialogueScene(list(n.lines), on_done=lambda nn=n: self._trainer_battle(nn)))

    def _trainer_battle(self, n):
        self.approacher = None
        self._fighting = n
        st = self.engine.state
        tb = n.trainer_battle
        enemy = [create_scimon(sid, lv) for sid, lv in tb] if isinstance(tb, list) else create_scimon(*tb)
        b = new_battle(st.party, enemy, st.battle_bag(), st.battle_modules(), trainer=n.name)
        bg = BG_FOR_AREA.get(getattr(self.map, "area", "overworld"), 1)

        def apply():
            self.engine.push(BattleScene(b, self.end_trainer_battle, allow_capture=False, allow_run=False, bg=bg))
        self.engine.fade_to(apply, color=(255, 255, 255))

    def end_trainer_battle(self, res):
        st = self.engine.state
        st.merge_battle_result(res["bag"], res["modules"])
        st.party = res["party"]
        n, self._fighting = self._fighting, None
        if res["outcome"] == "lose":
            st.heal_party()
            healer = self._nearest_visited_healer()
            if healer:
                self._blackout_to(healer)
            else:
                self.engine.toast.show("Your team was knocked offline... systems restored.", 3.0)
            return
        if n:
            st.beaten_trainers.add(n.id)
            post = self._evolution_lines() + list(n.post)
            if n.stamp:
                d = st.award_stamp(n.stamp)
                if d:
                    post = post + [f"You received the {d['name']} from {d['leader']}!", "It has been added to the stamp case in your Pack."]
            if getattr(n, "disc", None):
                dd = item_def(n.disc)
                if dd:
                    st.add_item(n.disc, 1)
                    post.append(f"They also handed you the {dd.name} - play it on a compatible Sci-Mon to teach its move!")
            if n.aside and n.tile != tuple(n.aside):
                n.place(*n.aside)                          # step out of the gate so the way opens
            if post:
                self.engine.push(DialogueScene(post))

    # ---- events / update --------------------------------------------------------------------
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_i, pygame.K_TAB, pygame.K_ESCAPE):
                self.open_pack()
                return
            if e.key == pygame.K_h:
                self.open_help()
                return
            if e.key == pygame.K_f and abilities.can_use(self.engine.state, "aerolift"):
                self.open_fly()
                return
        if is_confirm(e):
            if not self.player.moving:
                self.interact()
        elif is_click(e):
            if self.pack_rect.collidepoint(e.pos):
                self.open_pack()
            elif self.help_rect.collidepoint(e.pos):
                self.open_help()

    def open_fly(self):
        """Aerolift: fast-travel to any visited town/rest point."""
        eng = self.engine
        st = eng.state
        targets = []
        for area_id in sorted(st.visited_areas):
            if area_id == TOWN:
                targets.append(("Riven Town", TOWN, PLAYER_START))
            elif area_id in AREAS and AREAS[area_id].styled:
                a = AREAS[area_id]
                targets.append((a.name, area_id, a.start))
        if not targets:
            return
        eng.push(abilities.FlyMenu(targets, lambda t, tile: self._fly_to(t, tile)))

    def _fly_to(self, area_id, tile):
        st = self.engine.state
        st.location = {"area": area_id, "tile": list(tile), "facing": "down"}
        audio.play("heal")
        eng.transitioning = True
        import math as _m

        def apply():
            self.map = self._get_map(area_id)
            self.player.tile = tile
            self.player.pos = pygame.Vector2(tile[0] * 48, tile[1] * 48)
            self.player.facing = "down"
            self.player.moving = False
            self._sync_abilities()
            eng.transitioning = False
        eng.fade_to(apply, color=(180, 220, 240))

    def open_help(self):
        self.engine.push(HelpScene())

    def _held_dir(self):
        k = pygame.key.get_pressed()
        if not (k[pygame.K_UP] or k[pygame.K_w] or k[pygame.K_DOWN] or k[pygame.K_s]
                or k[pygame.K_LEFT] or k[pygame.K_a] or k[pygame.K_RIGHT] or k[pygame.K_d]):
            return touch.held_dir()                 # on-screen D-pad (None when not touching)
        if k[pygame.K_UP] or k[pygame.K_w]:
            return "up"
        if k[pygame.K_DOWN] or k[pygame.K_s]:
            return "down"
        if k[pygame.K_LEFT] or k[pygame.K_a]:
            return "left"
        if k[pygame.K_RIGHT] or k[pygame.K_d]:
            return "right"
        return None

    def update(self, dt):
        self.t += dt
        self.npcs.update(dt)
        self.map.update(dt)
        eng = self.engine
        self._sync_abilities()
        self._trainers_think(dt)
        self._approach_step(dt)
        if eng.top is self and not eng.transitioning:
            self._move(dt)
        self.camera.follow(self.player.pos, self.map.px_w, self.map.px_h)

    def _move(self, dt):
        p, m = self.player, self.map
        left = dt
        for _ in range(4):
            if self.engine.top is not self or self.engine.transitioning:
                break
            if not p.moving and self.approacher is None:      # frozen while a trainer approaches
                d = self._held_dir()
                if not d:
                    p.advance(0)
                    break
                p.facing = d
                self._sync_location()                         # turning while standing is saved too
                dx, dy = DIRS[d]
                land = m.ledge_landing(p.tile[0] + dx, p.tile[1] + dy, self._npc_rects()) if d == "down" else None
                if land:                                        # one-way ledge: hop over it (south only)
                    audio.play("select")
                    p.begin_jump(land)
                elif m.blocked(p.tile[0] + dx, p.tile[1] + dy, self._npc_rects()):
                    p.stand()
                    break
                else:
                    p.begin_step(d)
            arrived, left = p.advance(left)
            if arrived:
                self._on_step()
            if left <= 0 and not arrived:
                break

    def _on_step(self):
        m, (x, y) = self.map, self.player.tile
        t = m.tile_at(x, y)
        if m.kind == "overworld":
            link = LINKS.get(m.area, {}).get((x, y))
            if link:
                self.travel(link)
                return
            if t == "D":
                b = building_at(m.area, x, y)
                if b:
                    self.enter_building(b)
                    return
            st = self.engine.state
            if (st.party and not self.approacher and not self.building
                    and random.random() < ENCOUNTER_CHANCE):
                rolled = pick_encounter(st, m.area, (x, y))
                if rolled:
                    self.start_wild_battle(*rolled)
            # fishing: facing a water tile with a rod → casting encounter
            if (not self.approacher and not self.building and self._facing_water(m, x, y)
                    and random.random() < ENCOUNTER_CHANCE * 0.5):
                self._fishing(m, x, y)
        elif t == "E" and self.building:
            self.exit_building()
        self._sync_location()
        self._check_ambush()

    def _facing_water(self, m, x, y):
        """True when the tile the player faces is water (W) — a fishing spot."""
        d = self.player.facing
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.get(d, (0, 0))
        nx, ny = x + dx, y + dy
        if not (0 <= ny < m.h and 0 <= nx < m.w):
            return False
        return m.tile_at(nx, ny) == "W"

    def _fishing(self, m, x, y):
        """Roll a fishing encounter based on the best rod the player holds.  Uses the water/sea
        habitat pool with rod-tier level ranges; the gym ceiling and 50 cap still apply."""
        st = self.engine.state
        rod = None
        for rid in ("deep_rod", "field_rod", "probe_rod"):
            if st.qty(rid) > 0:
                rod = rid
                break
        if rod is None:
            return
        r = abilities.fishing_encounter(st, m.area, rod)
        if r:
            self.start_wild_battle(*r)

    def _sync_abilities(self):
        """Update map walkability and party checks from the current field abilities."""
        m = self.map
        if hasattr(m, 'walkable_override'):
            if abilities.can_use(self.engine.state, "aquaboard"):
                m.walkable_override.add("W")
            else:
                m.walkable_override.discard("W")

    # ---- the Corrupt Bandits (villain arc) ---------------------------------------------------
    def _check_ambush(self):
        """One Bandit pair per city: stepping on a trigger tile stages them on the road and starts the scene."""
        st = self.engine.state
        if self.building or self.map.kind != "overworld" or not st.party:
            return
        tile = self.player.tile
        for amb in villain.AMBUSHES:
            if amb["id"] in st.story:
                continue
            if self.map.area != amb["area"]:                 # tile coordinates repeat across areas!
                continue
            if amb["id"] == "bandit2" and "bandit1" not in st.story:
                continue
            if tile in amb["triggers"] and not any(n.id.startswith("bandit") for n in self.npcs):
                self._start_ambush(amb)
                return

    def _start_ambush(self, amb):
        """The pair stages itself on the road, shouts its piece, and the battle starts."""
        for i, spot in enumerate(amb["spots"]):
            who = ("bandit-a", "bandit-b")[i]
            self.npcs.add(NPC({"id": who, "x": spot[0], "y": spot[1], "name": "Corrupt Bandit", "lines": [],
                               "look": black_look(who), "facing": "down"}))
        audio.play("deny")
        self.engine.push(DialogueScene(list(amb["intro"]), on_done=lambda: self._start_bandit_battle(amb)))

    def _start_bandit_battle(self, amb):
        st = self.engine.state
        enemy = [create_scimon(sid, lv) for sid, lv in amb["team"]]
        b = new_battle(st.party, enemy, st.battle_bag(), st.battle_modules(), trainer=amb["leader"])
        bg = BG_FOR_AREA.get(amb["area"], 1)

        def apply():
            self.engine.push(BattleScene(b, lambda res: self.end_bandit_battle(amb, res),
                                         allow_capture=False, allow_run=False, bg=bg))
        self.engine.fade_to(apply, color=(255, 255, 255))

    def _dismiss_thugs(self):
        for n in [n for n in self.npcs if n.id.startswith("bandit")]:
            self.npcs.remove(n)

    def end_bandit_battle(self, amb, res):
        st = self.engine.state
        st.merge_battle_result(res["bag"], res["modules"])
        st.party = res["party"]
        self._dismiss_thugs()
        st.story.add(amb["id"])
        if res["outcome"] == "win":
            lines = list(amb["win"])
            if amb["id"] == "bandit2":
                st.add_item("banditticket", 1)
                lines.append("You find a repair ticket dropped during the scuffle - stamped with the Cush franchise logo.")
        else:
            st.heal_party()
            lines = list(amb["lose"])
            if amb["id"] == "bandit2":
                st.add_item("banditticket", 1)
                if len(st.party) >= 2:
                    taken = random.choice(st.party)
                    st.party.remove(taken)
                    st.snatched = taken
                    lines.insert(3, f"The Snatcher's black hold snaps shut around {taken.name}!")
                else:
                    lines.insert(3, "But your Field Scanner shrieks a counter-signal - the Snatcher burns out empty-handed!")
        name = st.name

        def after():
            if res["outcome"] == "lose":
                healer = self._nearest_visited_healer()
                if healer:
                    self._blackout_to(healer)
                else:
                    self.engine.toast.show("Your team was knocked offline... systems restored.", 3.0)
        self.engine.push(DialogueScene([ln.replace("{name}", name) for ln in lines], on_done=after))

    def _recover_snatched(self):
        """The stolen Sci-Mon sits in a shadow-box of the Cush franchise database (the arc's quiet clue)."""
        st = self.engine.state
        mon = st.snatched
        mon.hp = mon.max_hp
        lines = [ln.replace("{mon}", mon.name) for ln in villain.RECOVERY_LINES]
        if len(st.party) < PARTY_LIMIT:
            st.party.append(mon)
            lines.append(f"{mon.name} rejoins your party!")
        else:
            st.storage.append(mon)
            lines.append(f"Your party is full, so {mon.name} was placed in storage.")
        st.snatched = None
        st.story.add("snatch_done")
        audio.play("heal")
        self.engine.push(DialogueScene(lines))

    def _reveal_ready(self):
        st = self.engine.state
        return ("bandit1" in st.story and "bandit2" in st.story
                and villain.REVEAL_STAMP in st.stamps and "exposed" not in st.story and "boss_beaten" not in st.story)

    def _start_reveal(self):
        st = self.engine.state
        st.story.add("exposed")
        self.engine.push(DialogueScene([ln.replace("{name}", st.name) for ln in villain.REVEAL_LINES],
                                       on_done=self._start_boss_battle))

    def _start_boss_battle(self):
        st = self.engine.state
        enemy = [create_scimon(sid, lv) for sid, lv in villain.BOSS_TEAM]
        enemy[-1].name = "Grim " + enemy[-1].name                     # the shadow-palette ace
        b = new_battle(st.party, enemy, st.battle_bag(), st.battle_modules(), trainer=villain.BOSS_NAME)
        bg = BG_FOR_AREA.get(villain.REVEAL_BUILDING and "epidimy", 2)

        def apply():
            self.engine.push(BattleScene(b, self.end_boss_battle, allow_capture=False, allow_run=False, bg=bg))
        self.engine.fade_to(apply, color=(255, 255, 255))

    def end_boss_battle(self, res):
        st = self.engine.state
        st.merge_battle_result(res["bag"], res["modules"])
        st.party = res["party"]
        if res["outcome"] == "lose":
            st.heal_party()
            healer = self._nearest_visited_healer()
            if healer:
                self._blackout_to(healer)
            self.engine.toast.show("Cush: Ha! The nook will be here when you're ready to lose again.", 3.0)
            return
        st.story.add("boss_beaten")
        if st.qty("banditticket"):
            st.remove_item("banditticket", 1)
        st.add_item("mastersticket", 1)
        self._swap_nooks_to_kael()
        lines = [ln.replace("{name}", st.name) for ln in villain.BOSS_WIN_LINES + villain.KAEL_ARRIVAL]
        self.engine.push(DialogueScene(lines))

    def _kael_def(self, d):
        st = self.engine.state
        team = [(st.rival_species or "aquabit", 9), KAEL_RETEAM2]
        return {"id": "kael-nook", "x": d["x"], "y": d["y"], "name": villain.RIVAL_NAME, "facing": "down",
                "look": look_for("kael"), "service": "repair",
                "lines": [f"{villain.RIVAL_NAME}: The nook is under new management. Free repairs, honest books.",
                          f"{villain.RIVAL_NAME}: Dad's gone. Don't bring him up."],
                "battle": team, "rematch": True,
                "ask": list(villain.KAEL_REMATCH_ASK), "post": list(villain.KAEL_REMATCH_POST_WIN)}

    def _swap_nooks_to_kael(self):
        """After the fall, every nook's counter is Kael's - now and in every future visit."""
        for m in self.map.npc_defs:
            if m.get("service") == "repair":
                m.clear()
                m.update(self._kael_def({"x": m.get("x", 5), "y": m.get("y", 4)}))
        for n in [n for n in list(self.npcs) if getattr(n, "service", None) == "repair"]:
            self.npcs.remove(n)
            self.npcs.add(NPC(self._kael_def({"x": n.tile[0], "y": n.tile[1]})))

    # ---- drawing -------------------------------------------------------------------------------
    def draw(self, surf):
        m, cam = self.map, self.camera
        m.focus = self.player.rect.center
        m.draw(surf, cam, self.t, debug=self.engine.debug)
        # characters and standing furniture share one depth order: whoever's footprint bottom is lower draws later
        for c in (*self.npcs, self.player):                     # soft contact shadow grounds every sprite
            surf.blit(_contact_shadow(), (c.rect.centerx - 17 - cam.x, c.rect.bottom - 7 - cam.y))
        if self.player.lift > 0:                                # bigger shadow while hopping a ledge
            sh = pygame.Surface((34, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
            surf.blit(sh, (self.player.rect.centerx - 17 - cam.x, self.player.rect.bottom - 10 - cam.y))
        drawn = [(c.sort_y, c.image, c.draw_pos) for c in (*self.npcs, self.player)]
        drawn += [(pr.sort_y, self._prop_image(pr), (pr.x, pr.y)) for pr in m.props]
        for _, img, (wx, wy) in sorted(drawn, key=lambda d: d[0]):
            surf.blit(img, (wx - cam.x, wy - cam.y))
        if self.approacher:                                   # the spotted-you alert over the trainer's head
            n = self.approacher
            x, y = n.draw_pos
            label_chip(surf, "!", (x - cam.x + (n.image.get_width() - 26) // 2, y - cam.y - 30), (225, 65, 55), size=16)
        m.draw_top(surf, cam, self.t)
        if self.building and self.building.has_database:      # floating tag just above the database computer
            for ty, row in enumerate(m.rows):
                tx = row.find("@")
                if tx == -1:
                    continue
                span = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                while tx + span.width // TILE < len(row) and row[tx + span.width // TILE] == "@":
                    span.width += TILE
                over = [p for p in m.props if p.x < span.right and p.x + p.image.get_width() > span.left
                        and p.y <= span.bottom and p.sort_y >= span.top]
                host = min(over, key=lambda p: p.y) if over else None
                cx = (host.x + host.image.get_width() // 2) if host else span.centerx
                top = host.y if host else span.top
                img = render_text("SCI-DATABASE", "display", 8, (255, 255, 255))
                label_chip(surf, "SCI-DATABASE", (cx - cam.x - (img.get_width() + 10) // 2,
                                                  top - cam.y - img.get_height() - 10), (42, 103, 99), size=8)
        if self.engine.debug:
            for r in self._npc_rects():
                pygame.draw.rect(surf, (255, 0, 255), cam.apply(r), 2)
            pygame.draw.rect(surf, (0, 255, 255), cam.apply(self.player.rect), 2)
            for c in (*self.npcs, self.player):          # sprite extent vs hitbox: blue box = art, magenta/cyan = hitbox
                pygame.draw.rect(surf, (80, 120, 255), pygame.Rect(c.draw_pos, c.image.get_size()).move(-cam.x, -cam.y), 1)
            z = zone_at(self.map.area, *self.player.tile) if self.map.kind == "overworld" else None
            if z:
                for y in range(self.map.h):
                    for x in range(self.map.w):
                        zz = zone_at(self.map.area, x, y)
                        if zz is z:
                            pygame.draw.rect(surf, (255, 210, 60), cam.apply(pygame.Rect(x * TILE, y * TILE, TILE, TILE)), 1)
                text(surf, f"zone {z['zone_id']}  habitat {z['habitat_id']}  band {z['band']}",
                     (W // 2, H - 36), "display", 8, (255, 210, 60), anchor="midbottom", shadow=(0, 0, 0))
            text(surf, f"tile {self.player.tile}  fps {self.engine.clock.get_fps():.0f}", (W // 2, H - 24), "display",
                 8, (255, 255, 255), anchor="midbottom", shadow=(0, 0, 0))
        self._hud(surf)

    def _prop_image(self, pr):
        """A walk-behind building turns see-through while the player stands in its back yard, so you never lose the character."""
        z = getattr(pr, "back_zone", None)
        if z and z[0] <= self.player.tile[0] <= z[2] and z[1] <= self.player.tile[1] <= z[3]:
            if getattr(pr, "_faded", None) is None:
                pr._faded = pr.image.copy()
                pr._faded.set_alpha(105)
            return pr._faded
        return pr.image

    def _hud(self, surf):
        st = self.engine.state
        loc = self.building.name if self.building else self.map.name
        locr = render_text(loc, "display", 8, INK)
        lr = pygame.Rect(10, 10, locr.get_width() + 24, 28)    # location, extreme top left
        panel(surf, lr, "chip", blur=False, shadow=False)
        surf.blit(locr, locr.get_rect(center=lr.center))
        packr = render_text("Pack (I)", "display", 8, INK)
        helpr = render_text("Help (H)", "display", 8, INK)
        hr = pygame.Rect(W - 10 - (helpr.get_width() + 24), 10, helpr.get_width() + 24, 28)   # extreme top right
        pr = pygame.Rect(hr.x - 8 - (packr.get_width() + 24), 10, packr.get_width() + 24, 28)
        panel(surf, pr, "button", blur=False, shadow=False)
        text(surf, "Pack (I)", pr.center, "display", 8, INK, anchor="center")
        self.pack_rect = pr
        panel(surf, hr, "button", blur=False, shadow=False)
        text(surf, "Help (H)", hr.center, "display", 8, INK, anchor="center")
        self.help_rect = hr
        done, total = st.dex_progress
        text(surf, f"Captured {done}/{total}", (W - 12, H - 8), "display", 8, (255, 255, 255), anchor="bottomright",
             shadow=(0, 0, 0))
