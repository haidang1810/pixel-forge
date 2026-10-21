"""Regressions found by end-to-end runs: seeds on linear keys, minimal --rest, kit outlines, far tones,
per-animation overrides, static outlines, sheet.py, kit palettes, lint on effect frames, ideas.py."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

from test_rig2d import SCRIPTS, RIG, load, opened, humanoid


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)


def write(folder, name, data):
    path = Path(folder) / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class EvalFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig = load("rig2d", RIG)
        cls.presets = cls.rig.presets

    def render(self, spec, *extra):
        temp = Path(tempfile.mkdtemp())
        result = run("rig2d.py", write(temp, "spec.json", spec), "--out", temp / "out", *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return temp / "out"

    def test_seed_never_touches_stretch_or_offsets(self):
        hop = self.presets.anim("slime", "hop")
        seeded = self.presets.personalize(hop, "slime", {"seed": 99})
        for (a, _), (b, _) in zip(hop, seeded):
            for key in self.presets.LINEAR_KEYS & a.keys():
                self.assertAlmostEqual(a[key], b[key], msg=key)

    def test_rest_works_on_a_minimal_spec(self):
        out = self.render({"size": [56, 40], "rig": "quadruped", "palette": {"a": "#304050"}}, "--rest")
        self.assertTrue((out / "rest-grid.png").is_file())
        self.assertTrue((out / "rest-bones.json").is_file())

    def test_palette_kit_supplies_the_outline(self):
        spec = humanoid()
        del spec["outline"]
        spec["palette_kit"] = "sweetie-16"
        spec["materials"] = {m: {"kit": r} for m, r in
                             (("body", "red"), ("skin", "skin"), ("legs", "metal"), ("boots", "wood"))}
        spec["anims"] = [{"preset": "idle", "frames": 2}]
        out = self.render(spec)
        colors = {c for _, c in opened(out / "idle.png").getcolors(4096) if c[3]}
        self.assertIn((0x1A, 0x1C, 0x2C, 255), colors)

    def test_far_tone_stops_short_of_the_outline(self):
        ramp = ["k", "a", "b", "c"]
        darken = lambda c, n, t: ramp[max(0, ramp.index(c) - n)]
        self.assertEqual(self.rig.far_tone(darken, "b", 2, 0.35, "k"), "a")
        self.assertEqual(self.rig.far_tone(darken, "a", 2, 0.35, "k"), "a")
        self.assertEqual(self.rig.far_tone(darken, "c", 2, 0.35, "k"), "a")

    def test_per_animation_stamps_and_z(self):
        spec = humanoid()
        spec["stamps"] = [{"bone": "head", "at": [5, 2], "rows": ["x"], "colors": {"x": "#FF0000"}}]
        spec["anims"] = [{"preset": "idle", "frames": 2},
                         {"preset": "idle", "name": "sleepy", "frames": 2,
                          "stamps": [{"bone": "head", "at": [5, 2], "rows": ["x"], "colors": {"x": "#00FF00"}}]},
                         {"preset": "idle", "name": "front", "frames": 2, "z": {"upper_f": 99, "fore_f": 99, "hand_f": 99}}]
        out = self.render(spec)
        colors = lambda name: {c[:3] for _, c in opened(out / f"{name}.png").getcolors(4096)}
        self.assertIn((255, 0, 0), colors("idle"))
        self.assertNotIn((0, 255, 0), colors("idle"))
        self.assertIn((0, 255, 0), colors("sleepy"))
        self.assertNotIn((255, 0, 0), colors("sleepy"))
        self.assertNotEqual(opened(out / "idle.png").tobytes(), opened(out / "front.png").tobytes())

    def test_static_outline_and_sheet(self):
        temp = Path(tempfile.mkdtemp())
        frames = []
        for i, rows in enumerate([["aa", "aa"], ["aaa", "aaa"]]):
            frames.append(write(temp, f"f{i}.json", {"version": 1, "size": [6, 6], "outline": "o",
                                                     "palette": {".": "#00000000", "o": "#101010", "a": "#E0A040"},
                                                     "layers": [{"name": "box", "origin": [1, 1], "rows": rows}]}))
        result = run("pixel_art.py", "render", frames[0], "--out", temp / "f0")
        self.assertEqual(result.returncode, 0, result.stderr)
        image = opened(temp / "f0.png")
        self.assertEqual(image.getpixel((0, 1)), (16, 16, 16, 255))  # left of the box
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 0))  # diagonal stays empty
        bad = write(temp, "bad.json", {"version": 1, "size": [2, 2], "outline": "z", "palette": {"a": "#FFFFFF"},
                                       "layers": [{"name": "x", "rows": ["a"]}]})
        self.assertNotEqual(run("pixel_art.py", "render", bad, "--out", temp / "bad").returncode, 0)

        out = temp / "sheet"
        result = run("sheet.py", *frames, "--ms", 100, 300, "--name", "grow", "--out", out, "--once")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
        grow = manifest["animations"]["grow"]
        self.assertFalse(grow["loop"])
        self.assertEqual([f["ms"] for f in grow["frames"]], [100, 300])
        self.assertEqual(opened(out / "grow.png").size, (12, 6))
        for name in ("grow.preview.gif", "contact.png", "grow/frame-01.png"):
            self.assertTrue((out / name).is_file(), name)
        self.assertEqual(run("lint.py", out).returncode, 0)
        self.assertEqual(run("sheet.py", *frames, "--ms", 1, 2, 3, "--name", "x", "--out", out).returncode, 2)

    def test_kit_document_palette(self):
        result = run("palette_tools.py", "--kit", "sweetie-16")
        self.assertEqual(result.returncode, 0, result.stderr)
        doc = json.loads(result.stdout)
        self.assertEqual(doc["palette"]["o"].upper(), "#1A1C2C")
        self.assertEqual(doc["palette"]["."], "#00000000")
        for symbols in doc["ramps"].values():
            self.assertTrue(set(symbols) <= set(doc["palette"]))

    def test_lint_skips_effect_frames(self):
        spec = humanoid()
        spec["anims"] = [{"preset": "die", "style": "fade"}]
        out = self.render(spec)
        manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
        self.assertTrue(any("dissolve" in f.get("effects", []) for f in manifest["animations"]["die"]["frames"]))
        report = run("lint.py", out).stdout
        self.assertNotIn("empty", report)

    def test_manifest_loop_bom_and_lint_errors(self):
        temp = Path(tempfile.mkdtemp())
        spec = humanoid()
        spec["anims"] = [{"preset": "idle", "frames": 2}, {"preset": "hurt"}]
        source = temp / "spec.json"
        source.write_text(json.dumps(spec), encoding="utf-8-sig")  # PowerShell writes a BOM
        result = run("rig2d.py", source, "--out", temp / "out")
        self.assertEqual(result.returncode, 0, result.stderr)
        anims = json.loads((temp / "out" / "animation.json").read_text(encoding="utf-8"))["animations"]
        self.assertTrue(anims["idle"]["loop"])
        self.assertFalse(anims["hurt"]["loop"])
        missing = run("lint.py", temp / "nowhere")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("error:", missing.stderr)
        self.assertNotIn("Traceback", missing.stderr)

    def test_ideas_are_fresh_unless_seeded(self):
        roll = lambda *a: json.loads(run("ideas.py", "--count", 2, *a).stdout)
        a, b = roll(), roll()
        self.assertNotEqual(a["roll_seed"], b["roll_seed"])
        self.assertEqual(roll("--seed", a["roll_seed"]), a)
        for direction in a["directions"]:
            self.assertIn("seed", direction["motion"])
            self.assertRegex(direction["base_color"], r"^#[0-9A-F]{6}$")


if __name__ == "__main__":
    unittest.main()
