#!/usr/bin/env python3
"""Pack static pixel-art-json frames into an animated sprite sheet (props, items, effects).

    python sheet.py open-1.json open-2.json open-3.json open-4.json --ms 300 120 120 500 \\
        --name open --out OUT_DIR [--pivot 16 30] [--scale 8] [--once]

Writes OUT_DIR/<name>.png (a horizontal sheet), OUT_DIR/<name>/frame-XX.png, OUT_DIR/animation.json
in the same schema as rig2d (rect, ms, pivot per frame), OUT_DIR/<name>.preview.gif and
OUT_DIR/contact.png. lint.py works on OUT_DIR. Running it again with another --name adds that
animation to the same animation.json.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent


def load_renderer():
    spec = importlib.util.spec_from_file_location("pixel_art", HERE / "pixel_art.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checker(size, cell):
    bg = Image.new("RGBA", size, (38, 43, 61, 255))
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                bg.paste((48, 54, 76, 255), (x, y, min(size[0], x + cell), min(size[1], y + cell)))
    return bg


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", nargs="+", help="pixel-art-json documents, one per frame, in order")
    parser.add_argument("--ms", nargs="+", type=int, help="milliseconds per frame (one value for all, or one per frame)")
    parser.add_argument("--name", required=True, help="animation name, e.g. open")
    parser.add_argument("--out", required=True)
    parser.add_argument("--pivot", nargs=2, type=int, help="anchor point in frame pixels (default: bottom centre)")
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument("--once", action="store_true", help="a one-shot animation (recorded as loop: false)")
    args = parser.parse_args(argv)

    renderer = load_renderer()
    try:
        images = [renderer.render_document(renderer.read_json(path))[0] for path in args.frames]
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    size = images[0].size
    if any(im.size != size for im in images):
        print("error: every frame must have the same size", file=sys.stderr)
        return 2
    ms = args.ms or [100]
    if len(ms) == 1:
        ms = ms * len(images)
    if len(ms) != len(images):
        print("error: --ms takes one value, or one per frame", file=sys.stderr)
        return 2
    w, h = size
    pivot = list(args.pivot) if args.pivot else [w // 2, h - 1]

    out = Path(args.out)
    (out / args.name).mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
    for i, image in enumerate(images):
        sheet.paste(image, (i * w, 0))
        image.save(out / args.name / f"frame-{i:02d}.png")
    sheet.save(out / f"{args.name}.png")
    previews = []
    for image in images:
        big = image.resize((w * args.scale, h * args.scale), Image.NEAREST)
        bg = checker(big.size, args.scale * 4)
        bg.alpha_composite(big)
        previews.append(bg.convert("P", palette=Image.ADAPTIVE))
    previews[0].save(out / f"{args.name}.preview.gif", save_all=True, append_images=previews[1:], duration=ms, loop=0)

    manifest_path = out / "animation.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else \
        {"size": [w, h], "animations": {}}
    manifest["animations"][args.name] = {"sheet": f"{args.name}.png", "loop": not args.once, "frames": [
        {"rect": [i * w, 0, w, h], "ms": d, "pivot": pivot} for i, d in enumerate(ms)]}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    rows = list(manifest["animations"].values())
    cols = max(len(a["frames"]) for a in rows)
    s = args.scale
    contact = checker((cols * w * s, len(rows) * h * s), s * 4)
    for r, anim in enumerate(rows):
        with Image.open(out / anim["sheet"]) as strip:
            strip = strip.convert("RGBA")
            for c, frame in enumerate(anim["frames"]):
                x, y, fw, fh = frame["rect"]
                contact.alpha_composite(strip.crop((x, y, x + fw, y + fh)).resize((fw * s, fh * s), Image.NEAREST), (c * w * s, r * h * s))
    contact.save(out / "contact.png")
    print(f"wrote {out} ({args.name}: {len(images)} frames, {sum(ms)} ms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
