"""Procedural effect shapes for pixel art: lightning, persistent flames, particles and smoke.

Every function returns {(x, y): intensity} with intensity in 0..1 (0 = the dark rim, 1 = the white-hot
core). pixel_art.py maps intensities onto a `colors` ramp (dark to light) in the `bolt`, `flames`,
`particles` and `smoke` operations. All of them are deterministic for a given seed, and the animated ones
take a frame time `t` so a shape persists and moves between frames instead of being redrawn at random.
"""
import math
import random

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def _line(a, b):
    (x0, y0), (x1, y1) = (round(a[0]), round(a[1])), (round(b[0]), round(b[1]))
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


def _merge(into, cells):
    for q, v in cells.items():
        if v > into.get(q, -1):
            into[q] = v


def _snap_slope(a, b):
    """Snap a segment to a clean pixel slope (0, 1:2, 1:1, 2:1, vertical), keeping its length."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1
    angle = math.atan2(dy, dx)
    clean = [math.atan2(sy, sx) for sx, sy in ((1, 0), (2, 1), (1, 1), (1, 2), (0, 1), (-1, 2), (-1, 1), (-2, 1),
                                               (-1, 0), (-2, -1), (-1, -1), (-1, -2), (0, -1), (1, -2), (1, -1), (2, -1))]
    best = min(clean, key=lambda c: abs((angle - c + math.pi) % (2 * math.pi) - math.pi))
    return (a[0] + math.cos(best) * length, a[1] + math.sin(best) * length)


def _jagged(start, end, rng, jag, min_seg=3.0):
    """Midpoint displacement, then every segment snapped to a clean slope: a zigzag, not a wobble."""
    points = [start, end]
    while True:
        longest = max(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))
        if longest <= min_seg * 2:
            break
        out = [points[0]]
        for a, b in zip(points, points[1:]):
            d = math.dist(a, b)
            if d > min_seg * 2:
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                nx, ny = -(b[1] - a[1]) / d, (b[0] - a[0]) / d
                off = rng.uniform(-1, 1) * jag * d
                out.append((mx + nx * off, my + ny * off))
            out.append(b)
        points = out
    snapped = [points[0]]
    for p in points[1:]:
        snapped.append(_snap_slope(snapped[-1], p))
    snapped[-1] = end  # the bolt lands exactly on `to`, so chained bolts join up
    return snapped


def bolt(start, end, seed=1, jag=0.35, width=2.0, branches=2, fade=0.0, flicker=None, taper=0.6, rim=True, reach=1.0):
    """A forked lightning bolt from start to end. width tapers from the start to the end; the centre line
    is the hot core, the sides cool to the rim. branches: side forks off the main path (each with one
    level of sub-forks). fade 0..1: the bolt breaks into separate segments and cools (dying arcs).
    flicker: a second seed that only re-jitters the forks, so the main path can stay steady between
    frames while the branches crackle. taper: the width at the end (thin it to 0.5 for a needle tip, keep
    it near width for an even beam). rim=False drops the dark outer rim (a thin core with a soft glow,
    for dark ground or a bolt inside a brighter effect). reach scales the fork length (forks run 25-50%
    of the distance to the end; 0.4 keeps them short on a long bolt)."""
    rng = random.Random(seed)
    path = _jagged(start, end, rng, jag)
    out = {}
    frng = random.Random(flicker if flicker is not None else seed + 7919)
    keep = random.Random((flicker if flicker is not None else seed) * 31 + 7)

    def stroke(points, w0, w1, heat):
        total = sum(math.dist(a, b) for a, b in zip(points, points[1:])) or 1
        walked = 0.0
        for a, b in zip(points, points[1:]):
            seg = math.dist(a, b)
            if fade and keep.random() < fade * 0.6:
                walked += seg
                continue
            for x, y in _line(a, b):
                t = min(1.0, (walked + math.dist(a, (x, y))) / total)
                r = max(0.5, (w0 + (w1 - w0) * t) * (1 - 0.5 * fade))
                for dy in range(-int(r) - 1, int(r) + 2):
                    for dx in range(-int(r) - 1, int(r) + 2):
                        d = math.hypot(dx, dy)
                        if d <= r + 0.5:
                            core = heat * (1 - fade * 0.7) * (1 - 0.65 * d / (r + 0.5))
                            _merge(out, {(x + dx, y + dy): max(0.0, core)})
            walked += seg
    stroke(path, width, taper, 1.0)
    for _ in range(branches):
        i = frng.randrange(1, max(2, len(path) - 1))
        a = path[i]
        main = math.atan2(end[1] - start[1], end[0] - start[0])
        ang = main + frng.choice([-1, 1]) * frng.uniform(0.45, 1.0)
        length = math.dist(a, end) * frng.uniform(0.25, 0.5) * reach
        b = (a[0] + math.cos(ang) * length, a[1] + math.sin(ang) * length)
        sub = _jagged(a, b, frng, jag * 1.2, 2.0)
        stroke(sub, max(0.5, min(width * 0.5, taper + 0.6)), 0.5, 0.75)
        if len(sub) > 3 and frng.random() < 0.6:
            c = sub[len(sub) // 2]
            ang2 = ang + frng.choice([-1, 1]) * frng.uniform(0.4, 0.9)
            d = (c[0] + math.cos(ang2) * length * 0.4, c[1] + math.sin(ang2) * length * 0.4)
            stroke(_jagged(c, d, frng, jag * 1.3, 2.0), 0.5, 0.5, 0.55)
    if rim:
        edge = {(x + dx, y + dy): 0.0 for (x, y) in out for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (x + dx, y + dy) not in out}
        out.update(edge)  # a dark rim one pixel outside, so the bolt reads on bright ground
    return out


def ring(cx, cy, radius, width=2.0, squash=1.0, breakup=0.0, seed=1, arc=None):
    """A ring or shockwave band around (cx, cy): the outer edge is the hottest (1.0) and it cools inward
    over `width` pixels. squash < 1 flattens it into a ground ellipse (0.4-0.5 for a top-down 3/4 view).
    breakup 0..1 cuts it into separate arcs (a dying shockwave); arc = [from, to] in screen degrees
    (0 = right, 90 = down) keeps only that part: [0, 180] is the front half, [180, 360] the back half."""
    rng = random.Random(seed)
    gaps = []
    if breakup > 0:
        for _ in range(max(1, round(breakup * 8))):
            start = rng.uniform(0, 360)
            gaps.append((start, start + breakup * rng.uniform(15, 50)))
    out = {}
    reach = radius + 1
    for y in range(int(cy - reach * squash) - 1, int(cy + reach * squash) + 2):
        for x in range(int(cx - reach) - 1, int(cx + reach) + 2):
            dx, dy = x - cx, (y - cy) / max(squash, 0.05)
            d = math.hypot(dx, dy)
            inside = radius - d
            if not -0.5 <= inside < width:
                continue
            ang = math.degrees(math.atan2(dy, dx)) % 360
            if arc is not None and not (arc[0] <= ang <= arc[1] or arc[0] <= ang + 360 <= arc[1]):
                continue
            if any(a <= ang <= b or a <= ang + 360 <= b for a, b in gaps):
                continue
            out[(x, y)] = max(0.0, 1 - max(0.0, inside) / max(width, 0.5))
    return out


def flames(x, y, w, h, count=4, t=0, period=8, seed=1, lean=0.0):
    """Persistent flame tongues rising from the base line (x .. x+w, y = the base row), at most h tall.
    Each tongue keeps its place and phase: it sways, grows and shrinks, and once per cycle its tip pinches
    off as a small lick that rises and vanishes. t is the frame; the loop closes every `period` frames.
    lean shifts the tips sideways (wind or motion), in pixels at full height."""
    rng = random.Random(seed)
    out = {}
    phase_t = 2 * math.pi * t / max(1, period)
    for i in range(count):
        cx = x + (i + 0.5) * w / count + rng.uniform(-0.25, 0.25) * w / count
        base_half = max(1.0, w / count * rng.uniform(0.45, 0.6))
        tall = h * rng.uniform(0.55, 1.0)
        phase = rng.uniform(0, 2 * math.pi)
        speed = rng.choice([1, 1, 2])  # whole cycles per loop, so the loop closes
        a = phase_t * speed + phase
        height = tall * (0.82 + 0.18 * math.sin(a))
        sway = math.sin(a + 1.3) * base_half * 0.8 + lean
        for k in range(int(height) + 1):
            f = k / max(1.0, height)
            half = base_half * (1 - f) ** 0.75
            mid = cx + sway * f ** 1.5
            row = y - k
            for xx in range(int(math.floor(mid - half)), int(math.ceil(mid + half)) + 1):
                d = abs(xx + 0.5 - mid) / max(0.5, half)
                if d <= 1.0:
                    heat = (1 - f) * 0.9 + 0.1 - d * 0.45
                    _merge(out, {(xx, row): max(0.05, min(1.0, heat))})
        lick = (a / (2 * math.pi)) % 1.0
        if lick < 0.5:  # the tip pinches off and rises for half a cycle
            ly = y - height - 1 - lick * tall * 0.6
            lx = cx + sway + lean * 0.5
            size = max(0.6, base_half * 0.45 * (1 - lick * 1.6))
            for dy in range(-int(size) - 1, int(size) + 2):
                for dx in range(-int(size) - 1, int(size) + 2):
                    if dx * dx + (dy * 1.4) ** 2 <= size * size + 0.5:
                        _merge(out, {(round(lx + dx), round(ly + dy)): 0.35})
    rim = {}
    for (px, py) in out:
        for dx, dy in ((1, 0), (-1, 0), (0, -1)):
            q = (px + dx, py + dy)
            if q not in out:
                rim[q] = 0.0
    out.update(rim)
    return out


def particles(x, y, count=10, t=0, period=8, life=None, speed=1.5, angle=-90, spread=60, gravity=0.0,
              seed=1, size=2.0, mode="loop", trail=0):
    """Sparks, embers or debris. mode "loop": particles are born evenly over `period` frames and the loop
    closes; mode "burst": all are born at frame 0 (an explosion). Each particle has its own direction
    within `angle` +/- `spread`/2 degrees (screen degrees, -90 = up), speed (pixels per frame), gravity
    (pixels per frame squared, positive pulls down) and a life in frames, and it shrinks and cools with
    age. trail: a tapered streak this many pixels long behind fast sparks."""
    rng = random.Random(seed)
    life = life or period
    out = {}
    for i in range(count):
        birth = (i * period / count + rng.uniform(0, period / count)) if mode == "loop" else 0.0
        ang = math.radians(angle + rng.uniform(-spread / 2, spread / 2))
        v = speed * rng.uniform(0.6, 1.3)
        my_life = life * rng.uniform(0.7, 1.0)
        age = ((t - birth) % period) if mode == "loop" else (t - birth)
        if age < 0 or age > my_life:
            continue
        px = x + math.cos(ang) * v * age
        py = y + math.sin(ang) * v * age + 0.5 * gravity * age * age
        k = age / my_life
        r = max(0.0, size * (1 - k) - 0.5)
        heat = 1 - k * 0.85
        for dy in range(-int(r), int(r) + 1):
            for dx in range(-int(r), int(r) + 1):
                if dx * dx + dy * dy <= r * r + 0.5:
                    _merge(out, {(round(px + dx), round(py + dy)): heat})
        if trail:
            vx, vy = math.cos(ang) * v, math.sin(ang) * v + gravity * age
            n = math.hypot(vx, vy) or 1
            for s in range(1, trail + 1):
                q = (round(px - vx / n * s), round(py - vy / n * s))
                _merge(out, {q: heat * (1 - s / (trail + 1)) * 0.8})
    return out


def smoke(x, y, count=4, t=0, period=12, rise=1.0, drift=0.3, radius=2.0, grow=0.25, seed=1):
    """Smoke puffs born at (x, y) in turn, each rising `rise` and drifting `drift` pixels per frame,
    growing by `grow` per frame and cooling with age. Puffs are drawn oldest first and each keeps a lit
    upper-left and a darker lower-right edge, so the column reads as separate round lobes. Late in life a
    puff thins to a checker and shrinks away. The loop closes every `period` frames; for clearly separate
    puffs keep rise * period / count at least about 1.5 x radius."""
    rng = random.Random(seed)
    jitter = [(rng.uniform(-0.8, 0.8), rng.uniform(0.8, 1.2), rng.uniform(0, 6.28)) for _ in range(count)]
    puffs = []
    for i in range(count):
        birth = i * period / count
        age = (t - birth) % period
        puffs.append((age, i))
    out = {}
    for age, i in sorted(puffs, reverse=True):  # oldest first, the newest puff on top
        k = age / period
        dx0, size, wob = jitter[i]
        cx = x + drift * age + dx0 + math.sin(wob + age * 0.6) * 0.8
        cy = y - rise * age
        r = (radius + grow * age) * size
        if k > 0.8:
            r *= 1 - (k - 0.8) / 0.2 * 0.6  # the last fifth: shrink away
        heat = 0.85 - 0.7 * k
        for dy in range(-int(r) - 1, int(r) + 2):
            for dx in range(-int(r) - 1, int(r) + 2):
                d2 = dx * dx + dy * dy
                if d2 <= r * r + 0.3:
                    q = (round(cx + dx), round(cy + dy))
                    if k > 0.65 and (q[0] + q[1]) % 2:
                        continue  # thin to a checker before vanishing
                    edge = d2 > (r - 1.2) ** 2
                    lit = 0.15 if (dx + dy) < -r * 0.35 else (-0.25 if edge and (dx + dy) > 0 else 0.0)
                    out[q] = max(0.0, min(1.0, heat + lit))
    return out
