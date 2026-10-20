"""Render every preset of the humanoid_movement pack through the rig2d CLI and check grounding and the jump."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
RIG = SCRIPTS / "rig2d.py"
PRESETS = ["run", "jump", "jump_rise", "jump_fall", "land", "crouch", "crouch_walk", "sneak", "dash", "climb", "push"]


def frames_of(sheet):
    with Image.open(sheet) as image:
        image = image.convert("RGBA")
    h = image.height
    return [image.crop((i * h, 0, i * h + h, h)) for i in range(image.width // h)]


def character(rig="humanoid"):
    return {
        "name": "mover", "size": [48, 48], "rig": rig, "outline": "#101010",
        "materials": {"body": ["#203040", "#405060", "#6080A0"], "skin": ["#604030", "#A07050", "#E0B090"],
                      "legs": ["#202020", "#404040", "#606060"], "boots": ["#301810", "#503020", "#704830"]},
        "anims": [{"preset": name} for name in PRESETS],
    }


class HumanoidMovementPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outs = {}
        for rig in ("humanoid", "chibi"):
            temp = Path(tempfile.mkdtemp())
            source = temp / "spec.json"
            source.write_text(json.dumps(character(rig)), encoding="utf-8")
            out = temp / "out"
            result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(out)],
                                    capture_output=True, text=True)
            cls.outs[rig] = (result, out)

    def test_renders_every_preset(self):
        for rig, (result, out) in self.outs.items():
            with self.subTest(rig=rig):
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
                for name in PRESETS:
                    self.assertIn(name, manifest["animations"])
                    self.assertTrue((out / f"{name}.png").exists())

    def test_first_frame_rests_on_the_ground_row(self):
        for rig, (result, out) in self.outs.items():
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in PRESETS:
                with self.subTest(rig=rig, preset=name):
                    first = frames_of(out / f"{name}.png")[0]
                    bottom = first.getbbox()[3]  # the art ends on row h-2; the exclusive bbox bottom is h-1
                    self.assertEqual(bottom, first.height - 1)

    def test_jump_lifts_off_and_stays_inside_the_canvas(self):
        for rig, (result, out) in self.outs.items():
            with self.subTest(rig=rig):
                self.assertEqual(result.returncode, 0, result.stderr)
                boxes = [f.getbbox() for f in frames_of(out / "jump.png")]
                h = 48
                highest = min(box[3] for box in boxes)
                self.assertLess(highest, h - 1 - 3, "the jump's highest frame should leave the ground")
                self.assertEqual(boxes[-1][3], h - 1, "the jump should land back on the ground row")
                self.assertTrue(all(box[1] > 0 for box in boxes), f"jump clips the top edge: {boxes}")
                self.assertNotIn("jump frame", result.stderr)


if __name__ == "__main__":
    unittest.main()
