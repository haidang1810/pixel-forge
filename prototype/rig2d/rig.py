#!/usr/bin/env python3
"""Prototype: 2D skeletal pixel characters. Vector parts on bones, re-rasterized per frame.

The agent writes a short character spec (rig preset + overrides + animation presets);
this script computes poses, rasterizes at native size, shades, outlines, and exports.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

import presets

HERE = Path(__file__).resolve().parent
SYMBOLS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+-=?@"


def hex_rgba(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def deep_merge(base, override):
    result = dict(base)
    for key, value in (override or {}).items():
        result[key] = deep_merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


# ---------- geometry ----------

def down(angle):
    """Limb direction: 0 = straight down, positive = toward facing (+x)."""
    a = math.radians(angle)
    return (math.sin(a), math.cos(a))


def up(angle):
    """Spine direction: 0 = straight up, positive = lean forward."""
    a = math.radians(angle)
    return (math.sin(a), -math.cos(a))


def add(p, d, length):
    return (p[0] + d[0] * length, p[1] + d[1] * length)


class Bone:
    def __init__(self, start, direction, length):
        self.start, self.dir, self.length = start, direction, length
        self.end = add(start, direction, length)

    def local(self, u, v):
        """u along the bone, v perpendicular (+v is forward for an upright bone)."""
        nx, ny = -self.dir[1], self.dir[0]
        return (self.start[0] + self.dir[0] * u + nx * v, self.start[1] + self.dir[1] * u + ny * v)


def solve_skeleton(rig, pose, root):
    if rig.get("family") == "quadruped":
        return solve_quadruped(rig, pose, root)
    L, P = rig["bones"], pose
    bones = {}
    spine_dir = up(P.get("lean", 0))
    bones["spine"] = Bone(root, spine_dir, L["spine"])
    bones["head"] = Bone(add(bones["spine"].end, spine_dir, L["neck"]), up(P.get("lean", 0) + P.get("head", 0)), L["head"])
    shoulder = add(bones["spine"].end, spine_dir, -L["shoulder_drop"])
    for side in ("n", "f"):
        thigh = Bone(root, down(P.get("hip_" + side, 0)), L["thigh"])
        shin_angle = P.get("hip_" + side, 0) - P.get("knee_" + side, 0)
        shin = Bone(thigh.end, down(shin_angle), L["shin"])
        foot = Bone(shin.end, down(shin_angle + 90 + P.get("ankle_" + side, 0)), L["foot"])
        upper = Bone(shoulder, down(P.get("sh_" + side, 0)), L["upper_arm"])
        fore_angle = P.get("sh_" + side, 0) + P.get("el_" + side, 0)
        fore = Bone(upper.end, down(fore_angle), L["forearm"])
        bones.update({"thigh_" + side: thigh, "shin_" + side: shin, "foot_" + side: foot,
                      "upper_" + side: upper, "fore_" + side: fore})
        bones["hand_" + side] = Bone(fore.end, fore.dir, 0.01)
        bones["weapon_" + side] = Bone(fore.end, down(fore_angle + P.get("grip_" + side, 120)), 1)
    return bones


def solve_quadruped(rig, pose, root):
    """Side-view four-legged skeleton. root is the hip; the spine runs forward to the shoulder.

    Legs: bn/bf = back near/far, fn/ff = front near/far. Each leg has upper, lower and foot
    (metacarpal/metatarsal) bones: upper = hip_X, lower = upper + knee_X, foot = lower + ankle_X.
    pitch > 0 lowers the shoulder; neck is measured from straight up (forward > 0);
    head > 0 points the nose down; tail > 0 raises the tail.
    """
    L, P = rig["bones"], pose
    pitch = math.radians(P.get("pitch", 0))
    flex = math.radians(P.get("flex", 0))  # > 0 arches the back (hips and chest both drop)
    spine = Bone(root, (math.cos(pitch), math.sin(pitch)), L["body"])
    hips = Bone(root, (math.cos(pitch - flex / 2), math.sin(pitch - flex / 2)), L["body"] * 0.45)
    chest = Bone(hips.end, (math.cos(pitch + flex / 2), math.sin(pitch + flex / 2)), L["body"] * 0.55)
    bones = {"spine": spine, "hips": hips, "chest": chest}
    bones["neck"] = Bone(chest.local(chest.length - 1, -1), up(P.get("neck", 0)), L["neck"])
    bones["head"] = Bone(bones["neck"].end, down(90 - P.get("head", 0)), L["head"])
    tail_root = hips.local(-1, -1.5)
    bones["tail"] = Bone(tail_root, down(-90 - P.get("tail", 0)), L["tail"])
    # Three tail segments; tail2/tail3 bend each segment further (> 0 curls upward).
    angle, start = -90 - P.get("tail", 0), tail_root
    for i, key in enumerate((None, "tail2", "tail3"), 1):
        angle -= P.get(key, 0) if key else 0
        seg = Bone(start, down(angle), L["tail"] / 3)
        bones[f"tail{i}"], start = seg, seg.end
    for leg, anchor in (("bn", hips.local(0.5, 1)), ("bf", hips.local(0.5, 1)),
                        ("fn", chest.local(chest.length - 1.5, 1.5)), ("ff", chest.local(chest.length - 1.5, 1.5))):
        kind = "back" if leg[0] == "b" else "front"
        a = P.get("hip_" + leg, 0)
        b = a + P.get("knee_" + leg, 0)
        c = b + P.get("ankle_" + leg, 0)
        upper = Bone(anchor, down(a), L[kind + "_upper"])
        lower = Bone(upper.end, down(b), L[kind + "_lower"])
        foot = Bone(lower.end, down(c), L[kind + "_foot"])
        bones.update({"upper_" + leg: upper, "lower_" + leg: lower, "foot_" + leg: foot,
                      "paw_" + leg: Bone(foot.end, (0.0, 1.0), 0.01)})
    return bones


# ---------- shapes ----------

def capsule_test(a, b, r0, r1):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length2 = dx * dx + dy * dy or 1e-9

    def inside(x, y):
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
        px, py = ax + dx * t - x, ay + dy * t - y
        r = r0 + (r1 - r0) * t
        return px * px + py * py <= r * r

    def normal(x, y):
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
        r = max(r0 + (r1 - r0) * t, 0.5)
        return ((x - ax - dx * t) / r, (y - ay - dy * t) / r)
    pad = max(r0, r1) + 1
    box = (min(ax, b[0]) - pad, min(ay, b[1]) - pad, max(ax, b[0]) + pad, max(ay, b[1]) + pad)
    return inside, box, normal


def ellipse_test(center, rx, ry, direction):
    cx, cy = center
    c, s = -direction[1], direction[0]  # rotate so ry is along the bone

    def inside(x, y):
        lx, ly = x - cx, y - cy
        u, v = lx * c + ly * s, -lx * s + ly * c
        return (u / rx) ** 2 + (v / ry) ** 2 <= 1

    def normal(x, y):
        lx, ly = x - cx, y - cy
        u, v = (lx * c + ly * s) / rx, (-lx * s + ly * c) / ry
        return (u * c - v * s, u * s + v * c)
    pad = max(rx, ry) + 1
    return inside, (cx - pad, cy - pad, cx + pad, cy + pad), normal


def poly_test(points):
    def inside(x, y):
        hit = False
        j = len(points) - 1
        for i, (xi, yi) in enumerate(points):
            xj, yj = points[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                hit = not hit
            j = i
        return hit
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    hx, hy = max(max(xs) - cx, cx - min(xs), 0.5), max(max(ys) - cy, cy - min(ys), 0.5)

    def normal(x, y):
        return ((x - cx) / hx, (y - cy) / hy)
    return inside, (min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1), normal


def part_shape(part, bones):
    bone = bones[part["bone"]]
    shape = part.get("shape", "capsule")
    if shape == "capsule":
        u0, u1 = part.get("span", [0, bone.length])
        r0, r1 = part["r"] if isinstance(part["r"], list) else (part["r"], part["r"])
        return capsule_test(bone.local(u0, part.get("v", 0)), bone.local(u1, part.get("v", 0)), r0, r1)
    if shape == "ellipse":
        u, v = part.get("at", [bone.length / 2, 0])
        return ellipse_test(bone.local(u, v), part["rx"], part["ry"], bone.dir)
    if shape == "poly":
        return poly_test([bone.local(u, v) for u, v in part["points"]])
    raise ValueError(f"unknown shape {shape}")


def rasterize(inside, box, size):
    x0, y0, x1, y1 = box
    w, h = size
    pixels = set()
    for y in range(max(0, int(math.floor(y0))), min(h, int(math.ceil(y1)) + 1)):
        for x in range(max(0, int(math.floor(x0))), min(w, int(math.ceil(x1)) + 1)):
            if inside(x + 0.5, y + 0.5):
                pixels.add((x, y))
    return pixels


# ---------- cutout sprites ----------

def scale2x(grid):
    """EPX/Scale2x: doubles a pixel grid while keeping edges crisp (RotSprite's first step)."""
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


def snap(point):
    return (math.floor(point[0]) + 0.5, math.floor(point[1]) + 0.5)


def angle_of(direction):
    return math.atan2(direction[1], direction[0])


def mix(c, target, t):
    return tuple(round(c[i] + (target[i] - c[i]) * t) for i in range(3)) + (255,)


class Sprite:
    """A pixel layer drawn on the canvas in the rest pose; afterwards it follows its bone.

    Rotation is RotSprite-style: upscale 8x with Scale2x, rotate by nearest sampling, read back at
    native size. An unrotated layer is copied exactly.
    """

    def __init__(self, layer, palette, rest_bones):
        rows = layer["rows"]
        self.grid = [[palette[ch] if ch != "." else None for ch in row] for row in rows]
        self.big = self.grid
        for _ in range(3):
            self.big = scale2x(self.big)
        self.w, self.h = len(rows[0]), len(rows)
        rest = rest_bones[layer["bone"]]
        anchor = snap(rest.start)
        ox, oy = layer.get("origin", [0, 0])
        self.pivot = (anchor[0] - ox, anchor[1] - oy)
        self.rest_angle = angle_of(rest.dir)

    def paint(self, bone, size):
        ax, ay = snap(bone.start)
        delta = angle_of(bone.dir) - self.rest_angle
        delta = (delta + math.pi) % (2 * math.pi) - math.pi
        w, h = size
        out = {}
        if abs(delta) < math.radians(0.5):
            dx, dy = round(ax - self.pivot[0]), round(ay - self.pivot[1])
            for y, row in enumerate(self.grid):
                for x, c in enumerate(row):
                    if c and 0 <= x + dx < w and 0 <= y + dy < h:
                        out[(x + dx, y + dy)] = c
            return out
        cos, sin = math.cos(-delta), math.sin(-delta)
        reach = math.hypot(max(self.pivot[0], self.w - self.pivot[0]), max(self.pivot[1], self.h - self.pivot[1])) + 1
        for y in range(max(0, int(ay - reach)), min(h, int(ay + reach) + 1)):
            for x in range(max(0, int(ax - reach)), min(w, int(ax + reach) + 1)):
                rx, ry = x + 0.5 - ax, y + 0.5 - ay
                sx = self.pivot[0] + rx * cos - ry * sin
                sy = self.pivot[1] + rx * sin + ry * cos
                bx, by = math.floor(sx * 8), math.floor(sy * 8)
                if 0 <= bx < self.w * 8 and 0 <= by < self.h * 8 and self.big[by][bx]:
                    out[(x, y)] = self.big[by][bx]
        return out


def cleanup(color):
    """Pixel-art cleanup after rotation: drop stray single pixels and fill pinholes."""
    for x, y in list(color):
        if not any(n in color for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
            del color[(x, y)]
    if not color:
        return
    xs, ys = [p[0] for p in color], [p[1] for p in color]
    holes = {}
    for y in range(min(ys), max(ys) + 1):
        for x in range(min(xs), max(xs) + 1):
            if (x, y) not in color:
                around = [color.get(n) for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))]
                if all(around):
                    holes[(x, y)] = max(set(around), key=around.count)
    color.update(holes)


