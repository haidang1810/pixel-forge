# Rig specs: characters and animation

`scripts/rig2d.py` turns a short JSON spec into animated, side-view pixel sprites. A built-in skeleton is posed by animation presets, and the parts attached to it are drawn fresh for every frame. This is not a trained model: the art is only as good as the parts you author.

## Commands

```text
python SKILL_DIR/scripts/rig2d.py SPEC.json --out OUT_DIR --scale 8
python SKILL_DIR/scripts/rig2d.py SPEC.json --out OUT_DIR --rest --scale 12
python SKILL_DIR/scripts/rig2d.py SPEC.json --out OUT_DIR --bake BAKED.json
python SKILL_DIR/scripts/showcase.py hero/idle hero/walk --root PARENT_OF_OUT_DIRS --out hero.gif
python SKILL_DIR/scripts/gridview.py OUT_DIR/run/frame-01.png --out grid.png --scale 10
python SKILL_DIR/scripts/dumpframe.py SPEC.json OUT_DIR/run/frame-01.png --box 16 30 48 47
```

A render writes the following into `OUT_DIR`:
- `<anim>.png`: a horizontal sheet with no spacing.
- `<anim>.preview.gif`: an enlarged preview.
- `<anim>/frame-XX.png`: each frame as a separate image.
- `<anim>/frame-XX.json`: each frame in the v1 format, so `pixel_art.py patch` can edit it.
- `animation.json`: per frame, the rect in the sheet, the milliseconds and the `pivot`, which is the hip (skeleton root) in frame pixels. Align frames and animations in the engine by the pivot, because an animation may be shifted inside its frame to fit (for example a fall).
- `contact.png`: an overview of all frames.

Every frame is checked to reproduce exactly through `pixel_art.py`. A spec error exits with code 2 and writes nothing. `--out` must not be the folder that holds the spec. Outputs there are replaced on rerun. A warning reports art that touches the canvas edge.

`--rest` renders only the rest pose, writing three files. `rest-grid.png` shows the rest pose over a labeled grid with the bones drawn in. `rest-bones.json` lists every bone's start and end in canvas pixels. `rest.png` is the rest-pose art, written only once parts exist.

## Spec fields

```json
{
  "name": "hero", "size": [48, 48], "rig": "humanoid", "outline": "#141D2B",
  "root_x": 0.4, "proportions": {"head": 11}, "pose_offset": {"lean": 6},
  "materials": {"body": ["#29394E", "#4B627C", "#809BAB"], "skin": ["#8A5A4A", "#C98F6E", "#EDC29A"],
                "legs": ["#202939", "#3A4A60", "#5B6F88"], "boots": ["#3B2A26", "#5E4134", "#86604A"]},
  "parts": {"head": {"mat": "skin"}},
  "extras": [{"name": "hat", "bone": "head", "shape": "poly", "mat": "body", "z": 45, "points": [[9, -5], [9, 6], [16, 0]]}],
  "stamps": [{"bone": "head", "at": [6, 2], "rows": ["o.o"], "colors": {"o": "#141D2B"}}],
  "anims": [{"preset": "idle"}, {"preset": "walk", "frames": 8, "stride": 22}]
}
```

This example only shows the syntax; it is not an art template.

