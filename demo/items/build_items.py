#!/usr/bin/env python3
"""Demo items for the README: draw with cutout_tools ops, add an outline, save pixel-art-json v1.

Each item (or animation frame) becomes an editable v1 document with one "art" layer, rendered by
the skill's pixel_art.py. Animated items also get a horizontal sheet and a GIF.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "skills" / "pixel-forge" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from cutout_tools import Canvas  # noqa: E402

SIZE = (32, 32)
PALETTE = {
    "o": "#1E1A2B", "k": "#2A1A22", "W": "#FFFFFF", "G": "#FFF7D6",
    "a": "#4A2A2E", "b": "#6E3D33", "c": "#9A5A3C", "d": "#C4824E",          # wood
    "e": "#8A5A22", "f": "#C88A2E", "g": "#EBC255", "h": "#FFF2A8",          # gold
    "i": "#3A3F55", "j": "#5E6680", "l": "#9AA3BC", "m": "#D8DEEA",          # iron
    "n": "#5E1A2A", "p": "#9C2A3A", "q": "#D8475A", "r": "#FF8A8A",          # red
    "s": "#1C2E5E", "t": "#2E5AA8", "u": "#4F9BE8", "v": "#A8E2FF",          # blue
    "x": "#A8865A", "y": "#D8BE8A", "z": "#F4E6C0",                          # paper
    "5": "#22202E", "6": "#3A3850", "7": "#5A5878",                          # bomb
}


def rgba(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


RGB = {k: rgba(v) for k, v in PALETTE.items()}
SYMBOL = {v: k for k, v in RGB.items()}


def P(c, *pts):
    return {"op": "poly", "c": c, "pts": [list(p) for p in pts]}


def E(c, x0, y0, x1, y1):
    return {"op": "ellipse", "c": c, "box": [x0, y0, x1, y1]}


def L(c, *pts):
    return {"op": "line", "c": c, "pts": [list(p) for p in pts]}


def X(c, *pts):
    return {"op": "px", "c": c, "pts": [list(p) for p in pts]}


def C(c, *pts):
    return {"op": "clip", "c": c, "pts": [list(p) for p in pts]}


def ERASE(*pts):
    return {"op": "erase", "pts": [list(p) for p in pts]}


def outlined(ops):
    """Paint ops, then add a 1-px outline around everything (holes included)."""
    canvas = Canvas(SIZE, RGB).run(ops)
    img = canvas.img
    w, h = SIZE
    edge = [(x, y) for y in range(h) for x in range(w) if not img.getpixel((x, y))[3]
            and any(0 <= x + dx < w and 0 <= y + dy < h and img.getpixel((x + dx, y + dy))[3]
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for p in edge:
        img.putpixel(p, RGB["o"])
    return img


def document(img, name, description):
    used = sorted({SYMBOL[img.getpixel((x, y))] for y in range(SIZE[1]) for x in range(SIZE[0]) if img.getpixel((x, y))[3]})
    rows = ["".join(SYMBOL.get(img.getpixel((x, y)), ".") if img.getpixel((x, y))[3] else "."
                    for x in range(SIZE[0])) for y in range(SIZE[1])]
    return {"version": 1, "size": list(SIZE), "palette": {".": "#00000000", **{k: PALETTE[k] for k in used}},
            "layers": [{"name": "art", "rows": rows}], "meta": {"description": description}}


# ---------------- items ----------------

def chest_body():
    return [
        P("c", (5, 17), (26, 17), (26, 27), (5, 27)),
        L("b", (5, 21), (26, 21)), L("b", (5, 24), (26, 24)),
        L("d", (5, 18), (26, 18)), L("a", (5, 27), (26, 27)),
        P("b", (24, 18), (26, 18), (26, 27), (24, 27)),
        P("f", (8, 17), (9, 17), (9, 27), (8, 27)), P("f", (22, 17), (23, 17), (23, 27), (22, 27)),
        L("g", (8, 18), (8, 26)), L("g", (22, 18), (22, 26)),
    ]


def chest_lid(lift=0):
    y = -lift
    return [
        P("c", (5, 17 + y), (5, 13 + y), (7, 10 + y), (10, 9 + y), (21, 9 + y), (24, 10 + y), (26, 13 + y), (26, 17 + y)),
        C("d", (5, 9 + y), (26, 9 + y), (26, 11.5 + y), (5, 11.5 + y)),
        C("b", (5, 15 + y), (26, 15 + y), (26, 17 + y), (5, 17 + y)),
        P("b", (24, 10 + y), (26, 13 + y), (26, 17 + y), (24, 17 + y)),
        P("f", (8, 9.6 + y), (9, 9.4 + y), (9, 17 + y), (8, 17 + y)), P("f", (22, 9.4 + y), (23, 9.6 + y), (23, 17 + y), (22, 17 + y)),
        L("g", (8, 10 + y), (8, 16 + y)), L("g", (22, 10 + y), (22, 16 + y)),
        L("f", (5, 16 + y), (26, 16 + y)), L("g", (5, 16 + y), (20, 16 + y)),
    ]


def chest_lock():
    return [P("f", (14, 15), (17, 15), (17, 20), (14, 20)), L("g", (14, 15), (14, 19)), L("h", (14, 15), (16, 15)),
            X("k", (15, 17), (15, 18), (16, 17))]


def chest_frames():
    closed = chest_body() + chest_lid() + chest_lock()
    crack = chest_body() + chest_lid(lift=2) + [P("G", (6, 15), (25, 15), (25, 16), (6, 16)), X("h", (4, 14), (27, 14))] + chest_lock()
    inside = [P("a", (5, 15), (26, 15), (24, 3), (7, 3)),            # lid underside, swung back
              P("b", (8, 5), (23, 5), (24, 13), (7, 13)),
              P("f", (8, 3), (9, 3), (9, 15), (8, 15)), P("f", (22, 3), (23, 3), (23, 15), (22, 15)),
              L("f", (7, 3), (24, 3)), L("g", (8, 3), (20, 3)),
              P("k", (6, 15), (25, 15), (25, 17), (6, 17)),          # dark opening
              E("f", 8, 12, 14, 17), E("g", 12, 11, 19, 17), E("f", 17, 12, 23, 17),   # coin pile
              X("h", (14, 12), (15, 12), (10, 13), (19, 13), (16, 11)), X("e", (11, 16), (20, 16))]
    opened = inside + chest_body() + chest_lock()
    rays = [X("G", (15, 9), (15, 10), (16, 8), (11, 10), (20, 10), (13, 8), (18, 8)), X("h", (16, 9), (12, 9), (19, 9))]
    sparkle = opened + rays + [X("W", (16, 7), (28, 8), (3, 8)), X("h", (27, 9), (4, 9), (28, 6), (3, 6))]
    return [(closed, 700), (crack, 110), (opened, 140), (sparkle, 420), (opened, 260)]


def key():
    return [E("f", 3, 3, 13, 13), C("g", (3, 3), (13, 3), (13, 6), (3, 6)), E("e", 6, 6, 10, 10),
            ERASE(*[(x, y) for x in range(7, 10) for y in range(7, 10)]),
            P("f", (11, 13), (13, 11), (27, 25), (25, 27)), L("g", (12, 11), (26, 25)),
            P("f", (19, 23), (21, 21), (23, 23), (21, 25)), P("f", (23, 27), (25, 25), (27, 27), (25, 29)),
            L("e", (12, 13), (25, 26)), X("h", (6, 4), (7, 4), (13, 12))]


def coin_frames():
    def coin(rx):
        x0, x1 = 16 - rx, 15 + rx
        if rx <= 1:
            return [P("e", (15, 7), (16, 7), (16, 24), (15, 24)), L("g", (15, 8), (15, 23))]
        ops = [E("e", x0, 7, x1, 24), E("f", x0 + 1, 8, x1 - 1, 23), C("g", (x0, 7), (16, 7), (16, 12), (x0, 14))]
        if rx >= 6:
            ops += [E("e", x0 + 3, 11, x1 - 3, 20), E("g", x0 + 4, 12, x1 - 4, 19),
                    X("h", (15, 13), (14, 15), (15, 15), (16, 15), (15, 17)), X("W", (x0 + 2, 10))]
        elif rx >= 3:
            ops += [L("g", (16, 12), (16, 19)), X("h", (x0 + 1, 10))]
        return ops
    return [(coin(r), 110) for r in (8, 6, 3, 1, 3, 6)]


def gem():
    return [P("t", (9, 12), (12, 8), (20, 8), (23, 12), (16, 26)),
            P("u", (12, 8), (20, 8), (18, 12), (14, 12)), P("v", (14, 9), (18, 9), (17, 11), (15, 11)),
            P("s", (9, 12), (14, 12), (16, 26)), P("u", (14, 12), (18, 12), (16, 26)),
            L("v", (12, 9), (10, 12)), X("W", (14, 9), (13, 10), (16, 15)), X("s", (21, 13), (20, 15))]


def shield():
    return [P("l", (6, 5), (26, 5), (26, 16), (21, 24), (16, 28), (11, 24), (6, 16)),
            C("m", (6, 5), (26, 5), (26, 7), (6, 7)),
            P("t", (8, 7), (24, 7), (24, 15.5), (20, 22), (16, 25.5), (12, 22), (8, 15.5)),
            C("u", (8, 7), (16, 7), (16, 26), (8, 16)),
            P("g", (15, 8), (17, 8), (17, 24), (15, 24)), P("g", (9, 13), (23, 13), (23, 15), (9, 15)),
            L("h", (15, 8), (15, 13)), L("h", (9, 13), (14, 13)), X("e", (17, 16), (17, 20)),
            X("W", (8, 6), (9, 6))]


def scroll():
    return [P("y", (8, 9), (24, 9), (24, 23), (8, 23)),
            C("z", (8, 9), (17, 9), (17, 23), (8, 23)),
            L("x", (10, 13), (21, 13)), L("x", (10, 16), (19, 16)), L("x", (10, 19), (20, 19)),
            E("x", 5, 6, 26, 11), E("z", 6, 7, 25, 9), E("x", 5, 21, 26, 26), E("y", 6, 22, 25, 24),
            E("p", 17, 18, 23, 24), E("q", 18, 19, 21, 22), X("r", (19, 19)),
            P("p", (18, 23), (20, 23), (19, 28)), P("n", (21, 23), (23, 23), (23, 28))]


def bomb_frames():
    body = [E("5", 6, 10, 25, 29), E("6", 6, 10, 22, 26), E("7", 9, 13, 14, 18),
            X("W", (10, 14)), P("j", (13, 7), (18, 7), (18, 10), (13, 10)), L("l", (13, 7), (17, 7)),
            L("b", (16, 6), (17, 4), (19, 3), (21, 3))]
    spark_a = [X("h", (22, 2), (23, 3), (22, 4), (21, 2)), X("W", (22, 3)), X("q", (24, 1), (20, 1))]
    spark_b = [X("g", (22, 3), (23, 2), (21, 4)), X("W", (23, 3)), X("r", (25, 3), (22, 0), (20, 4))]
    return [(body + spark_a, 120), (body + spark_b, 120)]


def render(doc, prefix):
    path = Path(str(prefix) + ".json")
    path.write_text(json.dumps(doc), encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPTS / "pixel_art.py"), "render", str(path), "--out", str(prefix),
                    "--scale", "8"], check=True, capture_output=True)
    with Image.open(str(prefix) + ".png") as image:
        return image.convert("RGBA")


def main():
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    statics = {"key": (key(), "Gold key"), "gem": (gem(), "Blue cut gem"),
               "shield": (shield(), "Heater shield with gold cross"), "scroll": (scroll(), "Sealed scroll")}
    for name, (ops, text) in statics.items():
        render(document(outlined(ops), name, text), HERE / name)
    for name, frames, text in (("chest-open", chest_frames(), "Chest opening"), ("coin-spin", coin_frames(), "Spinning coin"),
                               ("bomb", bomb_frames(), "Bomb with a lit fuse")):
        images = []
        for i, (ops, ms) in enumerate(frames):
            prefix = out / f"{name}-{i:02d}"
            images.append((render(document(outlined(ops), f"{name} {i}", text), prefix), ms))
        sheet = Image.new("RGBA", (SIZE[0] * len(images), SIZE[1]), (0, 0, 0, 0))
        for i, (image, _) in enumerate(images):
            sheet.paste(image, (i * SIZE[0], 0))
        sheet.save(HERE / f"{name}.png")
        (HERE / f"{name}.anim.json").write_text(json.dumps(
            {"sheet": f"{name}.png", "frames": [{"rect": [i * SIZE[0], 0, *SIZE], "ms": ms, "source": f"out/{name}-{i:02d}.json"}
                                                 for i, (_, ms) in enumerate(images)]}, indent=1), encoding="utf-8")
    print("built items in", HERE)


if __name__ == "__main__":
    main()
