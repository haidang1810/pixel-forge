---
name: pixel-forge
description: Create or revise 2D pixel game assets by authoring editable JSON and rendering with code, without image-generation models. Use when the user requests procedural pixel art, exact pixel control, or text-to-pixel assets without image generation. Covers static icons, items and tiles, and side-view characters and mobs (humanoid, chibi, four-legged) with full mob animation sets (idle, walk, run, float, attack, hurt, die) exported as sprite sheets with pivots.
---

# Pixel Forge

Create original pixel art through structured drawing data and a deterministic renderer. No reference artwork is bundled or required. This skill supplies drawing instructions and tools, not a trained art model or a promise of professional quality.

## Setup

Read [references/format.md](references/format.md) before authoring static JSON. For a character, mob, or any animation, also read [references/rig.md](references/rig.md). Resolve `scripts/pixel_art.py` relative to this skill's directory. It needs Python 3.10+ and Pillow 9.1+. Prefer an existing Python with Pillow; in Codex desktop, `load_workspace_dependencies` can locate the bundled interpreter. On Windows use PowerShell `&` before a quoted interpreter path. If dependencies are absent, install `scripts/requirements.txt` into a task-local virtual environment.

## Authoring

1. Infer a small, concrete brief: subject, native size, perspective, distinctive features, light direction, and intended style. Respect supplied dimensions. Otherwise start around 32×32 for a character or 16–32 pixels for an item; state the assumption and proceed. For a set, share palette roles, scale, lighting, and outline treatment.
2. Plan the silhouette and placement of defining parts before detail. Name layers by their role. For a three-quarter pose, express direction in the silhouette, face placement, and near/far feature sizes. Make each distinctive feature readable through shape and structural pixels; color alone may not distinguish it from a different object.
3. Choose a compact palette with distinct outline, shadow, body, light, and accent roles; roughly 6–12 opaque colors is a useful starting point. Use colored shadows if they support the chosen style. Keep adjacent important parts distinguishable in value.
4. Write source JSON using row strings for precise clusters, polygons for larger silhouettes, rectangles for blocks, and one-pixel lines or point edits for finishing. Primitives are a scaffold: refine generic ellipses and rectangles into deliberate pixel clusters. Use small coherent highlight regions rather than scattering bright pixels. Keep intentional negative space between limbs and props.
5. Render early once the silhouette and major colors are present. Inspect the native image and enlarged preview with an image-viewing tool. Check recognizability, perspective, silhouette, contrast, and requested details before decorative shading. The report checks pixels, not beauty.
6. Make specific local corrections using named-layer patches or source edits. A useful correction names the visible issue, coordinates/part, and expected effect. Inspect the revised render. Start with at most two correction rounds; keep prior revisions and extend only for a concrete unresolved request. If visual inspection is unavailable, disclose that limitation.

## Characters and animation

Use `scripts/rig2d.py` for side-view characters and animated sprites; do not hand-draw every frame.

1. Pick the rig (`humanoid`, `chibi`, `quadruped`) and canvas, leaving room for reach (weapons, tails, gallop). Give the character its own posture with `pose_offset` and its identity through distinctive parts: silhouette features, accent colors, a readable face.
2. Choose the quality path and say which one:
   - **Vector parts**: shapes on bones, auto-shaded. This is quick and clean, good for prototypes and simple mobs.
   - **Cutout layers**: pixel regions painted once in the rest pose with `draw` ops, then split onto the bones automatically. This is the path toward final art.
3. Render. Inspect `contact.png` and at least one enlarged key frame per animation (the extremes of a stride or a swing). Check silhouette, readability, limbs tangling, parts detaching, and edge clipping.
4. Correct the parts or the posture first. Only then fix the key frames by hand with `touchups`. Keep at most two correction rounds unless a concrete issue remains.
5. Deliver the sheets, `animation.json`, a preview GIF made with `showcase.py`, and the spec. State the frame size, frame counts, timings, and the visible limitations.

## Tool loop

Here `python` means the interpreter found during setup; `SKILL_DIR` means this skill's actual absolute folder.

```text
python SKILL_DIR/scripts/pixel_art.py render sprite.json --out sprite-v1 --scale 12 --grid
python SKILL_DIR/scripts/pixel_art.py patch sprite.json edits.json --output sprite-v2.json
python SKILL_DIR/scripts/pixel_art.py render sprite-v2.json --out sprite-v2 --scale 12 --grid
```

Write outputs in the user's requested folder, otherwise `output/pixel-art/<asset-name>/` in the working project. Inspect `*.preview.png`; use `*.grid.png` to locate individual pixels. Grid coordinates are canvas coordinates; subtract a layer's origin when preparing local edits.

## Delivery and boundaries

- Deliver editable JSON, native transparent PNG, and an enlarged preview. Show the preview inline and link the source and native asset. State dimensions, actual changes, and visible limitations briefly.
- Render through the bundled code. Do not invoke image-generation models or obtain reference artwork unless the user changes that constraint. User-supplied references may be inspected when requested.
- Keep native export unscaled, without grid, interpolation, or baked checkerboard. Checkerboard and coordinate labels belong only in previews.
- Pixels are opaque or transparent only. Static images use `pixel_art.py`. Animation uses `rig2d.py` and is limited to the side-view rigs and presets in `references/rig.md`. Turnarounds, top-down directions, new motion types without a new preset, blended transparency and automatic artistic scoring are not implemented, so address those requests explicitly.
- Be candid about quality. Generated characters reach clean indie quality, especially with cutout layers and touch-ups, but are not guaranteed to match hand-made commercial pixel art.
