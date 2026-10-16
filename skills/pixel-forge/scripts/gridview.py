#!/usr/bin/env python3
"""Enlarge rendered frames over a labeled pixel grid, to find coordinates for hand touch-ups."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def grid_image(image, scale, background=(128, 128, 128, 255)):
    w, h = image.size
    m = 22
    sheet = Image.new("RGBA", (w * scale + m, h * scale + m), (30, 34, 48, 255))
    sheet.paste(Image.new("RGBA", (w * scale, h * scale), background), (m, m))
    sheet.alpha_composite(image.resize((w * scale, h * scale), Image.NEAREST), (m, m))
    draw = ImageDraw.Draw(sheet)
    for x in range(w + 1):
        draw.line([(m + x * scale, m), (m + x * scale, m + h * scale)],
                  fill=(150, 150, 150, 90) if x % 5 else (230, 230, 240, 160))
        if x % 5 == 0 and x < w:
            draw.text((m + x * scale + 1, 4), str(x), fill=(230, 230, 240, 255))
    for y in range(h + 1):
        draw.line([(m, m + y * scale), (m + w * scale, m + y * scale)],
                  fill=(150, 150, 150, 90) if y % 5 else (230, 230, 240, 160))
        if y % 5 == 0 and y < h:
            draw.text((2, m + y * scale + 1), str(y), fill=(230, 230, 240, 255))
    return sheet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", nargs="+")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=10)
    parser.add_argument("--cols", type=int, default=2)
    args = parser.parse_args(argv)
    sheets = [grid_image(Image.open(p).convert("RGBA"), args.scale) for p in args.frames]
    sw, sh = sheets[0].size
    rows = -(-len(sheets) // args.cols)
    out = Image.new("RGBA", (sw * args.cols, sh * rows), (20, 22, 30, 255))
    for i, sheet in enumerate(sheets):
        out.alpha_composite(sheet, ((i % args.cols) * sw, (i // args.cols) * sh))
    out.save(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
