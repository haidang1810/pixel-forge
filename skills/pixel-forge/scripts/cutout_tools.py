"""Declarative cutout drawing: paint regions in the rest pose, then split each region onto its bones.

A spec's "draw" list holds regions. Each region is painted on a canvas-sized layer with a short op
list (canvas coordinates, rest pose), then every painted pixel is given to its nearest bone among
the region's bones. The result is the same "cutout" layer format rig2d renders and rotates.

Ops (palette symbols as colors):
  {"op": "poly",    "c": "2", "pts": [[x, y], ...]}            filled polygon
  {"op": "ellipse", "c": "2", "box": [x0, y0, x1, y1]}         filled ellipse
  {"op": "line",    "c": "k", "pts": [[x, y], ...]}            1-px polyline
  {"op": "px",      "c": "y", "pts": [[x, y], ...]}            single pixels
  {"op": "clip",    "c": "5", "pts": [[x, y], ...]}            polygon painted only over existing pixels
  {"op": "band",    "c": "2", "depth": 4, "x": [x0, x1], "bottom": false, "jag": 1}
                     pixels within `depth` of the top (or bottom) silhouette edge, column by column
  {"op": "rim",     "c": "4"}                                  same as band with depth 1 (top edge)
  {"op": "erase",   "pts": [[x, y], ...]}                      clear pixels
"""
import math

from PIL import Image, ImageDraw

OPS = {"poly", "ellipse", "line", "px", "clip", "band", "rim", "erase"}


