"""Turn-based combat: the rules engine (a port of V34's planTurn) and the battle screen.

`plan_turn()` simulates a whole turn on a copy of the battle and returns a list of BattleEvents. Each event
carries the message to show and an `effect(state)` that mutates the *visible* state, so HP bars, statuses and
XP change exactly when their message appears -- the scene just plays the queue one frame at a time and never
blocks the main loop."""
import copy
import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

import pygame

import assets
import audio
from data import ITEMS, MODULES, SPECIES, STATUS_INFO, TECHNIQUES, type_rgb
from engine import Scene, StateId
from monsters import (Scimon, calc_damage, capture_chance, choose_enemy_move, eff_text, xp_for_level, xp_gain)
from settings import (CREAM, EXP_BLUE, H, HP_GREEN, INK, OLIVE, OLIVE_DARK, ORANGE, STAB_BLUE, TEAL_DARK, W, hexc)
from sprites import AttackFx, ImpactBurst, ScimonSprite, TrainerSprite
from ui import (Button, ButtonGrid, DialogueBox, bar, hp_color, icon_chip, is_back, is_click, is_confirm, label_chip, panel,
                render_text, status_chip, text, type_chip, wrap_text)


# =========================================================================== rules engine
@dataclass
class BattleState:
    party: list
    active_index: int
    enemy: Scimon
    bag: dict
    modules: dict
    defending: bool = False
    turn: int = 0
    run_attempts: int = 0
    outcome: str = ""            # "" | win | lose | caught | run
    must_switch: bool = False
    trainer: Optional[str] = None
    enemy_party: list = field(default_factory=list)   # trainers with more than one Sci-Mon
    enemy_index: int = 0
    enemy_token: int = 0                              # bumped whenever a new enemy Sci-Mon is sent out

    @property
    def player(self):
        return self.party[self.active_index]


@dataclass
class BattleEvent:
    text: Optional[str] = None
    effect: Optional[Callable] = None
    hit_enemy: bool = False
    hit_player: bool = False
    sfx: Optional[str] = None
    anim: Optional[tuple] = None        # (side, technique type): attacker plays its attack animation + MPW effect on the target


def _active(s):
    return s.party[s.active_index]


def enemy_label(s):
    return f"{s.trainer}'s {s.enemy.name}" if s.trainer else f"Wild {s.enemy.name}"


def new_battle(party, enemy, bag, modules, trainer=None):
    """Battles run on copies; the caller commits the result (party, bag) when the battle ends.  `enemy` is one
    Sci-Mon or a list of them (trainer teams): the next one is sent out whenever the current faints."""
    enemies = copy.deepcopy(list(enemy) if isinstance(enemy, (list, tuple)) else [enemy])
    party = copy.deepcopy(party)
    active = max(0, next((i for i, m in enumerate(party) if m.hp > 0), 0))
    return BattleState(party=party, active_index=active, enemy=enemies[0], bag=dict(bag), modules=dict(modules),
                       trainer=trainer, enemy_party=enemies)


def _swap_enemy(s, i):
    """The trainer sends out their next Sci-Mon: fresh body, fresh status, new token (the scene re-renders it)."""
    s.enemy_index = i
    s.enemy = s.enemy_party[i]
    s.enemy_token += 1


def trainer_credits(s, outcome, wallet):
    """Credits won by beating a trainer (20 x the enemy's level) or dropped in a loss (10 x the enemy's
    level, never more than the wallet holds).  Wild battles pay and cost nothing."""
    if not s.trainer or outcome not in ("win", "lose"):
        return 0
    if outcome == "win":
        return 20 * s.enemy.level
    return -min(10 * s.enemy.level, wallet)


def intro_events(s):
    e = s.enemy.name
    go = BattleEvent(f"Go! {s.player.name}!", sfx="select")
    if s.trainer:
        return [BattleEvent(f"{s.trainer} challenges you to a battle!", sfx="select"),
                BattleEvent(f"{s.trainer} sends out {e}!", sfx="select"), go]
    return [BattleEvent(f"A wild {e} appeared!", sfx="select"), go]