- `size`: the canvas `[w, h]`, 8–256. Leave room for reach, because a weapon swing or a tail needs space.
- `rig`: one of `humanoid`, `chibi`, `quadruped`, `bird`, `serpent` or `slime`.
- `build`: a body type for `humanoid`, `chibi` and `quadruped`: `bulky`, `slim`, `tall` or `short`. It scales bone lengths by group (legs, arms, body, head) and the thickness of every part, including the spec's own extras. Leave it out for the rig's standard body.
- `proportions`: overrides bone lengths by name, applied after `build`. `scale` multiplies them all.
- `motion`: the character's personality, applied to every animation (an anim entry's own `motion` overrides keys). See *Motion personality*.
- `style`: render style for vector parts. See *Style*.
- `root_x`: the horizontal position of the hip as a fraction of the width. The lowest foot is always planted on row `h-3`.
- `pose_offset`: added to every frame and to the rest pose, giving the character its own posture (for example `"lean": 12` for a hunch). `dx` and `dy` shift the whole character, art included.
- `shadow`: `{"color": "#RRGGBB", "rx": 6, "shrink": 0.06}` draws a 2-row ground shadow under the hip. It shrinks by `shrink` × `rx` per pixel of lift and never covers the art. Use it for floating or jumping characters. Games often want the shadow as a separate sprite, in which case leave it out.
- `anims`: preset entries. Any other field in an entry is passed to the preset: its parameters, or a fixed joint value. `name` lets you list the same preset twice. An entry's own `pose_offset` replaces the character's value for each key it names, so give the full value (for example `"dy": -3`, not a change relative to the character's `dy`).

All characters face right, in side view. Angles are degrees.

### Humanoid and chibi

- **Bones:**
  - `spine` and `head`;
  - `thigh_n`, `shin_n`, `foot_n` for the legs;
  - `upper_n`, `fore_n`, `hand_n` for the arms;
  - `weapon_n` (the held item).

  Each also comes in an `_f` version. `_n` is the near side and `_f` the far side, which is darker and drawn behind the body.
- **Joints:** `lean`, `head`, `hip_*`, `knee_*`, `ankle_*`, `sh_*`, `el_*`, `grip_*`. Limb angle 0 points straight down, and positive turns toward the facing side.
- **Presets:**
  - `idle` takes `frames`, `ms` and `breath`;
  - `walk` takes `frames`, `ms`, `stride`, `knee` and `arm`;
  - `attack` (a horizontal slash) takes `ms`, which scales all timings;
  - `hurt` (flash, knock-back, recover) takes `ms`. `"style": "float"` keeps a floating creature's hover pose;
  - `die` takes `ms`, `style` and `fade`. `"style": "fall"` (the default) staggers, drops to the knees and falls on the back. `"style": "fade"` is for floating creatures: a flash, then a dissolve while drifting up. `fade: N` adds N dissolve frames after a fall;
  - `float` hovers in place for ghosts and spirits, taking `frames`, `ms`, `bob`, `sway` and `wave`. The legs become trailing wisps whose wave runs from hip to tip: reshape them with `parts` and hide the feet. Lift the body with `pose_offset` `dy` (negative is up). Fixed joints passed in the entry, such as `"lean": 18` for a forward-flying variant, override the per-frame motion.

### Quadruped

- **Bones:** `spine`, `hips`, `chest`, `neck`, `head`, `tail` and `tail1`–`tail3`. Each leg has `upper_X`, `lower_X`, `foot_X` and `paw_X`, where X is `bn`, `bf`, `fn` or `ff` (back or front, near or far).
- **Joints:**
  - `pitch`: positive lowers the shoulders;
  - `flex`: positive arches the back;
  - `neck`: measured from straight up;
  - `head`: positive points the nose down;
  - `tail`: positive raises it; `tail2` and `tail3` curl it further;
  - `hip_X`, `knee_X`, `ankle_X` for each leg.
- **Presets:**
  - `idle` takes `frames`, `ms` and `wag`;
  - `walk` is a four-beat walk taking `frames`, `ms`, `stride` and `fold`;
  - `run` is a rotary gallop with a flight phase, taking `frames`, `ms`, `stride`, `fold` and `flex`;
  - `attack` is a pounce and bite (crouch, launch, snap, step back), taking `ms`;
  - `hurt` (flash, rear back, tail tucked) takes `ms`;
  - `die` (flash, buckle, drop, lie on the side with the legs out) takes `ms` and `fade`.

A full mob set is idle, a move (walk, run or float), attack, hurt and die. Death holds its last frame for 600 ms; play it once in the game. Preview GIFs loop every animation.

### Bird

- **Bones:** `body` (also `spine`), `neck`, `head`, `tail`, `wing_n`/`wingtip_n`, `wing_f`/`wingtip_f`, and legs `thigh_*`, `shin_*`, `foot_*`. Default part materials: `body`, `wing`, `beak`, `leg`.
- **Joints:** `body` (tilt, > 0 chest up), `neck`, `head`, `tail`, `wing_*` (limb angle: −95 folded back, 160 raised), `wingtip_*` (outer wing bend), `hip_*`, `knee_*`, `ankle_*`.
- **Presets:** `idle` (head bob), `hop`, `fly` (flap with a lagging wingtip; `lift` sets the height), `attack` (rear up, peck), `hurt`, `die`.

### Serpent

- **Bones:** `neck`, `head`, `jaw`, `seg1`…`seg8` running back from the root (where the neck leaves the ground). Default part material: `body`; the jaw can be given its own (`"parts": {"jaw": {"mat": "belly"}}`).
- **Joints:** `neck`, `head`, `jaw` (opens the mouth), `seg1`…`seg8` (bend of each segment relative to the previous one; > 0 turns down/back).
- **Presets:** `idle` (sway, tongue flick via `jaw`), `slither` (travelling wave, `amp`), `attack` (coil, strike with the jaw open, bite), `hurt`, `die`.

### Slime

- **Bones:** `body`, which points up from the bottom centre and carries the squash. Default part material: `body`; put eyes and highlights in `stamps` and `extras` on `body`.
- **Joints:** `stretch` (1 normal, > 1 tall and thin, < 1 squashed flat and wide) and `lean`.
- **Presets:** `idle` (wobble), `hop` (squash, launch, arc, land), `attack` (lunge stretched forward), `hurt`, `die` (melt into a puddle).

### Squash and stretch

Any bone can carry a `scale`: parts on it stretch along the bone by `scale` and narrow across it by 1/`scale`. The slime uses it for every frame. Part coordinates are always authored at scale 1.

## Motion personality

```json
"motion": {"weight": 0.8, "energy": 0.3, "exaggeration": 1.2, "seed": 41}
```

- `weight` (0 light, 1 heavy; default 0.5): heavier means a slower tempo, deeper knee bends and less time in the air.
- `energy` (0 sluggish, 1 lively; default 0.5): livelier means a faster tempo, bigger swings of the arms, head, tail and wings, and more bounce.
- `exaggeration` (0–2; default 1): scales every joint's swing away from the rest pose. Use 0.6 for subtle, 1.4 for cartoony.
- `seed` (integer): gives each joint a fixed small quirk (an angle offset and a gain) and makes the frame timing slightly uneven. Two creatures of one kind with different seeds never move identically; the same seed always repeats exactly.

At the defaults the presets are unchanged. Give every character a personality that matches its identity.

## Style

```json
"style": {"outline": "selout", "shades": 3, "dither": true, "light": "upper-back"}
```

- `outline`: `black` (the outline color everywhere), `selout` (each edge takes a darker tone of the fill it borders) or `none`. Leaving it out keeps the standard look: black, with light-facing edges tinted by `ramps`.
- `shades`: 2, 3 or 4 tones per material (4 uses a material's highlight color, if it has one).
- `dither`: checkers the boundary between two tones.
- `light`: `upper-front` (the default), `upper-back`, `top`, `front`, `back`, or degrees (0 from the facing side, 90 from straight above).

`shades`, `dither` and `light` apply to vector parts. Cutout layers keep their painted shading; `outline` applies to both. Share one style across all the assets of a game.

## Effects and special pose keys

Presets set these per frame. They can also be passed as fixed values in an anim entry.
- `flash: 1` turns every non-outline pixel into the `flash` color (spec field, default `#FFFFFF`), for hit frames.
- `dissolve: t` removes the fraction t (0–1) of pixels in an ordered 4×4 dither pattern, for fading out.
- `plant: "all"` rests the lowest pixel of the whole body, not just the feet, on the character's standing ground line, for lying and fallen poses.

Moves with `dx` (knock-back, lunges, falls) need horizontal room in the canvas. When a warning reports an edge, shift that animation with its own `pose_offset` `dx`. The pivot records the shift.

## Vector parts

Rig parts and `extras` attach a shape to a bone.

**Shapes:**
- `capsule`: `span [u0, u1]`, `r` or `[r0, r1]`, and an optional `v`;
- `ellipse`: `at [u, v]`, `rx` across the bone, `ry` along it;
- `poly`: `points [[u, v], ...]`.

Here `u` runs along the bone from its start, and `v` is perpendicular to it. For an upright bone, `+v` points forward. For a horizontal quadruped body bone, `+v` points down.

**Other fields:**
- `mat`: a material ramp of 3–4 colors, dark to light. Shading picks a tone from the surface direction against a light from the upper front. A fourth color is used for highlights.
- `z`: draw order.
- `group`: parts in one group are drawn as one piece, with no line between them.
- `far: true`: draws the part darker.
- `hidden: true`: removes a rig part.

`stamps` are small unrotated pixel rows placed at a bone point, used for eyes, mouths and slits. Vector parts are fast to author and animate cleanly, but they look generic. Use them for prototypes and simple mobs.

## Cutout layers (higher quality)

For final art, paint the character once, in its rest pose, as pixel regions. Each region is split onto its bones and moves with them. Shading is painted into the pixels; the renderer adds the outer outline.

1. Write the spec with `palette`, `ramps` and no parts, then run `--rest`. Read `rest-bones.json` and `rest-grid.png`.
2. Paint the regions in canvas coordinates around their bones, in a `draw` list. A region covering several bones is split by nearest bone, and pixels near a joint go to both bones so joints stay covered:
   ```json
   "palette": {"1": "#1C1A2A", "2": "#2C2A3E", "3": "#403E58", "4": "#5A5875", "k": "#120E1A"},
   "ramps": ["k1234"],
   "cleanup": true,
   "draw": [
     {"name": "body", "bones": ["hips", "chest"], "z": 30, "group": "body", "overlap": 2,
      "ops": [{"op": "poly", "c": "3", "pts": [[14, 25], [20, 19], [37, 18], [42, 27], [40, 35], [14, 29]]},
              {"op": "band", "c": "2", "depth": 4, "jag": 1},
              {"op": "rim", "c": "4"}]},
     {"name": "back_leg", "bones": ["upper_bn", "lower_bn", "foot_bn"], "z": 50, "group": "leg_bn",
      "mirror": {"bones": ["upper_bf", "lower_bf", "foot_bf"], "z": 10, "group": "leg_bf"},
      "ops": [{"op": "poly", "c": "3", "pts": [[16, 25], [24, 25], [23, 35], [18, 33]]}]}
   ]
   ```
   This shows the syntax only; it is not an art template. Ops, all using palette symbols:
   - `poly` (`pts`), `ellipse` (`box` [x0, y0, x1, y1]), `line` (`pts`), `px` (`pts`) and `erase` (`pts`);
   - `clip`: a polygon painted only over pixels the region already has, for shading inside a shape;
   - `band`: pixels within `depth` of the top silhouette edge (or the bottom, with `"bottom": true`), following the contour column by column. `x` limits the columns, and `jag` alternates the depth for a fur-like boundary;
   - `rim`: a 1-pixel band on the top edge, for rim light.

   A good order is: silhouette `poly`, then large shading with `band` and `clip`, then `rim`, then `px` details (eyes, teeth, toes).

   Region fields:
   - `z` is the first bone's draw order; each further bone gets `z + 1`. `group` merges the region's layers into one piece, with no lines between them.
   - `overlap` (default 1.5) is how far past the nearest bone a pixel may be and still be shared.
   - `mirror` reuses the same pixels on other bones, drawn darker (`far`). Use it for the far legs.
3. Render, then look at `contact.png` and `--rest`. Rotated layers use RotSprite (Scale2x ×3, nearest sampling, native readback), and unrotated layers are copied exactly. Expect small artifacts at large angles.
   - `ramps` lists palette symbols dark to light. Far parts, separation lines and selective outlines step down these ramps, so frames stay inside the palette. `far_steps` defaults to 2 and `selout_steps` to 3.
   - `cleanup` removes stray single pixels and fills pinholes after rotation.
4. Fix the key frames by hand with `touchups`. The edits are kept in the spec, so they survive re-renders:
   ```json
   "touchups": {"run": {"1": [{"color": "k", "pixels": [[29, 40], [29, 41]]}, {"erase": [[12, 30]]}]}}
   ```
   Use `dumpframe.py` to read exact coordinates and symbols, and `gridview.py` for a visual check.

To edit a layer pixel by pixel, freeze the drawing with `--bake BAKED.json`. This writes a copy of the spec in which every region becomes `cutout` rows: `{"name", "bone", "origin", "z", "group", "rows"}`, plus `{"from", "bone", "far"}` entries for mirrored layers. `origin` is the layer's top-left corner in the rest pose, and the pivot is the bone's rest start. `draw` and `cutout` can be mixed in one spec; drawn layers come first, so `cutout` entries can reuse them with `from`.

Moving the rest skeleton (`proportions`, `root_x`, rest joints in `pose_offset`) does not move the painted regions, so they no longer fit their bones. In that case, rerun `--rest` and adjust the coordinates. A global `dx` or `dy` in `pose_offset` is safe.

## Limits

- Side view facing right only. Turnarounds and top-down directions are not generated.
- Presets cover the motions listed above. Other motions need new preset functions in `rig_presets.py`.
- Quality depends on the authored parts. Inspect every animation; the tool does not judge art.
