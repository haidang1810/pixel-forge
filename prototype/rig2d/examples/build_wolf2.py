#!/usr/bin/env python3
"""Author the wolf2 rest pose as pixel layers, then split each layer onto its bones.

Run `rig.py examples/wolf2.json --rest` first so rest-bones.json exists; this script writes the
"cutout" and "palette" sections of wolf2.json. Drawing happens in canvas coordinates.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SPEC = HERE / "wolf2.json"
BONES = HERE.parents[2] / "output" / "rig2d" / "wolf2" / "rest-bones.json"
W, H = 64, 48

PALETTE = {
    "1": "#1C1A2A", "2": "#2C2A3E", "3": "#403E58", "4": "#5A5875",
    "5": "#8E8DA8", "6": "#B6B6CC", "7": "#DCDDEA", "8": "#F6F7FB",
    "y": "#FFB83D", "Y": "#FFE7A0", "k": "#120E1A", "m": "#6E2433", "t": "#C24A5A",
    "e": "#5B3A4C", "r": "#7A1E2E", "R": "#B83244", "P": "#E0606A",
}
RGB = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) + (255,) for k, v in PALETTE.items()}


class Layer:
    def __init__(self):
        self.img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def poly(self, c, pts):
        self.d.polygon([tuple(p) for p in pts], fill=RGB[c])

    def line(self, c, pts):
        self.d.line([tuple(p) for p in pts], fill=RGB[c])

    def px(self, c, *pts):
        for p in pts:
            self.img.putpixel(tuple(p), RGB[c])

    def clip(self, c, pts):
        """Paint polygon c only where this layer already has pixels."""
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in pts], fill=255)
        for y in range(H):
            for x in range(W):
                if mask.getpixel((x, y)) and self.img.getpixel((x, y))[3]:
                    self.img.putpixel((x, y), RGB[c])

    def rim(self, c, side="top"):
        """Highlight the first pixel facing the light (top edge) of the silhouette."""
        self.band(c, 1)

    def band(self, c, depth, x0=0, x1=W, bottom=False, jag=0):
        """Paint pixels within `depth` of the top (or bottom) silhouette edge, following its contour.

        jag > 0 alternates the depth by +-jag every two columns, giving a fur-like boundary.
        """
        src = self.img.copy()
        for x in range(max(0, int(x0)), min(W, int(x1))):
            ys = [y for y in range(H) if src.getpixel((x, y))[3]]
            if not ys:
                continue
            d = depth + (jag if (x // 2) % 2 else -jag)
            edge = max(ys) if bottom else min(ys)
            for y in ys:
                if (edge - y if bottom else y - edge) < d:
                    self.img.putpixel((x, y), RGB[c])


# ---------------- drawing ----------------

def draw_tail():
    t = Layer()
    # thick base that sinks into the rump, plume widening toward the curled tip
    t.poly("2", [(20, 21), (16, 20.5), (12, 18.5), (10, 16), (8, 12), (6, 10), (4, 11), (3, 14), (4, 18), (6, 22),
                 (9, 25), (13, 27.5), (17, 28), (20, 27)])
    # fluffy underside, light
    t.clip("5", [(19, 25), (14, 25), (10, 23), (7, 20), (5, 16), (3, 14), (4, 19), (6, 23), (10, 26), (14, 28), (19, 28)])
    t.clip("6", [(16, 27), (12, 26.5), (8, 24), (5, 20), (3.5, 16), (4, 20), (7, 24), (11, 27.5), (16, 28)])
    # white tip
    t.clip("7", [(9, 9), (2, 9), (2, 16), (5, 15), (8, 13)])
    t.clip("8", [(7, 9), (3, 9), (3, 13), (5, 12)])
    t.rim("4")
    t.clip("7", [(9, 9), (2, 9), (2, 13), (8, 12)])
    # tufts on the edges
    t.px("2", (12, 18), (9, 15))
    t.px("6", (3, 18), (5, 21), (8, 24))
    t.px("3", (14, 21), (11, 18), (16, 22), (13, 20))
    return t


def draw_body():
    b = Layer()
    # Arched back: rump peak, dip at the waist, high withers; deep chest and tucked belly.
    b.poly("3", [(14, 25), (15, 21.5), (17, 19.3), (20, 18.8), (23, 19.8), (26, 22.4), (29, 22.6), (33, 19.8),
                 (37, 18), (39, 20), (41, 23), (42, 27), (41.5, 31), (40, 35), (37, 35.6), (33, 34), (30, 30),
                 (27, 28), (24, 29.4), (21, 32), (17, 32), (14, 29)])
    b.band("2", 4, jag=1)                      # dark back following the top contour
    b.rim("4")                                 # rim light from above
    b.band("5", 5, 31, 43, bottom=True, jag=1)  # light chest with a furry boundary
    b.band("6", 3, 33, 43, bottom=True, jag=1)
    b.band("7", 2, 35, 42, bottom=True)
    b.band("5", 2, 25, 31, bottom=True)        # thin light line along the tucked belly
    return b


def draw_neck():
    n = Layer()
    # mane rising behind the head
    n.poly("2", [(34, 22), (35, 18), (37, 14), (39, 12), (42, 12), (44, 15), (43, 21), (42, 26), (37, 26)])
    n.poly("2", [(35, 18), (33, 17), (35, 16)])
    n.poly("2", [(37, 14), (35, 12), (38, 12)])
    n.rim("4")
    n.clip("3", [(38, 13), (42, 13), (42, 26), (38, 26)])
    # white throat ruff, jagged
    n.poly("6", [(41, 21), (44, 22), (45, 25), (44, 28), (42, 31), (41, 29), (40, 31), (39, 28), (40, 25)])
    n.px("7", (43, 23), (43, 24), (44, 25), (42, 26), (43, 26))
    n.px("5", (40, 28), (41, 30))
    return n


def draw_scarf():
    s = Layer()
    s.poly("R", [(36, 22), (41, 23), (44, 23), (44, 25), (41, 25), (36, 24)])
    s.poly("R", [(39, 25), (43, 25), (41, 29)])
    s.line("P", [(37, 22), (43, 23)])
    s.line("r", [(36, 24), (41, 25)])
    s.px("r", (41, 28), (42, 27))
    return s


def draw_head():
    h = Layer()
    h.poly("2", [(39, 17), (40, 14), (43, 13), (46, 14), (48, 16), (52, 17), (54, 18), (54, 20), (52, 21),
                 (49, 22), (47, 23), (43, 23), (40, 21)])
    # far ear (darker) and near ear
    h.poly("1", [(39, 15), (39, 9), (42, 13)])
    h.poly("2", [(41, 14), (42, 7), (45, 13)])
    h.poly("e", [(42, 13), (42.5, 9), (44, 13)])
    h.rim("4")
    # muzzle top lighter, cheek and jaw white
    h.clip("3", [(46, 17), (54, 17.5), (54, 19), (46, 19)])
    h.poly("6", [(40, 20), (43, 21), (46, 21), (49, 22), (52, 21.5), (52, 22.5), (48, 23.5), (44, 24), (42, 25), (41, 23)])
    h.px("7", (43, 22), (44, 22), (45, 22), (46, 22), (43, 23))
    h.px("5", (41, 24), (42, 24))
    # nose, mouth, fang
    h.px("k", (54, 18), (54, 19), (53, 18))
    h.line("k", [(48, 21), (52, 20)])
    h.px("8", (51, 21))
    # eye with slanted brow (angry)
    h.px("k", (45, 15), (46, 16), (47, 16), (47, 17))
    h.px("y", (45, 17), (46, 17))
    h.px("Y", (45, 17))
    return h


def draw_back_leg():
    g = Layer()
    # haunch: big teardrop, lit on its front, dark at the back edge
    g.poly("3", [(16, 25), (20, 23), (24, 25), (25.5, 29), (24.5, 33), (23, 35.5), (21, 35.5), (18, 33), (15.5, 29)])
    g.poly("2", [(16, 25), (18, 24), (17, 29), (18.5, 33), (16.5, 31), (15.5, 28)])
    g.poly("4", [(22, 26), (24, 26), (25, 29), (24.5, 32), (23, 30)])
    # shin angles back to the hock, then the near-vertical metatarsal and a paw pointing forward
    g.poly("5", [(21, 34), (23.5, 35), (20.5, 39.5), (18, 40.5), (17, 39)])
    g.poly("6", [(17.4, 39), (19.8, 39.5), (19.8, 43), (17.2, 43)])
    g.poly("6", [(16.5, 42.5), (21, 42.5), (21.5, 44.5), (16, 44.5)])
    g.px("4", (17, 39), (17, 40), (18, 41))
    g.px("7", (19, 40), (19, 41), (19, 43), (20, 43), (21, 43))
    g.px("k", (19, 44), (17, 44))  # toe splits
    return g


def draw_front_leg():
    f = Layer()
    # shoulder blends into the chest; elbow bump at the back; slim light forearm
    f.poly("3", [(35, 26), (39.5, 26), (40.5, 30), (38.5, 33.5), (36, 34.5), (34.5, 33), (35, 30)])
    f.poly("2", [(35, 27), (36, 27), (35.5, 33), (34.5, 33)])
    f.poly("5", [(35.8, 33), (38.6, 33), (38.3, 40.5), (36.2, 40.5)])
    f.poly("6", [(37, 34), (38.6, 34), (38.4, 40), (37, 40)])
    f.poly("6", [(36, 40), (38.4, 40), (38.7, 42.8), (36.2, 42.8)])
    f.poly("6", [(35.5, 42.5), (39.8, 42.5), (40.3, 44.5), (35.2, 44.5)])
    f.px("7", (38, 41), (38, 43), (39, 43))
    f.px("k", (38, 44), (36, 44))
    return f


# ---------------- split onto bones ----------------

def seg_dist(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / ((dx * dx + dy * dy) or 1e-9)))
    return math.hypot(ax + dx * t - p[0], ay + dy * t - p[1])


def symbol_of(rgba):
    for k, v in RGB.items():
        if v == rgba:
            return k
    raise ValueError(f"color {rgba} not in palette")


def to_layer(name, bone, pixels, z, group, **extra):
    xs, ys = [p[0] for p in pixels], [p[1] for p in pixels]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    rows = ["".join(pixels.get((x, y), ".") for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1)]
    return dict(name=name, bone=bone, origin=[x0, y0], z=z, group=group, rows=rows, **extra)


def split(layer, bones, names, overlap=1.5):
    """Give each pixel to its nearest bone; pixels near a joint also go to the neighbouring bone."""
    out = {n: {} for n in names}
    for y in range(H):
        for x in range(W):
            c = layer.img.getpixel((x, y))
            if not c[3]:
                continue
            p = (x + 0.5, y + 0.5)
            d = {n: seg_dist(p, bones[n]["start"], bones[n]["end"]) for n in names}
            best = min(d.values())
            for n in names:
                if d[n] <= best + overlap * (n != min(d, key=d.get)) or d[n] == best:
                    if d[n] - best <= overlap:
                        out[n][(x, y)] = symbol_of(c)
    return out


def main():
    bones = json.loads(BONES.read_text(encoding="utf-8"))
    layers = []
    tail = split(draw_tail(), bones, ["tail1", "tail2", "tail3"])
    for i, n in enumerate(["tail3", "tail2", "tail1"]):
        layers.append(to_layer(n, n, tail[n], 20 + i, "tail"))
    body = draw_body()
    hips = {p: s for p, s in split(body, bones, ["hips", "chest"], overlap=2)["hips"].items()}
    chest = split(body, bones, ["hips", "chest"], overlap=2)["chest"]
    layers.append(to_layer("hips", "hips", hips, 30, "body"))
    layers.append(to_layer("chest", "chest", chest, 31, "body"))
    neck = {(x, y): symbol_of(c) for y in range(H) for x in range(W) if (c := draw_neck().img.getpixel((x, y)))[3]}
    layers.append(to_layer("neck", "neck", neck, 33, "body"))
    scarf = {(x, y): symbol_of(c) for y in range(H) for x in range(W) if (c := draw_scarf().img.getpixel((x, y)))[3]}
    layers.append(to_layer("scarf", "neck", scarf, 36, "scarf"))
    head = {(x, y): symbol_of(c) for y in range(H) for x in range(W) if (c := draw_head().img.getpixel((x, y)))[3]}
    layers.append(to_layer("head", "head", head, 40, "head"))
    for kind, drawer, leg, z in (("back", draw_back_leg, "bn", 50), ("front", draw_front_leg, "fn", 54)):
        parts = split(drawer(), bones, [f"upper_{leg}", f"lower_{leg}", f"foot_{leg}"])
        far = leg[0] + "f"
        for i, seg in enumerate(["upper", "lower", "foot"]):
            layers.append(to_layer(f"{seg}_{leg}", f"{seg}_{leg}", parts[f"{seg}_{leg}"], z + i, "leg_" + leg))
            layers.append({"name": f"{seg}_{far}", "from": f"{seg}_{leg}", "bone": f"{seg}_{far}",
                           "z": z - 40 + i, "group": "leg_" + far, "far": True})
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["palette"] = PALETTE
    spec["cutout"] = layers
    SPEC.write_text(json.dumps(spec, indent=1), encoding="utf-8")
    print(f"wrote {len(layers)} layers to {SPEC}")


if __name__ == "__main__":
    main()
