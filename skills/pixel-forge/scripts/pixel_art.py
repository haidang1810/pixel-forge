#!/usr/bin/env python3
"""Deterministic palette-based pixel art renderer; no image-generation service."""
import argparse
from collections import Counter
import copy
import json
import math
from pathlib import Path
import re
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("Pillow is required. Run this Python interpreter with -m pip install Pillow.")


def object_keys(value, allowed, where):
    if not isinstance(value, dict):
        raise ValueError(f"{where}: expected an object")
    unknown = set(value) - set(allowed)
    if unknown:
        raise ValueError(f"{where}: unknown fields {sorted(unknown)}")


def integer(value, where, minimum=0, maximum=512):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{where}: expected integer {minimum}..{maximum}")
    return value


def pair(value, where, minimum=0, maximum=512):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{where}: expected [x, y] or [width, height]")
    return tuple(integer(n, where, minimum, maximum) for n in value)


def read_json(path):
    def finite_number(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"non-finite JSON number: {value}")
        return number

    def reject_constant(value):
        raise ValueError(f"invalid JSON constant: {value}")

    def unique_keys(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle, object_pairs_hook=unique_keys, parse_constant=reject_constant, parse_float=finite_number)


def same_file(first, second):
    """Protect inputs even when an output is a symlink or hard-link alias."""
    first, second = Path(first), Path(second)
    return first.resolve() == second.resolve() or (first.exists() and second.exists() and first.samefile(second))


def parse_palette(value):
    if not isinstance(value, dict) or not value:
        raise ValueError("palette: expected a nonempty object")
    result = {}
    for symbol, color in value.items():
        if not isinstance(symbol, str) or len(symbol) != 1 or not 33 <= ord(symbol) <= 126:
            raise ValueError("palette: symbols must be single visible ASCII characters")
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?", color):
            raise ValueError(f"palette.{symbol}: expected #RRGGBB or #RRGGBBAA")
        rgba = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)) + (int(color[7:9], 16) if len(color) == 9 else 255,)
        if rgba[3] not in (0, 255):
            raise ValueError(f"palette.{symbol}: version 1 supports alpha 00 or FF only")
        result[symbol] = (0, 0, 0, 0) if rgba[3] == 0 else rgba
    return result


def paint_operation(image, operation, palette, origin, where):
    if not isinstance(operation, dict):
        raise ValueError(f"{where}: expected operation object")
    kind = operation.get("op")
    fields = {
        "rect": {"op", "xy", "size", "color"},
        "ellipse": {"op", "xy", "size", "color"},
        "polygon": {"op", "points", "color"},
        "line": {"op", "points", "color"},
        "pixels": {"op", "points", "color"},
    }
    if not isinstance(kind, str) or kind not in fields:
        raise ValueError(f"{where}: op must be rect, ellipse, polygon, line, or pixels")
    object_keys(operation, fields[kind], where)
    symbol = operation.get("color")
    if not isinstance(symbol, str) or symbol not in palette:
        raise ValueError(f"{where}: color {symbol!r} is not in palette")
    color = palette[symbol]

    def point(value):
        x, y = pair(value, where + ".coordinate")
        x, y = x + origin[0], y + origin[1]
        if not 0 <= x < image.width or not 0 <= y < image.height:
            raise ValueError(f"{where}: coordinate {(x, y)} outside canvas {image.size}")
        return x, y

    draw = ImageDraw.Draw(image)
    if kind in ("rect", "ellipse"):
        x, y = point(operation.get("xy"))
        width, height = pair(operation.get("size"), where + ".size", 1)
        if x + width > image.width or y + height > image.height:
            raise ValueError(f"{where}: shape extends outside canvas")
        box = (x, y, x + width - 1, y + height - 1)
        if kind == "rect":
            draw.rectangle(box, fill=color)
        else:
            draw.ellipse(box, fill=color)
    else:
        coordinates = operation.get("points")
        required = {"polygon": 3, "line": 2, "pixels": 1}[kind]
        if not isinstance(coordinates, list) or len(coordinates) < required:
            raise ValueError(f"{where}: {kind} needs at least {required} points")
        points = [point(p) for p in coordinates]
        if kind == "polygon":
            draw.polygon(points, fill=color)
        elif kind == "line":
            draw.line(points, fill=color, width=1)
        else:
            draw.point(points, fill=color)