class Canvas:
    """One region's pixels in canvas coordinates."""

    def __init__(self, size, rgb):
        self.w, self.h = size
        self.rgb = rgb
        self.img = Image.new("RGBA", size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)

    def poly(self, c, pts):
        self.draw.polygon([tuple(p) for p in pts], fill=self.rgb[c])

    def ellipse(self, c, box):
        self.draw.ellipse(list(box), fill=self.rgb[c])

    def line(self, c, pts):
        self.draw.line([tuple(p) for p in pts], fill=self.rgb[c])

    def px(self, c, pts):
        for x, y in pts:
            if 0 <= x < self.w and 0 <= y < self.h:
                self.img.putpixel((x, y), self.rgb[c])

    def erase(self, pts):
        for x, y in pts:
            if 0 <= x < self.w and 0 <= y < self.h:
                self.img.putpixel((x, y), (0, 0, 0, 0))

    def clip(self, c, pts):
        mask = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in pts], fill=255)
        for y in range(self.h):
            for x in range(self.w):
                if mask.getpixel((x, y)) and self.img.getpixel((x, y))[3]:
                    self.img.putpixel((x, y), self.rgb[c])

    def band(self, c, depth, x=None, bottom=False, jag=0):
        x0, x1 = x if x else (0, self.w)
        src = self.img.copy()
        for col in range(max(0, int(x0)), min(self.w, int(x1))):
            ys = [y for y in range(self.h) if src.getpixel((col, y))[3]]
            if not ys:
                continue
            d = depth + (jag if (col // 2) % 2 else -jag)
            edge = max(ys) if bottom else min(ys)
            for y in ys:
                if (edge - y if bottom else y - edge) < d:
                    self.img.putpixel((col, y), self.rgb[c])

    def run(self, ops):
        for op in ops:
            kind = op["op"]
            if kind == "poly":
                self.poly(op["c"], op["pts"])
            elif kind == "ellipse":
                self.ellipse(op["c"], op["box"])
            elif kind == "line":
                self.line(op["c"], op["pts"])
            elif kind == "px":
                self.px(op["c"], op["pts"])
            elif kind == "clip":
                self.clip(op["c"], op["pts"])
            elif kind == "band":
                self.band(op["c"], op["depth"], op.get("x"), op.get("bottom", False), op.get("jag", 0))
            elif kind == "rim":
                self.band(op["c"], 1)
            elif kind == "erase":
                self.erase(op["pts"])
        return self


def seg_dist(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / ((dx * dx + dy * dy) or 1e-9)))
    return math.hypot(ax + dx * t - p[0], ay + dy * t - p[1])


def split(pixels, bones, names, overlap):
    """Give each pixel to its nearest bone; pixels within `overlap` of a nearer bone go to both,
    so joints stay covered when the bones rotate apart."""
    if len(names) == 1:
        return {names[0]: dict(pixels)}
    out = {n: {} for n in names}
    for (x, y), symbol in pixels.items():
        p = (x + 0.5, y + 0.5)
        d = {n: seg_dist(p, bones[n][0], bones[n][1]) for n in names}
        best = min(d.values())
        for n in names:
            if d[n] - best <= overlap:
                out[n][(x, y)] = symbol
    return out


def to_layer(name, bone, pixels, z, group, **extra):
    xs, ys = [p[0] for p in pixels], [p[1] for p in pixels]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    rows = ["".join(pixels.get((x, y), ".") for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1)]
    return dict(name=name, bone=bone, origin=[x0, y0], z=z, group=group, rows=rows, **extra)


def build_cutout(spec, rest_bones, hex_rgba):
    """Turn spec["draw"] regions into cutout layers. rest_bones maps name -> (start, end)."""
    palette = spec["palette"]
    rgb = {k: hex_rgba(v) for k, v in palette.items()}
    symbol_of = {}
    for k, c in rgb.items():
        symbol_of.setdefault(c, k)
    layers = []
    for region in spec["draw"]:
        canvas = Canvas(spec["size"], rgb).run(region["ops"])
        pixels = {(x, y): symbol_of[c] for y in range(canvas.h) for x in range(canvas.w)
                  if (c := canvas.img.getpixel((x, y)))[3]}
        if not pixels:
            continue
        bones = region["bones"]
        parts = split(pixels, rest_bones, bones, region.get("overlap", 1.5))
        group = region.get("group", region["name"])
        for i, bone in enumerate(bones):
            if not parts[bone]:
                continue
            name = region["name"] if len(bones) == 1 else f"{region['name']}:{bone}"
            layers.append(to_layer(name, bone, parts[bone], region.get("z", 0) + i, group))
        mirror = region.get("mirror")
        if mirror:  # reuse the same pixels on other bones, e.g. the far legs
            for i, (bone, target) in enumerate(zip(bones, mirror["bones"])):
                if not parts[bone]:
                    continue
                source = region["name"] if len(bones) == 1 else f"{region['name']}:{bone}"
                layers.append({"name": f"{source}>{target}", "from": source, "bone": target,
                               "z": mirror.get("z", 0) + i, "group": mirror.get("group", source + ">"),
                               "far": mirror.get("far", True)})
    return layers


def validate_draw(spec, bones):
    """Raise ValueError for a malformed "draw" list."""
    palette = spec.get("palette", {})
    names = set()
    for i, region in enumerate(spec["draw"]):
        where = f"draw[{i}] ({region.get('name')})"
        if not isinstance(region, dict) or not region.get("name"):
            raise ValueError(f"draw[{i}]: expected an object with a name")
        if region["name"] in names:
            raise ValueError(f"{where}: duplicate region name")
        names.add(region["name"])
        extra = set(region) - {"name", "bones", "z", "group", "ops", "overlap", "mirror"}
        if extra:
            raise ValueError(f"{where}: unknown fields {sorted(extra)}")
        region_bones = region.get("bones")
        if not (isinstance(region_bones, list) and region_bones):
            raise ValueError(f"{where}.bones: expected a nonempty list of bone names")
        for bone in region_bones + list(region.get("mirror", {}).get("bones", [])):
            if bone not in bones:
                raise ValueError(f"{where}: unknown bone {bone!r}; bones are {sorted(bones)}")
        if "mirror" in region and len(region["mirror"].get("bones", [])) != len(region_bones):
            raise ValueError(f"{where}.mirror.bones: expected one target bone per region bone")
        ops = region.get("ops")
        if not isinstance(ops, list) or not ops:
            raise ValueError(f"{where}.ops: expected a nonempty list")
        for j, op in enumerate(ops):
            kind = op.get("op") if isinstance(op, dict) else None
            if kind not in OPS:
                raise ValueError(f"{where}.ops[{j}]: unknown op {kind!r}; choose from {sorted(OPS)}")
            if kind != "erase" and op.get("c") not in palette:
                raise ValueError(f"{where}.ops[{j}]: color {op.get('c')!r} is not a palette symbol")
            needs = {"poly": "pts", "line": "pts", "px": "pts", "clip": "pts", "erase": "pts",
                     "ellipse": "box", "band": "depth"}.get(kind)
            if needs and needs not in op:
                raise ValueError(f"{where}.ops[{j}] ({kind}): missing {needs!r}")
