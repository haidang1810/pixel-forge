#!/usr/bin/env python3
"""Skeletal pixel characters and animation from a short spec; no image-generation service.

A spec picks a rig preset, overrides proportions and parts, and lists animation presets. Parts
are either vector shapes re-rasterized every frame or cutout pixel layers drawn in the rest pose
and rotated RotSprite-style. Every exported frame is also written in the pixel-art-json v1
format and checked to reproduce exactly through pixel_art.py. See references/rig.md.
"""
import argparse
import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import cutout_tools
import palette_tools
import polish
import rig_presets as presets

HERE = Path(__file__).resolve().parent
SYMBOLS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+-=?@"


def pixels_of(image):
    """Flat pixel list across Pillow versions (getdata is deprecated in newer releases)."""
    return list(image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata())


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
    def __init__(self, start, direction, length, scale=1.0):
        """scale is squash and stretch: parts on the bone stretch by `scale` along it and narrow by
        1/scale across it (scale < 1 squashes). Parts are authored at scale 1."""
        self.start, self.dir, self.length, self.scale = start, direction, length, scale
        self.end = add(start, direction, length)

    def local(self, u, v):
        """u along the bone, v perpendicular (+v is forward for an upright bone)."""
        nx, ny = -self.dir[1], self.dir[0]
        u, v = u * self.scale, v / self.scale
        return (self.start[0] + self.dir[0] * u + nx * v, self.start[1] + self.dir[1] * u + ny * v)


def solve_skeleton(rig, pose, root):
    family = rig.get("family")
    if family == "quadruped":
        return solve_quadruped(rig, pose, root)
    if family == "slime":
        return solve_slime(rig, pose, root)
    if family == "serpent":
        return solve_serpent(rig, pose, root)
    if family == "bird":
        return solve_bird(rig, pose, root)
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


def solve_slime(rig, pose, root):
    """A blob on the ground. root is the bottom centre; "body" points up and carries the squash.

    stretch > 1 is tall and thin, < 1 squashed flat and wide; lean > 0 tips the top forward.
    """
    L, P = rig["bones"], pose
    stretch = max(0.2, P.get("stretch", 1.0))
    body = Bone(root, up(P.get("lean", 0)), L["height"] * stretch, scale=stretch)
    return {"body": body, "foot_c": Bone(root, (0.0, 1.0), 0.01), "top": Bone(body.end, body.dir, 0.01)}


def solve_serpent(rig, pose, root):
    """A snake seen from the side. root is where the raised neck leaves the ground.

    neck: from straight up (forward > 0); head > 0 points the nose down; jaw opens the lower jaw.
    seg1..segN run backward from the root; seg_i bends each segment relative to the previous one
    (> 0 turns the body downward/back, < 0 lifts it), so a travelling wave is a sine over i.
    """
    L, P = rig["bones"], pose
    bones = {}
    bones["neck"] = Bone(root, up(P.get("neck", 0)), L["neck"])
    head_angle = 90 - P.get("head", 0)
    bones["head"] = Bone(bones["neck"].end, down(head_angle), L["head"])
    bones["jaw"] = Bone(bones["head"].local(0.5, 1.2), down(head_angle - P.get("jaw", 0)), L["head"] * 0.85)
    angle, start = -90.0, root
    for i in range(1, int(L["segments"]) + 1):
        angle += P.get(f"seg{i}", 0)
        seg = Bone(start, down(angle), L["seg"])
        bones[f"seg{i}"], start = seg, seg.end
    return bones


