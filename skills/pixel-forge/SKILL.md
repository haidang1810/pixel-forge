---
name: pixel-forge
description: Create or revise 2D pixel game assets by authoring editable JSON and rendering with code, without image-generation models. Use when the user requests procedural pixel art, exact pixel control, or text-to-pixel assets without image generation. Covers static icons, items and tiles, and side-view characters and mobs (humanoid, chibi, four-legged, bird, serpent, slime) with about 90 animation presets (locomotion, jumps, combat, casting, emotes, sitting and sleeping, hurt and death), body types, motion personality and render styles, exported as sprite sheets with pivots.
---

# Pixel Forge

Create original pixel art through structured drawing data and a deterministic renderer. No reference artwork is bundled or required. This skill supplies drawing instructions and tools, not a trained art model or a promise of professional quality.

## Setup

Read [references/format.md](references/format.md) before authoring static JSON, and [references/craft.md](references/craft.md) for the subject you are drawing (value and light, faces, hands, props, fire and smoke, animation, scenes, the generated-art tells to avoid). For a character, mob, or any animation, also read [references/rig.md](references/rig.md). Resolve `scripts/pixel_art.py` relative to this skill's directory. It needs Python 3.10+ and Pillow 9.1+. Prefer an existing Python with Pillow; in Codex desktop, `load_workspace_dependencies` can locate the bundled interpreter. On Windows use PowerShell `&` before a quoted interpreter path. If dependencies are absent, install `scripts/requirements.txt` into a task-local virtual environment.

## Make it this user's asset

Ten users asking for "an orc" should not get ten copies of the same orc. Read [references/design.md](references/design.md) for the shape language, the role table, proportions by sprite size and color rules. Before drawing anything:

1. Write down 2–3 identity traits taken from the user's words, or inferred from their game's genre and tone. Each trait must change something visible: silhouette, proportions, palette, accessories, how it moves.
2. When the request is short or leaves the look open, do not invent the traits from habit; models asked for the same creature pick the same traits every time. Run `python SKILL_DIR/scripts/ideas.py --role ROLE --rig RIG` (roles: hero, villain, brute, scout, mage, healer, critter, mob, elite, undead, beast; and item, prop, vfx for objects and effects). It draws from the operating system's randomness and prints directions with a dominant shape, a signature feature, base and accent colors, a build, a temperament with matching `motion` values and a fresh `seed`, and a style. Adapt one direction to the subject; drop any part that contradicts the user. Never reuse a seed from an example or a previous character.
3. Turn the traits into explicit choices instead of defaults, and state them in one line:
   - shape and colors: silhouette features, a palette built around the traits, and accent props;
   - for characters, also `build` (body type: `bulky`, `slim`, `tall`, `short`, `child`, `elderly`, `brute`), `motion` (`weight`, `energy`, `exaggeration`, `follow`, and the rolled `seed` so two creatures of one kind never move identically), `style` (outline, number of shades, dither, light direction) and posture (`pose_offset`);
   - for a set of assets, one bundled `palette_kit` (`pico-8`, `dawnbringer-16`, `dawnbringer-32`, `aap-64`, `sweetie-16`, `endesga-32`) shared by every asset, with materials taken from its named ramps; characters add `style.snap` to keep every pixel inside it, and static documents simply use the palette that `palette_tools.py --kit` prints.
4. When the brief leaves room, offer 2–3 short variant directions, or render small variants side by side (for example a different `build`, `motion` or palette), and let the user pick before polishing one. Skip this when the user gave a precise spec.

For a set of assets for one game, keep the style, palette roles and scale shared across the set, and vary identity within it.

## Authoring

