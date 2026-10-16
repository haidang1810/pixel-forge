"""Author original test items as JSON; all sprite pixels come from the skill renderer."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TOOL = ROOT.parent / "skills/pixel-forge/scripts/pixel_art.py"
OUT = ROOT / "items"
OUT.mkdir(exist_ok=True)


def polygon(color, *points):
    return {"op": "polygon", "points": [list(p) for p in points], "color": color}


def rect(color, x, y, w, h):
    return {"op": "rect", "xy": [x, y], "size": [w, h], "color": color}


def line(color, *points):
    return {"op": "line", "points": [list(p) for p in points], "color": color}


def pixels(color, *points):
    return {"op": "pixels", "points": [list(p) for p in points], "color": color}


def layer(name, *ops):
    return {"name": name, "ops": list(ops)}


def save(name, palette, layers, description):
    doc = {"version": 1, "size": [32, 32], "palette": {".": "#00000000", **palette}, "layers": layers,
           "meta": {"description": description, "light": "upper left", "source": "Original JSON operations; no reference images or image generation", "pivot": [16, 29]}}
    source = OUT / f"{name}.json"
    source.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(TOOL), "render", str(source), "--out", str(OUT / name), "--grid", "--scale", "12"], check=True)


save("jade-sword", {
    "o": "#182335", "s": "#31556C", "m": "#4D8B9B", "a": "#88C7C6", "h": "#DAF2DE",
    "b": "#69442F", "g": "#B78140", "y": "#EFC773", "w": "#FFF0AD", "d": "#194D4B", "t": "#398E75"
}, [
    layer("blade-outline", polygon("o", (12, 19), (13, 14), (23, 4), (28, 3), (27, 8), (17, 18))),
    layer("blade-steel", polygon("s", (14, 17), (15, 14), (24, 5), (26, 5), (25, 8), (17, 16)),
          polygon("a", (14, 16), (15, 13), (23, 5), (26, 4), (24, 7), (16, 15)),
          line("h", (14, 15), (24, 5), (26, 4)), line("m", (16, 16), (25, 7))),
    layer("grip", polygon("o", (8, 21), (11, 18), (14, 21), (10, 25), (7, 24)),
          polygon("d", (8, 22), (11, 19), (12, 21), (9, 24)),
          pixels("t", (10, 21), (9, 22)), pixels("y", (10, 20), (11, 21), (8, 22), (9, 23))),
    layer("guard", polygon("o", (9, 15), (11, 15), (18, 22), (18, 24), (16, 24), (8, 17)),
          polygon("g", (10, 16), (17, 23), (16, 23), (9, 16)), line("y", (10, 16), (17, 23)),
          pixels("w", (10, 16), (11, 17)), polygon("o", (13, 17), (16, 19), (14, 22), (11, 19)),
          polygon("t", (13, 18), (15, 19), (14, 21), (12, 19)), pixels("h", (13, 19))),
    layer("pommel", polygon("o", (6, 23), (9, 24), (10, 26), (7, 28), (4, 26)),
          polygon("g", (6, 24), (8, 25), (8, 26), (6, 27), (5, 26)), pixels("y", (6, 24), (5, 25)), pixels("w", (6, 25)))
], "A diagonal jade-hilt sword, pale steel blade and warm gold fittings")

save("ember-potion", {
    "o": "#22233D", "s": "#3A536B", "b": "#718E99", "a": "#ACCAC5", "h": "#E2F1D5",
    "r": "#682B4A", "m": "#B84750", "c": "#ED775D", "l": "#FFBD7D", "k": "#80503E", "g": "#C28B59", "y": "#F0C884"
}, [
    layer("bottle", polygon("o", (11, 7), (20, 7), (20, 11), (25, 16), (26, 20), (25, 25), (21, 28), (10, 28), (6, 25), (5, 20), (6, 16), (11, 11)),
          polygon("s", (12, 8), (19, 8), (19, 12), (24, 17), (25, 21), (23, 25), (20, 27), (10, 27), (7, 24), (6, 20), (7, 16), (12, 11)),
          polygon("b", (12, 9), (18, 9), (18, 12), (22, 16), (23, 20), (21, 24), (10, 25), (7, 22), (7, 18), (12, 12)),
          polygon("a", (12, 10), (14, 10), (13, 13), (9, 17), (8, 21), (7, 20), (8, 16))),
    layer("liquid", polygon("r", (8, 18), (12, 17), (18, 18), (23, 17), (24, 21), (22, 25), (19, 26), (11, 26), (8, 24), (7, 21)),
          polygon("m", (8, 18), (12, 18), (17, 19), (22, 18), (22, 22), (20, 25), (11, 25), (8, 22)),
          polygon("c", (8, 18), (12, 17), (18, 18), (21, 18), (20, 20), (12, 20), (8, 19)),
          line("l", (9, 18), (12, 18), (15, 19)), pixels("c", (12, 23), (13, 24), (14, 24))),
    layer("glass-reflection", line("h", (11, 13), (9, 15), (8, 17)), rect("h", 8, 19, 1, 3), pixels("a", (9, 23), (10, 24), (21, 24), (22, 22)),
          line("b", (13, 27), (19, 27))),
    layer("stopper", rect("o", 11, 3, 9, 5), rect("k", 12, 4, 7, 3), rect("g", 12, 4, 6, 2), line("y", (12, 4), (17, 4)), pixels("k", (14, 6), (17, 5)),
          rect("o", 10, 7, 11, 3), rect("a", 11, 8, 9, 1), rect("h", 11, 8, 4, 1)),
    layer("neck-cord", rect("o", 11, 10, 9, 2), rect("g", 12, 10, 7, 1), line("k", (19, 10), (21, 13)),
          polygon("o", (21, 12), (24, 13), (24, 16), (21, 15)), polygon("y", (22, 13), (23, 14), (22, 15)), pixels("r", (22, 14)))
], "An ember-red potion in a squat glass bottle, cork and small hanging tag")

save("treasure-chest", {
    "o": "#252337", "d": "#4D3040", "s": "#744039", "b": "#A05B3D", "a": "#CD8A50", "h": "#EAAF63",
    "g": "#A66D3D", "y": "#E2B65E", "l": "#FFE294", "r": "#A13B44"
}, [
    layer("silhouette", polygon("o", (5, 10), (8, 6), (21, 6), (27, 10), (28, 14), (28, 25), (24, 28), (5, 28), (3, 25), (3, 14))),
    layer("wood", polygon("s", (5, 13), (8, 8), (21, 8), (26, 11), (27, 15), (26, 24), (23, 26), (5, 26), (4, 24), (4, 14)),
          polygon("b", (5, 11), (8, 7), (20, 7), (24, 10), (24, 15), (4, 15)),
          polygon("a", (7, 10), (9, 8), (20, 8), (22, 10)), rect("b", 5, 18, 18, 7), rect("a", 6, 18, 16, 2),
          polygon("d", (24, 12), (27, 14), (27, 24), (24, 26)),
          line("s", (5, 12), (23, 12)), line("d", (5, 21), (22, 21)), line("s", (7, 24), (11, 24)), pixels("s", (18, 23), (19, 23))),
    layer("metal-bands", polygon("g", (7, 9), (9, 7), (11, 7), (9, 10), (9, 26), (7, 26)),
          polygon("y", (8, 9), (10, 7), (10, 9), (8, 11), (8, 25)),
          polygon("g", (18, 7), (20, 7), (22, 10), (22, 26), (20, 26), (20, 10)),
          polygon("y", (18, 8), (19, 8), (21, 10), (21, 25), (20, 25), (20, 10)),
          line("l", (8, 10), (8, 13)), line("l", (20, 10), (20, 13)),
          rect("o", 4, 15, 20, 3), rect("y", 5, 15, 18, 1), rect("d", 5, 16, 19, 1),
          line("g", (24, 15), (27, 13)), line("o", (24, 16), (27, 14))),
    layer("lock", rect("o", 12, 14, 6, 8), rect("g", 13, 15, 4, 6), rect("y", 13, 15, 3, 5), rect("l", 13, 15, 3, 1),
          rect("o", 14, 17, 2, 2), pixels("o", (15, 19)),
          pixels("l", (8, 19), (8, 24), (21, 19), (21, 24)), pixels("d", (9, 20), (9, 25), (22, 20), (22, 25)))
], "A three-quarter wooden treasure chest with gold bands and a readable central lock")
