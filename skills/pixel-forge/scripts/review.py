#!/usr/bin/env python3
"""Make one review image: key frames of every animation, enlarged, with a 1x and 2x row for readability.

    python review.py OUT_DIR --out review.png [--scale 8] [--frames 4]

Key frames are the first frame and the frames that differ most from their neighbours (the extremes of
a stride or a swing). Each row also shows the animation at 1x and 2x, the way a player sees it. Use it
with the critique rubric in SKILL.md: look at this image, score each criterion, fix the worst defect.
"""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw

BG = (38, 43, 61, 255)
BG2 = (48, 54, 76, 255)


def checker(size, cell):
    bg = Image.new("RGBA", size, BG)
    draw = ImageDraw.Draw(bg)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=BG2)
    return bg


def difference(a, b):
    diff = ImageChops.difference(a, b).convert("L")
    return sum(diff.histogram()[1:])


def key_frames(frames, count):
    if len(frames) <= count:
        return list(range(len(frames)))
    scores = []
    for i in range(1, len(frames)):
        scores.append((difference(frames[i - 1], frames[i]) + difference(frames[i], frames[(i + 1) % len(frames)]), i))
    picks = {0} | {i for _, i in sorted(scores, reverse=True)[:count - 1]}
    return sorted(picks)


def load(folder):
    manifest = json.loads((folder / "animation.json").read_text(encoding="utf-8-sig"))
    for name, anim in manifest["animations"].items():
        with Image.open(folder / anim["sheet"]) as sheet:
            sheet = sheet.convert("RGBA")
            yield name, [sheet.crop((x, y, x + w, y + h)) for x, y, w, h in (f["rect"] for f in anim["frames"])]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", help="a rig2d or sheet.py output folder")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument("--frames", type=int, default=4, help="key frames per animation")
    args = parser.parse_args(argv)
    folder = Path(args.folder)
    if not (folder / "animation.json").is_file():
        print(f"error: {folder}: no animation.json", file=sys.stderr)
        return 2
    rows = []
    for name, frames in load(folder):
        picks = key_frames(frames, args.frames)
        rows.append((name, frames, picks))
    w, h = rows[0][1][0].size
    s = args.scale
    label = 14
    small = max(len(f) for _, f, _ in rows) * w * 3 + 8
    width = max(args.frames * (w * s + 6), small) + 12
    height = sum(label + h * s + 6 + h * 2 + 10 for _ in rows)
    out = Image.new("RGBA", (width, height), (24, 27, 38, 255))
    draw = ImageDraw.Draw(out)
    y = 0
    for name, frames, picks in rows:
        draw.text((6, y + 2), f"{name}: frames {', '.join(str(i) for i in picks)} of {len(frames)}", fill=(220, 225, 240, 255))
        y += label
        x = 6
        for i in picks:
            big = frames[i].resize((w * s, h * s), Image.NEAREST)
            tile = checker(big.size, s * 4)
            tile.alpha_composite(big)
            out.alpha_composite(tile, (x, y))
            x += w * s + 6
        y += h * s + 6
        x = 6
        for frame in frames:  # 1x and 2x, as in game
            out.paste(BG, (x, y, x + w, y + h))
            out.alpha_composite(frame, (x, y))
            two = frame.resize((w * 2, h * 2), Image.NEAREST)
            out.paste(BG, (x + w + 2, y, x + w * 3 + 2, y + h * 2))
            out.alpha_composite(two, (x + w + 2, y))
            x += w * 3 + 4
        y += h * 2 + 10
    out.save(args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