# ---------- frame rendering ----------

LIGHT = (0.55, -0.83)  # from the upper-front for a right-facing character


def shade(mask, ramp, normal):
    """Volume cel shading: each pixel's surface direction against one global light."""
    out = {}
    for x, y in mask:
        nx, ny = normal(x + 0.5, y + 0.5)
        d = nx * LIGHT[0] + ny * LIGHT[1]
        if len(ramp) > 3 and d > 0.7:
            out[(x, y)] = ramp[3]
        elif d > 0.3:
            out[(x, y)] = ramp[2]
        elif d < -0.35:
            out[(x, y)] = ramp[0]
        else:
            out[(x, y)] = ramp[1]
    return out


def build_parts(spec, rig):
    parts = []
    if "cutout" in spec:
        palette = {k: hex_rgba(v) for k, v in spec["palette"].items()}
        rest_bones = place(spec, rig, rest_pose(spec, rig))
        layers = {layer["name"]: layer for layer in spec["cutout"]}
        for layer in spec["cutout"]:
            if "from" in layer:  # reuse another layer's pixels on a different bone (e.g. far legs)
                layer = dict(layers[layer["from"]], **{k: v for k, v in layer.items() if k != "from"})
            parts.append(dict(layer, shape="sprite", sprite=Sprite(layer, palette, rest_bones),
                              group=layer.get("group", layer["name"])))
        return sorted(parts, key=lambda p: p["z"])
    for name, part in rig["parts"].items():
        part = deep_merge(part, spec.get("parts", {}).get(name))
        if part.get("hidden"):
            continue
        parts.append(dict(part, name=name))
    for i, extra in enumerate(spec.get("extras", [])):
        parts.append(dict(extra, name=extra.get("name", f"extra{i}"), group=extra.get("group", f"extra{i}")))
    return sorted(parts, key=lambda p: p["z"])


