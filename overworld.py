"""The exploration state: Riven Town plus every interior, with grid movement, NPC talk, shops, repair, the
Sci-Database terminal, doors and tall-grass encounters. Port of V34's overworld.tsx game logic."""
import math
import random

import pygame

import assets
import audio
from battle import BG_FOR_AREA, BattleScene, new_battle
from data import ROUTE_ENCOUNTERS
from engine import Scene, StateId
from map import Camera, TileMap
from menus import DatabaseScene, InventoryScene, ServiceScene, ShopScene
from monsters import create_scimon
import epidimy
from routes import AREAS, HEALERS, LINKS, ROUTE1_START, TOWN, building_at, travel_cost
from scenes import DialogueScene
from settings import ENCOUNTER_CHANCE, H, INK, TILE, W
from sprites import DIRS, NPC, Player, look_animator
import touch
from ui import bar, hp_color, is_click, is_confirm, label_chip, panel, render_text, text
from worldmap import PLAYER_START, building_at_door, BUILDINGS


def pick_encounter():
    total = sum(e[1] for e in ROUTE_ENCOUNTERS)
    r = random.random() * total
    for sid, w, lo, hi in ROUTE_ENCOUNTERS:
        r -= w
        if r <= 0:
            return sid, random.randint(lo, hi)
    sid, _, lo, _ = ROUTE_ENCOUNTERS[0]
    return sid, lo


_OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
LOS_RANGE = 3                             # trainers spot the player up to this many tiles ahead
BUILDINGS_ALL = {b.id: b for b in BUILDINGS}          # town + Epidimy interiors, for the saved location
for _a in AREAS.values():
    BUILDINGS_ALL.update({b.id: b for b in _a.buildings})
