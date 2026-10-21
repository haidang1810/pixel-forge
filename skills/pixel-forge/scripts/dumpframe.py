#!/usr/bin/env python3
"""Print a rendered frame (or a region of it) as palette characters, for precise hand edits."""
import argparse
import json
from pathlib import Path

from PIL import Image


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec")
    parser.add_argument("frame")
    parser.add_argument("--box", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"), help="inclusive region")
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    lookup = {}
    for k, v in spec.get("palette", {}).items():
        lookup.setdefault(tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)), k)
    lookup[tuple(int(spec["outline"][i:i + 2], 16) for i in (1, 3, 5))] = "k"
    image = Image.open(args.frame).convert("RGBA")
    x0, y0, x1, y1 = args.box or (0, 0, image.width - 1, image.height - 1)
    # the box is inclusive; clamp it to the frame instead of failing on an out-of-range corner
    x0, x1 = max(0, min(x0, x1)), min(image.width - 1, max(x0, x1))
    y0, y1 = max(0, min(y0, y1)), min(image.height - 1, max(y0, y1))
    print("    " + "".join(str(x // 10) for x in range(x0, x1 + 1)))
    print("    " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
    for y in range(y0, y1 + 1):
        row = ""
        for x in range(x0, x1 + 1):
            r, g, b, a = image.getpixel((x, y))
            row += "." if not a else lookup.get((r, g, b), "?")
        print(f"{y:3d} {row}")


if __name__ == "__main__":
    main()
