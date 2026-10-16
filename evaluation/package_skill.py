"""Verify the actual demo pixels, package the skill, and install a new personal copy."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile
from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
SKILL = PROJECT / "skills/pixel-forge"
INSTALL = Path("C:/Users/dangh/.codex/skills/pixel-forge")
OUTPUT = PROJECT / "output/pixel-art-json-demo"
ASSETS = OUTPUT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("pixel_art", SKILL / "scripts/pixel_art.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

sources = [(name, PROJECT / "evaluation/items" / name) for name in ("jade-sword", "ember-potion", "treasure-chest")]
sources.append(("forest-spirit", PROJECT / "evaluation/with-skill/forest-spirit-v2"))
verified = []
for name, prefix in sources:
    document = engine.read_json(str(prefix) + ".json")
    expected, report = engine.render_document(document)
    with Image.open(str(prefix) + ".png") as actual:
        assert actual.mode == "RGBA" and actual.size == (32, 32), name
        assert actual.tobytes() == expected.tobytes(), name + ": PNG differs from source JSON"
        assert actual.getchannel("A").getextrema() == (0, 255), name
    for suffix in (".json", ".png", ".preview.png", ".grid.png", ".report.json"):
        shutil.copy2(str(prefix) + suffix, ASSETS / (name + suffix))
    verified.append({"asset": name, "size": report["size"], "opaque_pixels": report["opaque_pixels"], "opaque_colors": sum(1 for color in report["colors"] if color.endswith("FF")), "matches_json": True})

files = sorted(path for path in SKILL.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
assert not any(path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp") for path in files), "The skill must not bundle reference art"
assert not INSTALL.exists(), "An installed skill already exists; inspect it before updating"
shutil.copytree(SKILL, INSTALL, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
for path in files:
    installed = INSTALL / path.relative_to(SKILL)
    assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(installed.read_bytes()).digest()

with zipfile.ZipFile(OUTPUT / "pixel-forge.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, Path("pixel-forge") / path.relative_to(SKILL))
with zipfile.ZipFile(OUTPUT / "demo-assets.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(ASSETS.iterdir()):
        archive.write(path, Path("assets") / path.name)
    archive.write(OUTPUT / "preview.png", "preview.png")

result = {"installed_skill": str(INSTALL), "packaged_files": len(files), "bundled_reference_images": 0, "verified_assets": verified}
(OUTPUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
