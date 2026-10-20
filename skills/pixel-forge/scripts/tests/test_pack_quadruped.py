"""Renders every preset of the quadruped preset pack through the rig2d CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
RIG = SCRIPTS / "rig2d.py"
PRESETS = ["trot", "stalk", "sniff", "howl", "sit", "sit_idle", "lie_down", "sleep",
           "bite_combo", "charge", "rear_up", "shake", "leap"]


def spec():
    return {
        "name": "pack-quad", "size": [64, 48], "rig": "quadruped", "root_x": 0.32, "outline": "#15131C",
        "materials": {"fur": ["#343A54", "#5B6584", "#838DAF"], "paw": ["#1F2130", "#33374A", "#4A5068"]},
        "anims": [{"preset": name} for name in PRESETS],
    }


class QuadrupedPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = Path(tempfile.mkdtemp())
        source = temp / "spec.json"
        source.write_text(json.dumps(spec()), encoding="utf-8")
        cls.out = temp / "out"
        cls.result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(cls.out)],
                                    capture_output=True, text=True)

    def test_cli_succeeds(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_every_preset_starts_on_the_ground(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        manifest = json.loads((self.out / "animation.json").read_text(encoding="utf-8"))
        for name in PRESETS:
            with self.subTest(preset=name):
                self.assertIn(name, manifest["animations"])
                with Image.open(self.out / name / "frame-00.png") as image:
                    box = image.convert("RGBA").getbbox()
                    self.assertIsNotNone(box)
                    self.assertEqual(box[3], image.height - 1, f"{name} first frame bottom {box}")

    def test_rest_joints_reach_every_frame(self):
        sys.path.insert(0, str(SCRIPTS))
        import rig_presets
        for name in PRESETS:
            with self.subTest(preset=name):
                frames = rig_presets.anim("quadruped", name, tail=33)
                self.assertTrue(frames)
                self.assertTrue(all(pose["tail"] == 33 for pose, _ in frames))


if __name__ == "__main__":
    unittest.main()