AREA_STARTS = {TOWN: PLAYER_START, "route1": ROUTE1_START, epidimy.AREA_ID: epidimy.START}   # safe fallback spots


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
        self.engine.state.location = where

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
        """Walk from one outdoor area to another (town <-> Route 1) through a link tile (routes.LINKS)."""
        area, (tx, ty), facing = link

        def apply():
            self.map = self._get_map(None, area)
            self._load_npcs()
            self.player.place(tx, ty, facing)
            self._sync_location()
        self.engine.fade_to(apply)

    # ---- interaction -------------------------------------------------------------------
    def interact(self):
        p, m = self.player, self.map
        dx, dy = DIRS[p.facing]
        fx, fy = p.tile[0] + dx, p.tile[1] + dy
        if m.is_terminal(fx, fy) and self.building:
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
            else:
                self.engine.push(DialogueScene(npc.lines, on_done=lambda n=npc: self._after_talk(n)))

    def _offer_rematch(self, n):
        ask = list(n.rematch_ask) or [f"{n.name}: Another battle, {self.engine.state.name}?"]
        self.engine.push(DialogueScene(ask, choices=[("BATTLE!", lambda nn=n: self._trainer_battle(nn)),
                                                     ("NOT NOW", None)]))

    def _after_talk(self, npc):
        st = self.engine.state
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
            self.engine.push(ServiceScene(b, self._repair))

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

    def end_wild_battle(self, res):
        st = self.engine.state
        st.merge_battle_result(res["bag"], res["modules"])
        st.party = res["party"]
        out = res["outcome"]
        if out == "lose":
            st.heal_party()
            healer = self._nearest_visited_healer()
            if healer:                                    # a wipe sends you back to the last healer you used
                self._blackout_to(healer)
            else:
                self.engine.toast.show("Your team was knocked offline... systems restored.", 3.0)
        elif out == "caught" and res["caught"]:
            self.engine.toast.show(st.receive_scimon(res["caught"]), 2.6)
            if len(st.captured) >= 9:
                self.engine.toast.show("You completed the Sci-Dex! Congratulations, Researcher!", 4.0)

    def _nearest_visited_healer(self):
        """The healer the player has used that is closest to where they stand now (None if they never used one)."""
        visited = [h for h in HEALERS if h["id"] in self.engine.state.visited_healers]
        if not visited:
            return None
        area = self.building.area if self.building else getattr(self.map, "area", TOWN)
        tile = self.player.tile

        def cost(h):
            c = travel_cost(area, tile, h["area"], h["tile"])
            return (math.inf if c is None else c, h["id"])
        return min(visited, key=cost)

    def _blackout_to(self, healer):
        """Set the player down by the healer.  Runs inside the battle-exit fade, so the swap is never seen."""
        self.building = None
        self.map = self._get_map(None, healer["area"])
        self._load_npcs()
        self.player.place(*healer["tile"], healer["facing"])
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
        sid, lv = n.trainer_battle
        enemy = create_scimon(sid, lv)
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
            if n.aside and n.tile != tuple(n.aside):
                n.place(*n.aside)                          # step out of the gate so the way opens
            if n.post:
                self.engine.push(DialogueScene(list(n.post)))

    # ---- events / update --------------------------------------------------------------------
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_i, pygame.K_TAB, pygame.K_ESCAPE):
                self.open_pack()
                return
        if is_confirm(e):
            if not self.player.moving:
                self.interact()
        elif is_click(e) and self.pack_rect.collidepoint(e.pos):
            self.open_pack()

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
            if m.is_tall_grass(x, y) and not self.approacher and random.random() < ENCOUNTER_CHANCE:
                self.start_wild_battle(*pick_encounter())
        elif t == "E" and self.building:
            self.exit_building()
        self._sync_location()

    # ---- drawing -------------------------------------------------------------------------------
    def draw(self, surf):
        m, cam = self.map, self.camera
        m.focus = self.player.rect.center
        m.draw(surf, cam, self.t, debug=self.engine.debug)
        # characters and standing furniture share one depth order: whoever's footprint bottom is lower draws later
        if self.player.lift > 0:                                # ground shadow while hopping a ledge
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
        if self.engine.debug:
            for r in self._npc_rects():
                pygame.draw.rect(surf, (255, 0, 255), cam.apply(r), 2)
            pygame.draw.rect(surf, (0, 255, 255), cam.apply(self.player.rect), 2)
            for c in (*self.npcs, self.player):          # sprite extent vs hitbox: blue box = art, magenta/cyan = hitbox
                pygame.draw.rect(surf, (80, 120, 255), pygame.Rect(c.draw_pos, c.image.get_size()).move(-cam.x, -cam.y), 1)
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
        x = 10
        for mon in st.party[:6]:
            r = pygame.Rect(x, 10, 142, 42)
            panel(surf, r, "chip", blur=False, shadow=False)
            img = assets.mon_image(mon.species_id, 30, 30)
            surf.blit(img, img.get_rect(center=(r.x + 20, r.centery)))
            text(surf, f"{mon.name} L{mon.level}", (r.x + 40, r.y + 5), "body", 20, INK)
            ratio = mon.hp / mon.max_hp
            bar(surf, (r.x + 40, r.y + 26, 94, 8), ratio, hp_color(ratio))
            x += 148
        loc = self.building.name if self.building else self.map.name
        locr = render_text(loc, "display", 8, INK)
        w = max(150, locr.get_width() + 28)
        lr = pygame.Rect(W - 10 - w, 10, w, 28)
        panel(surf, lr, "chip", blur=False, shadow=False)
        surf.blit(locr, locr.get_rect(center=lr.center))
        cr = pygame.Rect(W - 10 - 150, 44, 150, 28)
        panel(surf, cr, "chip", blur=False, shadow=False)
        text(surf, f"\u00a2 {st.credits}", cr.center, "display", 8, INK, anchor="center")
        self.pack_rect = pygame.Rect(W - 10 - 150, 78, 150, 28)
        panel(surf, self.pack_rect, "button", blur=False, shadow=False)
        text(surf, "Pack (I)", self.pack_rect.center, "display", 8, INK, anchor="center")
        done, total = st.dex_progress
        text(surf, f"Captured {done}/{total}", (W - 12, H - 8), "display", 8, (255, 255, 255), anchor="bottomright",
             shadow=(0, 0, 0))