def solve_bird(rig, pose, root):
    """A bird seen from the side. root is the hip.

    body: body tilt (0 level, > 0 chest up); neck from straight up; head > 0 nose down; tail > 0 up.
    wing_n/wing_f: limb angle of the wing (0 down, -95 folded back along the body, 160 raised);
    wingtip_*: bend of the outer wing. hip/knee/ankle work like the humanoid legs.
    """
    L, P = rig["bones"], pose
    tilt = math.radians(P.get("body", 0))
    body = Bone(root, (math.cos(tilt), -math.sin(tilt)), L["body"])
    bones = {"spine": body, "body": body}
    bones["neck"] = Bone(body.local(L["body"] - 1, -1.5), up(P.get("neck", 0)), L["neck"])
    bones["head"] = Bone(bones["neck"].end, down(90 - P.get("head", 0)), L["head"])
    bones["tail"] = Bone(body.local(0.5, -0.5), down(-90 - P.get("tail", 0)), L["tail"])
    shoulder = body.local(L["body"] * 0.7, -1.8)
    for side in ("n", "f"):
        wing = P.get("wing_" + side, -95)
        upper = Bone(shoulder, down(wing), L["wing_upper"])
        tip = Bone(upper.end, down(wing + P.get("wingtip_" + side, 0)), L["wing_fore"])
        thigh = Bone(root, down(P.get("hip_" + side, 0)), L["thigh"])
        shin_angle = P.get("hip_" + side, 0) - P.get("knee_" + side, 0)
        shin = Bone(thigh.end, down(shin_angle), L["shin"])
        foot = Bone(shin.end, down(shin_angle + 90 + P.get("ankle_" + side, 0)), L["foot"])
        bones.update({"wing_" + side: upper, "wingtip_" + side: tip, "thigh_" + side: thigh,
                      "shin_" + side: shin, "foot_" + side: foot})
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
    rest_length = bone.length / bone.scale  # part coordinates are authored unscaled
    if shape == "capsule":
        u0, u1 = part.get("span", [0, rest_length])
        r0, r1 = part["r"] if isinstance(part["r"], list) else (part["r"], part["r"])
        return capsule_test(bone.local(u0, part.get("v", 0)), bone.local(u1, part.get("v", 0)),
                            r0 / bone.scale, r1 / bone.scale)
    if shape == "ellipse":
        u, v = part.get("at", [rest_length / 2, 0])
        return ellipse_test(bone.local(u, v), part["rx"] / bone.scale, part["ry"] * bone.scale, bone.dir)
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
LIGHTS = {"upper-front": LIGHT, "upper-back": (-0.55, -0.83), "top": (0.0, -1.0),
          "front": (0.83, -0.55), "back": (-0.83, -0.55)}


def light_vector(style):
    """Named light direction, or degrees: 0 = from the facing side, 90 = from straight above."""
    light = (style or {}).get("light", "upper-front")
    if isinstance(light, (int, float)):
        a = math.radians(light)
        return (math.cos(a), -math.sin(a))
    return LIGHTS[light]


def part_local(bone):
    """Inverse of Bone.local: canvas point -> unscaled (u, v) on the bone, so textures ride along."""
    nx, ny = -bone.dir[1], bone.dir[0]

    def local(x, y):
        rx, ry = x - bone.start[0], y - bone.start[1]
        return ((rx * bone.dir[0] + ry * bone.dir[1]) / bone.scale, (rx * nx + ry * ny) * bone.scale)
    return local


def shade(mask, ramp, normal, style=None, texture=None, local=None):
    """Volume cel shading: each pixel's surface direction against one global light.

    style: shades (2, 3 or 4 tones), dither (checker the boundary between two tones), light.
    texture: a polish.TEXTURES name, laid out in part-local coordinates from `local(x, y)`."""
    style = style or {}
    lx, ly = light_vector(style)
    shades = style.get("shades", 4)

    def tone(d):
        if shades >= 4 and len(ramp) > 3 and d > 0.7:
            return 3
        if shades >= 3 and d > 0.3:
            return 2
        if shades == 2:
            return 0 if d < -0.1 else 1
        return 0 if d < -0.35 else 1
    out = {}
    for x, y in mask:
        nx, ny = normal(x + 0.5, y + 0.5)
        d = nx * lx + ny * ly
        level = tone(d)
        if style.get("dither"):
            low, high = tone(d - 0.12), tone(d + 0.12)
            if low != high:
                level = high if (x + y) % 2 == 0 else low
        if texture:
            top = min(len(ramp), shades) - 1
            u, v = local(x + 0.5, y + 0.5)
            level = max(0, min(top, level + polish.texture_offset(texture, round(u), round(v), level, top)))
        out[(x, y)] = ramp[level]
    return out


def cutout_layers(spec, rig):
    """Pixel layers for a cutout character: drawn regions (spec "draw") first, then baked "cutout" rows."""
    layers = []
    if "draw" in spec:
        rest = place(spec, rig, rest_pose(spec, rig))
        layers += cutout_tools.build_cutout(spec, {k: (b.start, b.end) for k, b in rest.items()}, hex_rgba)
    return layers + list(spec.get("cutout", []))


def is_cutout(spec):
    return "cutout" in spec or "draw" in spec


