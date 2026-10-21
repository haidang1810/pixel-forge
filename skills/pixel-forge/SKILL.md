---
name: pixel-forge
description: Create or revise 2D pixel game assets by authoring editable JSON and rendering with code, without image-generation models. Use when the user requests procedural pixel art, exact pixel control, or text-to-pixel assets without image generation. Covers static icons, items and tiles, and side-view characters and mobs (humanoid, chibi, four-legged, bird, serpent, slime) with about 90 animation presets (locomotion, jumps, combat, casting, emotes, sitting and sleeping, hurt and death), body types, motion personality and render styles, exported as sprite sheets with pivots.
---

# Pixel Forge

Create original pixel art through structured drawing data and a deterministic renderer. No reference artwork is bundled or required. This skill supplies drawing instructions and tools, not a trained art model or a promise of professional quality.

## Setup

Read [references/format.md](references/format.md) before authoring static JSON. For a character, mob, or any animation, also read [references/rig.md](references/rig.md). Resolve `scripts/pixel_art.py` relative to this skill's directory. It needs Python 3.10+ and Pillow 9.1+. Prefer an existing Python with Pillow; in Codex desktop, `load_workspace_dependencies` can locate the bundled interpreter. On Windows use PowerShell `&` before a quoted interpreter path. If dependencies are absent, install `scripts/requirements.txt` into a task-local virtual environment.

## Make it this user's asset

Ten users asking for "an orc" should not get ten copies of the same orc. Read [references/design.md](references/design.md) for the shape language, the role table, proportions by sprite size and color rules. Before drawing anything:

1. Write down 2–3 identity traits taken from the user's words, or inferred from their game's genre and tone. Each trait must change something visible: silhouette, proportions, palette, accessories, how it moves.
2. When the request is short or leaves the look open, do not invent the traits from habit; models asked for the same creature pick the same traits every time. Run `python SKILL_DIR/scripts/ideas.py --role ROLE --rig RIG` (roles: hero, villain, brute, scout, mage, healer, critter, mob, elite, undead, beast). It draws from the operating system's randomness and prints directions with a dominant shape, a signature feature, base and accent colors, a build, a temperament with matching `motion` values and a fresh `seed`, and a style. Adapt one direction to the subject; drop any part that contradicts the user. Never reuse a seed from an example or a previous character.
3. Turn the traits into explicit choices instead of defaults, and state them in one line:
   - shape and colors: silhouette features, a palette built around the traits, and accent props;
   - for characters, also `build` (body type: `bulky`, `slim`, `tall`, `short`, `child`, `elderly`, `brute`), `motion` (`weight`, `energy`, `exaggeration`, `follow`, and the rolled `seed` so two creatures of one kind never move identically), `style` (outline, number of shades, dither, light direction) and posture (`pose_offset`);
   - for a set of assets, one bundled `palette_kit` (`pico-8`, `dawnbringer-16`, `dawnbringer-32`, `aap-64`, `sweetie-16`, `endesga-32`) shared by every asset, with materials taken from its named ramps and `style.snap` keeping every pixel inside it.
4. When the brief leaves room, offer 2–3 short variant directions, or render small variants side by side (for example a different `build`, `motion` or palette), and let the user pick before polishing one. Skip this when the user gave a precise spec.

For a set of assets for one game, keep the style, palette roles and scale shared across the set, and vary identity within it.

## Authoring

1. Infer a small, concrete brief: subject, native size, perspective, distinctive features, light direction, and intended style. Respect supplied dimensions. Otherwise start around 32×32 for a character or 16–32 pixels for an item; state the assumption and proceed. For a set, share palette roles, scale, lighting, and outline treatment.
2. Plan the silhouette and placement of defining parts before detail. Name layers by their role. For a three-quarter pose, express direction in the silhouette, face placement, and near/far feature sizes. Make each distinctive feature readable through shape and structural pixels; color alone may not distinguish it from a different object.
3. Choose a compact palette with distinct outline, shadow, body, light, and accent roles; roughly 6–12 opaque colors is a useful starting point. Use colored shadows if they support the chosen style. Keep adjacent important parts distinguishable in value.
4. Write source JSON using row strings for precise clusters, polygons for larger silhouettes, rectangles for blocks, and one-pixel lines or point edits for finishing. Primitives are a scaffold: refine generic ellipses and rectangles into deliberate pixel clusters. Use small coherent highlight regions rather than scattering bright pixels. Keep intentional negative space between limbs and props.
5. Render early once the silhouette and major colors are present. Inspect the native image and enlarged preview with an image-viewing tool. Check recognizability, perspective, silhouette, contrast, and requested details before decorative shading. The report checks pixels, not beauty.
6. Make specific local corrections using named-layer patches or source edits. A useful correction names the visible issue, coordinates/part, and expected effect. Inspect the revised render. Plan on three to five correction rounds, each fixing named problems; keep prior revisions, and stop when no concrete issue remains. If visual inspection is unavailable, disclose that limitation.

