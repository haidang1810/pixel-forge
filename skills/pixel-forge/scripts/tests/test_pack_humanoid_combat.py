"""Renders every preset of the humanoid_combat pack through the rig2d CLI and checks grounding."""
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
PACK = SCRIPTS / "preset_packs" / "humanoid_combat.py"


def pack_presets():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("humanoid_combat_under_test", PACK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sorted(module.ANIMS["humanoid"])


def character(anims):
    return {
        "name": "fighter", "size": [64, 56], "rig": "humanoid", "outline": "#101010", "root_x": 0.4,
        "materials": {"body": ["#203040", "#405060", "#6080A0"], "skin": ["#604030", "#A07050", "#E0B090"],
                      "legs": ["#202020", "#404040", "#606060"], "boots": ["#301810", "#503020", "#704830"],
                      "steel": ["#707880", "#B0B8C0", "#F0F4F8"]},
        "extras": [{"name": "blade", "bone": "weapon_n", "shape": "capsule", "span": [0, 12], "r": [1.0, 0.6],
                    "mat": "steel", "z": 61, "group": "sword"}],
        "style": {"polish": True},
        "anims": anims,
    }


class HumanoidCombatPackTests(unittest.TestCase):
    def test_every_preset_renders_with_feet_on_the_ground(self):
        names = pack_presets()
        self.assertEqual(set(names), {"heavy_attack", "thrust", "combo", "block", "parry", "kick", "shield_bash"})
        spec = character([{"preset": n} for n in names] + [{"preset": "shield_bash", "name": "bash_near", "arm": "n"}])
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            source = temp / "spec.json"
            source.write_text(json.dumps(spec), encoding="utf-8")
            out = temp / "out"
            result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((out / "animation.json").read_text(encoding="utf-8"))
            h = spec["size"][1]
            for name in names + ["bash_near"]:
                with self.subTest(preset=name):
                    self.assertIn(name, manifest["animations"])
                    with Image.open(out / name / "frame-00.png") as image:
                        bbox = image.convert("RGBA").getbbox()
                    self.assertEqual(bbox[3], h - 1, f"{name} first frame bottom {bbox}")

    def test_timing_scale_and_rest_joints(self):
        sys.path.insert(0, str(SCRIPTS))
        import rig_presets
        for name in pack_presets():
            with self.subTest(preset=name):
                frames = rig_presets.anim("humanoid", name)
                slow = rig_presets.anim("humanoid", name, ms=2.0)
                self.assertEqual([round(2 * d) for _, d in frames], [d for _, d in slow])
                fixed = rig_presets.anim("humanoid", name, head=7)
                self.assertTrue(all(p["head"] == 7 for p, _ in fixed))


if __name__ == "__main__":
    unittest.main()