def build_parts(spec, rig):
    parts = []
    if is_cutout(spec):
        palette = {k: hex_rgba(v) for k, v in spec["palette"].items()}
        rest_bones = place(spec, rig, rest_pose(spec, rig))
        all_layers = cutout_layers(spec, rig)
        layers = {layer["name"]: layer for layer in all_layers}
        for layer in all_layers:
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
        extra = presets.scale_part(copy.deepcopy(extra), rig)  # extras follow the build too
        parts.append(dict(extra, name=extra.get("name", f"extra{i}"), group=extra.get("group", f"extra{i}")))
    return sorted(parts, key=lambda p: p["z"])


def root_bone(bones):
    """Every solver creates the bone that starts at the skeleton root first."""
    return next(iter(bones.values()))


def place(spec, rig, pose):
    """Solve the skeleton, then plant the lowest foot on the ground row."""
    w, h = spec["size"]
    ground = h - 3
    probe = solve_skeleton(rig, pose, (0.0, 0.0))
    prefixes = tuple(rig.get("ground_bones", ("foot_", "paw_")))
    feet = [b for k, b in probe.items() if k.startswith(prefixes)] or list(probe.values())
    lowest = max(b.local(u, 0)[1] for b in feet for u in (-1, b.length / b.scale + 0.4))
    root = (round(w * spec.get("root_x", 0.4) + pose.get("dx", 0)) + 0.5, round(ground + 0.5 - lowest - rig["sole"]) + 0.5 + pose.get("dy", 0))
    return solve_skeleton(rig, pose, root)


def rest_pose(spec, rig):
    """The pose cutout layers are drawn in: the family's rest pose plus the character's posture."""
    pose = dict(presets.REST_POSES[rig.get("family", "humanoid")])
    for k, v in posture(spec, rig).items():
        if k not in ("dx", "dy"):  # a global shift moves the art too, so layers stay drawn where they are
            pose[k] = pose.get(k, 0) + v
    return pose


def posture(spec, rig, anim=None):
    """Joint offsets added to every frame: the build's own posture, plus the spec's pose_offset
    (an anim entry's pose_offset replaces the spec's value for each key it names)."""
    own = {**spec.get("pose_offset", {}), **((anim or {}).get("pose_offset", {}))}
    build = (rig.get("build") or {}).get("pose", {})
    return {k: build.get(k, 0) + own.get(k, 0) for k in set(build) | set(own)}


def apply_touchups(image, spec, anim, index):
    """Hand edits for one frame, kept in the spec so they survive every re-render."""
    edits = spec.get("touchups", {}).get(anim, {}).get(str(index), [])
    palette = {k: hex_rgba(v) for k, v in spec.get("palette", {}).items()}
    for edit in edits:
        color = (0, 0, 0, 0) if "erase" in edit else palette.get(edit["color"]) or hex_rgba(edit["color"])
        for x, y in edit.get("erase", edit.get("pixels", [])):
            image.putpixel((x, y), color)
    return image


def make_darken(spec, outline, materials=False):
    """Darken a color by stepping down its palette ramp, so shading never leaves the palette.

    spec["ramps"] lists palette symbols dark -> light (e.g. "k12345678"). Colors outside every
    ramp fall back to mixing toward the outline color by `t`.
    """
    palette = {k: hex_rgba(v) for k, v in spec.get("palette", {}).items()}
    steps_of = {}
    ramps = [[palette[ch] for ch in ramp] for ramp in spec.get("ramps", [])]
    if materials:  # vector characters: their material ramps are already dark -> light
        ramps += [[hex_rgba(c) for c in ramp] for ramp in spec.get("materials", {}).values()]
    for colors in ramps:
        for i, c in enumerate(colors):
            steps_of.setdefault(c, (colors, i))

    def darken(c, steps, t):
        if c in steps_of:
            colors, i = steps_of[c]
            return colors[max(0, i - steps)]
        return mix(c, outline, t)
    return darken


def snap_to_kit(image, slug):
    """Replace every opaque color by the nearest color of the palette kit (perceptually weighted)."""
    targets = [hex_rgba(c) for c in palette_tools.kit(slug)["colors"]]
    cache = {}

    def nearest(c):
        if c not in cache:
            cache[c] = min(targets, key=lambda t: 2 * (t[0] - c[0]) ** 2 + 4 * (t[1] - c[1]) ** 2 + 3 * (t[2] - c[2]) ** 2)
        return cache[c]
    px = image.load()
    for y in range(image.height):
        for x in range(image.width):
            c = px[x, y]
            if c[3]:
                px[x, y] = nearest(c)


BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def render_frame(spec, rig, pose, parts, previous=None):
    """Render one pose. Pose keys beyond joint angles:

    plant: "all"  rest the lowest pixel of the whole body (not only the feet) on the ground row,
                  for lying, crawling or fallen poses
    flash: 1      hit flash: every non-outline pixel becomes spec["flash"] (default white)
    dissolve: t   ordered-dither removal of a fraction t (0..1) of the pixels, for fading out
    """
    # Ground lock: measure where the feet (or, with plant "all", the whole body) actually end up and
    # shift by whole pixels so that bottom row lands exactly on the ground row h-3, with the outline
    # on h-2. The pose's own dy (jumps, hovering) is then applied on top.
    prefixes = tuple(rig.get("ground_bones", ("foot_", "paw_")))
    support = parts if pose.get("plant") == "all" else [p for p in parts if p["bone"].startswith(prefixes)]
    if support:
        bottom = _bottom(spec, rig, pose, support)
        if bottom is not None:
            pose = dict(pose, dy=pose.get("dy", 0) + (spec["size"][1] - 1) - bottom)
    image = _render(spec, rig, pose, parts, previous)
    image.info["pose"] = pose  # the grounded pose actually drawn; the next frame's smear starts here
    image.info["pivot"] = [math.floor(c) for c in root_bone(place(spec, rig, pose)).start]
    if pose.get("flash"):
        flash = hex_rgba(spec.get("flash", "#FFFFFF"))
        outline = hex_rgba(spec["outline"])
        for p, c in zip(((x, y) for y in range(image.height) for x in range(image.width)), pixels_of(image)):
            if c[3] and c != outline:
                image.putpixel(p, flash)
    if (spec.get("style") or {}).get("snap"):
        snap_to_kit(image, spec["palette_kit"])
    amount = pose.get("dissolve", 0)
    if amount > 0:
        for y in range(image.height):
            for x in range(image.width):
                if BAYER4[y % 4][x % 4] < amount * 16:
                    image.putpixel((x, y), (0, 0, 0, 0))
    return image


def _bottom(spec, rig, pose, parts):
    """Exclusive bottom row of `parts` drawn in `pose` at its grounded position (the pose's dy ignored).

    The trial canvas is `pad` rows taller and dy -pad cancels its lower ground row, so the art keeps
    its place and anything below the real canvas edge is still measured.
    """
    w, h = spec["size"]
    pad = h
    probe = {k: v for k, v in spec.items() if k != "shadow"}
    probe["size"] = [w, h + pad]
    trial = {k: v for k, v in pose.items() if k not in ("plant", "dissolve", "flash")}
    trial["dy"] = -pad
    box = _render(probe, rig, trial, parts).getbbox()
    return box[3] if box else None


