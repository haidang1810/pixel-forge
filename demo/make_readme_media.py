#!/usr/bin/env python3
"""Regenerate every image the README shows (docs/images) from the specs in this repository."""
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "pixel-forge" / "scripts"
EXAMPLES = ROOT / "examples" / "characters"
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


# One orc spec, four identities: what build, motion, style and palette change on their own.
ORC_VARIANTS = {
    "scout": {"build": "slim", "motion": {"weight": 0.15, "energy": 0.9, "seed": 11},
              "skin": ["#3B4A3A", "#62806A", "#94B89C"]},
    "brute": {"build": "bulky", "motion": {"weight": 0.95, "energy": 0.25, "seed": 22},
              "skin": ["#4A3A24", "#7A6234", "#AE9450"]},
    "warlord": {"build": "tall", "motion": {"weight": 0.6, "energy": 0.6, "exaggeration": 1.3, "seed": 33},
                "style": {"outline": "selout"}, "skin": ["#4A2430", "#7A3A48", "#B05A66"]},
    "grunt": {"build": "short", "motion": {"weight": 0.5, "energy": 0.7, "seed": 44},
              "style": {"shades": 3, "dither": True}, "skin": ["#2F4A24", "#4F7A34", "#7FAE4E"]},
}


def orc_variants():
    import json
    base = json.loads((EXAMPLES / "orc.json").read_text(encoding="utf-8"))
    folder = RENDER / "variants"
    folder.mkdir(parents=True, exist_ok=True)
    for name, v in ORC_VARIANTS.items():
        spec = dict(base, name=f"orc-{name}", build=v["build"], motion=v["motion"],
                    materials=dict(base["materials"], skin=v["skin"]),
                    anims=[{"preset": "walk", "frames": 8, "ms": 110, "stride": 20, "knee": 30}])
        if "style" in v:
            spec["style"] = v["style"]
        path = folder / f"{name}.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        run(SCRIPTS / "rig2d.py", path, "--out", RENDER / name)
    showcase([f"{n}/walk" for n in ORC_VARIANTS], IMAGES / "variety.gif", 4, 3, 2200)


def polish_compare():
    """The same knight and orc without and with colors, polish, textures and follow-through."""
    import json
    folder = RENDER / "raw"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("knight", "orc"):
        spec = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
        spec.pop("style", None)
        spec.pop("motion", None)
        for part in list(spec.get("parts", {}).values()) + spec.get("extras", []):
            part.pop("texture", None)
        if name == "orc":  # the hand-picked colors the orc had before generated ramps
            spec["materials"]["skin"] = ["#2F4A24", "#4F7A34", "#7FAE4E"]
            spec["materials"]["legs"] = ["#3A2620", "#5E3F2E", "#8A6045"]
        spec["name"] = f"{name}-raw"
        path = folder / f"{name}.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        run(SCRIPTS / "rig2d.py", path, "--out", RENDER / f"{name}-raw")
    showcase(["knight-raw/attack", "knight/attack", "orc-raw/attack", "orc/attack"], IMAGES / "polish.gif", 4, 4, 2200)


# A sample of the preset packs, each on a character it suits.
MOVES = [("knight", "heavy_attack", {}), ("knight", "jump", {}), ("mage", "cast", {}), ("knight", "combo", {}),
         ("wolf-vector", "howl", {}), ("wolf-vector", "leap", {}), ("raven", "glide", {}), ("serpent", "rear_up", {}),
         ("slime", "bounce_slam", {}), ("orc", "kick", {})]


def moves():
    import json
    folder = RENDER / "moves"
    folder.mkdir(parents=True, exist_ok=True)
    cells = []
    for character, preset, extra in MOVES:
        spec = json.loads((EXAMPLES / f"{character}.json").read_text(encoding="utf-8"))
        name = f"{character}-{preset}"
        spec["anims"] = [dict({"preset": preset}, **extra)]
        path = folder / f"{name}.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        run(SCRIPTS / "rig2d.py", path, "--out", RENDER / name)
        cells.append(f"{name}/{preset}")
    showcase(cells, IMAGES / "moves.gif", 5, 3, 2600)


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    run(ROOT / "demo" / "items" / "build_items.py")
    for name in ("wolf", "orc", "ghost", "knight", "mage", "slime", "serpent", "raven"):
        run(SCRIPTS / "rig2d.py", EXAMPLES / f"{name}.json", "--out", RENDER / name)
    run(SCRIPTS / "rig2d.py", EXAMPLES / "wolf.json", "--out", RENDER / "wolf-rest", "--rest", "--scale", 10)
    showcase(["wolf/idle", "wolf/run", "wolf/attack", "wolf/hurt", "wolf/die"], IMAGES / "wolf.gif", 5, 3, 2600)
    showcase(["orc/idle", "orc/walk", "orc/attack", "orc/hurt", "orc/die"], IMAGES / "orc.gif", 5, 3, 2600)
    showcase(["ghost/float", "ghost/fly", "ghost/hurt", "ghost/die"], IMAGES / "ghost.gif", 4, 3, 2600)
    showcase(["knight/idle", "knight/walk", "knight/attack", "mage/idle", "mage/walk"], IMAGES / "heroes.gif", 5, 3, 2400)
    showcase(["slime/hop", "slime/attack", "serpent/slither", "serpent/attack", "raven/fly", "raven/attack"],
             IMAGES / "critters.gif", 6, 3, 2400)
    orc_variants()
    polish_compare()
    moves()
    with Image.open(RENDER / "wolf-rest" / "rest-grid.png") as grid:
        grid.convert("RGB").save(IMAGES / "wolf-rig.png", optimize=True)
    items_sheet()
    items_gif()
    for path in sorted(IMAGES.iterdir()):
        print(f"{path.name:16s} {path.stat().st_size // 1024:5d} KB")


if __name__ == "__main__":
    main()