1. Infer a small, concrete brief: subject, native size, perspective, distinctive features, light direction, and intended style. Respect supplied dimensions. Otherwise start around 32×32 for a character or 16–32 pixels for an item; state the assumption and proceed. For a set, share palette roles, scale, lighting, and outline treatment.
2. Plan the silhouette and placement of defining parts before detail. Name layers by their role. For a three-quarter pose, express direction in the silhouette, face placement, and near/far feature sizes. Make each distinctive feature readable through shape and structural pixels; color alone may not distinguish it from a different object.
3. Choose a compact palette with distinct outline, shadow, body, light, and accent roles; roughly 6–12 opaque colors is a useful starting point. Use colored shadows if they support the chosen style. Keep adjacent important parts distinguishable in value.
4. Write source JSON using row strings for precise clusters, polygons for larger silhouettes, rectangles for blocks, and one-pixel lines or point edits for finishing. Primitives are a scaffold: refine generic ellipses and rectangles into deliberate pixel clusters. Use small coherent highlight regions rather than scattering bright pixels. Keep intentional negative space between limbs and props.
5. Render early once the silhouette and major colors are present. Inspect the native image and enlarged preview with an image-viewing tool. Check recognizability, perspective, silhouette, contrast, and requested details before decorative shading. The report checks pixels, not beauty.
6. Make specific local corrections using named-layer patches or source edits. A useful correction names the visible issue, coordinates/part, and expected effect. Inspect the revised render. Plan on three to five correction rounds, each fixing named problems; keep prior revisions, and stop when no concrete issue remains. If visual inspection is unavailable, disclose that limitation.

## Items, icons, props and scenes

