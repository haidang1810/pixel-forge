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


BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
BASIC_OPS = {
    "rect": {"op", "xy", "size", "color"},
    "ellipse": {"op", "xy", "size", "color"},
    "polygon": {"op", "points", "color"},
    "line": {"op", "points", "color", "width"},
    "pixels": {"op", "points", "color"},
}
# Richer operations: they clip to the canvas instead of rejecting out-of-bounds shapes.
EXTRA_OPS = {
    "circle": {"op", "center", "r", "color", "ring"},
    "box": {"op", "xy", "size", "color"},
    "fill": {"op", "xy", "color"},
    "dither": {"op", "xy", "size", "colors", "density"},
    "gradient": {"op", "xy", "size", "colors", "dir", "soft"},
    "noise": {"op", "xy", "size", "colors", "density", "seed", "on"},
    "shade": {"op", "region", "steps", "density"},
    "light": {"op", "region", "steps", "density"},
    "recolor": {"op", "map", "region", "density"},
    "stamp": {"op", "part", "xy", "flip", "swap"},
    "scatter": {"op", "parts", "xy", "size", "count", "seed", "on", "clip", "flip"},
    "grid": {"op", "xy", "rows"},
    "bolt": {"op", "from", "to", "colors", "seed", "jag", "width", "branches", "fade", "flicker", "taper", "rim", "reach"},
    "ring": {"op", "center", "radius", "colors", "width", "squash", "breakup", "seed", "arc"},
    "flames": {"op", "xy", "size", "colors", "count", "t", "period", "seed", "lean"},
    "particles": {"op", "origin", "colors", "count", "t", "period", "life", "speed", "angle", "spread", "gravity",
                  "seed", "size", "mode", "trail"},
    "smoke": {"op", "origin", "colors", "count", "t", "period", "rise", "drift", "radius", "grow", "seed"},
}


class Context:
    """Palette lookups shared by every layer, part and frame of one document."""

    def __init__(self, palette, ramps=(), parts=None):
        self.palette = palette
        self.ramp_names = list(ramps)
        self.symbol_of = {}
        for symbol, rgba in palette.items():
            self.symbol_of.setdefault(rgba, symbol)
        self.ramp_of = {}
        for ramp in ramps:
            colors = [palette[ch] for ch in ramp]
            for i, rgba in enumerate(colors):
                self.ramp_of.setdefault(rgba, (colors, i))
        self.parts = parts or {}
        self.part_images = {}
        self.materials = {}
        self.light = (-0.7071, -0.7071)

    def color(self, symbol, where):
        if not isinstance(symbol, str) or symbol not in self.palette:
            raise ValueError(f"{where}: color {symbol!r} is not in palette")
        return self.palette[symbol]

    def step(self, rgba, n):
        """Move a color n steps along its ramp (negative = darker); colors outside every ramp stay."""
        if rgba[3] == 0 or rgba not in self.ramp_of:
            return rgba
        colors, i = self.ramp_of[rgba]
        return colors[max(0, min(len(colors) - 1, i + n))]


def number(value, where, minimum=-1024, maximum=1024):
    if type(value) not in (int, float) or not minimum <= value <= maximum:
        raise ValueError(f"{where}: expected a number {minimum}..{maximum}")
    return value


def ipair(value, where, minimum=-1024, maximum=1024):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{where}: expected [x, y]")
    return tuple(int(number(n, where, minimum, maximum)) for n in value)


def dithered(x, y, density):
    return BAYER4[y % 4][x % 4] < density * 16


def region_test(region, origin, where):
    """A region in layer coordinates: {"rect": [x, y, w, h]}, {"circle": [cx, cy, r]} or
    {"polygon": [[x, y], ...]}; omitted means everywhere."""
    if region is None:
        return lambda x, y: True
    if not isinstance(region, dict) or len(region) != 1:
        raise ValueError(f"{where}.region: expected {{\"rect\"|\"circle\"|\"polygon\": ...}}")
    kind, value = next(iter(region.items()))
    ox, oy = origin
    if kind == "rect" and isinstance(value, list) and len(value) == 4:
        x0, y0, w, h = (int(number(v, where)) for v in value)
        return lambda x, y: x0 + ox <= x < x0 + ox + w and y0 + oy <= y < y0 + oy + h
    if kind == "circle" and isinstance(value, list) and len(value) == 3:
        cx, cy, r = (number(v, where) for v in value)
        return lambda x, y: (x - cx - ox) ** 2 + (y - cy - oy) ** 2 <= r * r + r * 0.8
    if kind == "polygon" and isinstance(value, list) and len(value) >= 3:
        pts = [(px_ + ox, py_ + oy) for px_, py_ in (ipair(v, where) for v in value)]
        return lambda x, y: inside_polygon(pts, x + 0.5, y + 0.5)
    raise ValueError(f"{where}.region: expected rect [x, y, w, h], circle [cx, cy, r] or polygon [[x, y], ...]")


def inside_polygon(pts, x, y):
    hit = False
    j = len(pts) - 1
    for i, (xi, yi) in enumerate(pts):
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def put(px, size, x, y, rgba):
    if 0 <= x < size[0] and 0 <= y < size[1]:
        px[x, y] = rgba


def disc(r):
    return [(dx, dy) for dy in range(-int(r) - 1, int(r) + 2) for dx in range(-int(r) - 1, int(r) + 2)
            if dx * dx + dy * dy <= r * r + r * 0.8]


def line_points(a, b):
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        yield x0, y0
        if (x0, y0) == (x1, y1):
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def render_part(name, ctx, where, depth=0):
    if name in ctx.part_images:
        return ctx.part_images[name]
    if name not in ctx.parts:
        raise ValueError(f"{where}: unknown part {name!r} (have: {', '.join(sorted(ctx.parts)) or 'none'})")
    if depth > 8:
        raise ValueError(f"{where}: parts nest too deeply")
    part = ctx.parts[name]
    object_keys(part, {"size", "rows", "layers", "mirror", "outline"}, f"parts.{name}")
    if "rows" in part:
        rows = part["rows"]
        if not isinstance(rows, list) or not rows or not all(isinstance(r, str) for r in rows):
            raise ValueError(f"parts.{name}.rows: expected strings")
        size = part.get("size") or [max(len(r) for r in rows), len(rows)]
        layers = [{"name": "rows", "rows": [r.ljust(size[0], ".") for r in rows]}]
    else:
        size, layers = part.get("size"), part.get("layers")
    size = pair(size, f"parts.{name}.size", 1)
    image = composite(size, layers, ctx, f"parts.{name}", part, depth + 1)
    ctx.part_images[name] = image
    return image


