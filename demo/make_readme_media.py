#!/usr/bin/env python3
"""Regenerate every image the README shows (docs/images) from the specs in this repository."""
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "pixel-forge" / "scripts"
EXAMPLES = ROOT / "prototype" / "rig2d" / "examples"
RENDER = ROOT / "output" / "readme"
IMAGES = ROOT / "docs" / "images"
BG = (34, 38, 54, 255)


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True, capture_output=True)


def showcase(cells, out, cols, scale, length):
    run(SCRIPTS / "showcase.py", *cells, "--root", RENDER, "--cols", cols, "--scale", scale, "--length", length, "--out", out)


def frames_of(sheet_path, size=32):
    with Image.open(sheet_path) as sheet:
        sheet = sheet.convert("RGBA")
        return [sheet.crop((i * size, 0, i * size + size, size)) for i in range(sheet.width // size)]


def items_sheet():
    items = ROOT / "demo" / "items"
    icons = [("treasure chest", ROOT / "evaluation/items/treasure-chest.png"), ("jade sword", ROOT / "evaluation/items/jade-sword.png"),
             ("ember potion", ROOT / "evaluation/items/ember-potion.png"), ("key", items / "key.png"), ("gem", items / "gem.png"),
             ("shield", items / "shield.png"), ("scroll", items / "scroll.png")]
    tiles = []
    for name, path in icons:
        with Image.open(path) as image:
            tiles.append((name, image.convert("RGBA")))
    tiles.append(("coin", frames_of(items / "coin-spin.png")[0]))
    tiles.append(("bomb", frames_of(items / "bomb.png")[0]))
    scale, cell, label = 4, 32 * 4 + 16, 16
    cols = 9
    sheet = Image.new("RGBA", (cols * cell, cell + label), BG)
    draw = ImageDraw.Draw(sheet)
    for i, (name, tile) in enumerate(tiles):
        x = i * cell + 8
        sheet.alpha_composite(tile.resize((128, 128), Image.NEAREST), (x, 8))
        width = draw.textlength(name)
        draw.text((x + (128 - width) / 2, 8 + 128 + 4), name, fill=(200, 205, 225, 255))
    sheet.save(IMAGES / "items.png")


def items_gif():
    items = ROOT / "demo" / "items"
    import json
    anims = []
    for name in ("chest-open", "coin-spin", "bomb"):
        meta = json.loads((items / f"{name}.anim.json").read_text(encoding="utf-8"))
        anims.append(list(zip(frames_of(items / f"{name}.png"), [f["ms"] for f in meta["frames"]])))
    scale, pad = 6, 12
    w = len(anims) * (32 * scale + pad) + pad
    h = 32 * scale + 2 * pad

    def at(frames, t):
        t %= sum(ms for _, ms in frames)
        for image, ms in frames:
            if t < ms:
                return image
            t -= ms
    out, durations = [], []
    for t in range(0, 1640, 20):
        frame = Image.new("RGBA", (w, h), BG)
        for i, frames in enumerate(anims):
            frame.alpha_composite(at(frames, t).resize((32 * scale, 32 * scale), Image.NEAREST), (pad + i * (32 * scale + pad), pad))
        if out and frame.tobytes() == out[-1].tobytes():
            durations[-1] += 20
        else:
            out.append(frame)
            durations.append(20)
    quant = [f.convert("RGB").quantize(colors=255, method=Image.MEDIANCUT, dither=Image.Dither.NONE) for f in out]
    palette = quant[0]
    quant = [f.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE) for f in out]
    quant[0].save(IMAGES / "items.gif", save_all=True, append_images=quant[1:], duration=durations, loop=0)


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    run(ROOT / "demo" / "items" / "build_items.py")
    for name in ("wolf3", "orc", "ghost2", "knight", "mage"):
        run(SCRIPTS / "rig2d.py", EXAMPLES / f"{name}.json", "--out", RENDER / name)
    run(SCRIPTS / "rig2d.py", EXAMPLES / "wolf3.json", "--out", RENDER / "wolf3-rest", "--rest", "--scale", 10)
    showcase(["wolf3/idle", "wolf3/run", "wolf3/attack", "wolf3/hurt", "wolf3/die"], IMAGES / "wolf.gif", 5, 3, 2600)
    showcase(["orc/idle", "orc/walk", "orc/attack", "orc/hurt", "orc/die"], IMAGES / "orc.gif", 5, 3, 2600)
    showcase(["ghost2/float", "ghost2/fly", "ghost2/hurt", "ghost2/die"], IMAGES / "ghost.gif", 4, 3, 2600)
    showcase(["knight/idle", "knight/walk", "knight/attack", "mage/idle", "mage/walk"], IMAGES / "heroes.gif", 5, 3, 2400)
    with Image.open(RENDER / "wolf3-rest" / "rest-grid.png") as grid:
        grid.convert("RGB").save(IMAGES / "wolf-rig.png", optimize=True)
    items_sheet()
    items_gif()
    for path in sorted(IMAGES.iterdir()):
        print(f"{path.name:16s} {path.stat().st_size // 1024:5d} KB")


if __name__ == "__main__":
    main()
