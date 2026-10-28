"""Effects operations, layer groups and transforms, composite.py, export.py, lint on animations, abtest."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import pixel_art  # noqa: E402

PALETTE = {".": "#00000000", "a": "#102040", "b": "#3070C0", "c": "#90D0FF", "d": "#FFFFFF",
           "r": "#401010", "o": "#C04020", "y": "#FFD060"}


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)


def fx_doc(edits_per_frame, size=(48, 48)):
    return {"version": 1, "size": list(size), "palette": dict(PALETTE), "layers": [{"name": "fx", "ops": []}],
            "animation": {"fps": 10, "frames": [{"edits": e} for e in edits_per_frame]}}


class VfxToolTests(unittest.TestCase):
    def colors(self, image):
        return {c[:3] for c in image.getdata() if c[3]}

    def test_bolt_has_core_and_rim(self):
        doc = fx_doc([[{"layer": "fx", "op": "bolt", "from": [10, 2], "to": [30, 45], "colors": "abcd", "seed": 3}]])
        image = pixel_art.render_frames(doc)[0][0]
        self.assertIn((255, 255, 255), self.colors(image))  # white-hot core
        self.assertIn((0x10, 0x20, 0x40), self.colors(image))  # dark rim
        box = image.getbbox()
        self.assertLessEqual(box[1], 3)
        self.assertGreaterEqual(box[3], 44)

    def test_bolt_without_rim_and_ring_halves(self):
        doc = fx_doc([[{"layer": "fx", "op": "bolt", "from": [10, 2], "to": [30, 45], "colors": "abcd", "seed": 3,
                        "rim": False, "width": 1.5, "taper": 0.5}]])
        self.assertNotIn((0x10, 0x20, 0x40), self.colors(pixel_art.render_frames(doc)[0][0]))
        front = fx_doc([[{"layer": "fx", "op": "ring", "center": [24, 24], "radius": 18, "squash": 0.45,
                          "colors": "abcd", "arc": [0, 180]}]])
        box = pixel_art.render_frames(front)[0][0].getbbox()
        self.assertGreaterEqual(box[1], 23)  # only the front (lower) half of the flattened ring
        self.assertLessEqual(box[3] - box[1], 13)

    def test_flames_loop_closes_and_moves(self):
        frames = [[{"layer": "fx", "op": "flames", "xy": [8, 10], "size": [30, 30], "colors": "roy", "t": t, "period": 6,
                    "seed": 2}] for t in range(7)]
        images = [img for img, _, _ in pixel_art.render_frames(fx_doc(frames))]
        self.assertEqual(images[0].tobytes(), images[6].tobytes())  # t = period wraps to t = 0
        self.assertNotEqual(images[0].tobytes(), images[3].tobytes())

    def test_particles_burst_and_smoke(self):
        frames = [[{"layer": "fx", "op": "particles", "origin": [24, 24], "colors": "roy", "count": 12, "t": t,
                    "mode": "burst", "spread": 360, "speed": 2, "seed": 4},
                   {"layer": "fx", "op": "smoke", "origin": [10, 40], "colors": "abc", "t": t, "seed": 1}] for t in (1, 5)]
        a, b = [img for img, _, _ in pixel_art.render_frames(fx_doc(frames))]
        wide = lambda im: (lambda bb: bb[2] - bb[0])(im.getbbox())
        self.assertGreater(wide(b), wide(a))  # the burst spreads out

    def test_layer_groups_and_transform(self):
        temp = Path(tempfile.mkdtemp())
        doc = {"version": 1, "size": [24, 24], "palette": dict(PALETTE),
               "layers": [{"name": "back", "group": "back", "ops": [{"op": "rect", "xy": [2, 2], "size": [6, 6], "color": "a"}]},
                          {"name": "lid", "group": "front", "ops": [{"op": "rect", "xy": [8, 10], "size": [12, 3], "color": "y"}]}],
               "animation": {"frames": [{}, {"edits": [{"layer": "lid", "transform": {"pivot": [8, 12], "rotate": -90}}]}]}}
        source = temp / "doc.json"
        source.write_text(json.dumps(doc))
        result = run("pixel_art.py", "render", source, "--out", temp / "doc")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("doc.back.png", "doc.front.png", "doc.front.strip.png", "doc.front.anim.json"):
            self.assertTrue((temp / name).is_file(), name)
        frames = pixel_art.render_frames(doc)
        rotated = frames[1][0]
        self.assertEqual(self.colors(rotated), self.colors(frames[0][0]))  # nearest sampling: no new colors
        box = rotated.crop((8, 0, 24, 24)).getbbox()
        self.assertGreater(box[3] - box[1], box[2] - box[0])  # the lid now stands upright

    def test_composite_export_lint_and_abtest(self):
        temp = Path(tempfile.mkdtemp())
        doc = fx_doc([[{"layer": "fx", "op": "flames", "xy": [8, 10], "size": [30, 30], "colors": "roy", "t": t,
                        "period": 4}] for t in range(4)])
        doc["meta"] = {"pivot": [24, 47]}
        (temp / "fx.json").write_text(json.dumps(doc))
        self.assertEqual(run("pixel_art.py", "render", temp / "fx.json", "--out", temp / "fx").returncode, 0)
        Image.new("RGBA", (80, 60), (200, 180, 120, 255)).save(temp / "bg.png")
        result = run("composite.py", "--bg", temp / "bg.png", "--at", 40, 55, "--layer", f"fx:{temp / 'fx.anim.json'}*2",
                     "--out", temp / "comp.gif")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((temp / "comp.gif").is_file())
        result = run("composite.py", "--bg", temp / "bg.png", "--at", 10, 55, "--layer", "move:4,0", "--layer", "once",
                     "--layer", f"fx:{temp / 'fx.anim.json'}*2", "--layer", "offset:40,0", "--layer", "wait:8",
                     "--layer", f"hit:{temp / 'fx.anim.json'}", "--out", temp / "seq.gif", "--scale", 1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(12 frames)", result.stdout)  # 8 flying frames, then the 4-frame hit
        result = run("export.py", temp / "fx.anim.json", "--out", temp / "build", "--name", "spell")
        self.assertEqual(result.returncode, 0, result.stderr)
        ase = json.loads((temp / "build" / "spell.aseprite.json").read_text())
        self.assertEqual(ase["meta"]["frameTags"][0]["to"], 3)
        self.assertEqual(ase["meta"]["pivots"]["fx_0"], [24, 47])
        self.assertIn("SpriteFrames", (temp / "build" / "spell.tres").read_text())
        result = run("lint.py", temp / "fx.anim.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        same = run("abtest.py", temp / "fx.png", temp / "fx.png", "--dir", temp / "ab")
        self.assertEqual(same.returncode, 2)
        self.assertIn("identical", same.stderr)

    def test_lint_ignores_glints(self):
        import lint
        image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        for x in range(1, 15):
            for y in range(1, 15):
                image.putpixel((x, y), (20, 20, 20, 255) if x in (1, 14) or y in (1, 14) else (90, 60, 40, 255))
        for p in ((4, 4), (8, 9), (11, 5), (6, 11)):
            image.putpixel(p, (250, 240, 200, 255))  # rivets: lighter than every neighbour
        _, findings = lint.lint_frame(image)
        self.assertFalse(any(f.startswith("stray") for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