def paint_operation(image, operation, ctx, origin, where, depth=0):
    if not isinstance(operation, dict):
        raise ValueError(f"{where}: expected operation object")
    kind = operation.get("op")
    if kind in EXTRA_OPS:
        object_keys(operation, EXTRA_OPS[kind], where)
        return paint_extra(image, operation, ctx, origin, where, depth)
    if not isinstance(kind, str) or kind not in BASIC_OPS:
        raise ValueError(f"{where}: op must be one of {', '.join(list(BASIC_OPS) + list(EXTRA_OPS))}")
    object_keys(operation, BASIC_OPS[kind], where)
    color = ctx.color(operation.get("color"), where)

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
        elif kind == "line" and operation.get("width", 1) != 1:
            brush = disc((number(operation["width"], where + ".width", 1, 32) - 1) / 2)
            px = image.load()
            for a, b in zip(points, points[1:]):
                for x, y in line_points(a, b):
                    for dx, dy in brush:
                        put(px, image.size, x + dx, y + dy, color)
        elif kind == "line":
            draw.line(points, fill=color, width=1)
        else:
            draw.point(points, fill=color)


def paint_extra(image, op, ctx, origin, where, depth):
    kind = op["op"]
    px = image.load()
    size = image.size
    ox, oy = origin

    def area():
        x, y = ipair(op.get("xy"), where + ".xy")
        w, h = pair(op.get("size"), where + ".size", 1, 1024)
        return [(x + ox + i, y + oy + j) for j in range(h) for i in range(w)
                if 0 <= x + ox + i < size[0] and 0 <= y + oy + j < size[1]], (x + ox, y + oy, w, h)

    def symbols(value, field):
        if not isinstance(value, str) or not value or any(ch not in ctx.palette for ch in value):
            raise ValueError(f"{where}.{field}: expected palette symbols")
        return [ctx.palette[ch] for ch in value]

    def density():
        return number(op.get("density", 1), where + ".density", 0, 1)

    if kind in ("bolt", "ring", "flames", "particles", "smoke"):
        # Procedural effects (vfx.py): intensities 0..1 mapped onto a dark-to-light `colors` ramp.
        import importlib.util
        spec_ = importlib.util.spec_from_file_location("vfx", Path(__file__).with_name("vfx.py"))
        vfx = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(vfx)
        ramp = symbols(op.get("colors"), "colors")
        num = lambda key, default, lo=-1024, hi=1024: number(op.get(key, default), f"{where}.{key}", lo, hi)
        if kind == "bolt":
            a, b = ipair(op.get("from"), where + ".from"), ipair(op.get("to"), where + ".to")
            cells = vfx.bolt((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), seed=int(num("seed", 1, -2**31, 2**31)),
                             jag=num("jag", 0.35, 0, 1), width=num("width", 2, 0.5, 12),
                             branches=int(num("branches", 2, 0, 12)), fade=num("fade", 0, 0, 1),
                             flicker=op.get("flicker"), taper=num("taper", 0.6, 0.5, 12), rim=op.get("rim", True) is not False,
                             reach=num("reach", 1, 0, 4))
        elif kind == "ring":
            c = pair(op.get("center"), where + ".center", -2048, 2048)
            arc = op.get("arc")
            if arc is not None:
                arc = pair(arc, where + ".arc", -360, 720)
            cells = vfx.ring(c[0] + ox, c[1] + oy, num("radius", 8, 0.5, 2048), width=num("width", 2, 0.5, 256),
                             squash=num("squash", 1, 0.05, 4), breakup=num("breakup", 0, 0, 1), seed=int(num("seed", 1, -2**31, 2**31)),
                             arc=arc)
        elif kind == "flames":
            x0, y0 = ipair(op.get("xy"), where + ".xy")
            fw, fh = pair(op.get("size"), where + ".size", 1, 1024)
            cells = vfx.flames(x0 + ox, y0 + oy + fh - 1, fw, fh, count=int(num("count", 4, 1, 64)), t=num("t", 0),
                               period=int(num("period", 8, 1, 240)), seed=int(num("seed", 1, -2**31, 2**31)), lean=num("lean", 0))
        elif kind == "particles":
            x0, y0 = ipair(op.get("origin"), where + ".origin")
            mode = op.get("mode", "loop")
            if mode not in ("loop", "burst"):
                raise ValueError(f"{where}.mode: expected loop or burst")
            cells = vfx.particles(x0 + ox, y0 + oy, count=int(num("count", 10, 1, 512)), t=num("t", 0),
                                  period=int(num("period", 8, 1, 240)), life=op.get("life"), speed=num("speed", 1.5),
                                  angle=num("angle", -90), spread=num("spread", 60, 0, 360), gravity=num("gravity", 0),
                                  seed=int(num("seed", 1, -2**31, 2**31)), size=num("size", 2, 0.5, 16), mode=mode,
                                  trail=int(num("trail", 0, 0, 16)))
        else:
            x0, y0 = ipair(op.get("origin"), where + ".origin")
            cells = vfx.smoke(x0 + ox, y0 + oy, count=int(num("count", 4, 1, 64)), t=num("t", 0),
                              period=int(num("period", 12, 1, 240)), rise=num("rise", 1.0), drift=num("drift", 0.3),
                              radius=num("radius", 2.0, 0.5, 64), grow=num("grow", 0.25), seed=int(num("seed", 1, -2**31, 2**31)))
        top = len(ramp) - 1
        for (x, y), v in cells.items():
            if kind == "bolt" and v <= 0 and 0 <= x < size[0] and 0 <= y < size[1] and px[x, y][3]:
                continue  # a bolt's dark rim never paints over what is already there (braided bolts stay seamless)
            put(px, size, x, y, ramp[max(0, min(top, round(v * top)))])
    elif kind == "grid":
        # Paste rows of palette symbols at xy; a space leaves the pixel below untouched. This is the
        # read-back loop: `pixel_art.py ascii` prints the art in the same symbols, you change a few.
        x0, y0 = ipair(op.get("xy"), where + ".xy")
        rows = op.get("rows")
        if not isinstance(rows, list) or not all(isinstance(r, str) for r in rows):
            raise ValueError(f"{where}.rows: expected a list of strings")
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == " ":
                    continue
                put(px, size, x0 + ox + i, y0 + oy + j, ctx.color(ch, f"{where}.rows[{j}][{i}]"))
    elif kind == "circle":
        cx, cy = ipair(op.get("center"), where + ".center")
        r = number(op.get("r"), where + ".r", 0, 512)
        color = ctx.color(op.get("color"), where)
        inner = set(disc(r - 1)) if op.get("ring") else set()
        for dx, dy in disc(r):
            if (dx, dy) not in inner:
                put(px, size, cx + ox + dx, cy + oy + dy, color)
    elif kind == "box":
        cells, (x, y, w, h) = area()
        color = ctx.color(op.get("color"), where)
        for i, j in cells:
            if i in (x, x + w - 1) or j in (y, y + h - 1):
                px[i, j] = color
    elif kind == "fill":
        x, y = ipair(op.get("xy"), where + ".xy")
        x, y = x + ox, y + oy
        color = ctx.color(op.get("color"), where)
        if not (0 <= x < size[0] and 0 <= y < size[1]):
            raise ValueError(f"{where}: fill starts outside the canvas")
        target = px[x, y]
        if target != color:
            stack = [(x, y)]
            while stack:
                i, j = stack.pop()
                if 0 <= i < size[0] and 0 <= j < size[1] and px[i, j] == target:
                    px[i, j] = color
                    stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
    elif kind == "dither":
        cells, _ = area()
        a, b = symbols("".join(op.get("colors", [])) if isinstance(op.get("colors"), list) else op.get("colors"), "colors")[:2]
        d = density()
        for i, j in cells:
            px[i, j] = b if dithered(i, j, d) else a
    elif kind == "gradient":
        cells, (x, y, w, h) = area()
        colors = symbols(op.get("colors"), "colors")
        vertical = op.get("dir", "v") == "v"
        soft = number(op.get("soft", 0.5), where + ".soft", 0, 1)
        n = len(colors)
        for i, j in cells:
            t = (j - y) / max(1, h) if vertical else (i - x) / max(1, w)
            value = t * n
            band = min(n - 1, int(value))
            frac = value - band
            if soft and band < n - 1 and frac > 1 - soft / 2 and dithered(i, j, (frac - (1 - soft / 2)) / soft):
                band += 1
            elif soft and band > 0 and frac < soft / 2 and not dithered(i, j, 0.5 + frac / soft):
                band -= 1
            px[i, j] = colors[band]
    elif kind == "noise":
        import random
        cells, _ = area()
        colors = symbols(op.get("colors"), "colors")
        rng = random.Random(op.get("seed", 1))
        d = number(op.get("density", 0.1), where + ".density", 0, 1)
        on = set(symbols(op["on"], "on")) if "on" in op else None
        for i, j in cells:
            pick = rng.random()
            choice = rng.choice(colors)
            if pick < d and (on is None or px[i, j] in on):
                px[i, j] = choice
    elif kind in ("shade", "light"):
        test = region_test(op.get("region"), origin, where)
        steps = int(number(op.get("steps", 1), where + ".steps", 1, 8)) * (-1 if kind == "shade" else 1)
        d = density()
        for j in range(size[1]):
            for i in range(size[0]):
                if px[i, j][3] and test(i, j) and dithered(i, j, d):
                    px[i, j] = ctx.step(px[i, j], steps)
    elif kind == "recolor":
        mapping = op.get("map")
        if not isinstance(mapping, dict):
            raise ValueError(f"{where}.map: expected {{\"a\": \"b\"}}")
        table = {ctx.color(a, where): ctx.color(b, where) for a, b in mapping.items()}
        test = region_test(op.get("region"), origin, where)
        d = density()
        for j in range(size[1]):
            for i in range(size[0]):
                if px[i, j] in table and test(i, j) and dithered(i, j, d):
                    px[i, j] = table[px[i, j]]
    elif kind == "stamp":
        part = render_part(op.get("part"), ctx, where, depth)
        x, y = ipair(op.get("xy"), where + ".xy")
        place(px, size, transformed(part, op.get("flip"), op.get("swap"), ctx, where), x + ox, y + oy)
    elif kind == "scatter":
        import random
        names = op.get("parts")
        if isinstance(names, str):
            names = [names]
        if not isinstance(names, list) or not names:
            raise ValueError(f"{where}.parts: expected a part name or a list of names")
        images = [render_part(n, ctx, where, depth) for n in names]
        cells, (x, y, w, h) = area()
        count = int(number(op.get("count"), where + ".count", 1, 4096))
        rng = random.Random(op.get("seed", 1))
        on = set(symbols(op["on"], "on")) if "on" in op else None
        clip = op.get("clip", False)
        before = image.copy().load() if (on or clip) else None
        placed, tries = 0, 0
        while placed < count and tries < count * 20:
            tries += 1
            cx, cy = x + rng.randrange(w), y + rng.randrange(h)
            art = rng.choice(images)
            flip = rng.choice([None, "x"]) if op.get("flip") == "random" else op.get("flip")
            if on is not None and not (0 <= cx < size[0] and 0 <= cy < size[1] and before[cx, cy] in on):
                continue
            art = transformed(art, flip, None, ctx, where)
            mask = (lambda i, j: before[i, j] in on) if (clip and on) else (lambda i, j: before[i, j][3]) if clip else None
            place(px, size, art, cx - art.width // 2, cy - art.height // 2, mask)
            placed += 1


def transformed(image, flip, swap, ctx, where):
    if flip:
        if flip not in ("x", "y", "xy"):
            raise ValueError(f"{where}.flip: expected x, y or xy")
        if "x" in flip:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if "y" in flip:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if swap:
        if not isinstance(swap, dict):
            raise ValueError(f"{where}.swap: expected {{\"a\": \"b\"}}")
        table = {ctx.color(a, where): ctx.color(b, where) for a, b in swap.items()}
        image = image.copy()
        data = image.load()
        for j in range(image.height):
            for i in range(image.width):
                if data[i, j] in table:
                    data[i, j] = table[data[i, j]]
    return image


def place(px, size, art, x0, y0, mask=None):
    data = art.load()
    for j in range(art.height):
        for i in range(art.width):
            c = data[i, j]
            x, y = x0 + i, y0 + j
            if c[3] and 0 <= x < size[0] and 0 <= y < size[1] and (mask is None or mask(x, y)):
                px[x, y] = c


# ---------- materials: flat regions in, shaded volumes out ----------

LIGHTS_2D = {"upper-left": (-0.7, -0.7), "upper-right": (0.7, -0.7), "top": (0.0, -1.0), "left": (-1.0, -0.15),
             "right": (1.0, -0.15)}
FORMS = ("dome", "bevel", "cylinder", "flat")
MATERIAL_KEYS = {"base", "ramp", "tones", "shift", "form", "bevel", "axis", "highlight"}
SPARE_SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#$%&*+=?@!^~<>[]{}|;:,/\\'`\"-_()"


def light_direction(document):
    light = document.get("light", "upper-left")
    if isinstance(light, (int, float)) and not isinstance(light, bool):
        a = math.radians(light)  # degrees: 0 = from the right, 90 = from straight above, 180 = from the left
        return math.cos(a), -math.sin(a)
    if light not in LIGHTS_2D:
        raise ValueError(f"light: expected one of {', '.join(LIGHTS_2D)} or degrees")
    x, y = LIGHTS_2D[light]
    n = math.hypot(x, y)
    return x / n, y / n


def expand_materials(document, palette, ramps):
    """Turn document materials into palette entries and ramps. Returns {name: (spec, [rgba dark->light])}."""
    materials = document.get("materials", {})
    if not isinstance(materials, dict):
        raise ValueError("materials: expected an object of named materials")
    import importlib.util
    tools = importlib.util.spec_from_file_location("palette_tools", Path(__file__).with_name("palette_tools.py"))
    module = importlib.util.module_from_spec(tools)
    tools.loader.exec_module(module)
    free = iter(ch for ch in SPARE_SYMBOLS if ch not in palette)
    out = {}
    for name, spec in materials.items():
        where = f"materials.{name}"
        object_keys(spec, MATERIAL_KEYS, where)
        if spec.get("form", "dome") not in FORMS:
            raise ValueError(f"{where}.form: expected one of {', '.join(FORMS)}")
        if "ramp" in spec:
            symbols = spec["ramp"]
            if not isinstance(symbols, str) or len(symbols) < 2 or any(ch not in palette for ch in symbols):
                raise ValueError(f"{where}.ramp: expected palette symbols, dark to light")
            colors = [palette[ch] for ch in symbols]
        elif isinstance(spec.get("base"), str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", spec["base"]):
            tones = int(number(spec.get("tones", 4), where + ".tones", 3, 6))
            hexes = module.ramp(spec["base"].upper(), tones=tones, shift=number(spec.get("shift", 24), where + ".shift", 0, 90))
            symbols = ""
            colors = []
            for hx in hexes:
                rgba = tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
                symbol = next((k for k, v in palette.items() if v == rgba), None)
                if symbol is None:
                    try:
                        symbol = next(free)
                    except StopIteration:
                        raise ValueError(f"{where}: no free palette symbols left for the generated ramp")
                    palette[symbol] = rgba
                symbols += symbol
                colors.append(rgba)
        else:
            raise ValueError(f"{where}: give \"base\": \"#RRGGBB\" or \"ramp\": \"symbols\"")
        ramps.append(symbols)
        out[name] = (spec, colors)
    return out


def chamfer(mask):
    big = 1e9
    dist = {q: big for q in mask}
    order = sorted(mask, key=lambda q: (q[1], q[0]))
    for sweep, steps in ((order, ((-1, 0, 1), (0, -1, 1), (-1, -1, 1.414), (1, -1, 1.414))),
                         (order[::-1], ((1, 0, 1), (0, 1, 1), (1, 1, 1.414), (-1, 1, 1.414)))):
        for x, y in sweep:
            best = dist[(x, y)]
            for dx, dy, cost in steps:
                other = dist.get((x + dx, y + dy))
                best = min(best, cost if other is None else other + cost)
            dist[(x, y)] = best
    return dist


def height_field(mask, spec):
    form = spec.get("form", "dome")
    if form == "dome":  # a smooth inflated volume (Poisson), no ridge down the middle
        dist = chamfer(mask)
        h = {q: d * d * 0.5 for q, d in dist.items()}
        for _ in range(40):
            for x, y in mask:
                h[(x, y)] = (h.get((x + 1, y), 0.0) + h.get((x - 1, y), 0.0) + h.get((x, y + 1), 0.0)
                             + h.get((x, y - 1), 0.0) + 1.0) / 4
        return {q: math.sqrt(v) * 1.15 for q, v in h.items()}
    if form in ("bevel", "flat"):  # a flat face with sloped edges (boxes, planks, panels, blades)
        width = 1 if form == "flat" else number(spec.get("bevel", 2), "bevel", 1, 16)
        return {q: min(d, width) * 1.6 for q, d in chamfer(mask).items()}
    # cylinder: round across the axis only (barrels, pillars, a sword grip, a log lying down)
    axis = spec.get("axis", "v")
    h = {}
    runs = {}
    for x, y in mask:
        runs.setdefault(y if axis == "v" else x, []).append(x if axis == "v" else y)
    for line, cells in runs.items():
        cells.sort()
        start = cells[0]
        for i, c in enumerate(cells + [None]):
            if c is None or (i and c != cells[i - 1] + 1):
                end = cells[i - 1]
                r = (end - start + 1) / 2
                mid = (start + end + 1) / 2
                for k in range(start, end + 1):
                    t = (k + 0.5 - mid) / r
                    q = (k, line) if axis == "v" else (line, k)
                    h[q] = math.sqrt(max(0.0, 1 - t * t)) * r
                if c is not None:
                    start = c
    return h


def components(mask):
    left, parts = set(mask), []
    while left:
        stack, part = [left.pop()], set()
        while stack:
            x, y = stack.pop()
            part.add((x, y))
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in left:
                    left.remove(q)
                    stack.append(q)
        parts.append(part)
    return parts


def shade_material(mask, spec, colors, light):
    """Shade every separate piece of a material region on its own (each plank, each coin)."""
    out = {}
    for part in components(mask):
        out.update(shade_piece(part, spec, colors, light))
    return out


def shade_thin(mask, colors, light):
    """Parts 1-4 px across (blades, rims, coin edges, straps) have no room for a volume: the edge facing
    the light takes the light tone, the edge facing away the shadow tone, the middle the base tone."""
    lx, ly = light
    count = len(colors)
    base = 1 if count > 2 else 0
    out = {}
    for x, y in mask:
        lit = any((x + dx, y + dy) not in mask and dx * lx + dy * ly > 0.3 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        dark = any((x + dx, y + dy) not in mask and dx * lx + dy * ly < -0.3 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        level = base + 1 if lit and not dark else 0 if dark and not lit else base
        out[(x, y)] = colors[min(level, count - 1)]
    return out


def shade_piece(mask, spec, colors, light):
    """Pick a ramp tone per pixel from a height field lit by one 3D light, with a reflected-light rim on
    the shadow side and single-pixel specks merged into their neighbours."""
    if max(chamfer(mask).values()) <= 2.0:
        return shade_thin(mask, colors, light)
    lx, ly = light
    lz = 0.9
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    Lx, Ly, Lz = lx / n, ly / n, lz / n
    h = height_field(mask, spec)
    count = len(colors)
    highlight = spec.get("highlight", True)
    cuts = {3: [0.38, 0.74], 4: [0.38, 0.74, 0.93], 5: [0.25, 0.5, 0.74, 0.93], 6: [0.2, 0.4, 0.58, 0.76, 0.93]}
    thresholds = cuts.get(count, cuts[4])[:count - 1]
    levels = {}
    for (x, y) in mask:
        gx = (h.get((x + 1, y), 0.0) - h.get((x - 1, y), 0.0)) / 2
        gy = (h.get((x, y + 1), 0.0) - h.get((x, y - 1), 0.0)) / 2
        norm = math.sqrt(gx * gx + gy * gy + 1.0)
        i = (-gx * Lx - gy * Ly + Lz) / norm
        level = sum(1 for t in thresholds if i > t)
        if not highlight:
            level = min(level, count - 2)
        levels[(x, y)] = level
    if count >= 4:  # reflected light: the shadow-side silhouette lifts one step, a core shadow stays inside
        for (x, y), level in list(levels.items()):
            if level == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (x + dx, y + dy) not in mask and dx * lx + dy * ly < -0.3:
                        if levels.get((x - dx, y - dy)) == 0:
                            levels[(x, y)] = 1
                        break
    for (x, y), level in list(levels.items()):  # clean-up: a lone tone inside a cluster joins its neighbours
        around = [levels.get(q) for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))]
        if None not in around and level not in around:
            levels[(x, y)] = max(set(around), key=around.count)
    return {q: colors[level] for q, level in levels.items()}


def _scale2x(grid):
    h, w = len(grid), len(grid[0])
    out = [[None] * (w * 2) for _ in range(h * 2)]
    for y in range(h):
        for x in range(w):
            p = grid[y][x]
            a = grid[y - 1][x] if y > 0 else p
            b = grid[y][x + 1] if x < w - 1 else p
            c = grid[y][x - 1] if x > 0 else p
            d = grid[y + 1][x] if y < h - 1 else p
            out[2 * y][2 * x] = a if c == a and c != d and a != b else p
            out[2 * y][2 * x + 1] = b if a == b and a != c and b != d else p
            out[2 * y + 1][2 * x] = c if d == c and d != b and c != a else p
            out[2 * y + 1][2 * x + 1] = d if b == d and b != a and d != c else p
    return out


def transform_layer(image, spec, where):
    """RotSprite-style rotation and scaling around a pivot: Scale2x three times, then nearest sampling, so
    edges stay clean and only the layer's own colors appear.
    spec: {"pivot": [x, y], "rotate": degrees (clockwise), "scale": [sx, sy]} (a negative scale flips;
    scale [1, 0.5] foreshortens a lid tilting away)."""
    object_keys(spec, {"pivot", "rotate", "scale"}, where)
    px_, py_ = ipair(spec.get("pivot"), where + ".pivot")
    ang = math.radians(number(spec.get("rotate", 0), where + ".rotate", -720, 720))
    sc = spec.get("scale", [1, 1])
    if not isinstance(sc, list) or len(sc) != 2:
        raise ValueError(f"{where}.scale: expected [sx, sy]")
    sx, sy = (number(v, where + ".scale", -16, 16) for v in sc)
    if abs(sx) < 0.05 or abs(sy) < 0.05:
        return Image.new("RGBA", image.size)
    box = image.getbbox()
    if not box:
        return image
    w, h = image.size
    src = image.load()
    grid = [[src[x, y] if src[x, y][3] else None for x in range(w)] for y in range(h)]
    big = grid
    for _ in range(3):
        big = _scale2x(big)
    cos, sin = math.cos(-ang), math.sin(-ang)
    out = Image.new("RGBA", image.size)
    dst = out.load()
    for y in range(h):
        for x in range(w):
            rx, ry = x + 0.5 - px_, y + 0.5 - py_
            ux, uy = rx * cos - ry * sin, rx * sin + ry * cos  # undo the rotation
            ux, uy = ux / sx + px_, uy / sy + py_            # undo the scale
            bx, by = math.floor(ux * 8), math.floor(uy * 8)
            if 0 <= bx < w * 8 and 0 <= by < h * 8:
                c = big[by][bx]
                if c is not None:
                    dst[x, y] = c
    return out


def composite(size, layers, ctx, where, options=None, depth=0):
    """Draw layers back to front, then mirror, glow and outline. Used for documents, parts and frames."""
    options = options or {}
    if not isinstance(layers, list) or not layers:
        raise ValueError(f"{where}.layers: expected a nonempty list")
    canvas = Image.new("RGBA", size)
    names = set()
    report = []
    late_blends = []
    solid = set()
    material_of = {}
    for index, layer in enumerate(layers):
        lw = f"{where}.layers[{index}]" if where != "document" else f"layers[{index}]"
        object_keys(layer, {"name", "origin", "visible", "rows", "ops", "blend", "steps", "density", "shift", "outline",
                            "after_glow", "solid", "mirror", "material", "group", "transform"}, lw)
        name = layer.get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError(f"{lw}.name: expected nonempty unique layer name")
        names.add(name)
        lw += f" ({name})"
        visible = layer.get("visible", True)
        if type(visible) is not bool:
            raise ValueError(f"{lw}.visible: expected true or false")
        origin = pair(layer.get("origin", [0, 0]), lw + ".origin")
        if origin[0] >= size[0] or origin[1] >= size[1]:
            raise ValueError(f"{lw}.origin: outside canvas")
        if "rows" not in layer and "ops" not in layer:
            raise ValueError(f"{lw}: provide rows or ops")
        image = Image.new("RGBA", size)
        if "rows" in layer:
            rows = layer["rows"]
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], str) or not rows[0]:
                raise ValueError(f"{lw}.rows: expected nonempty strings")
            width = len(rows[0])
            if width + origin[0] > size[0] or len(rows) + origin[1] > size[1]:
                raise ValueError(f"{lw}.rows: extends outside canvas")
            pixels = image.load()
            for y, row in enumerate(rows):
                if not isinstance(row, str) or len(row) != width:
                    raise ValueError(f"{lw}.rows[{y}]: expected {width} characters")
                for x, symbol in enumerate(row):
                    if symbol not in ctx.palette:
                        raise ValueError(f"{lw}.rows[{y}][{x}]: unknown palette symbol {symbol!r}")
                    pixels[x + origin[0], y + origin[1]] = ctx.palette[symbol]
        if "ops" in layer:
            if not isinstance(layer["ops"], list):
                raise ValueError(f"{lw}.ops: expected list")
            for op_index, operation in enumerate(layer["ops"]):
                paint_operation(image, operation, ctx, origin, f"{lw}.ops[{op_index}]", depth)
        if "mirror" in layer:  # mirror this layer's shape only; shading layers above stay one-sided
            mode = layer["mirror"]
            if mode not in ("x", "y", "xy"):
                raise ValueError(f"{lw}.mirror: expected x, y or xy")
            lp = image.load()
            if "x" in mode:
                for yy in range(size[1]):
                    for xx in range(size[0] // 2):
                        lp[size[0] - 1 - xx, yy] = lp[xx, yy]
            if "y" in mode:
                for yy in range(size[1] // 2):
                    for xx in range(size[0]):
                        lp[xx, size[1] - 1 - yy] = lp[xx, yy]
        if "material" in layer:
            # The layer is a flat region; its pixels are replaced by the material shaded as a volume.
            name = layer["material"]
            if name not in ctx.materials:
                raise ValueError(f"{lw}.material: unknown material {name!r} (have: {', '.join(ctx.materials) or 'none'})")
            spec, colors = ctx.materials[name]
            lp = image.load()
            mask = {(x, y) for y in range(size[1]) for x in range(size[0]) if lp[x, y][3]}
            for q, c in shade_material(mask, spec, colors, ctx.light).items():
                lp[q] = c
            # contact shadow: what is already below steps darker just outside this region, away from the light
            below = canvas.load()
            dx = 1 if ctx.light[0] < -0.3 else -1 if ctx.light[0] > 0.3 else 0
            dy = 1 if ctx.light[1] < -0.3 else -1 if ctx.light[1] > 0.3 else 0
            for x, y in mask:
                q = (x + dx, y + dy)
                if (dx or dy) and q not in mask and 0 <= q[0] < size[0] and 0 <= q[1] < size[1] and below[q][3]:
                    below[q] = ctx.step(below[q], -1)
            material_of.update({q: colors for q in mask})
        if "outline" in layer:  # this layer's own outline (smoke, glows and effects can stay unoutlined)
            symbol = layer["outline"]
            if not isinstance(symbol, str) or symbol not in ctx.palette or ctx.palette[symbol][3] == 0:
                raise ValueError(f"{lw}.outline: expected an opaque palette symbol")
            lp = image.load()
            edge = [(x, y) for y in range(size[1]) for x in range(size[0]) if lp[x, y][3] == 0 and any(
                0 <= x + dx < size[0] and 0 <= y + dy < size[1] and lp[x + dx, y + dy][3]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
            for point in edge:
                lp[point] = ctx.palette[symbol]
        if "transform" in layer:  # rotate / scale the finished layer around a pivot (a lid on its hinge)
            image = transform_layer(image, layer["transform"], lw + ".transform")
        if "shift" in layer:  # move the finished layer, art and all (clips at the canvas edge)
            dx, dy = ipair(layer["shift"], lw + ".shift")
            moved = Image.new("RGBA", size)
            moved.paste(image, (dx, dy))
            image = moved
        blend = layer.get("blend")
        if blend is not None:
            # A blend layer is not drawn: where it is opaque, what is below steps darker or lighter.
            if blend not in ("shade", "light"):
                raise ValueError(f"{lw}.blend: expected shade or light")
            steps = int(number(layer.get("steps", 1), lw + ".steps", 1, 8)) * (-1 if blend == "shade" else 1)
            d = number(layer.get("density", 1), lw + ".density", 0, 1)
            if visible and layer.get("after_glow"):
                late_blends.append((image, steps, d))  # a cast shadow that firelight must not wash out
            elif visible:
                mask, below = image.load(), canvas.load()
                for y in range(size[1]):
                    for x in range(size[0]):
                        if mask[x, y][3] and below[x, y][3] and dithered(x, y, d):
                            below[x, y] = ctx.step(below[x, y], steps)
        elif visible:
            canvas = Image.alpha_composite(canvas, image)
        if layer.get("solid") and visible:
            lp = image.load()
            solid.update((x, y) for y in range(size[1]) for x in range(size[0]) if lp[x, y][3])
        report.append({"name": name, "visible": visible, "bbox": image.getbbox()})
    px = canvas.load()
    w, h = size
    mirror = options.get("mirror")
    if mirror is not None:
        # Draw the left (or top) half; the other half is its mirror image.
        if mirror not in ("x", "y", "xy"):
            raise ValueError(f"{where}.mirror: expected x, y or xy")
        if "x" in mirror:
            for y in range(h):
                for x in range(w // 2):
                    px[w - 1 - x, y] = px[x, y]
        if "y" in mirror:
            for y in range(h // 2):
                for x in range(w):
                    px[x, h - 1 - y] = px[x, y]
    for i, light in enumerate(options.get("lights", [])):
        apply_light(px, size, light, ctx, solid, f"{where}.lights[{i}]")
    for i, glow in enumerate(options.get("glow", [])):
        apply_glow(px, size, glow, ctx, f"{where}.glow[{i}]")
    for image, steps, d in late_blends:
        mask = image.load()
        for y in range(h):
            for x in range(w):
                if mask[x, y][3] and px[x, y][3] and dithered(x, y, d):
                    px[x, y] = ctx.step(px[x, y], steps)
    if "outline" in options:
        # Optional automatic outline: every transparent pixel touching the art (4-neighbour) gets the
        # outline symbol's color, so a whole set shares one consistent outline without hand-drawing it.
        symbol = options["outline"]
        if not isinstance(symbol, str) or symbol not in ctx.palette or ctx.palette[symbol][3] == 0:
            raise ValueError("outline: expected an opaque palette symbol")
        edge = [(x, y) for y in range(h) for x in range(w) if px[x, y][3] == 0 and any(
            0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        selective = options.get("outline_style") == "selective"
        lx, ly = ctx.light
        for x, y in edge:
            color = ctx.palette[symbol]
            if selective:
                # Light-facing edges take the darkest tone of the material they border; the shadow side
                # and anything without a material keep the outline color.
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (x + dx, y + dy)
                    if q in material_of and (-dx) * lx + (-dy) * ly > 0.3:
                        color = material_of[q][0]
                        break
            px[x, y] = color
    return canvas if depth else (canvas, report)


def apply_light(px, size, light, ctx, solid, where):
    """A point light that stays in the palette and follows the geometry.

    Lit pixels step lighter along their ramps (or move onto a `tint` ramp), most where they are close
    to the source, where the line to it is not blocked by `solid` layers, and on surfaces that face it
    (an exposed edge toward the light). So firelight rims the anvil and the door jamb facing the fire,
    pools on the ground in front, and stops behind a wall, instead of painting a disc."""
    object_keys(light, {"at", "r", "steps", "tint", "on", "block", "falloff", "dither", "keys"}, where)
    keys = light.get("keys", "")  # the source's own colors (flames, lamp glass) stay as painted
    if not isinstance(keys, str) or any(ch not in ctx.palette for ch in keys):
        raise ValueError(f"{where}.keys: expected palette symbols")
    sources = {ctx.palette[ch] for ch in keys}
    lx, ly = ipair(light.get("at"), where + ".at")
    r = number(light.get("r", 24), where + ".r", 1, 512)
    steps = number(light.get("steps", 2), where + ".steps", 1, 6)
    block = number(light.get("block", 0.5), where + ".block", 0, 1)  # light lost per solid pixel crossed
    falloff = number(light.get("falloff", 1.0), where + ".falloff", 0.2, 4)
    on = light.get("on")
    if on is not None and (not isinstance(on, str) or any(ch not in ctx.palette for ch in on)):
        raise ValueError(f"{where}.on: expected palette symbols")
    receivers = {ctx.palette[ch] for ch in on} if on else None
    tint = light.get("tint")
    tint_colors = None
    if tint is not None:
        if not isinstance(tint, str) or len(tint) < 2 or any(ch not in ctx.palette for ch in tint):
            raise ValueError(f"{where}.tint: expected a ramp of palette symbols, dark to light")
        tint_colors = [ctx.palette[ch] for ch in tint]
    luma = lambda q: q[0] * 0.3 + q[1] * 0.59 + q[2] * 0.11
    w, h = size
    changes = {}
    reach = int(math.ceil(r))
    for y in range(max(0, ly - reach), min(h, ly + reach + 1)):
        for x in range(max(0, lx - reach), min(w, lx + reach + 1)):
            c = px[x, y]
            if not c[3] or c in sources or (receivers is not None and c not in receivers):
                continue
            if receivers is None and luma(c) < 28:
                continue  # voids, soot and outlines stay dark unless named in `on`
            d = math.hypot(x - lx, y - ly)
            if d > r:
                continue
            # visibility: solid pixels on the way, not counting the pixel's own surface (last 2 px)
            path = list(line_points((lx, ly), (x, y)))
            crossed = sum(1 for p in path[:-3] if p in solid and abs(p[0] - lx) + abs(p[1] - ly) > 4)  # not the emitter
            visible = max(0.0, 1 - block * crossed)
            if visible <= 0:
                continue
            # facing: the pixel two steps toward the light is open (or not solid): an exposed surface
            if d > 0:
                tx, ty = round(x + 2 * (lx - x) / d), round(y + 2 * (ly - y) / d)
                inside = (0 <= tx < w and 0 <= ty < h) and px[tx, ty][3] and (tx, ty) in solid
                facing = 0.45 if inside else 1.0
            else:
                facing = 1.0
            amount = steps * ((1 - d / (r + 1)) ** falloff) * visible * facing
            if light.get("dither"):
                n = int(amount) + (1 if dithered(x, y, amount - int(amount)) else 0)
            else:  # hard bands: no checkerboard over large surfaces
                n = int(amount + 0.35)
            if not n:
                continue
            if tint_colors:
                level = min(range(len(tint_colors)), key=lambda i: abs(luma(tint_colors[i]) - luma(c)))
                changes[(x, y)] = tint_colors[min(len(tint_colors) - 1, level + n - 1)]
            else:
                changes[(x, y)] = ctx.step(c, n)
    for point, c in changes.items():
        px[point] = c


def apply_glow(px, size, glow, ctx, where):
    """Light spill that stays in the palette: opaque pixels near a glowing key step lighter along
    their ramps, by up to `steps`, falling off over `r` pixels with a dithered edge."""
    object_keys(glow, {"keys", "r", "steps", "bands", "tint", "on"}, where)
    keys = glow.get("keys")
    if not isinstance(keys, str) or any(ch not in ctx.palette for ch in keys):
        raise ValueError(f"{where}.keys: expected palette symbols")
    sources = {ctx.palette[ch] for ch in keys}
    r = number(glow.get("r", 4), where + ".r", 1, 64)
    steps = number(glow.get("steps", 2), where + ".steps", 1, 6)
    bands = glow.get("bands", False)  # hard rings instead of a dithered falloff
    tint = glow.get("tint")  # a warm (or cool) ramp the lit pixels move onto, by brightness
    tint_colors = None
    if tint is not None:
        if not isinstance(tint, str) or len(tint) < 2 or any(ch not in ctx.palette for ch in tint):
            raise ValueError(f"{where}.tint: expected a ramp of palette symbols, dark to light")
        tint_colors = [ctx.palette[ch] for ch in tint]
    on = glow.get("on")  # only these colors receive the light (keep soot, voids and far walls dark)
    if on is not None and (not isinstance(on, str) or any(ch not in ctx.palette for ch in on)):
        raise ValueError(f"{where}.on: expected palette symbols")
    receivers = {ctx.palette[ch] for ch in on} if on else None
    w, h = size
    lit = [(x, y) for y in range(h) for x in range(w) if px[x, y] in sources]
    if not lit:
        return
    changes = {}
    reach = int(math.ceil(r))
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            if not c[3] or c in sources or (receivers is not None and c not in receivers):
                continue
            best = min((math.hypot(x - sx, y - sy) for sx, sy in lit if abs(x - sx) <= reach and abs(y - sy) <= reach),
                       default=None)
            if best is None or best > r:
                continue
            lift = steps * (1 - best / (r + 1))
            n = round(lift) if bands else int(lift) + (1 if dithered(x, y, lift - int(lift)) else 0)
            if not n:
                continue
            if tint_colors:
                # Pick the tint tone of the same brightness, then lift it: firelight warms cold stone.
                luma = lambda q: q[0] * 0.3 + q[1] * 0.59 + q[2] * 0.11
                level = min(range(len(tint_colors)), key=lambda i: abs(luma(tint_colors[i]) - luma(c)))
                changes[(x, y)] = tint_colors[min(len(tint_colors) - 1, level + n - 1)]
            else:
                changes[(x, y)] = ctx.step(c, n)
    for point, c in changes.items():
        px[point] = c


DOCUMENT_KEYS = {"version", "size", "palette", "layers", "meta", "outline", "ramps", "parts", "mirror", "glow",
                 "animation", "lights", "materials", "light", "outline_style"}


def document_context(document):
    palette = parse_palette(document.get("palette"))
    ramps = document.get("ramps", [])
    if not isinstance(ramps, list) or not all(isinstance(r, str) and len(r) >= 2 for r in ramps):
        raise ValueError("ramps: expected a list of palette-symbol strings, dark to light")
    for i, ramp in enumerate(ramps):
        missing = [ch for ch in ramp if ch not in palette]
        if missing:
            raise ValueError(f"ramps[{i}]: symbols {missing} are not in palette")
    parts = document.get("parts", {})
    if not isinstance(parts, dict):
        raise ValueError("parts: expected an object of named parts")
    if not isinstance(document.get("glow", []), list):
        raise ValueError("glow: expected a list")
    if document.get("outline_style", "solid") not in ("solid", "selective"):
        raise ValueError("outline_style: expected solid or selective")
    ramps = list(ramps)
    materials = expand_materials(document, palette, ramps)  # adds generated tones to the palette and ramps
    ctx = Context(palette, ramps, parts)
    ctx.materials = materials
    ctx.light = light_direction(document)
    return ctx


def render_document(document):
    """Return a native RGBA image and factual report, or raise ValueError. A document with an
    animation renders its first frame here; render_frames returns them all."""
    object_keys(document, DOCUMENT_KEYS, "document")
    if type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("version: expected 1")
    size = pair(document.get("size"), "size", 1)
    if "meta" in document and not isinstance(document["meta"], dict):
        raise ValueError("meta: expected object")
    ctx = document_context(document)
    for name in ctx.parts:
        render_part(name, ctx, f"parts.{name}")  # validate every part, used or not
    if "animation" in document:
        frames = render_frames(document)
        canvas, layer_report = frames[0][0], frames[0][2]
    else:
        canvas, layer_report = composite(size, document.get("layers"), ctx, "document", document)
    raw = iter(canvas.tobytes())
    counts = Counter(zip(raw, raw, raw, raw))
    opaque = sum(count for rgba, count in counts.items() if rgba[3])
    bbox = canvas.getbbox()
    warnings = []
    if not opaque:
        warnings.append("No visible pixels.")
    if bbox and (bbox[0] == 0 or bbox[1] == 0 or bbox[2] == size[0] or bbox[3] == size[1]):
        warnings.append("Artwork touches a canvas edge; check intended padding or tile seams.")
    report = {
        "renderer": "pixel-art-json/1", "size": list(size), "mode": "RGBA",
        "opaque_pixels": opaque, "transparent_pixels": size[0] * size[1] - opaque,
        "bbox": list(bbox) if bbox else None,
        "colors": {"#" + "".join(f"{n:02X}" for n in rgba): count for rgba, count in sorted(counts.items())},
        "layers": layer_report, "warnings": warnings,
        "meta": copy.deepcopy(document.get("meta", {})),
    }
    if "animation" in document:
        report["frames"] = len(frames)
    return canvas, report


def render_frames(document):
    """Frames of an animated document: each frame is a patch over the shared layers.

    "animation": {"fps": 8, "loop": true, "frames": [{"ms": 120, "edits": [...]}, ...]}
    Edits are like patch edits ({"layer": name, "op": ...}) and may also move a layer
    ({"layer": name, "move": [dx, dy]}) or hide or show it ({"layer": name, "visible": false}).
    Returns [(image, ms, layer report)]."""
    animation = document["animation"]
    object_keys(animation, {"fps", "loop", "frames"}, "animation")
    fps = number(animation.get("fps", 8), "animation.fps", 1, 60)
    frames = animation.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("animation.frames: expected a nonempty list")
    size = pair(document.get("size"), "size", 1)
    ctx = document_context(document)
    out = []
    for k, frame in enumerate(frames):
        where = f"animation.frames[{k}]"
        object_keys(frame, {"ms", "edits", "glow", "lights"}, where)
        ms = int(number(frame.get("ms", round(1000 / fps)), where + ".ms", 10, 60000))
        layers = copy.deepcopy(document.get("layers"))
        by_name = {layer.get("name"): layer for layer in layers if isinstance(layer, dict)}
        frame_parts = copy.deepcopy(document.get("parts", {}))
        for i, edit in enumerate(frame.get("edits", [])):
            ew = f"{where}.edits[{i}]"
            if isinstance(edit, dict) and "part" in edit and "layer" not in edit:
                # Edit inside a part, so stamped details (a lit window, a sign) can change per frame.
                name = edit["part"]
                if name not in frame_parts:
                    raise ValueError(f"{ew}: no part named {name!r}")
                part = frame_parts[name]
                if "rows" in part:
                    rows = part.pop("rows")
                    part["size"] = part.get("size") or [max(len(r) for r in rows), len(rows)]
                    part["layers"] = [{"name": "rows", "rows": [r.ljust(part["size"][0], ".") for r in rows]}]
                operation = {key: value for key, value in edit.items() if key != "part"}
                part["layers"][-1].setdefault("ops", []).append(operation)
                continue
            if not isinstance(edit, dict) or edit.get("layer") not in by_name:
                raise ValueError(f"{ew}: expected an edit naming an existing layer or part")
            layer = by_name[edit["layer"]]
            if "move" in edit:
                dx, dy = ipair(edit["move"], ew + ".move")
                sx, sy = layer.get("shift", [0, 0])
                layer["shift"] = [sx + dx, sy + dy]
            if "visible" in edit:
                layer["visible"] = edit["visible"]
            if "transform" in edit:
                layer["transform"] = edit["transform"]
            operation = {key: value for key, value in edit.items() if key not in ("layer", "move", "visible", "transform")}
            if operation:
                layer.setdefault("ops", []).append(operation)
        frame_ctx = ctx
        if frame_parts != ctx.parts:
            frame_ctx = Context(ctx.palette, list(ctx.ramp_names), frame_parts)
            frame_ctx.materials, frame_ctx.light = ctx.materials, ctx.light
        options = dict(document, **{k: frame[k] for k in ("glow", "lights") if k in frame})  # flickering light
        image, report = composite(size, layers, frame_ctx, "document", options)
        out.append((image, ms, report))
    return out


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


def ascii_art(document, frame=0, box=None):
    """The rendered art as palette symbols ("." or space for transparent, "?" for a color outside the
    palette), with x rulers on top and y labels on the left. Edit a few symbols and paste them back
    with a `grid` op."""
    render_document(document)
    if "animation" in document:
        frames = render_frames(document)
        if not 0 <= frame < len(frames):
            raise ValueError(f"--frame: expected 0..{len(frames) - 1}")
        image = frames[frame][0]
    else:
        image = render_document(document)[0]
    palette = document_context(document).palette  # includes generated material tones
    symbol_of = {}
    for symbol, rgba in palette.items():
        if rgba[3]:
            symbol_of.setdefault(rgba, symbol)
    x0, y0, x1, y1 = box or (0, 0, image.width - 1, image.height - 1)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(image.width - 1, x1), min(image.height - 1, y1)
    px = image.load()
    lines = ["    " + "".join(str(x // 10 % 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)),
             "    " + "".join(str(x % 10) for x in range(x0, x1 + 1))]
    for y in range(y0, y1 + 1):
        row = "".join(" " if not px[x, y][3] else symbol_of.get(px[x, y], "?") for x in range(x0, x1 + 1))
        lines.append(f"{y:3} {row}")
    return "\n".join(lines)


def group_document(document, group):
    """The document with only the layers of one `group` (and the frame edits that touch them)."""
    doc = copy.deepcopy(document)
    doc["layers"] = [l for l in doc["layers"] if l.get("group") == group]
    names = {l["name"] for l in doc["layers"]}
    if "animation" in doc:
        for frame in doc["animation"]["frames"]:
            frame["edits"] = [e for e in frame.get("edits", []) if e.get("layer") in names or "part" in e]
    return doc


def write_groups(document, prefix, scale):
    """Layers tagged with a `group` (for example back and front of a character) are also written per
    group, so the game can draw one group behind a sprite and the other in front of it."""
    groups = sorted({l.get("group") for l in document.get("layers", []) if isinstance(l, dict) and l.get("group")})
    paths = {}
    for group in groups:
        doc = group_document(document, group)
        gprefix = Path(f"{prefix}.{group}")
        image, _ = render_document(doc)
        image.save(Path(str(gprefix) + ".png"))
        paths[f"{group}_png"] = Path(str(gprefix) + ".png")
        if "animation" in doc:
            for key, path in write_animation(doc, gprefix, scale).items():
                paths[f"{group}_{key}"] = path
    return paths


def write_animation(document, prefix, scale):
    """A horizontal strip, a manifest in the rig2d schema, a looping preview GIF and a frames preview."""
    frames = render_frames(document)
    w, h = frames[0][0].size
    strip = Image.new("RGBA", (w * len(frames), h))
    for i, (image, _, _) in enumerate(frames):
        strip.paste(image, (i * w, 0))
    loop = document["animation"].get("loop", True)
    paths = {"strip": Path(str(prefix) + ".strip.png"), "anim": Path(str(prefix) + ".anim.json"),
             "gif": Path(str(prefix) + ".gif"), "frames_preview": Path(str(prefix) + ".frames.png")}
    strip.save(paths["strip"])
    pivot = (document.get("meta") or {}).get("pivot")  # meta.pivot travels with the frames for engines
    write_json(paths["anim"], {"size": [w, h], "loop": loop, "frames": [
        dict({"rect": [i * w, 0, w, h], "ms": ms}, **({"pivot": pivot} if pivot else {}))
        for i, (_, ms, _) in enumerate(frames)]})
    s = max(1, min(scale, 4096 // max(w, h)))
    big = [preview(image, s).convert("P", palette=Image.Palette.ADAPTIVE) for image, _, _ in frames]
    big[0].save(paths["gif"], save_all=True, append_images=big[1:], duration=[ms for _, ms, _ in frames],
                loop=0, disposal=2)
    preview(strip, max(1, min(scale, 4096 // max(strip.width, h)))).save(paths["frames_preview"])
    return paths


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
    text = commands.add_parser("ascii", help="Print the rendered art as palette symbols with coordinate rulers")
    text.add_argument("source", type=Path)
    text.add_argument("--frame", type=int, default=0, help="animation frame (0-based)")
    text.add_argument("--box", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"), help="inclusive region")
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
        if args.command == "ascii":
            print(ascii_art(source, args.frame, args.box))
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
        if "animation" in source:
            paths.update(write_animation(source, args.out, args.scale))
        paths.update(write_groups(source, args.out, args.scale))
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
