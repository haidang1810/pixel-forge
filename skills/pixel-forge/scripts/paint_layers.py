#!/usr/bin/env python3
"""Paint pixel detail onto the cutout layers of a character, in rest-pose canvas coordinates.

    python paint_layers.py BAKED.json EDITS.json --out PAINTED.json

Make BAKED.json with `rig2d.py SPEC.json --out DIR --bake BAKED.json`, render it with `--rest` and read
coordinates off rest-grid.png. EDITS.json is a list of edits, applied in order:

    [{"layer": "head", "color": "#2A1A20", "pixels": [[40, 18], [41, 18]]},
     {"layer": "head", "color": "k", "rect": [38, 20, 41, 21]},
     {"layer": "torso", "erase": [[30, 33]]}]

- layer: a cutout layer name (as listed by --list); the edit lands on that layer only, so it moves
  with that layer's bone in every frame.
- color: a palette symbol or #RRGGBB (new colors get a new symbol); pixels and/or rect (inclusive).
  An edit recolors only pixels the layer already has, so detail never changes the silhouette; add
  "grow": true to paint new pixels (a spike, a strap) and grow the layer.
- erase: pixels to clear. `--list` prints each layer's name, bone and box.
"""
import argparse
import json
from pathlib import Path
import sys

SYMBOLS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+-=?@"


def grid_of(layer):
    ox, oy = layer.get("origin", [0, 0])
    return {(ox + x, oy + y): ch for y, row in enumerate(layer["rows"]) for x, ch in enumerate(row) if ch != "."}


def rows_of(cells):
    if not cells:
        return [0, 0], ["."]
    x0, y0 = min(x for x, _ in cells), min(y for _, y in cells)
    x1, y1 = max(x for x, _ in cells), max(y for _, y in cells)
    return [x0, y0], ["".join(cells.get((x, y), ".") for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1)]


def apply(spec, edits):
    palette = spec["palette"]
    reverse = {v.upper(): k for k, v in palette.items()}
    layers = {layer["name"]: layer for layer in spec["cutout"] if "rows" in layer}
    for i, edit in enumerate(edits):
        name = edit.get("layer")
        if name not in layers:
            raise ValueError(f"edits[{i}]: no cutout layer named {name!r} (have: {', '.join(layers)})")
        layer = layers[name]
        cells = grid_of(layer)
        if "erase" in edit:
            for x, y in edit["erase"]:
                cells.pop((x, y), None)
        else:
            color = edit.get("color")
            if color in palette:
                symbol = color
            elif isinstance(color, str) and color.startswith("#") and len(color) == 7:
                symbol = reverse.get(color.upper())
                if symbol is None:
                    symbol = next(s for s in SYMBOLS if s not in palette and s != ".")
                    palette[symbol] = color.upper()
                    reverse[color.upper()] = symbol
            else:
                raise ValueError(f"edits[{i}]: color {color!r} is neither a palette symbol nor #RRGGBB")
            points = [tuple(p) for p in edit.get("pixels", [])]
            if "rect" in edit:
                x0, y0, x1, y1 = edit["rect"]
                points += [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
            for p in points:
                if p in cells or edit.get("grow"):
                    cells[p] = symbol
        layer["origin"], layer["rows"] = rows_of(cells)
    return spec


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec")
    parser.add_argument("edits", nargs="?")
    parser.add_argument("--out")
    parser.add_argument("--list", action="store_true", help="list the layers and their boxes")
    args = parser.parse_args(argv)
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8-sig"))
        if "cutout" not in spec:
            raise ValueError("the spec has no cutout layers; make them with rig2d.py --bake")
        if args.list:
            for layer in spec["cutout"]:
                if "rows" in layer:
                    (x0, y0), rows = layer["origin"], layer["rows"]
                    print(f"{layer['name']:12} bone {layer['bone']:10} z {layer['z']:3}  box {x0},{y0} to {x0 + len(rows[0]) - 1},{y0 + len(rows) - 1}")
            return 0
        if not args.edits or not args.out:
            raise ValueError("give EDITS.json and --out (or --list)")
        edits = json.loads(Path(args.edits).read_text(encoding="utf-8-sig"))
        apply(spec, edits)
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(spec, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