def place(spec, rig, pose):
    """Solve the skeleton, then plant the lowest foot on the ground row."""
    w, h = spec["size"]
    ground = h - 3
    probe = solve_skeleton(rig, pose, (0.0, 0.0))
    lowest = max(b.local(u, 0)[1] for k, b in probe.items() if k.startswith("foot_") for u in (-1, b.length + 0.4))
    root = (round(w * spec.get("root_x", 0.4) + pose.get("dx", 0)) + 0.5, round(ground + 0.5 - lowest - rig["sole"]) + 0.5 + pose.get("dy", 0))
    return solve_skeleton(rig, pose, root)


def rest_pose(spec, rig):
    """The pose cutout layers are drawn in: the family's rest pose plus the character's posture."""
    pose = dict(presets.REST_POSES[rig.get("family", "humanoid")])
    for k, v in spec.get("pose_offset", {}).items():
        if k not in ("dx", "dy"):  # a global shift moves the art too, so layers stay drawn where they are
            pose[k] = pose.get(k, 0) + v
    return pose


def apply_touchups(image, spec, anim, index):
    """Hand edits for one frame, kept in the spec so they survive every re-render."""
    edits = spec.get("touchups", {}).get(anim, {}).get(str(index), [])
    palette = {k: hex_rgba(v) for k, v in spec.get("palette", {}).items()}
    for edit in edits:
        color = (0, 0, 0, 0) if "erase" in edit else palette.get(edit["color"]) or hex_rgba(edit["color"])
        for x, y in edit.get("erase", edit.get("pixels", [])):
            image.putpixel((x, y), color)
    return image


