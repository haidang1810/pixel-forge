"""Behavior tests: wrong pixel placement, data loss, and invalid-input acceptance."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "pixel_art.py"


def sample():
    return {
        "version": 1,
        "size": [4, 3],
        "palette": {".": "#00000000", "r": "#FF0000", "b": "#0000FF"},
        "layers": [
            {"name": "base", "rows": ["rrrr", "r..r", "rrrr"]},
            {"name": "detail", "origin": [1, 1], "rows": ["b."]},
        ],
    }


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.is_file():
            cls.engine = None
            return
        spec = importlib.util.spec_from_file_location("pixel_art", SCRIPT)
        cls.engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.engine)

    def setUp(self):
        self.assertIsNotNone(self.engine, "pixel_art.py renderer has not been implemented")

    def test_layers_preserve_native_rgba_and_transparent_holes(self):
        image, report = self.engine.render_document(sample())
        self.assertEqual(image.size, (4, 3))
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(image.getpixel((1, 1)), (0, 0, 255, 255))
        self.assertEqual(image.getpixel((2, 1)), (0, 0, 0, 0))
        self.assertEqual(report["opaque_pixels"], 11)
        self.assertEqual(report["bbox"], [0, 0, 4, 3])

    def test_rect_size_and_operation_order(self):
        doc = sample()
        doc["layers"] = [{"name": "shapes", "ops": [
            {"op": "rect", "xy": [1, 0], "size": [2, 2], "color": "r"},
            {"op": "pixels", "points": [[2, 1]], "color": "b"},
        ]}]
        image, _ = self.engine.render_document(doc)
        self.assertEqual(image.getpixel((1, 0)), (255, 0, 0, 255))
        self.assertEqual(image.getpixel((2, 1)), (0, 0, 255, 255))
        self.assertEqual(image.getpixel((3, 1)), (0, 0, 0, 0))
        self.assertEqual(image.getpixel((1, 2)), (0, 0, 0, 0))

    def test_primitives_rasterize_without_new_colors(self):
        doc = sample()
        doc["size"] = [8, 8]
        doc["layers"] = [{"name": "shapes", "ops": [
            {"op": "polygon", "points": [[0, 0], [3, 0], [0, 3]], "color": "r"},
            {"op": "ellipse", "xy": [4, 4], "size": [3, 3], "color": "b"},
            {"op": "line", "points": [[7, 0], [7, 3]], "color": "b"},
        ]}]
        image, _ = self.engine.render_document(doc)
        self.assertEqual(image.getpixel((1, 1)), (255, 0, 0, 255))
        self.assertEqual(image.getpixel((5, 5)), (0, 0, 255, 255))
        self.assertEqual(image.getpixel((7, 2)), (0, 0, 255, 255))
        self.assertEqual(image.getpixel((3, 3)), (0, 0, 0, 0))
        self.assertTrue({image.getpixel((x, y)) for x in range(8) for y in range(8)} <= {(255, 0, 0, 255), (0, 0, 255, 255), (0, 0, 0, 0)})

    def test_invalid_art_is_rejected_instead_of_silently_clipped(self):
        mutations = [
            lambda d: d["layers"][0].update(rows=["rrrr", "rr", "rrrr"]),
            lambda d: d["layers"][0].update(rows=["rrxr"]),
            lambda d: d["layers"][1].update(origin=[4, 1]),
            lambda d: d["layers"][1].update(name="base"),
            lambda d: d["palette"].update(r="#FF000080"),
            lambda d: d.update(size=[4.0, 3]),
            lambda d: d["layers"][1].update(ops=[{"op": "pixels", "points": [[9, 0]], "color": "r"}]),
            lambda d: d["layers"][1].update(ops=[{"op": "rect", "xy": [0, 0], "size": [0, 2], "color": "r"}]),
            lambda d: d["layers"][1].update(opps=[]),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                doc = sample()
                mutate(doc)
                with self.assertRaises(ValueError):
                    self.engine.render_document(doc)

    def test_patch_is_layer_local_and_does_not_mutate_source(self):
        doc = sample()
        before = copy.deepcopy(doc)
        patch = {"edits": [{"layer": "detail", "op": "pixels", "points": [[0, 0]], "color": "."}]}
        updated = self.engine.patch_document(doc, patch)
        image, _ = self.engine.render_document(updated)
        self.assertEqual(doc, before)
        self.assertEqual(updated["layers"][0], before["layers"][0])
        self.assertEqual(image.getpixel((1, 1)), (0, 0, 0, 0))
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0, 255))

    def test_hidden_layers_do_not_contribute_but_are_validated(self):
        doc = sample()
        doc["layers"][1]["visible"] = False
        image, _ = self.engine.render_document(doc)
        self.assertEqual(image.getpixel((1, 1)), (0, 0, 0, 0))
        doc["layers"][1]["rows"] = ["x"]
        with self.assertRaises(ValueError):
            self.engine.render_document(doc)

    def test_patch_rejects_unknown_layer_and_unknown_palette_color(self):
        for edit in [
            {"layer": "missing", "op": "pixels", "points": [[0, 0]], "color": "r"},
            {"layer": "detail", "op": "pixels", "points": [[0, 0]], "color": "x"},
        ]:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.engine.patch_document(sample(), {"edits": [edit]})

    def test_cli_exports_png_and_keeps_source_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "art.json"
            source.write_text(json.dumps(sample()), encoding="utf-8")
            original = source.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "render", str(source), "--out", str(root / "art"), "--scale", "4", "--grid"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_bytes(), original)
            with Image.open(root / "art.png") as image:
                self.assertEqual(image.size, (4, 3))
                self.assertEqual(image.getpixel((1, 1)), (0, 0, 255, 255))
            with Image.open(root / "art.preview.png") as image:
                self.assertEqual(image.size, (16, 12))
                self.assertEqual(image.getpixel((4, 4)), (0, 0, 255, 255))
            self.assertTrue((root / "art.grid.png").is_file())
            report = json.loads((root / "art.report.json").read_text())
            self.assertEqual(report["size"], [4, 3])

    def test_cli_invalid_input_writes_no_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "bad.json"
            source.write_text('{"version": 1}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "render", str(source), "--out", str(root / "bad")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error", result.stderr.lower())
            self.assertFalse((root / "bad.png").exists())

    def test_erasing_upper_layer_reveals_lower_layer(self):
        doc = sample()
        doc["layers"][1] = {"name": "detail", "rows": ["b"]}
        updated = self.engine.patch_document(doc, {"edits": [
            {"layer": "detail", "op": "pixels", "points": [[0, 0]], "color": "."}
        ]})
        image, _ = self.engine.render_document(updated)
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0, 255))

    def test_cli_patch_recolors_and_renders_new_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, edits, target = [root / name for name in ("art.json", "edit.json", "v2.json")]
            source.write_text(json.dumps(sample()), encoding="utf-8")
            edits.write_text(json.dumps({"palette": {"b": "#00FF00"}}), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "patch", str(source), str(edits), "--output", str(target)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            image, _ = self.engine.render_document(json.loads(target.read_text()))
            self.assertEqual(image.getpixel((1, 1)), (0, 255, 0, 255))
            self.assertEqual(json.loads(source.read_text())["palette"]["b"], "#0000FF")
            result = subprocess.run([sys.executable, str(SCRIPT), "patch", str(source), str(edits), "--output", str(source)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(source.read_text())["palette"]["b"], "#0000FF")

    def test_cli_protects_source_from_report_path_collision(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "art.report.json"
            source.write_text(json.dumps(sample()), encoding="utf-8")
            before = source.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "render", str(source), "--out", str(root / "art")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse((root / "art.png").exists())

    def test_duplicate_json_keys_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "duplicate.json"
            source.write_text('{"version": 1, "version": 2}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "validate", str(source)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate", result.stderr)

    def test_nonfinite_json_is_rejected(self):
        for number in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "nonfinite.json"
                text = json.dumps({**sample(), "meta": {"value": "NUMBER"}}).replace('"NUMBER"', number)
                source.write_text(text, encoding="utf-8")
                result = subprocess.run([sys.executable, str(SCRIPT), "validate", str(source)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)

    def test_grid_at_scale_one_still_shows_art(self):
        image, _ = self.engine.render_document(sample())
        grid = self.engine.preview(image, 1, grid=True)
        self.assertEqual(grid.getpixel((26, 26)), (255, 0, 0))

    def test_rerender_refreshes_existing_grid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "art.json"
            source.write_text(json.dumps(sample()), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), "render", str(source), "--out", str(root / "art"), "--scale", "4"]
            subprocess.run(command + ["--grid"], capture_output=True, check=True)
            doc = sample()
            doc["palette"]["r"] = "#00FF00"
            source.write_text(json.dumps(doc), encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(root / "art.grid.png") as image:
                self.assertEqual(image.getpixel((26, 26)), (0, 255, 0))

    def test_hardlink_output_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, alias, edits = [root / name for name in ("source.json", "alias.json", "edits.json")]
            source.write_text(json.dumps(sample()), encoding="utf-8")
            try:
                os.link(source, alias)
            except OSError as error:
                self.skipTest(f"Filesystem does not support hard links: {error}")
            before = source.read_bytes()
            edits.write_text(json.dumps({"palette": {"r": "#00FF00"}}), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "patch", str(source), str(edits), "--output", str(alias)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
