"""SCI-MON (Python / Pygame edition) -- entry point.

    pip install -r requirements.txt
    python main.py

Flow: Title -> wake-up scene -> pick a starter -> rival battle with Kael -> explore Riven Town.

The same file runs on the desktop and, built with pygbag, in the browser (GitHub Pages)."""
import asyncio

from engine import Engine
from scenes import TitleScene


async def main():
    engine = Engine()
    engine.push(TitleScene())
    await engine.run_async()


if __name__ == "__main__":
    asyncio.run(main())