def _status_fail(mon):
    if mon.status == "Glitched" and random.random() < 0.25:
        return f"{mon.name}'s technique destabilized!"
    if mon.status == "Electrified" and random.random() < 0.25:
        return f"{mon.name} is disrupted and can't move!"
    return None


def _target(s, side):
    return _active(s) if side == "player" else s.enemy


def _execute_move(sim, side, tech_id, events):
    att = _target(sim, side)
    dfn = _target(sim, "enemy" if side == "player" else "player")
    if att.hp <= 0 or dfn.hp <= 0:
        return
    tech = TECHNIQUES[tech_id]
    label = att.name if side == "player" else enemy_label(sim)
    foe_side = "enemy" if side == "player" else "player"
    hit = dict(hit_enemy=(side == "player"), hit_player=(side == "enemy"))
    events.append(BattleEvent(f"{label} used {tech.name}!", sfx="select", anim=(side, tech.type)))

    fail = _status_fail(att)
    if fail:
        events.append(BattleEvent(fail))
        return
    if random.random() > tech.accuracy / 100:
        events.append(BattleEvent("But the technique missed!"))
        return

    if tech.category == "status":
        if tech.buff_power:
            stage = min(3, att.power_stage + 1)
            att.power_stage = stage
            events.append(BattleEvent(f"{label}'s Power rose!", sfx="heal",
                                      effect=lambda s, side=side, stage=stage: setattr(_target(s, side), "power_stage", stage)))
        elif tech.status:
            if dfn.status:
                events.append(BattleEvent(f"It had no effect - {dfn.name} is already affected."))
            else:
                st = tech.status
                dfn.status = st
                events.append(BattleEvent(f"{dfn.name} became {st}!", **hit,
                                          effect=lambda s, fs=foe_side, st=st: setattr(_target(s, fs), "status", st)))
        return

    dmg, eff, crit = calc_damage(att, dfn, tech, defending=(side == "enemy" and sim.defending))
    new_hp = max(0, dfn.hp - dmg)
    dfn.hp = new_hp
    events.append(BattleEvent("A critical hit!" if crit else None, **hit, sfx="hit",
                              effect=lambda s, fs=foe_side, hp=new_hp: setattr(_target(s, fs), "hp", hp)))
    t = eff_text(eff)
    if t:
        events.append(BattleEvent(t))
    if tech.drain and dmg > 0:
        healed = min(att.max_hp, att.hp + max(1, int(dmg * tech.drain)))
        att.hp = healed
        events.append(BattleEvent(f"{label} absorbed energy!", sfx="heal",
                                  effect=lambda s, side=side, hp=healed: setattr(_target(s, side), "hp", hp)))
    if tech.status and tech.status_chance and not dfn.status and random.random() < tech.status_chance:
        st = tech.status
        dfn.status = st
        events.append(BattleEvent(f"{dfn.name} became {st}!",
                                  effect=lambda s, fs=foe_side, st=st: setattr(_target(s, fs), "status", st)))


