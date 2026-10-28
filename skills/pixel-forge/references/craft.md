# Craft notes: what reviewers mark down, and how to avoid it

Short rules by subject, with size budgets and small pixel templates you can paste with a `grid` op (a space keeps the pixel below). Templates use `k` dark/outline, `d` shadow, `m` mid, `l` light, `w` highlight; swap in your own palette symbols. Adapt them; never paste the same template unchanged across a whole set. Several ideas here follow the public rule catalogue of the Aseprite AI Artist project (MIT, github.com/with-pebbly/aseprite-ai-artist), rewritten for this skill.

## Order of work

Silhouette, then big values (light side, shadow side), then color, then clusters and edges, then details. Fixing edges before the values are right repeats work. Check at 1x after each stage: if it does not read at 1x, detail will not save it.

## Value and light

- The lit side of the subject is among the lightest values in the picture and its core shadow among the darkest. A subject sitting in the bottom third of the value range reads as murk, the most common fault with limited palettes.
- Desaturate a copy (or squint): the subject must still separate from its surroundings and its main parts from each other.
- One light direction for the whole asset and every frame. Highlights on both sides is a classic machine-made tell.
- Shading steps change hue, not only value: shadows lean blue-violet, lights lean warm (`lint.py` reports `flat_ramp`).
- No pillow shading (darkening evenly toward every edge). Put the highlight toward the light and a crescent of shadow on the far side.

## Clusters, noise, lines

- Clusters of 3 pixels or more that follow the form. Random 1–2 pixel specks read as dirt; at most one deliberate single pixel per object (an eye glint, a specular dot).
- Lines and curves use monotone runs: a curve's runs grow or shrink steadily (1,1,2,3,4), never 2,3,1,2. Slopes look cleanest at 1:1, 1:2, 1:3.
- No banding: two tones in parallel runs that start and end in the same columns read as stripes. Stagger the ends.
- Dither only in short transitions (1–3 pixels) or large skies, never as a texture over half an object.
- No near-duplicate colors: two colors a viewer cannot tell apart are one color doing no work (`lint.py` reports `duplicates`).
- Every mark on a surface has a cause you could name (a seam, wear, a stain under a drip). Uniform detail everywhere is a machine tell; leave quiet resting areas.

## Faces and eyes

| Character height | Eye | Mouth |
|---|---|---|
| 16–24 px | 1 px (2 px tall for cute) | usually none |
| 32–48 px | 1×2 or 2×2, dark, 1 px brow line above | 1–2 px |
| 64 px and up | 2×3 with a 1 px highlight and a brow plane | 3–4 px line, 1–2 tooth pixels |

Eyes sit near the vertical middle of the head; at small sizes a bigger head (up to a third of the height) buys space for expression. Change the eye per state: narrowed in attack, shut in hurt, closed or X in death.

```text
eye 2x2 + brow (64 px char)   eye 2x3 with glint        shut eye
kkkk                           kkk                       kkk.
kwl.                           kwl                       ....
kll.                           kll                       .kkk
                               kkl
```

## Hands and held items

A hand at 32–48 px is a 2×2 to 3×3 fist; fingers are a darker line across it, not individual digits. A held item passes behind the fingers: draw the grip, then the fist over it, and keep the item attached in every frame.

```text
fist on a vertical grip (grip g)   fist, side view
 g                                 .mm.
mmmm                               mlld
mkkd                               mkkd
dgdd                               .dd.
 g
```

## Props and items (32×32)

- Fill 70–85% of the cell; read at 1x in an inventory slot.
- Containers in 3/4 view with a visible top plane. A lid rotates around its hinge: draw it closed, foreshortened, open with its inside face shown, with an overshoot.
- Glass: dark see-through interior, bright rim highlights following the curve, one reflection streak, a liquid line. Never a flat opaque fill.
- Metal: high contrast, hard highlight and dark reflection next to each other. Gold: orange-brown shadow to pale yellow highlight, a wide range.
- Wood: grain along the planks, darker seams, planks that follow the object's curve.
- Piles: readable units, each with a dark gap below it, lit together as one mound. A 32 px coin pile: 2–3 short stacks of edge-on coins (2 px bands alternating light and mid, a dark line under each), a low mound in front built from overlapping 4–6 px ellipses each with a light top arc and a dark bottom arc, 1–2 coins standing or leaning face-on in front, and empty space above. Keep the mound's top edge bumpy (one bump per coin); a smooth dome reads as a lump.

