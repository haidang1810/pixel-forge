# Pixel Art JSON version 1

## Document

UTF-8 JSON. Unknown fields, duplicate JSON keys, and non-finite numbers are rejected. This geometric example explains syntax only; it is not an art template:

```json
{
  "version": 1,
  "size": [8, 8],
  "palette": {".": "#00000000", "o": "#192438", "a": "#73D6BC"},
  "layers": [
    {"name": "shape", "origin": [2, 2], "rows": [".oo.", "oaao", ".oo."]},
    {"name": "accent", "ops": [{"op": "pixels", "points": [[3, 3]], "color": "o"}]}
  ],
  "meta": {"description": "A small geometric syntax example", "pivot": [4, 7]}
}
```

Every row character must match a palette key exactly. The renderer reports the row and column of any unknown symbol.

- `version`: integer `1`.
- `size`: `[width, height]`, integers 1–512. For larger scenes, create tiles or components; this renderer targets small art.
- `palette`: nonempty map from one visible ASCII character to `#RRGGBB` or `#RRGGBBAA`. Alpha must be `00` or `FF`. Fully transparent colors normalize to zero RGBA. `.` is an ordinary palette key; define it as transparent when using dots in rows. A transparent symbol in rows paints transparency into that layer (it does not erase lower layers), so to leave pixels of a layer untouched, give that layer smaller rows or use ops.
- `layers`: nonempty array in back-to-front order. Names must be unique.
- `outline`: optional opaque palette symbol. After all layers are composited, every transparent pixel that touches an opaque one (up, down, left or right) takes this color, so layers can be drawn without their own outline. Leave a one-pixel margin on the canvas for it. `palette_tools.py --kit SLUG` prints a palette whose `o` is the kit's outline.
- `meta`: optional object for your brief, palette roles, pivot, and notes. It is copied to the report and does not affect rendering. Frame timing and engine import settings are not inferred.

