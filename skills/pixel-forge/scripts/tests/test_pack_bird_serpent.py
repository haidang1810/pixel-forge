"""Render every preset of the bird_serpent pack through the rig2d CLI and check grounding."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
RIG = SCRIPTS / "rig2d.py"
EXAMPLES = SCRIPTS.parents[2] / "examples" / "characters"

BIRD = {"glide": "air", "takeoff": "ground", "land": "air_start", "dive": "air", "peck_ground": "ground",
        "screech": "ground"}
SERPENT = {"coil": "ground", "rear_up": "ground", "spit": "ground", "hiss": "ground", "sidewind": "ground"}


def bbox(path):
    with Image.open(path) as image:
        return image.convert("RGBA").getbbox()


class BirdSerpentPackTests(unittest.TestCase):
    def render(self, example, anims):
        spec = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
        spec["anims"] = [{"preset": name} for name in anims]
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        out = tmp / "out"
        result = subprocess.run([sys.executable, str(RIG), str(tmp / "spec.json"), "--out", str(out), "--scale", "2"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return spec, out

    def check(self, spec, out, kinds):
        h = spec["size"][1]
        for name, kind in kinds.items():
            frames = sorted((out / name).glob("frame-*.png"))
            self.assertGreater(len(frames), 1, name)
            for frame in frames:
                box = bbox(frame)
                self.assertIsNotNone(box, f"{name} {frame.name} is empty")
                self.assertGreater(box[1], 0, f"{name} {frame.name} touches the top edge {box}")
            first = bbox(frames[0])
            if kind == "ground":
                self.assertEqual(first[3], h - 1, f"{name} first frame not on the ground row {first}")
            elif kind == "air_start":
                self.assertLess(first[3], h - 1, f"{name} should start airborne {first}")
                self.assertEqual(bbox(frames[-1])[3], h - 1, f"{name} should end on the ground")
            else:
                for frame in frames:
                    self.assertLess(bbox(frame)[3], h - 1, f"{name} {frame.name} touches the ground")

    def test_bird_presets(self):
        spec, out = self.render("raven.json", BIRD)
        self.check(spec, out, BIRD)
        last = bbox(sorted((out / "takeoff").glob("frame-*.png"))[-1])
        self.assertLess(last[3], spec["size"][1] - 1, "takeoff should end airborne")

    def test_serpent_presets(self):
        spec, out = self.render("serpent.json", SERPENT)
        self.check(spec, out, SERPENT)


if __name__ == "__main__":
    unittest.main()