def render_document(document):
    """Return a native RGBA image and factual report, or raise ValueError."""
    object_keys(document, {"version", "size", "palette", "layers", "meta"}, "document")
    if type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("version: expected 1")
    size = pair(document.get("size"), "size", 1)
    palette = parse_palette(document.get("palette"))
    if "meta" in document and not isinstance(document["meta"], dict):
        raise ValueError("meta: expected object")
    layers = document.get("layers")
    if not isinstance(layers, list) or not layers:
        raise ValueError("layers: expected a nonempty list")
    canvas = Image.new("RGBA", size)
    names = set()
    layer_report = []
    for index, layer in enumerate(layers):
        where = f"layers[{index}]"
        object_keys(layer, {"name", "origin", "visible", "rows", "ops"}, where)
        name = layer.get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError(f"{where}.name: expected nonempty unique layer name")
        names.add(name)
        where += f" ({name})"
        visible = layer.get("visible", True)
        if type(visible) is not bool:
            raise ValueError(f"{where}.visible: expected true or false")
        origin = pair(layer.get("origin", [0, 0]), where + ".origin")
        if origin[0] >= size[0] or origin[1] >= size[1]:
            raise ValueError(f"{where}.origin: outside canvas")
        if "rows" not in layer and "ops" not in layer:
            raise ValueError(f"{where}: provide rows or ops")
        image = Image.new("RGBA", size)
        if "rows" in layer:
            rows = layer["rows"]
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], str) or not rows[0]:
                raise ValueError(f"{where}.rows: expected nonempty strings")
            width = len(rows[0])
            if width + origin[0] > size[0] or len(rows) + origin[1] > size[1]:
                raise ValueError(f"{where}.rows: extends outside canvas")
            pixels = image.load()
            for y, row in enumerate(rows):
                if not isinstance(row, str) or len(row) != width:
                    raise ValueError(f"{where}.rows[{y}]: expected {width} characters")
                for x, symbol in enumerate(row):
                    if symbol not in palette:
                        raise ValueError(f"{where}.rows[{y}][{x}]: unknown palette symbol {symbol!r}")
                    pixels[x + origin[0], y + origin[1]] = palette[symbol]
        if "ops" in layer:
            if not isinstance(layer["ops"], list):
                raise ValueError(f"{where}.ops: expected list")
            for op_index, operation in enumerate(layer["ops"]):
                paint_operation(image, operation, palette, origin, f"{where}.ops[{op_index}]")
        if visible:
            canvas = Image.alpha_composite(canvas, image)
        layer_report.append({"name": name, "visible": visible, "bbox": image.getbbox()})

    raw = iter(canvas.tobytes())
    counts = Counter(zip(raw, raw, raw, raw))
    opaque = sum(count for rgba, count in counts.items() if rgba[3])
    bbox = canvas.getbbox()
    warnings = []
    if not opaque:
        warnings.append("No visible pixels.")
    if bbox and (bbox[0] == 0 or bbox[1] == 0 or bbox[2] == size[0] or bbox[3] == size[1]):
        warnings.append("Artwork touches a canvas edge; check intended padding or tile seams.")
    return canvas, {
        "renderer": "pixel-art-json/1", "size": list(size), "mode": "RGBA",
        "opaque_pixels": opaque, "transparent_pixels": size[0] * size[1] - opaque,
        "bbox": list(bbox) if bbox else None,
        "colors": {"#" + "".join(f"{n:02X}" for n in rgba): count for rgba, count in sorted(counts.items())},
        "layers": layer_report, "warnings": warnings,
        "meta": copy.deepcopy(document.get("meta", {})),
    }


