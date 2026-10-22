"""The richer static format: ramps, parts, mirror, glow, blend layers, extra ops and animation frames."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pixel_art  # noqa: E402

PALETTE = {".": "#00000000", "k": "#101010", "a": "#303060", "b": "#5050A0", "c": "#8080E0",
           "y": "#E0C040", "Y": "#FFF0A0"}


def doc(**extra):
    base = {"version": 1, "size": [16, 12], "palette": dict(PALETTE), "ramps": ["kabc", "yY"],
            "layers": [{"name": "body", "ops": [{"op": "rect", "xy": [2, 2], "size": [6, 8], "color": "b"}]}]}
    base.update(extra)
    return base


def colors(image):
    return {c for c in image.getdata() if c[3]}


class FormatExtrasTests(unittest.TestCase):
    def render(self, document):
        return pixel_art.render_document(document)[0]

    def test_old_documents_render_unchanged(self):
        plain = {"version": 1, "size": [4, 4], "palette": {"a": "#FF0000", ".": "#00000000"},
                 "layers": [{"name": "x", "rows": ["a...", ".a..", "..a.", "...a"]}]}
        image = self.render(plain)
        self.assertEqual(image.getpixel((2, 2)), (255, 0, 0, 255))
        self.assertEqual(image.getpixel((1, 2)), (0, 0, 0, 0))

    def test_mirror_copies_the_left_half(self):
        image = self.render(doc(mirror="x"))
        for y in range(12):
            for x in range(8):
                self.assertEqual(image.getpixel((x, y)), image.getpixel((15 - x, y)))

    def test_shade_light_and_glow_stay_in_the_palette(self):
        d = doc(glow=[{"keys": "Y", "r": 4, "steps": 2}])
        d["layers"][0]["ops"] += [{"op": "shade", "region": {"rect": [2, 6, 6, 4]}},
                                  {"op": "light", "region": {"circle": [4, 3, 1]}},
                                  {"op": "pixels", "points": [[5, 5]], "color": "Y"}]
        d["layers"].append({"name": "cast", "blend": "shade", "ops": [{"op": "rect", "xy": [6, 2], "size": [2, 8], "color": "k"}]})
        image = self.render(d)
        allowed = {tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) + (255,) for k, v in PALETTE.items() if k != "."}
        self.assertTrue(colors(image) <= allowed)
        self.assertEqual(image.getpixel((3, 8))[:3], (0x30, 0x30, 0x60))  # shaded b -> a
        self.assertEqual(image.getpixel((7, 9))[:3], (0x10, 0x10, 0x10))  # shaded to a, then the blend layer to k

    def test_parts_stamp_scatter_and_extra_ops(self):
        d = doc(parts={"dot": {"rows": ["y"]}, "pair": {"rows": ["cc"]}})
        d["layers"][0]["ops"] += [{"op": "stamp", "part": "pair", "xy": [9, 1], "swap": {"c": "y"}},
                                  {"op": "scatter", "parts": "dot", "xy": [2, 2], "size": [6, 8], "count": 5, "seed": 2,
                                   "on": "b"},
                                  {"op": "circle", "center": [12, 8], "r": 2, "color": "a", "ring": True},
                                  {"op": "line", "points": [[0, 11], [15, 11]], "color": "k", "width": 3}]
        image = self.render(d)
        self.assertEqual(image.getpixel((10, 1))[:3], (0xE0, 0xC0, 0x40))
        self.assertGreater(sum(1 for c in image.getdata() if c[:3] == (0xE0, 0xC0, 0x40)), 2)
        self.assertEqual(image.getpixel((12, 8)), (0, 0, 0, 0))  # ring is hollow
        with self.assertRaises(ValueError):
            bad = doc(); bad["layers"][0]["ops"].append({"op": "stamp", "part": "nope", "xy": [0, 0]})
            self.render(bad)

    def test_animation_frames_are_patches(self):
        d = doc(animation={"fps": 10, "frames": [{}, {"edits": [{"layer": "body", "move": [1, 0]}]},
                                                 {"ms": 300, "edits": [{"layer": "body", "op": "recolor", "map": {"b": "c"}}]}]})
        frames = pixel_art.render_frames(d)
        self.assertEqual([ms for _, ms, _ in frames], [100, 100, 300])
        self.assertEqual(frames[1][0].getpixel((8, 5))[:3], (0x50, 0x50, 0xA0))
        self.assertEqual(frames[2][0].getpixel((4, 5))[:3], (0x80, 0x80, 0xE0))

    def test_render_cli_writes_animation_files(self):
        import subprocess, tempfile
        temp = Path(tempfile.mkdtemp())
        source = temp / "a.json"
        source.write_text(json.dumps(doc(animation={"frames": [{}, {"edits": [{"layer": "body", "visible": False}]}]})))
        result = subprocess.run([sys.executable, str(Path(pixel_art.__file__)), "render", str(source), "--out", str(temp / "a")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for suffix in (".png", ".strip.png", ".anim.json", ".gif", ".frames.png"):
            self.assertTrue((temp / ("a" + suffix)).is_file(), suffix)
        manifest = json.loads((temp / "a.anim.json").read_text())
        self.assertEqual(len(manifest["frames"]), 2)

    def test_grid_op_and_ascii_round_trip(self):
        d = doc()
        d["layers"][0]["ops"].append({"op": "grid", "xy": [2, 2], "rows": ["c c", " k "]})
        image = self.render(d)
        self.assertEqual(image.getpixel((2, 2))[:3], (0x80, 0x80, 0xE0))
        self.assertEqual(image.getpixel((3, 2))[:3], (0x50, 0x50, 0xA0))  # space kept the rect below
        self.assertEqual(image.getpixel((3, 3))[:3], (0x10, 0x10, 0x10))
        text = pixel_art.ascii_art(d, box=[0, 0, 9, 4]).splitlines()
        self.assertEqual(text[2 + 2][4:4 + 6], "  cbcb")  # the space kept b
        self.assertEqual(text[2 + 3][4:4 + 6], "  bkbb")

    def test_abtest_hides_and_reveals_the_order(self):
        import subprocess, tempfile
        temp = Path(tempfile.mkdtemp())
        for name, color in (("old.png", (255, 0, 0, 255)), ("new.png", (0, 255, 0, 255))):
            from PIL import Image
            Image.new("RGBA", (2, 2), color).save(temp / name)
        script = Path(pixel_art.__file__).with_name("abtest.py")
        r = subprocess.run([sys.executable, str(script), str(temp / "old.png"), str(temp / "new.png"), "--dir", str(temp / "ab")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        from PIL import Image
        greens = [n for n in "ab" if Image.open(temp / "ab" / f"{n}.png").getpixel((0, 0))[1] == 255]
        out = subprocess.run([sys.executable, str(script), "--reveal", str(temp / "ab")], capture_output=True, text=True).stdout
        self.assertIn(f"new version is {greens[0]}", out)

    def test_lint_flags_duplicates_and_banding(self):
        import lint
        from PIL import Image
        image = Image.new("RGBA", (24, 12), (0, 0, 0, 0))
        for x in range(1, 23):
            for y in range(1, 11):
                image.putpixel((x, y), (16, 16, 16, 255))  # outline ring
        for x in range(2, 22):
            for y in range(2, 10):
                image.putpixel((x, y), (200, 60, 60, 255) if y < 4 else (160, 45, 45, 255) if y < 7 else (120, 30, 30, 255))
        image.putpixel((10, 2), (201, 61, 60, 255))
        findings = lint.lint_frame(image)[1]
        self.assertTrue(any(f.startswith("duplicates") for f in findings), findings)
        self.assertTrue(any(f.startswith("banding") for f in findings), findings)

    def test_lights_are_blocked_by_solid_layers_and_spare_the_source(self):
        d = doc()
        d["layers"] = [{"name": "floor", "ops": [{"op": "rect", "xy": [0, 8], "size": [16, 4], "color": "b"}]},
                       {"name": "wall", "solid": True, "ops": [{"op": "rect", "xy": [9, 0], "size": [2, 8], "color": "b"}]},
                       {"name": "fire", "ops": [{"op": "pixels", "points": [[4, 7]], "color": "Y"}]}]
        d["lights"] = [{"at": [4, 7], "r": 12, "steps": 2, "keys": "Y"}]
        image = self.render(d)
        self.assertEqual(image.getpixel((4, 7))[:3], (0xFF, 0xF0, 0xA0))  # the source stays as painted
        self.assertEqual(image.getpixel((4, 8))[:3], (0x80, 0x80, 0xE0))  # floor next to the fire lit b -> c
        self.assertEqual(image.getpixel((14, 9))[:3], (0x50, 0x50, 0xA0))  # floor behind the wall stays b


if __name__ == "__main__":
    unittest.main()
