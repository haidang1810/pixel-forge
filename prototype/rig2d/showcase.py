#!/usr/bin/env python3
"""Combine rendered animations into one labeled, looping GIF grid."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def load(root, character, anim):
    manifest = json.loads((root / character / "animation.json").read_text(encoding="utf-8"))
    entry = manifest["animations"][anim]
    sheet = Image.open(root / character / entry["sheet"]).convert("RGBA")
    return [(sheet.crop((x, y, x + w, y + h)), f["ms"]) for f in entry["frames"] for x, y, w, h in [f["rect"]]]


def frame_at(frames, t):
    t %= sum(ms for _, ms in frames)
    for image, ms in frames:
        if t < ms:
            return image
        t -= ms


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cells", nargs="+", help="character/anim, e.g. knight/walk")
    parser.add_argument("--root", required=True, help="folder holding rendered characters")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=6)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--length", type=int, default=2400, help="GIF length in ms")
    args = parser.parse_args(argv)

    root = Path(args.root)
    anims = [(cell.replace("/", " - "), load(root, *cell.split("/"))) for cell in args.cells]
    fw = max(f[0][0].width for _, f in anims) * args.scale
    fh = max(f[0][0].height for _, f in anims) * args.scale
    pad, label, step = 8, 18, 20
    cw, ch = fw + pad * 2, fh + label + pad * 2
    rows = -(-len(anims) // args.cols)
    background = Image.new("RGBA", (cw * args.cols, ch * rows), (30, 34, 48, 255))
    draw = ImageDraw.Draw(background)
    cell = args.scale * 4
    for i, (name, _) in enumerate(anims):
        x, y = (i % args.cols) * cw + pad, (i // args.cols) * ch + pad
        for yy in range(0, fh, cell):
            for xx in range(0, fw, cell):
                if (xx // cell + yy // cell) % 2:
                    draw.rectangle([x + xx, y + label + yy, x + xx + cell - 1, y + label + yy + cell - 1], fill=(40, 45, 62, 255))
        draw.text((x, y), name, fill=(220, 225, 240, 255))

    frames, durations = [], []
    for t in range(0, args.length, step):
        frame = background.copy()
        for i, (_, anim) in enumerate(anims):
            x, y = (i % args.cols) * cw + pad, (i // args.cols) * ch + pad + label
            image = frame_at(anim, t)
            frame.alpha_composite(image.resize((image.width * args.scale, image.height * args.scale), Image.NEAREST), (x, y))
        if frames and frame.tobytes() == frames[-1].tobytes():
            durations[-1] += step
        else:
            frames.append(frame)
            durations.append(step)
    strip = Image.new("RGB", (frames[0].width, frames[0].height * len(frames)))
    for i, frame in enumerate(frames):
        strip.paste(frame.convert("RGB"), (0, i * frames[0].height))
    palette = strip.quantize(colors=255, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    out = [f.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    out[0].save(args.out, save_all=True, append_images=out[1:], duration=durations, loop=0)
    print(f"wrote {args.out}: {len(out)} frames")


if __name__ == "__main__":
    main()