def make_darken(spec, outline):
    """Darken a color by stepping down its palette ramp, so shading never leaves the palette.

    spec["ramps"] lists palette symbols dark -> light (e.g. "k12345678"). Colors outside every
    ramp fall back to mixing toward the outline color by `t`.
    """
    palette = {k: hex_rgba(v) for k, v in spec.get("palette", {}).items()}
    steps_of = {}
    for ramp in spec.get("ramps", []):
        colors = [palette[ch] for ch in ramp]
        for i, c in enumerate(colors):
            steps_of.setdefault(c, (colors, i))

    def darken(c, steps, t):
        if c in steps_of:
            colors, i = steps_of[c]
            return colors[max(0, i - steps)]
        return mix(c, outline, t)
    return darken


def render_frame(spec, rig, pose, parts):
    w, h = spec["size"]
    bones = place(spec, rig, pose)
    mats = {k: [hex_rgba(c) for c in v] for k, v in spec.get("materials", {}).items()}
    outline = hex_rgba(spec["outline"])
    darken = make_darken(spec, outline)

    color, owner = {}, {}
    for index, part in enumerate(parts):
        if part.get("shape") == "sprite":
            painted = part["sprite"].paint(bones[part["bone"]], (w, h))
            if part.get("far"):
                painted = {p: darken(c, spec.get("far_steps", 2), spec.get("far_shade", 0.35)) for p, c in painted.items()}
        else:
            inside, box, normal = part_shape(part, bones)
            mask = rasterize(inside, box, (w, h))
            ramp = mats[part["mat"]]
            if part.get("far"):
                ramp = [ramp[0], ramp[0], ramp[1]]
            painted = shade(mask, ramp, normal)
        for p, c in painted.items():
            color[p], owner[p] = c, (index, part.get("group", part["name"]))
    # Separate overlapping groups: a back pixel touching a front group gets darker.
    for (x, y), (index, group) in list(owner.items()):
        for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            other = owner.get(nb)
            if not other or other[0] <= index or other[1] == group:
                continue
            back, front = parts[index], parts[other[0]]
            if not (back.get("separate", True) and front.get("separate", True)):
                continue
            if back.get("shape") == "sprite":
                color[(x, y)] = darken(color[(x, y)], 2, 0.45)
                break
            if back.get("mat") == front.get("mat"):
                color[(x, y)] = mats[back["mat"]][0]
                break
    for stamp in spec.get("stamps", []):
        bone = bones[stamp["bone"]]
        ox, oy = bone.local(*stamp["at"])
        ox, oy = int(math.floor(ox)), int(math.floor(oy))
        palette = {k: hex_rgba(v) for k, v in stamp["colors"].items()}
        for dy, row in enumerate(stamp["rows"]):
            for dx, ch in enumerate(row):
                if ch != "." and 0 <= ox + dx < w and 0 <= oy + dy < h:
                    color[(ox + dx, oy + dy)] = palette[ch]
    if spec.get("cleanup"):
        cleanup(color)
    edge = [(x, y) for x in range(w) for y in range(h)
            if (x, y) not in color and any(n in color for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))]
    selout = {}
    for x, y in edge:
        # Selective outline: edges facing the light take a dark tint of the fill they border.
        lit = color.get((x, y + 1)) or color.get((x - 1, y))
        selout[(x, y)] = darken(lit, spec.get("selout_steps", 3), spec.get("selout", 1.0)) if lit else outline
    color.update(selout)
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for p, c in color.items():
        image.putpixel(p, c)
    return image


