"""SCI-MON (Python / Pygame edition) -- entry point.

    pip install -r requirements.txt
    python main.py

Flow: Title -> wake-up scene -> Prof. Venn's lab briefing -> pick a starter -> rival battle with Kael -> explore Riven Town.

The same file runs on the desktop and, built with pygbag, in the browser (GitHub Pages).  In the browser
it draws a loading bar while assets load and prints any startup error on the canvas instead of failing silently."""
import asyncio
import os
import sys
import traceback

ON_SCREEN_ERRORS = sys.platform == "emscripten" or bool(os.environ.get("SCIMON_SHOW_ERRORS"))


def _lines(text, width=78):
    out = []
    for raw in text.splitlines():
        while len(raw) > width:
            out.append(raw[:width]); raw = "  " + raw[width:]
        out.append(raw)
    return out


async def show_error(text):
    """Keep the error visible on the canvas (and in the console) so it can be read / screenshotted."""
    import pygame
    print(text, file=sys.stderr)
    pygame.init()
    pygame.font.init()
    screen = pygame.display.get_surface() or pygame.display.set_mode((960, 640))
    font = pygame.font.Font(None, 20)
    lines = ["SCI-MON failed to start - please screenshot this:", ""] + _lines(text)[-28:]
    while True:
        if any(e.type == pygame.QUIT for e in pygame.event.get()):
            return
        screen.fill((24, 8, 12))
        for i, ln in enumerate(lines):
            screen.blit(font.render(ln, True, (255, 200, 200) if i else (255, 255, 255)), (12, 10 + i * 20))
        pygame.display.flip()
        await asyncio.sleep(0.1)


def _loading(screen, font, done, total):
    import pygame
    w, h = screen.get_size()
    screen.fill((16, 20, 32))
    t = font.render("SCI-MON  -  loading...", True, (230, 235, 255))
    screen.blit(t, ((w - t.get_width()) // 2, h // 2 - 40))
    pygame.draw.rect(screen, (60, 70, 100), (w // 2 - 200, h // 2, 400, 18), 2)
    pygame.draw.rect(screen, (120, 200, 255), (w // 2 - 198, h // 2 + 2, int(396 * done / max(1, total)), 14))
    pygame.display.flip()


async def main():
    try:
        import pygame
        import assets
        from engine import Engine
        from scenes import TitleScene

        engine = Engine(preload=False)
        font = pygame.font.Font(None, 36)
        _loading(engine.screen, font, 0, 1)
        await asyncio.sleep(0)
        for done, total in assets.preload_steps():            # yield to the browser every few assets
            if done % 8 == 0 or done == total:
                pygame.event.pump()
                _loading(engine.screen, font, done, total)
                await asyncio.sleep(0)
        engine.push(TitleScene())
        await engine.run_async()
    except SystemExit:
        raise
    except BaseException:
        if ON_SCREEN_ERRORS:
            await show_error(traceback.format_exc())
        raise


asyncio.run(main())