def _render(spec, rig, pose, parts, previous=None):
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
            bone = bones[part["bone"]]
            painted = shade(mask, ramp, normal, spec.get("style"), part.get("texture"), part_local(bone))
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
    opts = polish.options(spec.get("style"))
    tones = None
    if opts:
        ramps = [[hex_rgba(c) for c in r] for r in spec.get("materials", {}).values()]
        palette = {k: hex_rgba(v) for k, v in spec.get("palette", {}).items()}
        ramps += [[palette[ch] for ch in r] for r in spec.get("ramps", [])]
        tones = polish.Tones(ramps)
        if opts["clean"]:
            polish.clean(color, owner)
            polish.despeckle(color, tones)
        polish.lighting(color, owner, parts, tones, light_vector(spec.get("style")), opts)
        if opts["clean"]:
            polish.despeckle(color, tones)  # lighting can leave single-pixel tone changes behind
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
    kind = (spec.get("style") or {}).get("outline")
    if kind == "selout":
        # Every edge takes a darker tone of the fill it borders.
        shade_down = make_darken(spec, outline, materials=True)
        for x, y in edge:
            fill = next(c for c in (color.get(n) for n in ((x, y + 1), (x - 1, y), (x + 1, y), (x, y - 1))) if c)
            selout[(x, y)] = shade_down(fill, spec.get("selout_steps", 3), 0.6)
    elif kind == "black":
        selout = {p: outline for p in edge}
    elif kind is None:
        for x, y in edge:
            # Edges facing the light take a dark tint of the fill they border.
            lit = color.get((x, y + 1)) or color.get((x - 1, y))
            selout[(x, y)] = darken(lit, spec.get("selout_steps", 3), spec.get("selout", 1.0)) if lit else outline
    color.update(selout)
    if opts.get("aa") and kind != "none":
        polish.corner_aa(color, set(selout), tones)
    target = pose.get("smear")
    if opts.get("smear") and target and previous is not None and target in bones:
        before = place(spec, rig, previous)[target]
        reach = max([1.0] + [max(part.get("span", [0, 1])[1], *(u for u, _ in part.get("points", [[0, 0]])),
                                 part.get("at", [0, 0])[0] + part.get("ry", 0))
                             for part in parts if part.get("bone") == target and part.get("shape") != "sprite"])
        if "smear" in spec:
            fill = hex_rgba(spec["smear"])
        else:  # the brightest color the character already uses, so the trail stays in the palette
            candidates = [hex_rgba(c) for r in spec.get("materials", {}).values() for c in r]
            candidates += [hex_rgba(c) for c in spec.get("palette", {}).values() if len(c) == 7]
            fill = max(candidates, key=lambda c: c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722)
        polish.smear(color, before, bones[target], reach, fill)
    shadow = spec.get("shadow")
    if shadow:
        # Ground shadow for floating characters: shrinks as the body rises; never covers the art.
        lift = max(0.0, -pose.get("dy", 0))
        rx = max(1.0, shadow.get("rx", 6) * (1 - shadow.get("shrink", 0.06) * lift))
        cx, cy = root_bone(bones).start[0], h - 2.5
        fill = hex_rgba(shadow["color"])
        for y in (h - 3, h - 2):
            for x in range(w):
                if abs(x + 0.5 - cx) <= rx - (y == h - 2) and (x, y) not in color:
                    color[(x, y)] = fill
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for (x, y), c in color.items():
        if 0 <= x < w and 0 <= y < h:  # negative indexes would wrap to the far edge
            image.putpixel((x, y), c)
    return image


# ---------- export ----------

def to_v1_document(image, name):
    """Express a frame in the existing pixel-art-json v1 schema so it stays patchable."""
    colors = sorted({c for c in pixels_of(image) if c[3]})
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


