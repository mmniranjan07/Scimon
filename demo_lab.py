"""Standalone demo of the new pipeline: load the lab from the sprite atlases, walk around it, collide with the
furniture, open the chest.   python demo_lab.py

Arrows/WASD move (one tile per step, Pokemon-style) | Space/Enter/Z interact (chest, terminal) | F3 collision overlay
| Esc quit.  Everything here is the real game code: TileMap (layers + collision), Player (4-direction animator),
Camera, animated props -- just without the scene stack, menus and battles."""
import pygame

from map import Camera, TileMap
from settings import FPS, H, TILE, W
from sprites import DIRS, Player
from state import GameState
from worldmap import BUILDINGS


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Sci-Mon lab demo")
    clock = pygame.time.Clock()

    lab = next(b for b in BUILDINGS if b.id == "lab")
    tilemap = TileMap.interior(lab)                  # builds background / midground / foreground + collision grid
    state = GameState()
    tilemap.sync_state(state)
    player = Player(*lab.interior.spawn)
    player.place(*lab.interior.spawn, "up")
    camera, debug, t = Camera(), False, 0.0
    keys = {pygame.K_UP: "up", pygame.K_w: "up", pygame.K_DOWN: "down", pygame.K_s: "down",
            pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right", pygame.K_d: "right"}

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)       # clamp so a hitch can't teleport the player through a wall
        t += dt
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F3:
                debug = not debug
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z) and not player.moving:
                dx, dy = DIRS[player.facing]
                fx, fy = player.tile[0] + dx, player.tile[1] + dy
                obj = tilemap.interactable_at(fx, fy)
                if obj:
                    print(*(obj.interact(state) or []), sep="\n")
                elif tilemap.is_terminal(fx, fy):
                    print("Sci-Database terminal")

        # ---- movement: pick a direction, refuse the step if the destination tile is blocked ----------------
        if not player.moving:
            held = pygame.key.get_pressed()
            d = next((name for k, name in keys.items() if held[k]), None)
            if d:
                player.facing = d
                dx, dy = DIRS[d]
                if tilemap.blocked(player.tile[0] + dx, player.tile[1] + dy):   # solid tile / out of map
                    player.stand()                                              # bump: face it, don't move
                else:
                    player.begin_step(d)
        player.advance(dt)
        tilemap.update(dt)                           # chest, power cores, terminal screens, hovering Sci-Mon
        camera.follow(player.pos, tilemap.px_w, tilemap.px_h)

        # ---- render: background+walls, then props and the player depth-sorted, then the foreground layer ----
        tilemap.draw(screen, camera, t, debug=debug)
        items = [(p.sort_y, p.image, (p.x, p.y)) for p in tilemap.props]
        items.append((player.sort_y, player.image, player.draw_pos))
        for _, img, (x, y) in sorted(items, key=lambda i: i[0]):
            screen.blit(img, (x - camera.x, y - camera.y))
        tilemap.draw_top(screen, camera, t)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
