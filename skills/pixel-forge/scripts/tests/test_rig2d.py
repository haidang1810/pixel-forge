"""Behavior tests for rig2d: grounded poses, exact v1 export, cutout layers, touch-ups, and spec errors."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
RIG = SCRIPTS / "rig2d.py"


def load(name, path):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def opened(path):
    """Load an image fully and close the file."""
    with Image.open(path) as image:
        return image.convert("RGBA")


def humanoid():
    return {
        "name": "test", "size": [40, 40], "rig": "humanoid", "outline": "#101010",
        "materials": {"body": ["#203040", "#405060", "#6080A0"], "skin": ["#604030", "#A07050", "#E0B090"],
                      "legs": ["#202020", "#404040", "#606060"], "boots": ["#301810", "#503020", "#704830"]},
        "anims": [{"preset": "idle", "frames": 3, "ms": 120}, {"preset": "walk", "frames": 4}],
    }


def quad_cutout():
    # One unrotating body layer and a far copy of a leg layer, in a 2-symbol palette.
    return {
        "name": "q", "size": [48, 40], "rig": "quadruped", "outline": "#101010",
        "palette": {"a": "#304050", "b": "#6080A0", "c": "#A0C0E0"},
        "ramps": ["abc"],
        "cutout": [
            {"name": "body", "bone": "spine", "origin": [14, 18], "z": 30, "group": "body",
             "rows": ["bbbbbbbbbbbb", "bccccccccccb", "bbbbbbbbbbbb"]},
            {"name": "leg", "bone": "upper_bn", "origin": [15, 21], "z": 50, "group": "leg", "rows": ["cc", "cc", "cc"]},
            {"name": "leg_far", "from": "leg", "bone": "upper_bf", "z": 10, "group": "legf", "far": True},
        ],
        "anims": [{"preset": "idle", "frames": 2}],
    }


class Rig2dTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig = load("rig2d", RIG)
        cls.v1 = load("pixel_art", SCRIPTS / "pixel_art.py")

    def run_cli(self, spec, *extra):
        temp = Path(tempfile.mkdtemp())
        source = temp / "spec.json"
        source.write_text(json.dumps(spec), encoding="utf-8")
        out = temp / "out"
        result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(out), *extra],
                                capture_output=True, text=True)
        return result, out

    def test_sheet_manifest_and_exact_v1_frames(self):
        result, out = self.run_cli(humanoid())
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
        idle = manifest["animations"]["idle"]
        self.assertEqual([f["ms"] for f in idle["frames"]], [120, 120, 120])
        self.assertEqual(opened(out / "idle.png").size, (120, 40))
        self.assertEqual(opened(out / "walk.png").size, (160, 40))
        for i in range(3):
            document = json.loads((out / "idle" / f"frame-{i:02d}.json").read_text(encoding="utf-8"))
            image, _ = self.v1.render_document(document)
            frame = opened(out / "idle" / f"frame-{i:02d}.png")
            self.assertEqual(image.tobytes(), frame.tobytes())
            alphas = {px[3] for px in self.rig.pixels_of(frame)}
            self.assertLessEqual(alphas, {0, 255})

    def test_feet_stay_planted_on_ground_row(self):
        result, out = self.run_cli(humanoid())
        self.assertEqual(result.returncode, 0, result.stderr)
        for anim, count in (("idle", 3), ("walk", 4)):
            for i in range(count):
                bbox = opened(out / anim / f"frame-{i:02d}.png").getbbox()
                self.assertIn(bbox[3], (39, 40 - 1), f"{anim} {i} bottom {bbox}")

    def test_unrotated_cutout_layer_is_copied_exactly(self):
        spec = quad_cutout()
        result, out = self.run_cli(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        colors = {"b": (0x60, 0x80, 0xA0, 255), "c": (0xA0, 0xC0, 0xE0, 255)}
        for i in range(2):
            frame = opened(out / "idle" / f"frame-{i:02d}.png")
            for y, row in enumerate(spec["cutout"][0]["rows"]):
                for x, ch in enumerate(row):
                    if 15 <= x + 14 <= 17:  # columns covered by the near leg layer
                        continue
                    self.assertEqual(frame.getpixel((14 + x, 18 + y)), colors[ch], (i, x, y))

    def test_far_copy_steps_down_the_palette_ramp(self):
        rig = load("rig2d", RIG)
        spec = quad_cutout()
        rig.validate_spec(spec)
        family_rig = rig.presets.rig("quadruped", {})
        parts = rig.build_parts(spec, family_rig)
        far = next(p for p in parts if p["name"] == "leg_far")
        self.assertTrue(far["far"])
        image = rig.render_frame(spec, family_rig, rig.rest_pose(spec, family_rig), parts)
        allowed = {(0x30, 0x40, 0x50, 255), (0x60, 0x80, 0xA0, 255), (0xA0, 0xC0, 0xE0, 255), (0x10, 0x10, 0x10, 255), (0, 0, 0, 0)}
        self.assertLessEqual(set(rig.pixels_of(image)), allowed)

    def test_touchups_survive_rerender(self):
        spec = quad_cutout()
        spec["touchups"] = {"idle": {"1": [{"color": "c", "pixels": [[2, 2]]}, {"erase": [[14, 18]]}]}}
        result, out = self.run_cli(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        frame = opened(out / "idle" / "frame-01.png")
        self.assertEqual(frame.getpixel((2, 2)), (0xA0, 0xC0, 0xE0, 255))
        self.assertEqual(frame.getpixel((14, 18))[3], 0)
        untouched = opened(out / "idle" / "frame-00.png")
        self.assertEqual(untouched.getpixel((2, 2))[3], 0)

    def test_rest_sheet_lists_bones(self):
        result, out = self.run_cli(quad_cutout(), "--rest")
        self.assertEqual(result.returncode, 0, result.stderr)
        bones = json.loads((out / "rest-bones.json").read_text(encoding="utf-8"))
        self.assertIn("tail3", bones)
        self.assertTrue((out / "rest-grid.png").is_file() and (out / "rest.png").is_file())

    def test_float_hovers_above_its_ground_shadow(self):
        spec = humanoid()
        spec["pose_offset"] = {"dy": -6}
        spec["shadow"] = {"color": "#222233", "rx": 5}
        spec["anims"] = [{"preset": "float", "frames": 4}]
        result, out = self.run_cli(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        shadow = (0x22, 0x22, 0x33, 255)
        for i in range(4):
            frame = opened(out / "float" / f"frame-{i:02d}.png")
            body_rows = [y for y in range(40) for x in range(40)
                         if frame.getpixel((x, y))[3] and frame.getpixel((x, y)) != shadow]
            self.assertLess(max(body_rows), 40 - 3 - 4, f"frame {i} is not floating")
            self.assertTrue(any(frame.getpixel((x, 37)) == shadow for x in range(40)), f"frame {i} has no shadow")

    def drawn_quad(self):
        spec = quad_cutout()
        spec.pop("cutout")
        spec["draw"] = [
            {"name": "body", "bones": ["spine"], "z": 30, "group": "body",
             "ops": [{"op": "poly", "c": "b", "pts": [[14, 18], [25, 18], [25, 20], [14, 20]]},
                     {"op": "clip", "c": "c", "pts": [[15, 19], [24, 19], [24, 19.9], [15, 19.9]]}]},
            {"name": "leg", "bones": ["upper_bn"], "z": 50, "group": "leg",
             "ops": [{"op": "poly", "c": "c", "pts": [[15, 21], [16, 21], [16, 23], [15, 23]]}],
             "mirror": {"bones": ["upper_bf"], "z": 10, "group": "legf"}},
        ]
        return spec

    def test_drawn_regions_match_equivalent_cutout_rows(self):
        drawn, out_drawn = self.run_cli(self.drawn_quad())
        rows, out_rows = self.run_cli(quad_cutout())
        self.assertEqual(drawn.returncode, 0, drawn.stderr)
        self.assertEqual(rows.returncode, 0, rows.stderr)
        self.assertEqual(opened(out_drawn / "idle.png").tobytes(), opened(out_rows / "idle.png").tobytes())

    def test_split_shares_joint_pixels_between_bones(self):
        tools = load("cutout_tools", SCRIPTS / "cutout_tools.py")
        bones = {"a": ((0, 0), (10, 0)), "b": ((10, 0), (20, 0))}
        pixels = {(x, 0): "x" for x in range(20)}
        parts = tools.split(pixels, bones, ["a", "b"], overlap=1.5)
        self.assertIn((9, 0), parts["a"])
        self.assertIn((9, 0), parts["b"])  # joint pixel goes to both bones
        self.assertNotIn((2, 0), parts["b"])
        self.assertNotIn((17, 0), parts["a"])

    def test_bake_freezes_draw_into_identical_cutout(self):
        spec = self.drawn_quad()
        temp = Path(tempfile.mkdtemp())
        source = temp / "spec.json"
        source.write_text(json.dumps(spec), encoding="utf-8")
        baked = temp / "baked.json"
        result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(temp / "a"), "--bake", str(baked)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        frozen = json.loads(baked.read_text(encoding="utf-8"))
        self.assertNotIn("draw", frozen)
        self.assertTrue(any("rows" in layer for layer in frozen["cutout"]))
        again = subprocess.run([sys.executable, str(RIG), str(baked), "--out", str(temp / "b")], capture_output=True, text=True)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(opened(temp / "a" / "idle.png").tobytes(), opened(temp / "b" / "idle.png").tobytes())

    def test_invalid_draw_regions_fail(self):
        cases = []
        bad = self.drawn_quad(); bad["draw"][0]["ops"][0]["op"] = "spray"; cases.append((bad, "unknown op"))
        bad = self.drawn_quad(); bad["draw"][0]["ops"][0]["c"] = "z"; cases.append((bad, "not a palette symbol"))
        bad = self.drawn_quad(); bad["draw"][1]["mirror"]["bones"] = ["upper_bf", "lower_bf"]
        cases.append((bad, "one target bone per region bone"))
        bad = self.drawn_quad(); bad["draw"][0]["bones"] = ["wing"]; cases.append((bad, "unknown bone"))
        for spec, message in cases:
            result, out = self.run_cli(spec)
            self.assertEqual(result.returncode, 2, (message, result.stderr))
            self.assertIn(message, result.stderr)
            self.assertFalse(out.exists(), message)

    def test_hurt_flashes_and_die_lies_on_the_standing_ground_line(self):
        spec = humanoid()
        spec["anims"] = [{"preset": "idle", "frames": 2}, {"preset": "hurt"}, {"preset": "die"}]
        result, out = self.run_cli(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        flash = opened(out / "hurt" / "frame-00.png")
        colors = {c for c in self.rig.pixels_of(flash) if c[3]}
        self.assertEqual(colors, {(255, 255, 255, 255), (0x10, 0x10, 0x10, 255)})
        standing = opened(out / "idle" / "frame-00.png").getbbox()
        manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
        die = manifest["animations"]["die"]["frames"]
        lying = opened(out / "die" / f"frame-{len(die) - 1:02d}.png").getbbox()
        self.assertEqual(lying[3], standing[3])
        self.assertGreater(lying[2] - lying[0], lying[3] - lying[1], "the last die frame should lie down")
        self.assertTrue(all(len(f["pivot"]) == 2 for f in die))

    def test_fade_death_dissolves_to_nothing(self):
        spec = humanoid()
        spec["pose_offset"] = {"dy": -4}
        spec["anims"] = [{"preset": "die", "style": "fade"}]
        result, out = self.run_cli(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        frames = json.loads((out / "animation.json").read_text(encoding="utf-8"))["animations"]["die"]["frames"]
        last = opened(out / "die" / f"frame-{len(frames) - 1:02d}.png")
        self.assertIsNone(last.getbbox())
        middle = opened(out / "die" / "frame-03.png")
        self.assertIsNotNone(middle.getbbox())

    def test_quadruped_has_a_full_mob_set(self):
        spec = quad_cutout()
        spec["anims"] = [{"preset": p} for p in ("idle", "walk", "run", "attack", "hurt", "die")]
        result, out = self.run_cli(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(manifest["animations"]), ["attack", "die", "hurt", "idle", "run", "walk"])

    def test_motion_personality(self):
        presets = self.rig.presets
        walk = presets.anim("humanoid", "walk")
        self.assertIs(presets.personalize(walk, "humanoid", {}), walk)  # defaults change nothing
        heavy = presets.personalize(walk, "humanoid", {"weight": 1, "energy": 0.2})
        light = presets.personalize(walk, "humanoid", {"weight": 0, "energy": 1})
        self.assertGreater(sum(ms for _, ms in heavy), sum(ms for _, ms in walk))
        self.assertLess(sum(ms for _, ms in light), sum(ms for _, ms in walk))
        swing = lambda frames: max(abs(p["sh_n"] - presets.REST["sh_n"]) for p, _ in frames)
        self.assertGreater(swing(light), swing(heavy))
        a = presets.personalize(walk, "humanoid", {"seed": 3})
        self.assertEqual(a, presets.personalize(walk, "humanoid", {"seed": 3}))
        self.assertNotEqual(a, presets.personalize(walk, "humanoid", {"seed": 4}))

    def test_builds_change_the_silhouette(self):
        widths = {}
        for build in ("bulky", "slim"):
            spec = humanoid()
            spec["build"] = build
            spec["anims"] = [{"preset": "idle", "frames": 1}]
            result, out = self.run_cli(spec)
            self.assertEqual(result.returncode, 0, result.stderr)
            box = opened(out / "idle" / "frame-00.png").getbbox()
            widths[build] = box[2] - box[0]
            self.assertEqual(box[3], 39, f"{build} feet should rest on the ground row")
        self.assertGreater(widths["bulky"], widths["slim"])
        bad = humanoid(); bad["build"] = "huge"
        result, _ = self.run_cli(bad)
        self.assertEqual(result.returncode, 2)

    def test_new_rigs_render_every_preset_on_the_ground(self):
        mats = {"body": ["#203040", "#405060", "#6080A0"], "wing": ["#202030", "#404060", "#606090"],
                "beak": ["#806020", "#C09040", "#F0C060"], "leg": ["#604020", "#806040", "#A08060"]}
        for rig, moves in (("slime", ["idle", "hop", "attack", "hurt", "die"]),
                           ("serpent", ["idle", "slither", "attack", "hurt", "die"]),
                           ("bird", ["idle", "hop", "fly", "attack", "hurt", "die"])):
            spec = {"name": rig, "size": [64, 48], "rig": rig, "outline": "#101010", "root_x": 0.5,
                    "materials": mats, "anims": [{"preset": m} for m in moves]}
            result, out = self.run_cli(spec)
            self.assertEqual(result.returncode, 0, (rig, result.stderr))
            idle = opened(out / "idle" / "frame-00.png").getbbox()
            self.assertEqual(idle[3], 47, f"{rig} idle should rest on the ground row")
            if rig == "bird":
                flying = opened(out / "fly" / "frame-00.png").getbbox()
                self.assertLess(flying[3], 47 - 8, "the bird should be off the ground while flying")
            if rig == "slime":
                squashed = opened(out / "hop" / "frame-00.png").getbbox()
                self.assertGreater(squashed[2] - squashed[0], idle[2] - idle[0])

    def test_styles(self):
        def render(style):
            spec = humanoid()
            spec["anims"] = [{"preset": "idle", "frames": 1}]
            if style:
                spec["style"] = style
            result, out = self.run_cli(spec)
            self.assertEqual(result.returncode, 0, result.stderr)
            return opened(out / "idle" / "frame-00.png")
        outline = (0x10, 0x10, 0x10, 255)
        self.assertNotIn(outline, self.rig.pixels_of(render({"outline": "none"})))
        two = {c for c in self.rig.pixels_of(render({"shades": 2})) if c[3]}
        lightest = {(0x60, 0x80, 0xA0, 255), (0xE0, 0xB0, 0x90, 255), (0x60, 0x60, 0x60, 255), (0x70, 0x48, 0x30, 255)}
        self.assertFalse(two & lightest, "two shades should not use the light tone")
        self.assertNotEqual(render(None).tobytes(), render({"light": "upper-back"}).tobytes())
        bad = humanoid(); bad["style"] = {"outline": "thick"}
        result, _ = self.run_cli(bad)
        self.assertEqual(result.returncode, 2)

    def test_scale2x_keeps_flat_regions(self):
        grid = [[1, 1], [1, 1]]
        self.assertEqual(self.rig.scale2x(grid), [[1] * 4 for _ in range(4)])

    def test_invalid_specs_fail_without_outputs(self):
        cases = []
        bad = humanoid(); bad["anims"] = [{"preset": "run"}]; cases.append((bad, "not a humanoid preset"))
        bad = humanoid(); bad["extras"] = [{"bone": "wing", "shape": "capsule", "r": 1, "mat": "body", "z": 1}]
        cases.append((bad, "unknown bone"))
        bad = humanoid(); bad["parts"] = {"head": {"mat": "gold"}}; cases.append((bad, "not defined in materials"))
        bad = quad_cutout(); bad["cutout"][0]["rows"][1] = "bccccccccczb"; cases.append((bad, "unknown palette symbol"))
        bad = quad_cutout(); bad["touchups"] = {"idle": {"0": [{"color": "c", "pixels": [[99, 1]]}]}}
        cases.append((bad, "outside the canvas"))
        bad = humanoid(); bad["colour"] = "#000000"; cases.append((bad, "unknown fields"))
        for spec, message in cases:
            result, out = self.run_cli(spec)
            self.assertEqual(result.returncode, 2, (message, result.stderr))
            self.assertIn(message, result.stderr)
            self.assertFalse(out.exists(), message)

    def test_out_dir_holding_the_spec_is_refused(self):
        temp = Path(tempfile.mkdtemp())
        source = temp / "spec.json"
        source.write_text(json.dumps(humanoid()), encoding="utf-8")
        result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(temp)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(sorted(p.name for p in temp.iterdir()), ["spec.json"])


if __name__ == "__main__":
    unittest.main()
