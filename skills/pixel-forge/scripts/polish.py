"""Pixel-art polish passes applied by rig2d when spec["style"]["polish"] is on.

All tone changes step along the color ramps (materials and spec ramps), so frames stay inside the
palette. Colors outside every ramp (stamps such as eyes) are left alone.
"""

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
PASSES = ("clean", "aa", "ao", "cast", "rim", "smear")


def options(style):
    """style["polish"]: true for every pass, or {"clean": bool, "aa": ..., "ao": ..., "cast": ..., "rim": ..., "smear": ...}."""
    polish = (style or {}).get("polish")
    if polish is True:
        return {p: True for p in PASSES}
    if isinstance(polish, dict):
        return {p: bool(polish.get(p, False)) for p in PASSES}
    return {}


class Tones:
    """Ramp lookup: step a color darker or lighter inside its own ramp."""

    def __init__(self, ramps):
        self.where = {}
        for colors in ramps:
            for i, c in enumerate(colors):
                self.where.setdefault(c, (colors, i))

    def step(self, c, n):
        if c not in self.where:
            return c
        colors, i = self.where[c]
        return colors[max(0, min(len(colors) - 1, i + n))]

    def same_ramp(self, a, b):
        return a in self.where and b in self.where and self.where[a][0] is self.where[b][0]


def clean(color, owner):
    """Drop one-pixel bumps on thick edges and lone speckles inside a same-ramp cluster."""
    def count(p):
        return sum((p[0] + dx, p[1] + dy) in color for dx, dy in N4)
    bumps = []
    for (x, y) in color:
        near = [(x + dx, y + dy) for dx, dy in N4 if (x + dx, y + dy) in color]
        if len(near) == 1 and count(near[0]) >= 3:
            bumps.append((x, y))
    for p in bumps:
        color.pop(p, None)
        owner.pop(p, None)


def despeckle(color, tones):
    changes = {}
    for (x, y), c in color.items():
        around = [color.get((x + dx, y + dy)) for dx, dy in N4]
        if None in around or c in around:
            continue
        best = max(set(around), key=around.count)
        if around.count(best) >= 3 and tones.same_ramp(c, best):
            changes[(x, y)] = best
    color.update(changes)


def lighting(color, owner, parts, tones, light, opts):
    """Ambient occlusion where a front group overlaps a back one, cast shadow away from the light,
    and a rim light on silhouette edges that face away from the light."""
    lx, ly = light
    steps = {}
    if opts.get("ao") or opts.get("cast"):
        cast = (round(lx * 2.5), round(ly * 2.5))
        for (x, y), (index, group) in owner.items():
            if parts[index].get("shape") == "sprite":
                continue  # cutout art carries its own painted shading
            darker = 0
            if opts.get("ao"):
                for dx in (-2, -1, 0, 1, 2):
                    for dy in (-2, -1, 0, 1, 2):
                        other = owner.get((x + dx, y + dy))
                        if other and other[0] > index and other[1] != group:
                            darker = 1
                            break
                    if darker:
                        break
            if opts.get("cast"):
                other = owner.get((x + cast[0], y + cast[1]))
                if other and other[0] > index and other[1] != group:
                    darker += 1
            if darker:
                steps[(x, y)] = -min(2, darker)
    if opts.get("rim"):
        rim = set()
        for (x, y) in color:
            if (x, y) in steps or (x, y) not in owner or parts[owner[(x, y)][0]].get("shape") == "sprite":
                continue
            if any((x + dx, y + dy) not in color and dx * lx + dy * ly < -0.5 for dx, dy in N4):
                rim.add((x, y))
        for (x, y) in rim:  # only runs of two or more: a lone rim pixel reads as noise
            if any((x + dx, y + dy) in rim for dx, dy in N8):
                steps[(x, y)] = 1
    for p, n in steps.items():
        color[p] = tones.step(color[p], n)


def corner_aa(color, outline_pixels, tones):
    """Soften outer corners: a fill pixel boxed in by outline on two perpendicular sides, with open
    space on the diagonal between them, steps one tone darker."""
    changes = {}
    for (x, y), c in color.items():
        if (x, y) in outline_pixels:
            continue
        for (ax, ay), (bx, by) in (((1, 0), (0, -1)), ((1, 0), (0, 1)), ((-1, 0), (0, -1)), ((-1, 0), (0, 1))):
            if (x + ax, y + ay) in outline_pixels and (x + bx, y + by) in outline_pixels \
                    and (x + ax + bx, y + ay + by) not in color:
                changes[(x, y)] = tones.step(c, -1)
                break
    color.update(changes)


TEXTURES = ("fur", "scales", "cloth", "metal", "noise")


def texture_offset(kind, u, v, level, top):
    """Tone offset for a texture at part-local integer coordinates (moves with the part)."""
    if kind == "fur":
        if (u * 5 + v * 3) % 7 == 0:
            return -1
        if level >= 2 and (u + v * 2) % 9 == 0:
            return 1
    elif kind == "scales":
        row = v // 3
        if v % 3 == 0 and (u + (row % 2) * 2) % 4 == 0:
            return -1
        if v % 3 == 1 and (u + (row % 2) * 2) % 4 == 2 and level < top:
            return 1
    elif kind == "cloth":
        if (u + v) % 6 == 0:
            return -1
    elif kind == "metal":
        # a diagonal glint across the lit side and a few dark scratches in the shadow side
        if level >= 2 and (u + v) % 7 in (0, 1):
            return 1
        if level == 0 and (u - 2 * v) % 9 == 0:
            return 1
    elif kind == "noise":
        if (u * 73856093 ^ v * 19349663) % 9 == 0:
            return -1
    return 0


def smear(color, before, after, reach, fill):
    """A slash arc swept from a bone's previous to its current position, on empty pixels only (it
    never covers the character). Intermediate bone positions rotate around the moving bone start,
    and only the tip leaves a trail: a solid band about two pixels wide along the tip's path."""
    import math
    a0, a1 = math.atan2(before.dir[1], before.dir[0]), math.atan2(after.dir[1], after.dir[0])
    turn = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    steps = max(4, int(abs(turn) / 0.18))
    inner, outer = [], []
    for k in range(steps + 1):
        t = k / steps
        sx = before.start[0] + (after.start[0] - before.start[0]) * t
        sy = before.start[1] + (after.start[1] - before.start[1]) * t
        a = a0 + turn * t
        dx, dy = math.cos(a), math.sin(a)
        inner.append((sx + dx * reach * 0.7, sy + dy * reach * 0.7))
        outer.append((sx + dx * reach, sy + dy * reach))
    trail = {}
    for k in range(steps):
        quad = [inner[k], outer[k], outer[k + 1], inner[k + 1]]
        xs, ys = [q[0] for q in quad], [q[1] for q in quad]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                if (x, y) in color or (x, y) in trail or not _inside(quad, x + 0.5, y + 0.5):
                    continue
                if _near_path((x + 0.5, y + 0.5), outer) < 1.9:
                    trail[(x, y)] = fill
    color.update(trail)


def _near_path(p, path):
    """Distance from p to a polyline."""
    import math
    best = float("inf")
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / ((dx * dx + dy * dy) or 1e-9)))
        best = min(best, math.dist(p, (ax + dx * t, ay + dy * t)))
    return best


def _inside(pts, x, y):
    hit, j = False, len(pts) - 1
    for i, (xi, yi) in enumerate(pts):
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit
