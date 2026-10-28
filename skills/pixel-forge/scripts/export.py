#!/usr/bin/env python3
"""Export animations for game engines: one packed atlas plus Aseprite, TexturePacker and Godot files.

    python export.py OUT_DIR/ fx.anim.json other.anim.json --out build/ --name hero

Inputs: rig2d or sheet.py output folders (their animation.json; every animation in it), or pixel_art
PREFIX.anim.json files (one animation named after the prefix). Writes into --out:
- NAME.png: every frame packed into one atlas, one row per animation;
- NAME.aseprite.json: Aseprite "array" JSON with per-frame durations and frameTags (Phaser 3:
  this.load.aseprite('hero', 'hero.png', 'hero.aseprite.json'); this.anims.createFromAseprite('hero'));
  pivots and loop flags are in meta.pivots and meta.loops;
- NAME.texturepacker.json: TexturePacker JSON-hash frames with pivots (generic loaders);
- NAME.tres: a Godot 4 SpriteFrames resource (per-frame durations and loop flags) next to NAME.png.
"""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image


def collect(source):
    """[(name, loop, [(image, ms, pivot)])] from one input."""
    path = Path(source)
    if path.is_dir():
        path = path / "animation.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    out = []
    if "animations" in data:
        for name, anim in data["animations"].items():
            sheet = Image.open(path.parent / anim["sheet"]).convert("RGBA")
            out.append((name, anim.get("loop", True), [frame(sheet, f) for f in anim["frames"]]))
    else:
        stem = path.name[:-len(".anim.json")] if path.name.endswith(".anim.json") else path.stem
        sheet = Image.open(path.with_name(stem + ".strip.png")).convert("RGBA")
        out.append((Path(stem).name, data.get("loop", True), [frame(sheet, f) for f in data["frames"]]))
    return out


def frame(sheet, f):
    x, y, w, h = f["rect"]
    return sheet.crop((x, y, x + w, y + h)), int(f.get("ms", 100)), list(f.get("pivot") or [w // 2, h - 1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--out", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    try:
        anims = [a for source in args.inputs for a in collect(source)]
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    names = [a[0] for a in anims]
    if len(set(names)) != len(names):
        print(f"error: animation names repeat across inputs: {names}", file=sys.stderr)
        return 2
    width = max(sum(img.width for img, _, _ in frames) for _, _, frames in anims)
    height = sum(max(img.height for img, _, _ in frames) for _, _, frames in anims)
    atlas = Image.new("RGBA", (width, height))
    placed = []  # (anim name, index, x, y, w, h, ms, pivot)
    y = 0
    for name, _, frames in anims:
        x = 0
        for i, (img, ms, pivot) in enumerate(frames):
            atlas.paste(img, (x, y))
            placed.append((name, i, x, y, img.width, img.height, ms, pivot))
            x += img.width
        y += max(img.height for img, _, _ in frames)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    image_name = f"{args.name}.png"
    atlas.save(out / image_name)

    aseprite_frames, tags, start = [], [], 0
    for name, loop, frames in anims:
        tags.append({"name": name, "from": start, "to": start + len(frames) - 1, "direction": "forward"})
        start += len(frames)
    for name, i, x, y, w, h, ms, pivot in placed:
        aseprite_frames.append({"filename": f"{name}_{i}", "frame": {"x": x, "y": y, "w": w, "h": h},
                                "rotated": False, "trimmed": False,
                                "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h},
                                "sourceSize": {"w": w, "h": h}, "duration": ms})
    meta = {"app": "pixel-forge", "version": "1", "image": image_name, "format": "RGBA8888",
            "size": {"w": atlas.width, "h": atlas.height}, "scale": "1", "frameTags": tags,
            "pivots": {f"{n}_{i}": p for n, i, *_, p in placed}, "loops": {n: l for n, l, _ in anims}}
    (out / f"{args.name}.aseprite.json").write_text(json.dumps({"frames": aseprite_frames, "meta": meta}, indent=1),
                                                   encoding="utf-8")
    tp = {"frames": {f"{name}_{i}": {"frame": {"x": x, "y": y, "w": w, "h": h}, "rotated": False, "trimmed": False,
                                     "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h},
                                     "sourceSize": {"w": w, "h": h},
                                     "pivot": {"x": round(pivot[0] / w, 4), "y": round(pivot[1] / h, 4)},
                                     "duration": ms}
                     for name, i, x, y, w, h, ms, pivot in placed},
          "animations": {name: [f"{name}_{i}" for i in range(len(frames))] for name, _, frames in anims},
          "meta": {"app": "pixel-forge", "image": image_name, "size": {"w": atlas.width, "h": atlas.height}}}
    (out / f"{args.name}.texturepacker.json").write_text(json.dumps(tp, indent=1), encoding="utf-8")

    # Godot 4 SpriteFrames: one AtlasTexture per frame; speed from the shortest frame, durations relative.
    lines, sub = [], 1
    ids = {}
    for name, i, x, y, w, h, ms, pivot in placed:
        ids[(name, i)] = sub
        lines.append(f'[sub_resource type="AtlasTexture" id="AtlasTexture_{sub}"]\natlas = ExtResource("1_atlas")\n'
                     f'region = Rect2({x}, {y}, {w}, {h})\n')
        sub += 1
    anim_entries = []
    for name, loop, frames in anims:
        base = min(ms for _, ms, _ in frames)
        entries = ", ".join('{\n"duration": %s,\n"texture": SubResource("AtlasTexture_%d")\n}'
                            % (round(ms / base, 4), ids[(name, i)]) for i, (_, ms, _) in enumerate(frames))
        anim_entries.append('{\n"frames": [%s],\n"loop": %s,\n"name": &"%s",\n"speed": %s\n}'
                            % (entries, "true" if loop else "false", name, round(1000 / base, 4)))
    tres = (f'[gd_resource type="SpriteFrames" load_steps={sub + 1} format=3]\n\n'
            f'[ext_resource type="Texture2D" path="res://{image_name}" id="1_atlas"]\n\n' + "\n".join(lines) +
            "\n[resource]\nanimations = [" + ", ".join(anim_entries) + "]\n")
    (out / f"{args.name}.tres").write_text(tres, encoding="utf-8")
    print(f"wrote {out / image_name} ({len(placed)} frames, {len(anims)} animations) with .aseprite.json, "
          f".texturepacker.json and .tres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