## Items, icons and props

Items, icons, tiles and props use `pixel_art.py` only; skip `rig.md` and `design.md` beyond its color rules.
- `python SKILL_DIR/scripts/palette_tools.py --kit endesga-32` prints a ready document `palette` (with `"o"` as the kit's outline) and the kit's named ramps as symbol strings, so a set of items shares one palette.
- The document field `"outline": "o"` draws a one-pixel outline around everything after the layers are composited, so layers need not paint it.
- For an animated prop (a chest opening, a torch, a coin spin), draw one document per frame, then pack them: `python SKILL_DIR/scripts/sheet.py open-0.json open-1.json open-2.json --ms 200 80 400 --name open --out OUT_DIR --once`. It writes a sheet, frames, `animation.json` in the rig schema, a preview GIF and `contact.png`.
- `python SKILL_DIR/scripts/lint.py` accepts a single PNG or a `sheet.py` output folder.

## Characters and animation

Use `scripts/rig2d.py` for side-view characters and animated sprites; do not hand-draw every frame.

1. Pick the rig and canvas, leaving room for reach (weapons, tails, gallop, wings). The rigs are `humanoid`, `chibi`, `quadruped`, `bird`, `serpent` and `slime`. Apply the identity choices above: `build`, `motion`, `style`, `pose_offset`, and distinctive parts such as silhouette features, accent colors and a readable face. Each rig's default parts and the materials they need are in the *Default parts* table of `rig.md`; weapons are extras on the `weapon_n` bone.
   - Presets: each rig has `idle`, a move, `attack`, `hurt` and `die`, and the preset packs add about 70 more (`run`, `jump`, `cast`, `block`, `sit`, `sleep`, `howl`, `glide`, `spit` and others). The full list per rig is under *Preset packs* in `rig.md`. Chained poses come in pairs: play `sit` once, then loop `sit_idle`; a humanoid plays `sleep` once, then loops `sleep_idle`; a quadruped plays `lie_down` once, then loops `sleep`.
2. Choose the quality path and say which one:
   - **Vector parts**: shapes on bones, auto-shaded. This is quick and clean, good for prototypes and simple mobs.
   - **Cutout layers**: pixel regions painted once in the rest pose with `draw` ops, then split onto the bones automatically. This is the path toward final art.
3. Build colors from base colors with hue-shifted ramps (`{"base": "#RRGGBB"}` materials or `palette_gen`) rather than picking shades by hand. For final art, turn on `"style": {"polish": true}` (cutout characters: `"style": {"polish": {"aa": true, "smear": true}}`), add `texture` to parts where the material calls for it (fur, scales, cloth, metal), and give `motion` some `follow`.
4. Render. Inspect `contact.png` and at least one enlarged key frame per animation (the extremes of a stride or a swing). Check silhouette, readability, limbs tangling, parts detaching, and edge clipping. Run `scripts/lint.py OUT_DIR` and fix the findings that are real problems.
5. Correct the parts or the posture first. Only then fix the key frames by hand with `touchups` (frame numbers are 0-based, as in the file names). Expect three to five rounds; stop when no concrete issue remains. Put one-pixel eyes and highlights in `stamps`, which are never rotated, even on cutout characters: single pixels painted into a rotating layer can vanish. An anim entry can carry its own `stamps` (closed eyes while sleeping) and `z` (draw order for that animation).
6. Deliver the sheets, `animation.json`, a preview GIF made with `showcase.py`, and the spec. State the frame size, frame counts, timings, and the visible limitations.

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