```text
coin, face on (8 px)     coin stack (side)      gold mound edge
..kkkk..                 kddddk                 ..klwk..
.kllllk.                 kmmmmk                 .klmmlk.
kllwwlmk                 kddddk                 klmddmlk
klwmmlmk                 kmmmmk                 kdkddkdk
klwmmlmk                 kddddk
klmmmmdk
.kmmmdk.
..kkkk..
```

## Fire, smoke, magic (animated)

- Fire: 3–5 tongues that persist between frames, rise, sway, split and break off at the top, over a flickering base. White-yellow core at the bottom, orange body, red tips. 6–8 frames at 80–100 ms. Never re-randomize every pixel each frame.
- Smoke: separate puffs born at the source, rising, growing, drifting with the wind, getting darker or thinner, then breaking into a few pixels and vanishing. Each puff lives for several frames; several overlap; the column stays connected to the chimney.
- Light from a fire falls on the surfaces facing it (a warm rim on the nearest edges, the ground in front), not as a circular halo. Use document `lights` with `solid` walls and a warm `tint` ramp, the flame colors in `keys`, and a per-frame `r` that pulses with the flame; keep `glow` for a small halo.

```text
flame tongue, 4 frames (w core, l body, m tips)
..m..    ...m.    .m...    ..m..
..lm.    ..ml.    .ml..    .ml..
.lwl.    .lwl.    .lwl.    .lwl.
.lwwl    lwwl.    .lwwl    lwwwl
```

## Effects (VFX)

- Build effects from the `bolt`, `flames`, `particles` and `smoke` operations (`format.md`) instead of hand-scripting shapes; drive them with `t` so they persist between frames.
- Beats: anticipation (a charge, a sigil, sparks gathering: 2-3 frames), the peak (1-2 frames, the brightest and biggest, held longest), the release or impact, then a decay that breaks the shape apart (arcs dying, embers falling, smoke thinning); never just fade the whole thing.
- Size against the characters: a hit spark is about half a character tall, a big spell up to two or three characters; leave headroom so the peak frame never clips the canvas.
- Readable on both bright and dark ground: a dark rim under bright effects (lightning, fire) and a coloured rim around dark ones (black flames, shadow magic); a white-hot core only at the hottest point.
- Effects that wrap a character are two layers: `group: back` behind the sprite, `group: front` in front of it; keep the character's body mostly clear.
- Preview at game scale on a screenshot of the game with `scripts/composite.py` before judging; an effect that reads enlarged can vanish at 1x.
- A projectile is a loop with a steady head (only the tail and sparks change); the impact starts on its own bright frame; a lingering effect (a burn, a poison cloud) is a separate quiet loop.

## Animation

- Key poses first, then in-betweens; hold key frames longer (a strike 1–2 frames, the recovery longer).
- Idle must move at least 1–2 px somewhere at 1x (breath in the chest, a head bob, a lagging ear or tail).
- Anticipation before a fast action, follow-through after it, and secondary parts (hair, ears, cloth) lagging a frame.
- Volume and limb lengths stay constant between frames; a shape that grows or shrinks keeps all its parts.
- Check every key frame at full size, not only a filmstrip: a broken shape on one frame hides in a thumbnail.

## Scenes and buildings

- Ground the subject: a ground line, footing or contact shadow so it does not float. Buildings sit on the bottom rows with a 1–2 px ground strip; put `meta.pivot` at the bottom centre so the engine can place it on the terrain.
- One focal point; quiet areas around it. Story props near the focal point.
- Mixed projection is a common fault: front-on facades with an oblique ground slab. Pick one view for everything.
- Value hierarchy: the focal point has the strongest contrast; the background has the least.

## Generated-art tells (review checklist)

Check these before calling anything done; three together mean the asset looks machine-made: near-duplicate colors, value-only ramps, speckle as texture, banding, uniform detail everywhere, highlights on two sides, pillow shading, perfect mirror symmetry on an organic subject, shapes built only from rectangles (no 2:1 slopes or rounded corners), wobbly runs on lines, frame-to-frame drift in size or palette.
