"""Render every preset of the slime_float pack through the rig2d CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
RIG = SCRIPTS / "rig2d.py"
EXAMPLES = SCRIPTS.parents[2] / "examples" / "characters"

SLIME = ["bounce_slam", "wobble", "spit", "split", "melt_in", "rise", "crawl"]
GHOST = ["float_attack", "vanish", "appear", "haunt"]


def opened(path):
    with Image.open(path) as image:
        return image.convert("RGBA")


def render(example, presets):
    spec = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
    spec["anims"] = [{"preset": p} for p in presets]
    temp = Path(tempfile.mkdtemp())
    source = temp / "spec.json"
    source.write_text(json.dumps(spec), encoding="utf-8")
    out = temp / "out"
    result = subprocess.run([sys.executable, str(RIG), str(source), "--out", str(out)],
                            capture_output=True, text=True)
    return result, out, spec


def frames(out, anim):
    return sorted((out / anim).glob("frame-*.png"))


class SlimeFloatPackTests(unittest.TestCase):
    def test_slime_presets_render_and_start_on_the_ground(self):
        result, out, spec = render("slime.json", SLIME)
        self.assertEqual(result.returncode, 0, result.stderr)
        h = spec["size"][1]
        for anim in SLIME:
            first = frames(out, anim)
            self.assertTrue(first, anim)
            box = opened(first[0]).getbbox()
            self.assertEqual(box[3], h - 1, f"{anim} should start on the ground row")

    def test_slime_airborne_and_squashed_frames_stay_in_the_canvas(self):
        result, out, spec = render("slime.json", ["bounce_slam", "melt_in"])
        self.assertEqual(result.returncode, 0, result.stderr)
        w, h = spec["size"]
        for anim in ("bounce_slam", "melt_in"):
            for path in frames(out, anim):
                x0, y0, x1, y1 = opened(path).getbbox()
                self.assertTrue(x0 > 0 and y0 > 0 and x1 < w, f"{anim} {path.name} touches the edge")

    def test_ghost_presets_render_and_fade(self):
        for example in ("ghost.json", "ghost-vector.json"):
            result, out, _ = render(example, GHOST)
            self.assertEqual(result.returncode, 0, f"{example}: {result.stderr}")
            vanish, appear = frames(out, "vanish"), frames(out, "appear")
            self.assertIsNone(opened(vanish[-1]).getbbox(), f"{example}: vanish should end invisible")
            self.assertIsNotNone(opened(vanish[0]).getbbox())
            self.assertIsNone(opened(appear[0]).getbbox(), f"{example}: appear should start invisible")
            self.assertIsNotNone(opened(appear[-1]).getbbox())
            for anim in ("float_attack", "haunt"):
                self.assertTrue(frames(out, anim), f"{example}: {anim} has no frames")


if __name__ == "__main__":
    unittest.main()
