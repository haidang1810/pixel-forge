"""Tests for the humanoid_actions preset pack: every preset renders through the rig2d CLI and starts grounded."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
RIG = SCRIPTS / "rig2d.py"
sys.path.insert(0, str(SCRIPTS))

import rig_presets  # noqa: E402  (loads the preset packs)

PRESETS = ["cast", "cast_loop", "shoot_bow", "throw", "wave", "cheer", "sit", "sit_idle", "sleep", "sleep_idle",
           "stunned", "knockback", "taunt"]
LOOPS = {"cast_loop", "wave", "sit_idle", "sleep_idle", "stunned"}


def spec(rig):
    return {
        "name": "test", "size": [48, 48], "rig": rig, "outline": "#101010",
        "materials": {"body": ["#203040", "#405060", "#6080A0"], "skin": ["#604030", "#A07050", "#E0B090"],
                      "legs": ["#202020", "#404040", "#606060"], "boots": ["#301810", "#503020", "#704830"]},
        "extras": [{"name": "rod", "bone": "weapon_n", "shape": "capsule", "span": [-1, 8], "r": 0.8,
                    "mat": "skin", "z": 61, "group": "rod"}],
        "anims": [{"preset": p} for p in PRESETS],
    }


class HumanoidActionsPackTests(unittest.TestCase):
    def test_registered(self):
        for name in PRESETS:
            self.assertIn(name, rig_presets.ANIMS["humanoid"], name)
        self.assertTrue(LOOPS <= rig_presets.LOOPING)

    def test_fixed_joints_reach_every_frame(self):
        for name in PRESETS:
            for pose, ms in rig_presets.anim("humanoid", name, grip_n=118, knee_f=9):
                self.assertEqual((pose["grip_n"], pose["knee_f"]), (118, 9), name)
                self.assertGreater(ms, 0, name)

    def test_timing_ranges(self):
        total = {n: sum(ms for _, ms in rig_presets.anim("humanoid", n)) for n in PRESETS}
        self.assertTrue(500 <= total["cast"] <= 1200, total["cast"])
        self.assertTrue(500 <= total["shoot_bow"] <= 900, total["shoot_bow"])
        self.assertTrue(300 <= total["throw"] <= 500, total["throw"])
        self.assertTrue(200 <= total["knockback"] <= 500, total["knockback"])
        longer = sum(ms for _, ms in rig_presets.anim("humanoid", "cast", charge=900))
        self.assertGreater(longer, total["cast"])

    def test_every_preset_renders_and_starts_grounded(self):
        for rig in ("humanoid", "chibi"):
            with self.subTest(rig=rig):
                temp = Path(tempfile.mkdtemp())
                source = temp / "spec.json"
                source.write_text(json.dumps(spec(rig)), encoding="utf-8")
                out = temp / "out"
                result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(out), "--scale", "2"],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
                for name in PRESETS:
                    self.assertIn(name, manifest["animations"])
                    with Image.open(out / name / "frame-00.png") as image:
                        bbox = image.convert("RGBA").getbbox()
                    self.assertIsNotNone(bbox, name)
                    self.assertEqual(bbox[3], 48 - 1, f"{rig} {name} first frame bottom {bbox}")


if __name__ == "__main__":
    unittest.main()
