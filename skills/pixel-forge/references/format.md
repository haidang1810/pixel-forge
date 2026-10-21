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
- `palette`: nonempty map from one visible ASCII character to `#RRGGBB` or `#RRGGBBAA`. Alpha must be `00` or `FF`. Fully transparent colors normalize to zero RGBA. `.` is an ordinary palette key; define it as transparent when using dots in rows.
- `layers`: nonempty array in back-to-front order. Names must be unique.
- `outline`: optional opaque palette symbol. After all layers are composited, every transparent pixel that touches an opaque one (up, down, left or right) takes this color, so layers can be drawn without their own outline. Leave a one-pixel margin on the canvas for it. `palette_tools.py --kit SLUG` prints a palette whose `o` is the kit's outline.
- `meta`: optional object for your brief, palette roles, pivot, and notes. It is copied to the report and does not affect rendering. Frame timing and engine import settings are not inferred.

## Layer

Fields: `name`, optional `origin` (default `[0,0]`), optional `visible` (default `true`), and `rows` and/or `ops`.

`rows` is a rectangular, nonempty array of equal-length strings. Its first character is at the layer origin. It may cover only part of the canvas. Empty space outside it is transparent. Write no spaces or tabs as padding. All coordinates are zero-based integers; x increases rightward, y downward.

`ops` is an array of drawing operations. Rows are painted first, then operations in order. All operation coordinates are local to the layer origin, including coordinates inside a patch. Shapes must fit the canvas; the renderer rejects out-of-bounds inputs instead of clipping them.

Hidden layers are still validated. Transparent paint erases pixels on the current layer and reveals any lower layer; it does not erase the whole composite. Later opaque paint replaces earlier paint exactly. There is no antialiasing or blending within a layer.

## Operations

| Operation | Fields | Meaning |
|---|---|---|
| `pixels` | `points`, `color` | Paint each listed `[x,y]` pixel; at least one point |
| `line` | `points`, `color` | Connected one-pixel-wide segments; at least two points, endpoints included |
| `polygon` | `points`, `color` | Filled polygon including boundary; at least three vertices |
| `rect` | `xy`, `size`, `color` | Filled rectangle; `xy` is top-left, `size` is `[width,height]` |
| `ellipse` | `xy`, `size`, `color` | Filled ellipse within the specified pixel rectangle |

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