def load_v1_renderer():
    path = HERE / "pixel_art.py"
    spec = importlib.util.spec_from_file_location("pixel_art", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_rest_sheet(spec, rig, out, scale):
    """Rest-pose art (if any) over a labeled grid with bone lines, plus bone coordinates as JSON."""
    pose = rest_pose(spec, rig)
    bones = place(spec, rig, pose)
    w, h = spec["size"]
    art = render_frame(spec, rig, pose, build_parts(spec, rig)) if is_cutout(spec) or "materials" in spec else None
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


SPEC_KEYS = {"name", "size", "rig", "root_x", "outline", "proportions", "pose_offset", "materials", "parts",
             "extras", "stamps", "anims", "palette", "cutout", "ramps", "cleanup", "selout", "selout_steps",
             "far_steps", "far_shade", "touchups", "shadow", "draw", "flash", "motion", "build", "style",
             "palette_gen", "smear", "palette_kit"}
HEX = "0123456789abcdefABCDEF"


def is_hex(value):
    return isinstance(value, str) and len(value) == 7 and value[0] == "#" and all(c in HEX for c in value[1:])


def prepare_spec(spec):
    """Expand generated colors: materials given as {"base": ...} and palette_gen ramps."""
    if not isinstance(spec, dict):
        raise ValueError("spec: expected a JSON object")
    spec = palette_tools.expand_palette(spec)
    if "palette_kit" in spec:
        palette_tools.kit(spec["palette_kit"])  # unknown kits fail early with the list of names
    if isinstance(spec.get("materials"), dict):
        spec = dict(spec, materials=palette_tools.expand_materials(spec["materials"], spec.get("palette_kit")))
    return spec


def validate_spec(spec):
    """Reject a spec with an actionable message before anything is written."""
    if not isinstance(spec, dict):
        raise ValueError("spec: expected a JSON object")
    unknown = set(spec) - SPEC_KEYS
    if unknown:
        raise ValueError(f"spec: unknown fields {sorted(unknown)}")
    size = spec.get("size")
    if not (isinstance(size, list) and len(size) == 2 and all(type(n) is int and 8 <= n <= 256 for n in size)):
        raise ValueError("size: expected [width, height], integers 8..256")
    if not is_hex(spec.get("outline")):
        raise ValueError("outline: expected #RRGGBB")
    rig_name = spec.get("rig", "humanoid")
    if rig_name not in presets.RIGS:
        raise ValueError(f"rig: unknown {rig_name!r}; choose from {sorted(presets.RIGS)}")
    family = presets.RIGS[rig_name]["family"]
    anims = spec.get("anims")
    if not isinstance(anims, list) or not anims:
        raise ValueError("anims: expected a nonempty list")
    names = set()
    for i, anim in enumerate(anims):
        preset = anim.get("preset") if isinstance(anim, dict) else None
        if preset not in presets.ANIMS[family]:
            raise ValueError(f"anims[{i}].preset: {preset!r} is not a {family} preset; choose from {sorted(presets.ANIMS[family])}")
        name = anim.get("name", preset)
        if name in names:
            raise ValueError(f"anims[{i}]: duplicate animation name {name!r}; set a distinct 'name'")
        names.add(name)
    for where, motion in [("motion", spec.get("motion"))] + [(f"anims[{i}].motion", a.get("motion")) for i, a in enumerate(anims)]:
        if motion is None:
            continue
        if not isinstance(motion, dict) or set(motion) - {"weight", "energy", "exaggeration", "seed", "follow"}:
            raise ValueError(f"{where}: expected an object with weight, energy, exaggeration, follow and/or seed")
        for key, low, high in (("weight", 0, 1), ("energy", 0, 1), ("exaggeration", 0, 2), ("follow", 0, 1)):
            value = motion.get(key)
            if value is not None and not (isinstance(value, (int, float)) and low <= value <= high):
                raise ValueError(f"{where}.{key}: expected a number {low}..{high}")
        if "seed" in motion and type(motion["seed"]) is not int:
            raise ValueError(f"{where}.seed: expected an integer")
    build = spec.get("build")
    if build is not None and build not in presets.BUILDS.get(family, {}):
        raise ValueError(f"build: {build!r} is not a {family} build; choose from {sorted(presets.BUILDS.get(family, {}))}")
    rig = presets.rig(rig_name, spec.get("proportions", {}), build)
    bones = set(solve_skeleton(rig, rest_pose(spec, rig), (0.0, 0.0)))
    materials = spec.get("materials", {})
    for k, ramp in materials.items():
        if not (isinstance(ramp, list) and len(ramp) in (3, 4) and all(is_hex(c) for c in ramp)):
            raise ValueError(f"materials.{k}: expected 3 or 4 #RRGGBB colors, dark to light")
    if not is_cutout(spec):
        for name, part in spec.get("parts", {}).items():
            if name not in rig["parts"]:
                raise ValueError(f"parts.{name}: not a part of rig {rig_name!r}; known parts {sorted(rig['parts'])}")
        merged = [deep_merge(p, spec.get("parts", {}).get(n)) for n, p in rig["parts"].items()]
        for where, part in [(f"parts", p) for p in merged] + [(f"extras[{i}]", e) for i, e in enumerate(spec.get("extras", []))]:
            if part.get("hidden"):
                continue
            if part.get("bone") not in bones:
                raise ValueError(f"{where}: unknown bone {part.get('bone')!r}; bones are {sorted(bones)}")
            if part.get("mat") not in materials:
                raise ValueError(f"{where}: material {part.get('mat')!r} is not defined in materials")
    for where, part in [(f"parts.{n}", p) for n, p in spec.get("parts", {}).items()] +             [(f"extras[{i}]", e) for i, e in enumerate(spec.get("extras", []))]:
        if "texture" in part and part["texture"] not in polish.TEXTURES:
            raise ValueError(f"{where}.texture: choose from {list(polish.TEXTURES)}")
    palette = spec.get("palette", {})
    for k, v in palette.items():
        if len(k) != 1 or k == "." or not is_hex(v):
            raise ValueError(f"palette.{k}: expected a single character (not '.') mapped to #RRGGBB")
    if is_cutout(spec) and not palette:
        raise ValueError("palette: cutout characters need a palette of single-character symbols")
    drawn = set()
    if "draw" in spec:
        if not isinstance(spec["draw"], list) or not spec["draw"]:
            raise ValueError("draw: expected a nonempty list of regions")
        cutout_tools.validate_draw(spec, bones)
        for region in spec["draw"]:
            names_here = [region["name"]] if len(region["bones"]) == 1 else [f"{region['name']}:{b}" for b in region["bones"]]
            drawn.update(names_here)
            drawn.update(f"{n}>{t}" for n, t in zip(names_here, region.get("mirror", {}).get("bones", [])))
    if "cutout" in spec:
        layers = dict.fromkeys(drawn)
        for i, layer in enumerate(spec["cutout"]):
            where = f"cutout[{i}] ({layer.get('name')})"
            if layer.get("name") in layers:
                raise ValueError(f"{where}: duplicate layer name")
            if layer.get("bone") not in bones:
                raise ValueError(f"{where}: unknown bone {layer.get('bone')!r}; bones are {sorted(bones)}")
            if "from" in layer:
                if layer["from"] not in layers:
                    raise ValueError(f"{where}: 'from' must name an earlier layer")
            else:
                rows = layer.get("rows")
                if not (isinstance(rows, list) and rows and all(isinstance(r, str) and len(r) == len(rows[0]) > 0 for r in rows)):
                    raise ValueError(f"{where}.rows: expected equal-length nonempty strings")
                for y, row in enumerate(rows):
                    for x, ch in enumerate(row):
                        if ch != "." and ch not in palette:
                            raise ValueError(f"{where}.rows[{y}][{x}]: unknown palette symbol {ch!r}")
            layers[layer.get("name")] = layer
    style = spec.get("style")
    if style is not None:
        if not isinstance(style, dict) or set(style) - {"outline", "shades", "dither", "light", "polish", "snap"}:
            raise ValueError("style: expected an object with outline, shades, dither, light, polish and/or snap")
        if style.get("snap") and "palette_kit" not in spec:
            raise ValueError("style.snap: needs a palette_kit to snap to")
        pol = style.get("polish", False)
        if not (isinstance(pol, bool) or (isinstance(pol, dict) and set(pol) <= set(polish.PASSES)
                                          and all(isinstance(v, bool) for v in pol.values()))):
            raise ValueError(f"style.polish: true, false, or an object of booleans for {list(polish.PASSES)}")
        if style.get("outline", "black") not in ("black", "selout", "none"):
            raise ValueError("style.outline: choose black, selout or none")
        if style.get("shades", 4) not in (2, 3, 4):
            raise ValueError("style.shades: choose 2, 3 or 4")
        if not isinstance(style.get("dither", False), bool):
            raise ValueError("style.dither: expected true or false")
        light = style.get("light", "upper-front")
        if not (isinstance(light, (int, float)) and not isinstance(light, bool)) and light not in LIGHTS:
            raise ValueError(f"style.light: a number of degrees or one of {sorted(LIGHTS)}")
    if "smear" in spec and not is_hex(spec["smear"]):
        raise ValueError("smear: expected #RRGGBB, the motion-trail color")
    if "flash" in spec and not is_hex(spec["flash"]):
        raise ValueError("flash: expected #RRGGBB, the hit-flash color")
    shadow = spec.get("shadow")
    if shadow is not None and not (isinstance(shadow, dict) and is_hex(shadow.get("color"))
                                   and set(shadow) <= {"color", "rx", "shrink"}):
        raise ValueError("shadow: expected {\"color\": \"#RRGGBB\", \"rx\": half-width, \"shrink\": per-pixel of lift}")
    for i, ramp in enumerate(spec.get("ramps", [])):
        missing = [ch for ch in ramp if ch not in palette]
        if missing:
            raise ValueError(f"ramps[{i}]: symbols {missing} are not in palette")
    for anim, frames in spec.get("touchups", {}).items():
        if anim not in names:
            raise ValueError(f"touchups.{anim}: no animation with that name")
        for index, edits in frames.items():
            for edit in edits:
                color = edit.get("color")
                if "erase" not in edit and color not in palette and not is_hex(color):
                    raise ValueError(f"touchups.{anim}.{index}: color {color!r} is neither a palette symbol nor #RRGGBB")
                for x, y in edit.get("erase", edit.get("pixels", [])):
                    if not (0 <= x < size[0] and 0 <= y < size[1]):
                        raise ValueError(f"touchups.{anim}.{index}: pixel {[x, y]} is outside the canvas")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument("--rest", action="store_true",
                        help="only render the rest pose with a coordinate grid and skeleton, for drawing cutout layers")
    parser.add_argument("--bake", metavar="SPEC_OUT",
                        help="write a copy of the spec whose drawn regions are frozen into cutout rows, for pixel edits")
    args = parser.parse_args(argv)

    try:
        spec = prepare_spec(json.loads(Path(args.spec).read_text(encoding="utf-8")))
        validate_spec(spec)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    rig = presets.rig(spec.get("rig", "humanoid"), spec.get("proportions", {}), spec.get("build"))
    out = Path(args.out)
    if Path(args.spec).resolve().parent == out.resolve() or out.resolve() in Path(args.spec).resolve().parents:
        print("error: --out must not contain the spec file; outputs there are replaced on rerun", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    if args.bake:
        target = Path(args.bake)
        if target.resolve() == Path(args.spec).resolve():
            print("error: --bake must write a new file, not the source spec", file=sys.stderr)
            return 2
        baked = {k: v for k, v in spec.items() if k != "draw"}
        baked["cutout"] = cutout_layers(spec, rig)
        target.write_text(json.dumps(baked, indent=1), encoding="utf-8")
        print(f"wrote {target}")
    if args.rest:
        write_rest_sheet(spec, rig, out, args.scale)
        return
    parts = build_parts(spec, rig)
    v1 = load_v1_renderer()
    w, h = spec["size"]
    manifest = {"size": [w, h], "facing": "right", "animations": {}}
    rows_for_contact = []
    for anim in spec["anims"]:
        name = anim.get("name", anim["preset"])
        params = {k: v for k, v in anim.items() if k not in ("preset", "name", "pose_offset", "motion")}
        family = rig.get("family", "humanoid")
        frames = presets.personalize(presets.anim(family, anim["preset"], **params), family,
                                     {**spec.get("motion", {}), **anim.get("motion", {})},
                                     loop=anim["preset"] in presets.LOOPING_BY_FAMILY.get(family, set()))
        images = []
        (out / name).mkdir(exist_ok=True)
        offset = posture(spec, rig, anim)
        drawn = None
        for i, (pose, duration) in enumerate(frames):
            # Character posture (hunch, wide stance...) is added on top of every preset frame.
            pose = {**pose, **{k: pose.get(k, 0) + v for k, v in offset.items()}}
            image = render_frame(spec, rig, pose, parts, drawn)
            drawn = image.info["pose"]
            image = apply_touchups(image, spec, name, i)
            doc = to_v1_document(image, f"{spec.get('name', 'character')} {name} {i}")
            check, _ = v1.render_document(doc)
            if pixels_of(check) != pixels_of(image):
                raise RuntimeError(f"{name} frame {i}: v1 source does not reproduce the frame")
            (out / name / f"frame-{i:02d}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            image.save(out / name / f"frame-{i:02d}.png")
            box = image.getbbox()
            if box and (box[0] == 0 or box[1] == 0 or box[2] == w or box[3] == h):
                print(f"warning: {name} frame {i} touches the canvas edge {box}")
            images.append((image, duration, image.info["pivot"]))
        sheet = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
        for i, (image, *_) in enumerate(images):
            sheet.paste(image, (i * w, 0))
        sheet.save(out / f"{name}.png")
        previews = [enlarge(image, args.scale).convert("P", palette=Image.ADAPTIVE) for image, *_ in images]
        previews[0].save(out / f"{name}.preview.gif", save_all=True, append_images=previews[1:],
                         duration=[d for _, d, _ in images], loop=0, disposal=2)
        # pivot: the hip (skeleton root) in frame pixels, so an engine can align frames and animations.
        manifest["animations"][name] = {"sheet": f"{name}.png", "frames": [
            {"rect": [i * w, 0, w, h], "ms": d, "pivot": pivot} for i, (_, d, pivot) in enumerate(images)]}
        rows_for_contact.append(images)
    (out / "animation.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    cols = max(len(r) for r in rows_for_contact)
    s = args.scale
    contact = checker((cols * w * s, len(rows_for_contact) * h * s), s * 4)
    for r, images in enumerate(rows_for_contact):
        for c, (image, *_) in enumerate(images):
            contact.alpha_composite(image.resize((w * s, h * s), Image.NEAREST), (c * w * s, r * h * s))
    contact.save(out / "contact.png")
    print(f"wrote {out}")


if __name__ == "__main__":
    raise SystemExit(main())
