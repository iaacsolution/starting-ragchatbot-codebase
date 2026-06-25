"""
Capture a demo GIF of the RAG chatbot.
Run from repo root: python make_demo_gif.py
"""

import asyncio
import time
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

FRAMES_DIR = Path("demo_frames")
OUTPUT = Path("demo.gif")
URL = "http://localhost:8000"
QUESTION = "Comment fonctionne le tool use dans Claude ?"
VIEWPORT = {"width": 1100, "height": 750}


async def capture():
    FRAMES_DIR.mkdir(exist_ok=True)
    frames = []
    idx = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport=VIEWPORT)
        await page.goto(URL, wait_until="networkidle")
        await asyncio.sleep(1)

        async def shot(duration_ms=120):
            nonlocal idx
            path = FRAMES_DIR / f"frame_{idx:04d}.png"
            await page.screenshot(path=str(path))
            frames.append((str(path), duration_ms))
            idx += 1

        # Frame initiale — page chargée
        for _ in range(6):
            await shot(80)

        # Cliquer sur le champ de saisie et taper
        input_box = page.locator(
            "input[type=text], textarea, #user-input, .chat-input"
        ).first
        await input_box.click()
        await asyncio.sleep(0.2)
        await shot()

        for char in QUESTION:
            await input_box.type(char, delay=30)
            if idx % 4 == 0:
                await shot(60)

        await shot(300)  # pause avant envoi

        # Envoyer
        await input_box.press("Enter")
        await shot(150)

        # Capturer le streaming de la réponse
        for i in range(55):
            await asyncio.sleep(0.18)
            await shot(100 if i < 40 else 180)

        # Attendre le badge RAGAS
        try:
            await page.wait_for_selector(
                ".ragas-badge, [class*='ragas']", timeout=20000
            )
        except Exception:
            pass
        await asyncio.sleep(1)
        for _ in range(8):
            await shot(200)

        # Pause finale
        for _ in range(10):
            await shot(300)

        await browser.close()

    print(f"{len(frames)} frames capturées")
    return frames


def build_gif(frames):
    images = []
    durations = []
    for path, ms in frames:
        img = (
            Image.open(path)
            .convert("RGBA")
            .convert("P", palette=Image.ADAPTIVE, colors=128)
        )
        images.append(img)
        durations.append(ms)

    images[0].save(
        OUTPUT,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    size_kb = OUTPUT.stat().st_size // 1024
    print(f"GIF créé : {OUTPUT} ({size_kb} KB, {len(images)} frames)")


if __name__ == "__main__":
    frames = asyncio.run(capture())
    build_gif(frames)
