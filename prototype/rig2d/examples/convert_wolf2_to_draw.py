#!/usr/bin/env python3
"""One-off: record build_wolf2's drawing calls as declarative "draw" ops and write wolf3.json."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec_ = importlib.util.spec_from_file_location("build_wolf2", HERE / "build_wolf2.py")
wolf = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(wolf)


class Recorder:
    def __init__(self):
        self.ops = []

    def poly(self, c, pts):
        self.ops.append({"op": "poly", "c": c, "pts": [list(p) for p in pts]})

    def line(self, c, pts):
        self.ops.append({"op": "line", "c": c, "pts": [list(p) for p in pts]})

    def px(self, c, *pts):
        self.ops.append({"op": "px", "c": c, "pts": [list(p) for p in pts]})

    def clip(self, c, pts):
        self.ops.append({"op": "clip", "c": c, "pts": [list(p) for p in pts]})

    def rim(self, c, side="top"):
        self.ops.append({"op": "rim", "c": c})

    def band(self, c, depth, x0=0, x1=wolf.W, bottom=False, jag=0):
        op = {"op": "band", "c": c, "depth": depth}
        if (x0, x1) != (0, wolf.W):
            op["x"] = [x0, x1]
        if bottom:
            op["bottom"] = True
        if jag:
            op["jag"] = jag
        self.ops.append(op)


wolf.Layer = Recorder
draw = [
    {"name": "tail", "bones": ["tail3", "tail2", "tail1"], "z": 20, "group": "tail", "ops": wolf.draw_tail().ops},
    {"name": "body", "bones": ["hips", "chest"], "z": 30, "group": "body", "overlap": 2, "ops": wolf.draw_body().ops},
    {"name": "neck", "bones": ["neck"], "z": 33, "group": "body", "ops": wolf.draw_neck().ops},
    {"name": "scarf", "bones": ["neck"], "z": 36, "group": "scarf", "ops": wolf.draw_scarf().ops},
    {"name": "head", "bones": ["head"], "z": 40, "group": "head", "ops": wolf.draw_head().ops},
    {"name": "back_leg", "bones": ["upper_bn", "lower_bn", "foot_bn"], "z": 50, "group": "leg_bn",
     "mirror": {"bones": ["upper_bf", "lower_bf", "foot_bf"], "z": 10, "group": "leg_bf"}, "ops": wolf.draw_back_leg().ops},
    {"name": "front_leg", "bones": ["upper_fn", "lower_fn", "foot_fn"], "z": 54, "group": "leg_fn",
     "mirror": {"bones": ["upper_ff", "lower_ff", "foot_ff"], "z": 14, "group": "leg_ff"}, "ops": wolf.draw_front_leg().ops},
]
spec = json.loads((HERE / "wolf2.json").read_text(encoding="utf-8"))
spec.pop("cutout")
spec["name"] = "wolf3"
spec["draw"] = draw
(HERE / "wolf3.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
print("wrote wolf3.json with", sum(len(r["ops"]) for r in draw), "ops")
