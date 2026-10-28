#!/usr/bin/env python3
"""Preview animations in place: stack them on a background (a screenshot of the game) at 1x, as a GIF.

    python composite.py --bg shot.png --crop 200 120 240 160 --at 120 130 \\
        --layer back:summon.back.anim.json+idle.back.anim.json*3+dismiss.back.anim.json \\
        --layer image:player.png@20,46 \\
        --layer front:summon.front.anim.json+idle.front.anim.json*3+dismiss.front.anim.json \\
        --out preview.gif --scale 2

Each --layer is drawn in order (first = furthest back) with its pivot on --at (in crop coordinates):
- NAME:A.anim.json+B.anim.json*3 plays animations one after another (*N repeats one); a pixel_art
  PREFIX.anim.json is read with its PREFIX.strip.png, a rig2d/sheet.py animation.json with "#name"
  (OUT/animation.json#idle). Pivots come from the manifest (default: bottom centre).
- image:FILE.png@PX,PY is a still sprite (a character standing in the effect), pivot PX,PY.
- move:DX,DY moves the next layer by DX,DY pixels per frame (a projectile flying).
Layers shorter than the longest hold their last frame. Frame timing follows the first animated layer.
"""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image


def load_anim(ref):
    """[(image, ms, pivot)] for one animation reference."""
    path, _, name = ref.partition("#")
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if "animations" in data:  # rig2d / sheet.py manifest
        anim = data["animations"][name] if name else next(iter(data["animations"].values()))
        sheet = Image.open(path.parent / anim["sheet"]).convert("RGBA")
        frames = anim["frames"]
    else:  # pixel_art PREFIX.anim.json
        sheet = Image.open(path.with_name(path.name[:-len(".anim.json")] + ".strip.png")).convert("RGBA")
        frames = data["frames"]
    out = []
    for f in frames:
        x, y, w, h = f["rect"]
        pivot = f.get("pivot") or [w // 2, h - 1]
        out.append((sheet.crop((x, y, x + w, y + h)), f.get("ms", 100), tuple(pivot)))
    return out


def sequence(spec):
    frames = []
    for part in spec.split("+"):
        ref, _, times = part.partition("*")
        frames += load_anim(ref) * int(times or 1)
    return frames


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bg", required=True)
    parser.add_argument("--crop", nargs=4, type=int, metavar=("X", "Y", "W", "H"))
    parser.add_argument("--at", nargs=2, type=int, required=True, help="where pivots go, in crop coordinates")
    parser.add_argument("--layer", action="append", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--hold", type=int, default=400, help="ms to hold the last frame before the GIF loops")
    args = parser.parse_args(argv)
    try:
        bg = Image.open(args.bg).convert("RGBA")
        if args.crop:
            x, y, w, h = args.crop
            bg = bg.crop((x, y, x + w, y + h))
        layers, move = [], None
        for spec in args.layer:
            kind, _, rest = spec.partition(":")
            if kind == "image":
                file, _, pv = rest.partition("@")
                img = Image.open(file).convert("RGBA")
                pivot = tuple(int(v) for v in pv.split(",")) if pv else (img.width // 2, img.height - 1)
                layers.append(([(img, None, pivot)], move))
            elif kind == "move":
                move = tuple(float(v) for v in rest.split(","))
                continue
            else:
                layers.append((sequence(rest), move))
            move = None
    except (OSError, ValueError, KeyError, StopIteration) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    timed = next((seq for seq, _ in layers if seq[0][1] is not None), None)
    count = max(len(seq) for seq, _ in layers)
    pictures, durations = [], []
    for i in range(count):
        canvas = bg.copy()
        for seq, mv in layers:
            img, _, (px, py) = seq[min(i, len(seq) - 1)]
            dx, dy = (mv[0] * i, mv[1] * i) if mv else (0, 0)
            canvas.alpha_composite(img, (round(args.at[0] - px + dx), round(args.at[1] - py + dy))) \
                if 0 <= args.at[0] - px + dx < canvas.width * 2 else None
        big = canvas.resize((canvas.width * args.scale, canvas.height * args.scale), Image.NEAREST)
        pictures.append(big.convert("P", palette=Image.ADAPTIVE))
        durations.append(timed[min(i, len(timed) - 1)][1] if timed else 100)
    durations[-1] = max(durations[-1], args.hold)
    pictures[0].save(args.out, save_all=True, append_images=pictures[1:], duration=durations, loop=0, disposal=2)
    print(f"wrote {args.out} ({count} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