- `ramps`: optional list of palette-symbol strings, dark to light (`["kgGl", "kOoy"]`). `shade`, `light`, blend layers and `glow` step colors along them, so tones stay in the palette.
- `parts`: optional named parts, reused by `stamp` and `scatter`: `{"leaf": {"rows": ["gG", "g."]}}`, or `{"size": [w, h], "layers": [...], "mirror": "x", "outline": "k"}`. Parts share the document palette and may stamp other parts.
- `mirror`: optional `"x"`, `"y"` or `"xy"`: after compositing, the left (top) half is copied mirrored onto the other half. Draw half of anything symmetric. A whole-document mirror also mirrors the shading, so for a lit object put `"mirror"` on the shape layer instead (a layer's own mirror runs before the layers above it) and draw the one-sided light and shadow in a layer on top.
- `glow`: optional list of `{"keys": "Yl", "r": 6, "steps": 2}`: opaque pixels within `r` of a glowing key step up to `steps` lighter along their ramps, with a dithered falloff. It stays inside the palette (no blended colors). `"bands": true` gives hard rings instead of dither. `"on": "symbols"` limits which colors receive the light (leave soot, voids and walls facing away out of it); for light that follows the geometry, paint a warm ramp onto the faces turned toward the source and use `glow` only for a small halo. `"tint": "WOoy"` (a ramp, dark to light) moves lit pixels onto that ramp at their own brightness, then lifts them: firelight turns cold stone warm. Glow works on colors: give a glowing key its own hex (a key that shares its hex with another glows with it), and list every color of the light source in `keys` (all flame tones), or the tint repaints the source too. A frame may carry its own `glow` list, which replaces the document's for that frame, so the spill can flicker with the flames.
- `lights`: optional list of point lights that stay in the palette and follow the geometry: `{"at": [x, y], "r": 40, "steps": 2, "keys": "hjlmv", "tint": "FGHI", "block": 0.3}`. Lit pixels step lighter along their ramps (or move onto the `tint` ramp at their own brightness), most where they are near the source, where the line to it is not blocked by layers marked `"solid": true` (walls, roofs; `block` is the light lost per solid pixel crossed), and on surfaces facing it. `keys` are the source's own colors, left as painted; `on` limits which colors receive light; near-black pixels stay dark. Bands are hard unless `"dither": true`. A frame may carry its own `lights` (a flickering fire). Use lights for the spill on walls, ground and props; `glow` for a small halo at the source.
- `animation`: optional `{"fps": 8, "loop": true, "frames": [{"ms": 120, "edits": [...]}, ...]}`. Every frame is the document plus that frame's edits: patch-style ops appended to a layer (`{"layer": "lid", "op": "rect", ...}`), `{"layer": "flame", "move": [0, -1]}` to shift a layer, or `{"layer": "spark", "visible": false}`, or an op on a part (`{"part": "window", "op": "recolor", ...}`) to change a stamped detail. `PREFIX.png` is frame 0. `render` then also writes `PREFIX.strip.png` (all frames side by side), `PREFIX.anim.json` (rect and ms per frame, plus `loop`), `PREFIX.gif` and `PREFIX.frames.png` (an enlarged strip to inspect).

Order: layers (rows, then ops, then `shift`), blend layers, `mirror`, `lights`, `glow`, blend layers marked `after_glow`, `outline`.

## Layer

Fields: `name`, optional `origin` (default `[0,0]`), optional `visible` (default `true`), and `rows` and/or `ops`. Optional `shift: [dx, dy]` moves the finished layer (clipping at the edge). Optional `outline` gives this layer its own outline (use it instead of the document `outline` when smoke or glows must stay unoutlined). A layer may have `"ops": []`, an empty layer that animation frames draw into. Optional `blend: "shade"` or `"light"` (with `steps`, default 1, and `density` 0–1) makes the layer a light mask: it is not drawn, and wherever it is opaque the layers below step darker or lighter along the ramps. Use it for cast shadows across several objects and for light spill. Blend layers apply before `glow`, so firelight can wash out a nearby shadow; add `"after_glow": true` to apply that shadow after the glow. One step on a 4–5 tone ramp is subtle: use `steps: 2` for shadows that must read at 1x.

`rows` is a rectangular, nonempty array of equal-length strings. Its first character is at the layer origin. It may cover only part of the canvas. Empty space outside it is transparent. Write no spaces or tabs as padding. All coordinates are zero-based integers; x increases rightward, y downward.

`ops` is an array of drawing operations. Rows are painted first, then operations in order. All operation coordinates are local to the layer origin, including coordinates inside a patch. Shapes must fit the canvas; the renderer rejects out-of-bounds inputs instead of clipping them (the richer operations below clip instead). Shading ops (`shade`, `light`, `recolor`) change only pixels of their own layer; to shade what is below, use a blend layer.

Hidden layers are still validated. Transparent paint erases pixels on the current layer and reveals any lower layer; it does not erase the whole composite. Later opaque paint replaces earlier paint exactly. There is no antialiasing or blending within a layer.

## Operations

| Operation | Fields | Meaning |
|---|---|---|
| `pixels` | `points`, `color` | Paint each listed `[x,y]` pixel; at least one point |
| `line` | `points`, `color` | Connected one-pixel-wide segments; at least two points, endpoints included |
| `polygon` | `points`, `color` | Filled polygon including boundary; at least three vertices |
| `rect` | `xy`, `size`, `color` | Filled rectangle; `xy` is top-left, `size` is `[width,height]` |
| `ellipse` | `xy`, `size`, `color` | Filled ellipse within the specified pixel rectangle |

Richer operations (these clip to the canvas instead of rejecting out-of-bounds shapes):

| Operation | Fields | Meaning |
|---|---|---|
| `line` + `width` | `points`, `color`, `width` | A round brush of that width: poles, tubes, thick strokes |
| `circle` | `center`, `r`, `color`, optional `ring` | Pixel-art circle; `ring: true` draws a clean 1-pixel ring |
| `box` | `xy`, `size`, `color` | 1-pixel rectangle border |
| `fill` | `xy`, `color` | 4-connected flood fill of the region under `xy` on this layer |
| `dither` | `xy`, `size`, `colors` (two symbols), `density` | Ordered 4×4 dither; the second color covers `density` |
| `gradient` | `xy`, `size`, `colors` (dark→light or any order), `dir` (`v`/`h`), `soft` | Bands with dithered seams (`soft` 0 = hard bands) |
| `noise` | `xy`, `size`, `colors`, `density`, `seed`, optional `on` | Sparse speckle, only on pixels whose color is in `on`. Only for granular materials (gravel, sand, rough stone) |
| `shade` / `light` | optional `region`, `steps`, `density` | Step this layer's colors along the ramps inside a region |
| `recolor` | `map` (`{"a": "b"}`), optional `region`, `density` | Swap colors inside a region |
| `stamp` | `part`, `xy`, optional `flip` (`x`/`y`/`xy`), `swap` | Place a part with its top-left at `xy`, optionally recolored |
| `grid` | `xy`, `rows` | Paste rows of palette symbols; a space keeps the pixel below (templates, read-back edits) |
| `scatter` | `parts` (name or list), `xy`, `size`, `count`, `seed`, optional `on`, `clip`, `flip` (`"random"`) | Brush: centers land at random points of the area; with `on` only on those colors, and with `clip` the part paints only onto them |

`grid` (`xy`, `rows`) pastes rows of palette symbols at `xy`; a space leaves the pixel below untouched. Use it with `pixel_art.py ascii DOC.json [--frame N] [--box X0 Y0 X1 Y1]`, which prints the rendered art in the same symbols with coordinate rulers: read a region, change the few symbols that are wrong, paste them back.

A `region` is `{"rect": [x, y, w, h]}`, `{"circle": [cx, cy, r]}` or `{"polygon": [[x, y], ...]}` in layer coordinates; leave it out for the whole layer. Stack a low-`density` large region and a full small one for a soft falloff.

Every operation also contains `"op"` with the operation name. `color` is a palette character, not a hex string. Rectangles and ellipse bounds end at `[x+width-1, y+height-1]`. Widths and heights must be positive. For predictable polygon fills, use simple non-self-intersecting polygons. For thicker strokes or outlines, construct explicit regions or edit rows; there is no automatic outline/stroke parameter.

## Patch

`patch` accepts optional palette updates and an array of `edits`. Each edit names an existing layer and otherwise has exactly the fields of a drawing operation:

```json
{
  "palette": {"a": "#93E3CE"},
  "edits": [
    {"layer": "accent", "op": "pixels", "points": [[3, 3]], "color": "."},
    {"layer": "accent", "op": "pixels", "points": [[4, 3]], "color": "o"}
  ]
}
```

Palette replacement recolors every layer using that character. Edits append operations to the named layers. The whole revised document is validated before saving. `--output` must differ from both source and patch-file paths. Existing output revisions may be overwritten, so choose versioned filenames when comparison matters.

To rename, move, add, delete, or reorder layers, edit the source document and validate it. The patch command intentionally covers palette changes and local pixel painting only.

## CLI and files

```text
python scripts/pixel_art.py validate INPUT.json
python scripts/pixel_art.py render INPUT.json --out OUTPUT_PREFIX --scale 12 --grid
python scripts/pixel_art.py patch INPUT.json PATCH.json --output REVISED.json
```

Append `.png`, `.preview.png`, `.report.json`, and (with `--grid`) `.grid.png` to the prefix. Pass `--out output/sword`, not `--out output/sword.png`. Rendered outputs at the prefix are replaced on rerun; an existing grid is also refreshed even if `--grid` is omitted, so it cannot show an old revision. Source JSON and aliases of the source file are protected. Validation failure returns exit code 2 and writes no render outputs.

Native PNG is exactly the document size, RGBA, without a grid. Preview uses nearest-neighbor scaling over a dark checkerboard. Scale is 1–32, with preview sides limited to 4096 pixels. Grid uses at least 4× enlargement so lines leave visible pixel interiors, and adds top/left coordinate labels. Read grid coordinates at pixel cells, not at image-file positions; the grid image has a 24-pixel margin.

The report records size, RGBA color counts, transparent/opaque counts, layer bounds, metadata, and warnings. Bounding boxes use `[left, top, right, bottom]` with right/bottom exclusive. Edge contact can be intentional for seamless tiles. Warnings are observations, not automatic failures or aesthetic ratings.