# ---------- export ----------

def to_v1_document(image, name):
    """Express a frame in the existing pixel-art-json v1 schema so it stays patchable."""
    colors = sorted({c for c in image.get_flattened_data() if c[3]})
    palette = {".": "#00000000"}
    lookup = {(0, 0, 0, 0): "."}
    for symbol, c in zip(SYMBOLS, colors):
        palette[symbol] = "#%02X%02X%02X" % c[:3]
        lookup[c] = symbol
    w, h = image.size
    rows = ["".join(lookup[image.getpixel((x, y))] for x in range(w)) for y in range(h)]
    return {"version": 1, "size": [w, h], "palette": palette, "layers": [{"name": "frame", "rows": rows}],
            "meta": {"description": name}}


def checker(size, cell):
    bg = Image.new("RGBA", size, (38, 43, 61, 255))
    draw = ImageDraw.Draw(bg)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(48, 54, 76, 255))
    return bg


def enlarge(image, scale):
    big = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
    bg = checker(big.size, scale * 4)
    bg.alpha_composite(big)
    return bg


def load_v1_renderer(skill_dir):
    path = Path(skill_dir) / "scripts" / "pixel_art.py"
    spec = importlib.util.spec_from_file_location("pixel_art", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_rest_sheet(spec, rig, out, scale):
    """Rest-pose art (if any) over a labeled grid with bone lines, plus bone coordinates as JSON."""
    pose = rest_pose(spec, rig)
    bones = place(spec, rig, pose)
    w, h = spec["size"]
    art = render_frame(spec, rig, pose, build_parts(spec, rig)) if "cutout" in spec or "materials" in spec else None
    m = 24
    sheet = Image.new("RGBA", (w * scale + m, h * scale + m), (30, 34, 48, 255))
    sheet.alpha_composite(checker((w * scale, h * scale), scale), (m, m))
    if art:
        sheet.alpha_composite(art.resize((w * scale, h * scale), Image.NEAREST), (m, m))
    draw = ImageDraw.Draw(sheet)
    for x in range(w + 1):
        draw.line([(m + x * scale, m), (m + x * scale, m + h * scale)], fill=(70, 78, 100, 255) if x % 5 else (110, 120, 150, 255))
        if x % 5 == 0 and x < w:
            draw.text((m + x * scale + 1, 2), str(x), fill=(220, 225, 240, 255))
    for y in range(h + 1):
        draw.line([(m, m + y * scale), (m + w * scale, m + y * scale)], fill=(70, 78, 100, 255) if y % 5 else (110, 120, 150, 255))
        if y % 5 == 0 and y < h:
            draw.text((2, m + y * scale + 1), str(y), fill=(220, 225, 240, 255))
    coords = {}
    for name, bone in bones.items():
        a = (m + bone.start[0] * scale, m + bone.start[1] * scale)
        b = (m + bone.end[0] * scale, m + bone.end[1] * scale)
        draw.line([a, b], fill=(255, 90, 90, 255), width=2)
        draw.ellipse([a[0] - 3, a[1] - 3, a[0] + 3, a[1] + 3], fill=(255, 220, 90, 255))
        coords[name] = {"start": [round(c, 2) for c in bone.start], "end": [round(c, 2) for c in bone.end]}
    sheet.save(out / "rest-grid.png")
    if art:
        art.save(out / "rest.png")
    (out / "rest-bones.json").write_text(json.dumps(coords, indent=1), encoding="utf-8")
    print(f"wrote {out / 'rest-grid.png'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument("--skill-dir", default=str(HERE.parents[1] / "skills" / "pixel-forge"))
    parser.add_argument("--rest", action="store_true",
                        help="only render the rest pose with a coordinate grid and skeleton, for drawing cutout layers")
    args = parser.parse_args(argv)

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    rig = presets.rig(spec.get("rig", "humanoid"), spec.get("proportions", {}))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.rest:
        write_rest_sheet(spec, rig, out, args.scale)
        return
    parts = build_parts(spec, rig)
    v1 = load_v1_renderer(args.skill_dir)
    w, h = spec["size"]
    manifest = {"size": [w, h], "facing": "right", "animations": {}}
    rows_for_contact = []
    for anim in spec["anims"]:
        name = anim.get("name", anim["preset"])
        params = {k: v for k, v in anim.items() if k not in ("preset", "name", "pose_offset")}
        frames = presets.anim(rig.get("family", "humanoid"), anim["preset"], **params)
        images = []
        (out / name).mkdir(exist_ok=True)
        offset = {**spec.get("pose_offset", {}), **anim.get("pose_offset", {})}
        for i, (pose, duration) in enumerate(frames):
            # Character posture (hunch, wide stance...) is added on top of every preset frame.
            pose = {k: pose.get(k, 0) + offset.get(k, 0) for k in set(pose) | set(offset)}
            image = apply_touchups(render_frame(spec, rig, pose, parts), spec, name, i)
            doc = to_v1_document(image, f"{spec.get('name', 'character')} {name} {i}")
            check, _ = v1.render_document(doc)
            assert list(check.get_flattened_data()) == list(image.get_flattened_data()), "v1 source does not reproduce frame"
            (out / name / f"frame-{i:02d}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            image.save(out / name / f"frame-{i:02d}.png")
            box = image.getbbox()
            if box and (box[0] == 0 or box[1] == 0 or box[2] == w or box[3] == h):
                print(f"warning: {name} frame {i} touches the canvas edge {box}")
            images.append((image, duration))
        sheet = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
        for i, (image, _) in enumerate(images):
            sheet.paste(image, (i * w, 0))
        sheet.save(out / f"{name}.png")
        previews = [enlarge(image, args.scale).convert("P", palette=Image.ADAPTIVE) for image, _ in images]
        previews[0].save(out / f"{name}.preview.gif", save_all=True, append_images=previews[1:],
                         duration=[d for _, d in images], loop=0, disposal=2)
        manifest["animations"][name] = {"sheet": f"{name}.png", "frames": [
            {"rect": [i * w, 0, w, h], "ms": d} for i, (_, d) in enumerate(images)]}
        rows_for_contact.append(images)
    (out / "animation.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    cols = max(len(r) for r in rows_for_contact)
    s = args.scale
    contact = checker((cols * w * s, len(rows_for_contact) * h * s), s * 4)
    for r, images in enumerate(rows_for_contact):
        for c, (image, _) in enumerate(images):
            contact.alpha_composite(image.resize((w * s, h * s), Image.NEAREST), (c * w * s, r * h * s))
    contact.save(out / "contact.png")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