def _end_of_turn_status(sim, side, events):
    mon = _target(sim, side)
    if mon.hp <= 0 or not mon.status:
        return
    label = mon.name if side == "player" else enemy_label(sim)
    hit = dict(hit_player=(side == "player"), hit_enemy=(side == "enemy"))
    if mon.status in ("Overheated", "Deoxygenated"):
        hp = max(0, mon.hp - max(1, mon.max_hp // 12))
        mon.hp = hp
        events.append(BattleEvent(f"{label} is hurt by {mon.status}!", **hit, sfx="hit",
                                  effect=lambda s, side=side, hp=hp: setattr(_target(s, side), "hp", hp)))
    elif mon.status == "Nanite-Infected":
        hp = max(0, mon.hp - max(1, mon.max_hp // 16))
        stab = max(0, mon.stability - max(1, mon.max_stability // 8))
        mon.hp, mon.stability = hp, stab

        def fx(s, side=side, hp=hp, stab=stab):
            m = _target(s, side)
            m.hp, m.stability = hp, stab
        events.append(BattleEvent(f"{label}'s systems are corrupted by nanites!", sfx="hit", effect=fx))


def _apply_xp(sim, events):
    mon, sp = _active(sim), SPECIES[_active(sim).species_id]
    gain = xp_gain(sim.enemy)
    events.append(BattleEvent(f"{mon.name} gained {gain} EXP!", sfx="xp",
                              effect=lambda s, g=gain: setattr(_active(s), "xp", _active(s).xp + g)))
    work, level = mon.xp + gain, mon.level
    while work >= xp_for_level(level):
        work -= xp_for_level(level)
        level += 1
        events.append(BattleEvent(f"{mon.name} grew to Lv. {level}!", sfx="heal",
                                  effect=lambda s, lv=level: _active(s).level_up_to(lv)))
        for lv, tech in sp.learnset:
            if lv == level:
                def learn(s, tech=tech):
                    m = _active(s)
                    if tech not in m.moves and len(m.moves) < 4:
                        m.moves.append(tech)
                events.append(BattleEvent(f"{mon.name} can use {TECHNIQUES[tech].name}!", effect=learn))

        def settle(s, w=work, lv=level):
            _active(s).xp, _active(s).xp_to_next = w, xp_for_level(lv)
        events.append(BattleEvent(effect=settle))


def _finalize(sim, events):
    if sim.enemy.hp <= 0:
        events.append(BattleEvent(f"{enemy_label(sim)} was defeated!", sfx="faint"))
        _apply_xp(sim, events)
        nxt = next((i for i, m in enumerate(sim.enemy_party) if m.hp > 0 and i != sim.enemy_index), None)
        if nxt is not None:
            incoming = sim.enemy_party[nxt]
            events.append(BattleEvent(f"{sim.trainer} sends out {incoming.name}!", sfx="select",
                                      effect=lambda s, i=nxt: _swap_enemy(s, i)))
            return
        events.append(BattleEvent(effect=lambda s: setattr(s, "outcome", "win")))
        return
    if _active(sim).hp <= 0:
        events.append(BattleEvent(f"{_active(sim).name} was knocked offline!", sfx="faint"))
        if any(m.hp > 0 for i, m in enumerate(sim.party) if i != sim.active_index):
            events.append(BattleEvent(effect=lambda s: setattr(s, "must_switch", True)))
        else:
            events.append(BattleEvent("You have no operational Scimon left...",
                                      effect=lambda s: setattr(s, "outcome", "lose")))


def plan_turn(battle, action):
    """action: ("move", tech_id) | ("defend",) | ("capture", module_id) | ("item", item_id) | ("switch", idx) | ("run",)"""
    sim = copy.deepcopy(battle)
    sim.turn += 1
    sim.defending = False
    ev = []
    player = _active(sim)
    enemy_move = choose_enemy_move(sim.enemy, player)
    kind = action[0]

    def enemy_phase(both=False):
        _execute_move(sim, "enemy", enemy_move, ev)
        _end_of_turn_status(sim, "player", ev)
        if both:
            _end_of_turn_status(sim, "enemy", ev)
        _finalize(sim, ev)

    if kind == "run":
        sim.run_attempts += 1
        # Gen I escape: F = ((A*32) / (B/4)) + 30*C (mod 256); F > 255 escapes outright,
        # else a roll of 0-255 below F escapes. A: player's current Speed (never stage-modified here);
        # B: wild Speed / 4, 0 becomes 1; C: attempts this battle, reset whenever the player attacks.
        b = max(1, sim.enemy.speed // 4)
        f = player.speed * 32 // b + 30 * sim.run_attempts
        ev.append(BattleEvent(effect=lambda s, n=sim.run_attempts: setattr(s, "run_attempts", n)))
        if f > 255 or random.randrange(256) < f % 256:
            ev.append(BattleEvent("Got away safely!", sfx="select", effect=lambda s: setattr(s, "outcome", "run")))
            return ev
        ev.append(BattleEvent("Couldn't get away!"))
        enemy_phase()
        return ev

    if kind == "capture":
        mid = action[1]
        if sim.modules.get(mid, 0) <= 0:
            return [BattleEvent("No modules of that type left!")]
        chance = capture_chance(sim.enemy, mid)
        sim.modules[mid] -= 1
        ev.append(BattleEvent(f"You threw a {MODULES[mid].name}!", sfx="capture",
                              effect=lambda s, m=mid: s.modules.__setitem__(m, s.modules.get(m, 0) - 1)))
        success = random.random() < chance
        shakes = 3 if success else 2 if chance > 0.6 else 1 if chance > 0.3 else 0
        ev += [BattleEvent("...", sfx="select") for _ in range(shakes)]
        if success:
            ev.append(BattleEvent(f"Gotcha! {sim.enemy.name} was contained!", sfx="capture",
                                  effect=lambda s: setattr(s, "outcome", "caught")))
            return ev
        ev.append(BattleEvent(f"{sim.enemy.name} broke free!"))
        enemy_phase()
        return ev

    if kind == "item":
        iid = action[1]
        item = ITEMS[iid]
        if sim.bag.get(iid, 0) <= 0:
            return [BattleEvent("You're out of that item!")]
        sim.bag[iid] -= 1
        use = lambda s, i=iid: s.bag.__setitem__(i, s.bag.get(i, 0) - 1)   # noqa: E731
        if item.heal:
            healed = min(player.max_hp, player.hp + item.heal)
            player.hp = healed

            def fx(s, hp=healed):
                use(s)
                _active(s).hp = hp
            ev.append(BattleEvent(f"You used {item.name}. {player.name} recovered!", sfx="heal", effect=fx))
        elif item.restore_stability:
            player.stability, player.status = player.max_stability, None

            def fx(s):
                use(s)
                m = _active(s)
                m.stability, m.status = m.max_stability, None
            ev.append(BattleEvent(f"You used {item.name}. {player.name} stabilized!", sfx="heal", effect=fx))
        enemy_phase()
        return ev

    if kind == "switch":
        idx = action[1]
        ev.append(BattleEvent(f"{sim.party[idx].name}, deploy!", sfx="select",
                              effect=lambda s, i=idx: setattr(s, "active_index", i)))
        sim.active_index = idx
        enemy_phase(both=True)
        return ev

    if kind == "defend":
        sim.defending = True
        rec = max(1, player.max_stability // 6)
        player.stability = min(player.max_stability, player.stability + rec)

        def fx(s, rec=rec):
            s.defending = True
            m = _active(s)
            m.stability = min(m.max_stability, m.stability + rec)
        ev.append(BattleEvent(f"{player.name} braced and reinforced its systems!", sfx="select", effect=fx))
        enemy_phase(both=True)
        return ev

    tech = action[1]
    sim.run_attempts = 0          # attacking resets the escape counter (C = 0 next time)
    ev.append(BattleEvent(effect=lambda s: setattr(s, "run_attempts", 0)))
    if player.speed >= sim.enemy.speed:
        _execute_move(sim, "player", tech, ev)
        if sim.enemy.hp > 0:
            _execute_move(sim, "enemy", enemy_move, ev)
    else:
        _execute_move(sim, "enemy", enemy_move, ev)
        if _active(sim).hp > 0:
            _execute_move(sim, "player", tech, ev)
    _end_of_turn_status(sim, "player", ev)
    _end_of_turn_status(sim, "enemy", ev)
    _finalize(sim, ev)
    return ev


# =========================================================================== battle screen
SCENE_H = 480
CTRL = pygame.Rect(14, SCENE_H + 8, W - 28, H - SCENE_H - 22)
ENEMY_MID = (722, 236)
PLAYER_MID = (236, 452)

# MPW battle backgrounds (assets/mpw/bg/bg1 grass, bg2 beach, bg3 snow), picked by the outdoor area the fight starts in.
# Styled towns fight on the grass field, routes and wild places on the beach field, Epidimy keeps its snow field.
BG_FOR_AREA = {"overworld": 1, "route1": 2, "epidimy": 3}
BUTTON_ICONS = {"fight": "options1", "defend": "options2", "switch": "options3", "capture": "options4",
                "item": "baricon4", "run": "baricon6"}

# The wider network (routes.py merges towns.py + kanto.py): styled towns fight on the grass field, the routes
# and wild places on the beach field.  (Epidimy keeps its snow field; route1 its beach.)
try:
    import routes as _routes
    for _a in _routes.AREAS.values():
        BG_FOR_AREA.setdefault(_a.id, 1 if _a.styled else 2)
except Exception:                           # never let background picking break the battle scene
    pass


class BattleScene(Scene):
    state_id = StateId.BATTLE

    def __init__(self, battle, on_end, allow_capture=True, allow_run=True, bg=1):
        self.bs = copy.deepcopy(battle)
        self.on_end = on_end
        self.allow_capture, self.allow_run = allow_capture, allow_run
        self.bg = bg if bg in (1, 2, 3) else 1
        self.fx = []                     # running AttackFx
        self.queue, self.qi = [], 0
        self.waiting = False
        self.menu = "message"            # message | main | fight | capture | item | switch
        self.forced_switch = False
        self.msg = DialogueBox(rect=CTRL, size=36)
        self.grid = None
        self.t = 0.0
        self.end_timer = None
        self.burst = ImpactBurst()
        self.shown = {"p": self.bs.player.hp / self.bs.player.max_hp, "e": 1.0}
        self.shown_xp = self.bs.player.xp / max(1, self.bs.player.xp_to_next)
        self.shown_stab = {"p": 1.0, "e": 1.0}
        self.player_uid = None
        self.enemy_token = self.bs.enemy_token
        self._make_sprites(appear=True)
        self.trainer = TrainerSprite((ENEMY_MID[0] + 150, ENEMY_MID[1] - 20)) if self.bs.trainer else None
        self.cursor_hint = ""

    # ---- setup -----------------------------------------------------------------------
    def _make_sprites(self, appear=False):
        e = self.bs.enemy
        self.enemy_sprite = ScimonSprite(e.species_id, (ENEMY_MID[0], ENEMY_MID[1] - 8), (250, 220), appear=appear)
        self._make_player_sprite(appear)

    def _make_player_sprite(self, appear=True):
        p = self.bs.player
        self.player_sprite = ScimonSprite(p.species_id, (PLAYER_MID[0], PLAYER_MID[1] - 12), (300, 260), back=True,
                                          appear=appear)
        self.player_uid = p.uid
        self.shown["p"] = p.hp / p.max_hp
        self.shown_xp = p.xp / max(1, p.xp_to_next)

    def on_enter(self):
        self._play(intro_events(self.bs))

    # ---- event playback ------------------------------------------------------------------
    def _apply(self, ev):
        if ev.effect:
            ev.effect(self.bs)
        if ev.anim:
            side, ttype = ev.anim
            atk, tgt = (self.player_sprite, self.enemy_sprite) if side == "player" else (self.enemy_sprite, self.player_sprite)
            atk.attack(1 if side == "player" else -1)
            self.fx.append(AttackFx(ttype, tgt.rect.center))
        if ev.hit_enemy:
            self.enemy_sprite.hit()
            self.burst.trigger(self.enemy_sprite.rect.center)
        if ev.hit_player:
            self.player_sprite.hit()
            self.burst.trigger(self.player_sprite.rect.center)
        if ev.sfx:
            audio.play(ev.sfx)
        if self.bs.player.uid != self.player_uid:
            self._make_player_sprite(True)
        if self.bs.enemy_token != self.enemy_token:
            self.enemy_token = self.bs.enemy_token
            self.enemy_sprite = ScimonSprite(self.bs.enemy.species_id, (ENEMY_MID[0], ENEMY_MID[1] - 8), (250, 220),
                                             appear=True)
            self.shown["e"], self.shown_stab["e"] = 1.0, 1.0
        if self.bs.enemy.hp <= 0 or self.bs.outcome == "caught":
            self.enemy_sprite.faint()
        if self.bs.player.hp <= 0:
            self.player_sprite.faint()

    def _play(self, events):
        self.queue, self.qi = events, 0
        self._show_step()

    def _show_step(self):
        q = self.queue
        i = self.qi
        while i < len(q) and q[i].text is None:      # effect-only events apply instantly
            self._apply(q[i])
            i += 1
        if i >= len(q):
            self.qi, self.waiting = i, False
            self._resolve_end()
            return
        ev = q[i]
        self._apply(ev)
        self.msg.set_lines([ev.text])
        self.menu, self.waiting, self.qi = "message", True, i + 1

    def _resolve_end(self):
        s = self.bs
        if s.outcome:
            if self.end_timer is None:
                self.end_timer = 0.6
            self.menu = "message"
            return
        if s.must_switch:
            s.must_switch = False
            self.forced_switch = True
            self._open("switch")
            return
        self.forced_switch = False
        self._open("main")

    def _finish(self):
        if getattr(self, "_finishing", False):
            return
        self._finishing = True
        s = self.bs
        credits = trainer_credits(s, s.outcome, self.engine.state.credits)   # trainer prize / loss, 0 for wild
        result = {"outcome": s.outcome, "party": s.party, "bag": s.bag, "modules": s.modules,
                  "caught": s.enemy if s.outcome == "caught" else None, "credits": credits}

        def apply():
            if credits:
                self.engine.state.add_credits(credits)
            self.engine.pop(self)
            self.on_end(result)
        self.engine.fade_to(apply)

    # ---- menus ---------------------------------------------------------------------------------
    def _open(self, menu):
        self.menu = menu
        s = self.bs
        area = pygame.Rect(CTRL.x + 460, CTRL.y, CTRL.w - 460, CTRL.h)
        btns = []
        if menu == "main":
            cols = 2
            bw, bh = (area.w - 12) // 2, (area.h - 16) // 3
            spec = [("FIGHT", "fight", True, True), ("DEFEND", "defend", True, False),
                    ("CAPTURE", "capture", self.allow_capture, False), ("ITEM", "item", True, False),
                    ("SCIMON", "switch", any(m.hp > 0 and i != s.active_index for i, m in enumerate(s.party)), False),
                    ("RUN", "run", self.allow_run, False)]
            for i, (lab, tag, ok, accent) in enumerate(spec):
                btns.append(Button(lab, (area.x + (i % 2) * (bw + 12), area.y + 4 + (i // 2) * (bh + 4), bw, bh),
                                   enabled=ok, accent=accent, tag=tag, icon=BUTTON_ICONS.get(tag)))
        elif menu == "fight":
            cols = 2
            bw, bh = (area.w - 12) // 2, 54
            for i, mid in enumerate(s.player.moves):
                t = TECHNIQUES[mid]
                btns.append(Button(t.name, (area.x + (i % 2) * (bw + 12), area.y + 4 + (i // 2) * (bh + 8), bw, bh),
                                   tag=mid, sub=t.type.upper(), color=type_rgb(t.type)))
            btns.append(Button("BACK", (area.x, area.bottom - 40, 120, 34), tag="back"))
        elif menu in ("capture", "item", "switch"):
            cols = 1
            rows = []
            if menu == "capture":
                for m in MODULES.values():
                    n = s.modules.get(m.id, 0)
                    star = "*" if m.match_type and m.match_type in s.enemy.types else ""
                    rows.append((f"{m.name}{star}", f"x{n}", m.id, n > 0))
            elif menu == "item":
                for it in ITEMS.values():
                    n = s.bag.get(it.id, 0)
                    if n > 0:
                        rows.append((it.name, f"x{n}", it.id, True))
            else:
                for i, m in enumerate(s.party):
                    rows.append((f"{m.name} Lv{m.level}", f"{m.hp}/{m.max_hp}", i, m.hp > 0 and i != s.active_index))
            top = area.y + 2
            avail = area.h - 4 - (0 if (menu == "switch" and self.forced_switch) else 38)
            rh = min(40, max(26, avail // max(1, min(len(rows), 6))))
            for i, (lab, right, tag, ok) in enumerate(rows[:6]):
                btns.append(Button(lab, (area.x, top + i * (rh + 2), area.w, rh), enabled=ok, tag=tag, right=right))
            if not (menu == "switch" and self.forced_switch):
                btns.append(Button("BACK", (area.x, area.bottom - 34, 120, 32), tag="back"))
            if menu == "item" and not rows:
                self.cursor_hint = "Your bag is empty."
        self.grid = ButtonGrid(btns, cols=cols, allow_back=not (menu == "switch" and self.forced_switch))
        self.cursor_hint = ""

    def _activate(self, b):
        s, m = self.bs, self.menu
        audio.play("select")
        if b.tag == "back":
            self._open("main")
        elif m == "main":
            if b.tag == "defend":
                self._act(("defend",))
            elif b.tag == "run":
                self._act(("run",))
            else:
                self._open({"fight": "fight", "capture": "capture", "item": "item", "switch": "switch"}[b.tag])
        elif m == "fight":
            self._act(("move", b.tag))
        elif m == "capture":
            self._act(("capture", b.tag))
        elif m == "item":
            self._act(("item", b.tag))
        elif m == "switch":
            if self.forced_switch:            # replacing a fainted Scimon is free: the enemy doesn't act
                s.active_index, s.must_switch, self.forced_switch = b.tag, False, False
                self._make_player_sprite(True)
                self._open("main")
            else:
                self._act(("switch", b.tag))

    def _act(self, action):
        self.forced_switch = False
        self._play(plan_turn(self.bs, action))

    # ---- scene interface ---------------------------------------------------------------------
    def handle_event(self, e):
        if self.end_timer is not None:
            return
        if self.menu == "message":
            if is_confirm(e) or is_click(e):
                if not self.msg.waiting:
                    self.msg.advance()           # first press: finish typing
                elif self.waiting:
                    self.waiting = False
                    self._show_step()
            return
        if self.grid:
            r = self.grid.handle(e)
            if r:
                kind, b = r
                if kind == "activate":
                    self._activate(b)
                elif kind == "deny":
                    audio.play("deny")
                elif kind == "back" and self.menu != "main":
                    self._open("main")

    def update(self, dt):
        self.t += dt
        self.msg.update(dt)
        for sp in (self.enemy_sprite, self.player_sprite):
            sp.update(dt)
        if self.trainer:
            self.trainer.update(dt)
        self.burst.update(dt)
        for f in self.fx:
            f.update(dt)
        self.fx = [f for f in self.fx if f.alive]
        if self.grid:
            self.grid.update(dt)
        k = min(1.0, dt * 9)                        # smooth bars (V34: 0.5 s CSS transition)

        def ease(cur, target):
            # settle exactly on the target: exponential easing alone never reaches 0, which used to leave a
            # red sliver on the bar of an offline Scimon
            nxt = cur + (target - cur) * k
            return target if abs(target - nxt) < 0.002 else nxt

        p, en = self.bs.player, self.bs.enemy
        self.shown["p"] = ease(self.shown["p"], p.hp / p.max_hp)
        self.shown["e"] = ease(self.shown["e"], en.hp / en.max_hp)
        self.shown_stab["p"] = ease(self.shown_stab["p"], p.stability / p.max_stability)
        self.shown_stab["e"] = ease(self.shown_stab["e"], en.stability / en.max_stability)
        self.shown_xp = ease(self.shown_xp, p.xp / max(1, p.xp_to_next))
        if self.end_timer is not None and self.msg.waiting and not self.waiting:
            self.end_timer -= dt
            if self.end_timer <= 0:
                self._finish()

    # ---- drawing ------------------------------------------------------------------------------
    def _background(self, surf):
        """MPW battle background (640x320 art scaled 1.5x to the 960x480 stage; smooth keeps the non-integer
        scale from doubling pixels unevenly)."""
        surf.blit(assets.scaled(f"mpw/bg/bg{self.bg}.png", W, SCENE_H, smooth=True), (0, 0))

    def _platform(self, surf, center, wide=False):
        """Soft ground shadow under a fighter (the MPW backgrounds have no platform art)."""
        w, h = (330, 76) if wide else (270, 62)
        sh = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (20, 40, 20, 46), sh.get_rect())
        pygame.draw.ellipse(sh, (20, 40, 20, 40), sh.get_rect().inflate(-w // 3, -h // 3))
        surf.blit(sh, sh.get_rect(center=center))

    def _info_panel(self, surf, rect, mon, shown, shown_stab, enemy):
        panel(surf, rect, "panel")
        x, y = rect.x + 18, rect.y + 12
        text(surf, mon.name, (x, y), "display", 16, INK)
        text(surf, f"Lv{mon.level}", (rect.right - 18, y), "display", 16, INK, anchor="topright")
        sx = status_chip(surf, mon.status, x, y + 26) if mon.status else x
        by = y + 28 + (0 if not mon.status else 0)
        bx = rect.x + 18
        if mon.status:
            by = y + 50
        icon_chip(surf, "baricon2", (bx, by - 5), ORANGE)
        bar(surf, (bx + 38, by, rect.w - 36 - 38 - 4, 14), shown, hp_color(shown))
        by += 27
        if not enemy:
            text(surf, f"{mon.hp}/{mon.max_hp}", (rect.right - 18, by - 2), "body", 24, INK, anchor="topright")
            by += 20
        icon_chip(surf, "baricon5", (bx, by - 8), TEAL_DARK)
        bar(surf, (bx + 44, by - 3, rect.w - 36 - 44 - 4, 9), shown_stab, STAB_BLUE)
        if not enemy:
            by += 27
            icon_chip(surf, "baricon3", (bx, by - 8), (240, 192, 32))
            bar(surf, (bx + 44, by - 3, rect.w - 36 - 44 - 4, 9), min(1.0, self.shown_xp), EXP_BLUE, segmented=True)

    def draw(self, surf):
        surf.fill(TEAL_DARK)                     # control strip backdrop (nothing ghosts through the glass)
        self._background(surf)
        self._platform(surf, (ENEMY_MID[0], ENEMY_MID[1] + 6))
        self._platform(surf, (PLAYER_MID[0], PLAYER_MID[1] + 2), wide=True)
        if self.trainer:
            self.trainer.draw(surf)
        self.enemy_sprite.draw(surf)
        self.player_sprite.draw(surf)
        for f in self.fx:
            f.draw(surf)
        self.burst.draw(surf)
        e, p = self.bs.enemy, self.bs.player
        eh = 100 + (22 if e.status else 0)
        self._info_panel(surf, pygame.Rect(30, 28, 380, eh), e, self.shown["e"], self.shown_stab["e"], True)
        ph = 142 + (22 if p.status else 0)
        self._info_panel(surf, pygame.Rect(W - 30 - 400, SCENE_H - ph - 28, 400, ph), p, self.shown["p"],
                         self.shown_stab["p"], False)
        sfx = render_text("SFX OFF" if audio.muted else "SFX ON", "display", 8, INK)
        panel(surf, (W - 112, 10, 100, 26), "button", blur=False, shadow=False)
        surf.blit(sfx, sfx.get_rect(center=(W - 62, 23)))
        self._controls(surf)

    def _controls(self, surf):
        if self.menu == "message" or not self.grid:
            self.msg.draw(surf)
            return
        left = pygame.Rect(CTRL.x, CTRL.y, 448, CTRL.h)
        panel(surf, left, "message")
        s = self.bs
        if self.menu == "fight" and self.grid.current and self.grid.current.tag != "back":
            t = TECHNIQUES[self.grid.current.tag]
            info = t.desc if t.category == "status" else f"PWR {t.power}  -  ACC {t.accuracy}"
            text(surf, t.category.upper(), (left.x + 24, left.y + 18), "display", 8, (200, 235, 225))
            text(surf, info if t.category != "status" else "STATUS", (left.x + 24, left.y + 40), "body", 34,
                 (248, 246, 230))
            for k, ln in enumerate(wrap_text(t.desc, "body", 26, left.w - 48)[:3]):
                text(surf, ln, (left.x + 24, left.y + 76 + k * 24), "body", 26, (210, 232, 224))
        else:
            prompt = {"main": f"What will {s.player.name} do?", "fight": f"What will {s.player.name} do?",
                      "capture": "Choose a module. (* = matches type)", "item": "Choose an item.",
                      "switch": "Choose your next Scimon!" if self.forced_switch else "Choose a Scimon."}[self.menu]
            for k, ln in enumerate(wrap_text(prompt, "body", 38, left.w - 48)):
                text(surf, ln, (left.x + 24, left.y + 22 + k * 36), "body", 38, (248, 246, 230), shadow=(20, 40, 38))
            if self.menu == "item" and not self.grid.buttons[:-1]:
                text(surf, "Your bag is empty.", (left.x + 24, left.y + 98), "body", 28, (255, 214, 170))
        self.grid.draw(surf, size=16 if self.menu in ("main",) else 16)
