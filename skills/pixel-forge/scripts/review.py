#!/usr/bin/env python3
"""Make one review image: key frames of every animation, enlarged, with a 1x and 2x row for readability.

    python review.py OUT_DIR --out review.png [--scale 8] [--frames 4]
    python review.py PREFIX.anim.json --out review.png      (a pixel_art.py animation)
    python review.py sword.png potion.png --out review.png  (static art at 1x, 2x, 4x and 8x)

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
    if folder.is_file() or folder.name.endswith(".anim.json"):  # a pixel_art.py animation
        anim = json.loads(folder.read_text(encoding="utf-8-sig"))
        strip = folder.with_name(folder.name[:-len(".anim.json")] + ".strip.png")
        with Image.open(strip) as sheet:
            sheet = sheet.convert("RGBA")
            yield strip.stem, [sheet.crop((x, y, x + w, y + h)) for x, y, w, h in (f["rect"] for f in anim["frames"])]
        return
    manifest = json.loads((folder / "animation.json").read_text(encoding="utf-8-sig"))
    for name, anim in manifest["animations"].items():
        with Image.open(folder / anim["sheet"]) as sheet:
            sheet = sheet.convert("RGBA")
            yield name, [sheet.crop((x, y, x + w, y + h)) for x, y, w, h in (f["rect"] for f in anim["frames"])]


def review_images(paths, out):
    """Static art (items, icons, props): each image at 1x, 2x and 4x on a dark game-like background,
    the sizes a player and an inventory grid show it at, plus an 8x view to inspect clusters."""
    images = []
    for path in paths:
        with Image.open(path) as image:
            images.append((path.stem, image.convert("RGBA")))
    rows = []
    for name, image in images:
        tiles = [image.resize((image.width * s, image.height * s), Image.NEAREST) for s in (1, 2, 4, 8)]
        rows.append((name, tiles))
    width = max(sum(t.width + 8 for t in tiles) for _, tiles in rows) + 8
    height = sum(14 + max(t.height for t in tiles) + 8 for _, tiles in rows)
    sheet = Image.new("RGBA", (width, height), (24, 27, 38, 255))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for name, tiles in rows:
        draw.text((6, y + 2), f"{name}: 1x 2x 4x 8x", fill=(220, 225, 240, 255))
        y += 14
        x = 6
        for t in tiles:
            sheet.paste(BG, (x, y, x + t.width, y + t.height))
            sheet.alpha_composite(t, (x, y))
            x += t.width + 8
        y += max(t.height for t in tiles) + 8
    sheet.save(out)
    print(f"wrote {out}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", help="a rig2d or sheet.py output folder, or a pixel_art PREFIX.anim.json")
    parser.add_argument("more", nargs="*", help="more PNGs, when reviewing static art")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument("--frames", type=int, default=4, help="key frames per animation")
    parser.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "W", "H"),
                        help="tile this region of every frame side by side, enlarged (fire, smoke, a hand)")
    args = parser.parse_args(argv)
    if all(f.lower().endswith(".png") for f in [args.folder] + args.more):
        return review_images([Path(f) for f in [args.folder] + args.more], Path(args.out))
    folder = Path(args.folder)
    if folder.is_dir() and not (folder / "animation.json").is_file():
        found = sorted(folder.glob("*.anim.json"))
        if len(found) == 1:
            folder = found[0]
    if not (folder.is_file() and folder.name.endswith(".anim.json")) and not (folder / "animation.json").is_file():
        print(f"error: {folder}: expected a rig2d/sheet.py folder (animation.json) or a pixel_art PREFIX.anim.json",
              file=sys.stderr)
        return 2
    if args.region:
        x, y, rw, rh = args.region
        s = max(2, min(16, 960 // max(rw, rh)))
        crops = [(name, [f.crop((x, y, x + rw, y + rh)) for f in frames]) for name, frames in load(folder)]
        cols = max(len(c) for _, c in crops)
        sheet = Image.new("RGBA", (cols * (rw * s + 4) + 4, len(crops) * (rh * s + 18)), (24, 27, 38, 255))
        draw = ImageDraw.Draw(sheet)
        for r_, (name, cs) in enumerate(crops):
            top = r_ * (rh * s + 18)
            draw.text((4, top + 2), f"{name}: region {x},{y} {rw}x{rh}, frames 0-{len(cs) - 1}", fill=(220, 225, 240, 255))
            for i, c in enumerate(cs):
                big = c.resize((rw * s, rh * s), Image.NEAREST)
                tile = checker(big.size, s * 4)
                tile.alpha_composite(big)
                sheet.alpha_composite(tile, (4 + i * (rw * s + 4), top + 14))
        sheet.save(args.out)
        print(f"wrote {args.out}")
        return 0
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