def patch_document(document, patch):
    """Apply palette replacements and appended layer-local operations to a copy."""
    render_document(document)
    object_keys(patch, {"palette", "edits"}, "patch")
    if not patch:
        raise ValueError("patch: provide palette or edits")
    updated = copy.deepcopy(document)
    if "palette" in patch:
        parse_palette(patch["palette"])
        updated["palette"].update(patch["palette"])
    edits = patch.get("edits", [])
    if not isinstance(edits, list):
        raise ValueError("patch.edits: expected list")
    by_name = {layer["name"]: layer for layer in updated["layers"]}
    for index, edit in enumerate(edits):
        if not isinstance(edit, dict):
            raise ValueError(f"patch.edits[{index}]: expected object")
        name = edit.get("layer")
        if not isinstance(name, str) or name not in by_name:
            raise ValueError(f"patch.edits[{index}]: unknown layer {name!r}")
        operation = {key: copy.deepcopy(value) for key, value in edit.items() if key != "layer"}
        by_name[name].setdefault("ops", []).append(operation)
    render_document(updated)
    return updated


def preview(image, scale, grid=False):
    scale = integer(scale, "scale", 1, 32)
    if grid:
        scale = max(4, scale)
    if max(image.size) * scale > 4096:
        raise ValueError("preview exceeds 4096 pixels per side; use a smaller --scale")
    backing = Image.new("RGBA", image.size, "#252937")
    draw = ImageDraw.Draw(backing)
    for y in range(image.height):
        for x in range(image.width):
            if (x // 4 + y // 4) % 2:
                draw.point((x, y), fill="#303647")
    backing = Image.alpha_composite(backing, image)
    enlarged = backing.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    if not grid:
        return enlarged
    margin = 24
    result = Image.new("RGB", (enlarged.width + margin, enlarged.height + margin), "#171B25")
    result.paste(enlarged, (margin, margin))
    draw = ImageDraw.Draw(result)
    label_step = max(1, (18 + scale - 1) // scale)
    for x in range(image.width + 1):
        xx = margin + x * scale
        draw.line((xx, margin, xx, result.height - 1), fill="#454B5A")
        if x < image.width and x % label_step == 0:
            draw.text((xx + 1, 6), str(x), fill="#C5CBDB")
    for y in range(image.height + 1):
        yy = margin + y * scale
        draw.line((margin, yy, result.width - 1, yy), fill="#454B5A")
        if y < image.height and y % label_step == 0:
            draw.text((2, yy + 1), str(y), fill="#C5CBDB")
    return result


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate source and print factual report")
    check.add_argument("source", type=Path)
    render = commands.add_parser("render", help="Export native PNG, checker preview, and report")
    render.add_argument("source", type=Path)
    render.add_argument("--out", required=True, type=Path, help="Output prefix; suffixes are appended")
    render.add_argument("--scale", type=int, default=12)
    render.add_argument("--grid", action="store_true", help="Export a coordinate grid (minimum 4x); existing grids are refreshed")
    patch_parser = commands.add_parser("patch", help="Save validated edits as a new JSON document")
    patch_parser.add_argument("source", type=Path)
    patch_parser.add_argument("patch_file", type=Path)
    patch_parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        source = read_json(args.source)
        if args.command == "patch":
            if same_file(args.output, args.source) or same_file(args.output, args.patch_file):
                raise ValueError("--output must differ from source and patch file; keep the original revision")
            updated = patch_document(source, read_json(args.patch_file))
            write_json(args.output, updated)
            print(json.dumps({"source": str(args.output.resolve())}))
            return 0
        image, report = render_document(source)
        if args.command == "validate":
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        paths = {"png": Path(str(args.out) + ".png"), "preview": Path(str(args.out) + ".preview.png"), "report": Path(str(args.out) + ".report.json")}
        grid_path = Path(str(args.out) + ".grid.png")
        if args.grid or grid_path.exists():
            paths["grid"] = grid_path
        if any(same_file(args.source, path) for path in paths.values()):
            raise ValueError("output path would overwrite source JSON; choose another --out prefix")
        enlarged = preview(image, args.scale)
        grid_image = preview(image, args.scale, grid=True) if "grid" in paths else None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        image.save(paths["png"], format="PNG")
        enlarged.save(paths["preview"], format="PNG")
        if grid_image:
            grid_image.save(paths["grid"], format="PNG")
        write_json(paths["report"], report)
        print(json.dumps({"files": {name: str(path.resolve()) for name, path in paths.items()}, "size": report["size"], "warnings": report["warnings"]}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, OverflowError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