Items, icons, tiles, props and small scenes use `pixel_art.py` (see `format.md`); skip `rig.md` and `design.md` beyond its color rules.
- Palette: `python SKILL_DIR/scripts/palette_tools.py --kit endesga-32` prints a ready `palette` (with `"o"` as the kit's outline) and named ramps; or write mnemonic keys yourself (`g`/`G` light and dark green). Keep 2–4 tones per material and declare them in `ramps`.
- Start from materials: draw each part as a flat region with a `material` (`format.md`: `dome`, `bevel`, `cylinder`), set one `light` and `"outline_style": "selective"`, and let the renderer shade, outline and clean it. Spend your effort on the silhouette, the choice of forms and the hand-drawn details on top (glints, grain, labels, wear).
- Never hand-draw what the tools do: `"outline": "o"` draws the outline, `"mirror": "x"` the symmetric half, `parts` + `stamp` repeated details (rivets, bolts, planks, coins), `stamp` with `swap` color variants, `gradient` and `shade`/`light` regions the large tone changes, a `blend: "shade"` layer the cast shadows, `glow` the light from flames, gems and potions.
- Organic texture (leaves, moss, rust, grass) is 2–3 tiny parts scattered with `scatter` and `on`/`clip`.
- **No filler noise.** Every mark on a surface needs a cause you could name, placed where that cause would put it: plank seams and nail heads, brick courses with offset joints, rain streaks under a ledge, rust runs under a bracket, wear on edges people touch. A clean flat area beats a speckled one; `noise` is only for granular materials.
- Give each asset one focal point and one implied light source: the lit side of every form faces it, shadows fall away from it, warm light against cool shadow (or the reverse). Small story details (a dent, a label, a crack, a sticker, a drip) do more than extra shading.
- Animated props (a chest opening, a torch, a coin spin): one document with `animation` frames as patches; keep motion in a small area (the flame, the lid, the sparkle) and hold key frames longer than in-betweens. `sheet.py` packs separate documents instead.
- **Light sets the mood.** Decide the time of day and the light sources before drawing, and build the palette from them. Dusk or night: overall values low, shadows and the sky side cool blue-violet, a warm rim only where the low sun or a fire reaches, the darkest values under eaves and in doorways. A light source must light its surroundings: `glow` with `tint` (a warm ramp) spills firelight onto stone, wood and metal nearby, and `bands: true` gives crisp rings instead of dither. Animate the spill with the fire: give frames their own `glow` (a larger `r` on tall-flame frames).
- **Item craft:** fill about 70–85% of the cell so the shape reads at 1x (a sword runs corner to corner with a real tapered point). Show containers (chests, crates, barrels) in a 3/4 view with the top plane visible unless the game is strictly side-on. Material cues: glass is a dark see-through interior with bright rim highlights, a reflection streak and a liquid meniscus line; metal has hard high-contrast highlights and dark reflections; gold runs from orange-brown shadow to pale yellow light, a wide value range, never one orange mass; wood has grain along the planks and darker seams. A pile (coins, gems, apples) is individual readable units, each with a dark gap or shadow under it, shaded together as one mound. Labels and bands wrap around the form, following its curve.
- **Hinged motion:** a lid or door rotates around its hinge: draw it at 3 or more angles (closed, foreshortened, open showing its inside face), add an overshoot and settle; never just slide it up.
- **No mechanical grids.** Vary tile, brick and plank sizes, offset joints irregularly, break the pattern where things meet (a chimney through a roof, a ridge cap, chipped edges), and change values across a surface (sun-faded top, soot near a chimney, dirt near the ground). A generator script is fine, but give it randomness and exceptions.
- **Fire and smoke:** fire is 3–5 persistent tongues that rise, sway and split over 6–8 frames, with a flickering ember loop below; never re-randomize every pixel each frame. Smoke is separate puffs that leave the source, rise, grow, drift with the wind, thin into a dither and vanish; each puff lives for several frames, and several overlap.
- Animated documents: `review.py PREFIX.anim.json --out review.png` shows the key frames and the 1x/2x loop, and `--region X Y W H` tiles one area (the fire, the smoke) across every frame, enlarged. A layer can carry its own `outline` (draw smoke and glows without one), and frame edits can name a `part` to change stamped details per frame.
- Effects (spells, hits, projectiles, auras): see *Effects* in `craft.md`; build them from the `bolt`, `flames`, `particles` and `smoke` operations, split what wraps a character into `group: back` and `group: front`, and rotate hinged or swinging parts with a layer `transform`.
- `python SKILL_DIR/scripts/composite.py --bg SCREENSHOT.png --crop X Y W H --at X Y --layer back:fx.back.anim.json --layer image:hero.png@PX,PY --layer front:fx.front.anim.json --out preview.gif` previews animations in place on the game's background at 1x (sequences: `a.anim.json+b.anim.json*3`; a flying projectile: `--layer move:DX,DY` before its layer).
- `python SKILL_DIR/scripts/export.py OUT_DIR fx.anim.json --out build --name hero` packs everything into one atlas with Aseprite JSON (Phaser 3 `load.aseprite` / `createFromAseprite`), TexturePacker JSON and a Godot 4 `SpriteFrames` `.tres`, keeping per-frame durations, loops and pivots.
- `python SKILL_DIR/scripts/lint.py` accepts a single PNG, a `PREFIX.anim.json` or a `sheet.py`/`rig2d.py` output folder.

## Characters and animation

Pick the path by size:
- **Small sprites (about 40 pixels or less: bats, slimes, critters, tiny heroes):** draw the key frames by hand with `pixel_art.py` and an `animation` (frames as patches, or one document per frame packed with `sheet.py`). At this size every pixel is a decision, and rotating painted layers on a rig breaks thin parts (wing spars, limbs) into specks. Draw the extremes first (wings fully up, fully spread down), then 1–2 in-betweens; give hurt its own drawn pose (squashed, eyes shut).
- **Larger characters (about 48 pixels and up):** use `scripts/rig2d.py`; do not hand-draw every frame.

1. Pick the rig and canvas, leaving room for reach (weapons, tails, gallop, wings). The rigs are `humanoid`, `chibi`, `quadruped`, `bird`, `serpent` and `slime`. Apply the identity choices above: `build`, `motion`, `style`, `pose_offset`, and distinctive parts such as silhouette features, accent colors and a readable face. Each rig's default parts and the materials they need are in the *Default parts* table of `rig.md`; weapons are extras on the `weapon_n` bone.
   - Presets: each rig has `idle`, a move, `attack`, `hurt` and `die`, and the preset packs add about 70 more (`run`, `jump`, `cast`, `block`, `sit`, `sleep`, `howl`, `glide`, `spit` and others). The full list per rig is under *Preset packs* in `rig.md`. Chained poses come in pairs: play `sit` once, then loop `sit_idle`; a humanoid plays `sleep` once, then loops `sleep_idle`; a quadruped plays `lie_down` once, then loops `sleep`.
2. Choose the quality path and say which one:
   - **Vector parts**: shapes on bones, shaded automatically as lit volumes. Quick and clean; with good materials, groups and a strong face it reaches final quality for mobs.
   - **Cutout layers**: pixel regions painted once in the rest pose with `draw` ops, then split onto the bones automatically. This is the path toward final art.
3. Build colors from base colors with hue-shifted ramps (`{"base": "#RRGGBB"}` materials or `palette_gen`) rather than picking shades by hand. For final art, turn on `"style": {"polish": true}` (cutout characters: `"style": {"polish": {"aa": true, "smear": true}}`), add `texture` to parts where the material calls for it (fur, scales, cloth, metal), and give `motion` some `follow`.
4. Render, then run `python SKILL_DIR/scripts/review.py OUT_DIR --out review.png` and look at it: key frames of every animation enlarged, plus the animation at 1x and 2x as a player sees it. Run `scripts/lint.py OUT_DIR` and fix the findings that are real problems.
5. Critique and correct until the asset meets the quality bar below. Fix the parts, colors or posture first, and only then the key frames by hand with `touchups` (frame numbers are 0-based, as in the file names). Put one-pixel eyes and highlights in `stamps`, which are never rotated, even on cutout characters: single pixels painted into a rotating layer can vanish. An anim entry can carry its own `stamps` (closed eyes while sleeping) and `z` (draw order for that animation).
6. Deliver the sheets, `animation.json`, a preview GIF made with `showcase.py`, and the spec. State the frame size, frame counts, timings, and the visible limitations.

## Quality bar and critique loop

Judge the render the way a pixel-art lead would, at 1x and 2x as well as enlarged. Score each criterion from 1 to 10, where 8 means "ships in a good commercial indie game":
1. **Silhouette:** recognizable at 1x; distinct features (ears, snout, weapon, hat) do not fuse into one blob.
2. **Form:** each body reads as a lit volume: a light side, a shadow side with a core shadow, and no flat fills or pillow shading.
3. **Clusters:** deliberate clusters of 2+ pixels; no stray specks, banding or jaggies; no dark lines between parts of one body.
4. **Color and value:** adjacent parts differ clearly in value (a near arm against the torso, legs against each other, skin against cloth), with a small hue-shifted palette.
5. **Design:** appealing proportions; the face has an eye with a socket or brow and a mouth line; gear is big enough to read (at least 3-4 pixels).
6. **Animation:** readable key poses, weight and arcs; weapons stay attached to the hand; effects connect to the motion; nothing pops or detaches.

Self-scores run about two points too high, and reviewers' specific claims are often wrong. Follow [references/critique.md](references/critique.md): an outside reviewer (a subagent given only the PNGs) or your own cold read, defects with pixel boxes checked against the pixels before you act, and a fix kept only when it wins a blind A/B (`scripts/abtest.py`). After each render, write the six scores honestly, name the weakest criterion with the frame and part, fix that, and render again. Repeat until every criterion is 8 or more, or until six rounds pass; then say which criteria fell short and why. Common fixes:
- muddy value: push a ramp's base lighter or darker (`{"base": ...}`) so neighbors differ by about 20% in brightness; give the near arm or sleeve a different material from the torso;
- segmented body: put parts of one body in one `group`;
- noise: remove `texture` from small parts, and drop single-pixel decorations that are not eyes or highlights;
- weak face: an eye stamp with a dark socket or brow row above it, and a 2-3 pixel mouth line;
- small canvas: characters with gear read better at 56-64 pixels than at 32-40.

## Tool loop

Here `python` means the interpreter found during setup; `SKILL_DIR` means this skill's actual absolute folder.

```text
python SKILL_DIR/scripts/pixel_art.py render sprite.json --out sprite-v1 --scale 12 --grid
python SKILL_DIR/scripts/pixel_art.py ascii sprite.json --box 8 4 23 15
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
