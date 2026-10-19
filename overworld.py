"""The exploration state: Riven Town plus every interior, with grid movement, NPC talk, shops, repair, the
Sci-Database terminal, doors and tall-grass encounters. Port of V34's overworld.tsx game logic."""
import random

import pygame

import assets
import audio
from battle import BattleScene, new_battle
from data import ROUTE_ENCOUNTERS
from engine import Scene, StateId
from map import Camera, TileMap
from menus import DatabaseScene, InventoryScene, ServiceScene, ShopScene
from monsters import create_scimon
from routes import LINKS, TOWN
from scenes import DialogueScene
from settings import ENCOUNTER_CHANCE, H, INK, TILE, W
from sprites import DIRS, NPC, Player
from ui import bar, hp_color, is_click, is_confirm, panel, render_text, text
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
        self.pack_rect = pygame.Rect(0, 0, 0, 0)

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
            self.npcs.add(NPC(d))

    def _npc_rects(self):
        return [pygame.Rect(n.tile[0] * TILE, n.tile[1] * TILE, TILE, TILE) for n in self.npcs]

    def npc_at(self, x, y):
        return next((n for n in self.npcs if n.tile == (x, y)), None)

    def enter_building(self, b):
        def apply():
            self.building = b
            self.map = self._get_map(b)
            self._load_npcs()
            self.player.place(*b.interior.spawn, "up")
            self.map.sync_state(self.engine.state)
        audio.play("door")
        self.engine.fade_to(apply)

    def exit_building(self):
        b = self.building

        def apply():
            self.building = None
            self.map = self._get_map(None)
            self._load_npcs()
            self.player.place(*b.entry_return, "down")
        audio.play("door")
        self.engine.fade_to(apply)

    def travel(self, link):
        """Walk from one outdoor area to another (town <-> Route 1) through a link tile (routes.LINKS)."""
        area, (tx, ty), facing = link

        def apply():
            self.map = self._get_map(None, area)
            self._load_npcs()
            self.player.place(tx, ty, facing)
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
            self.engine.push(DialogueScene(npc.lines, on_done=lambda n=npc: self._after_talk(n)))

    def _after_talk(self, npc):
        st = self.engine.state
        if npc.heals:
            st.heal_party()
            audio.play("heal")
            self.engine.toast.show("Scimons restored!", 1.8)
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
        scene = BattleScene(b, self.end_wild_battle)
        audio.play("capture")
        self.engine.fade_to(lambda: self.engine.push(scene), color=(255, 255, 255))

    def end_wild_battle(self, res):
        st = self.engine.state
        st.merge_battle_result(res["bag"], res["modules"])
        st.party = res["party"]
        out = res["outcome"]
        if out == "lose":
            st.heal_party()
            self.engine.toast.show("Your team was knocked offline... systems restored.", 3.0)
        elif out == "caught" and res["caught"]:
            self.engine.toast.show(st.receive_scimon(res["caught"]), 2.6)
            if len(st.captured) >= 9:
                self.engine.toast.show("You completed the Sci-Dex! Congratulations, Researcher!", 4.0)

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
        if eng.top is self and not eng.transitioning:
            self._move(dt)
        self.camera.follow(self.player.pos, self.map.px_w, self.map.px_h)

    def _move(self, dt):
        p, m = self.player, self.map
        left = dt
        for _ in range(4):
            if self.engine.top is not self or self.engine.transitioning:
                break
            if not p.moving:
                d = self._held_dir()
                if not d:
                    p.advance(0)
                    break
                p.facing = d
                dx, dy = DIRS[d]
                if m.blocked(p.tile[0] + dx, p.tile[1] + dy, self._npc_rects()):
                    p.stand()
                    break
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
                b = building_at_door(x, y)
                if b:
                    self.enter_building(b)
                    return
            if m.is_tall_grass(x, y) and random.random() < ENCOUNTER_CHANCE:
                self.start_wild_battle(*pick_encounter())
        elif t == "E" and self.building:
            self.exit_building()

    # ---- drawing -------------------------------------------------------------------------------
    def draw(self, surf):
        m, cam = self.map, self.camera
        m.focus = self.player.rect.center
        m.draw(surf, cam, self.t, debug=self.engine.debug)
        # characters and standing furniture share one depth order: whoever's footprint bottom is lower draws later
        drawn = [(c.sort_y, c.image, c.draw_pos) for c in (*self.npcs, self.player)]
        drawn += [(pr.sort_y, self._prop_image(pr), (pr.x, pr.y)) for pr in m.props]
        for _, img, (wx, wy) in sorted(drawn, key=lambda d: d[0]):
            surf.blit(img, (wx - cam.x, wy - cam.y))
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
