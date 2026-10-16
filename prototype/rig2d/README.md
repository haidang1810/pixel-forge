# rig2d prototype

Pixel characters and animation from a short spec. Vector parts are attached to a 2D skeleton and redrawn as pixels for each frame. Needs only Python and Pillow.

```text
python rig.py examples/knight.json --out ../../output/rig2d/knight --scale 8
```

- `presets.py`: built-in rigs and animations. `humanoid` and `chibi` have `idle`, `walk` and `attack`; `quadruped` has `idle`, `walk` (four-beat walk) and `run` (rotary gallop). A spec refers to them by name. Pass parameters as fields of the anim entry, e.g. `{"preset": "walk", "frames": 8, "stride": 22}`.
- `rig.py`: skeleton solving, rasterizing, cel shading, outlines between parts and around the silhouette, face stamps, and export.
- Output: one sheet PNG per animation, a preview GIF, `contact.png`, `animation.json` (frame rects and timings), and `<anim>/frame-XX.json` in the pixel-art-json v1 format. Every frame is checked to reproduce exactly through the v1 renderer, so the existing `patch` tool can edit it by hand.

A spec-level `pose_offset` (e.g. `{"lean": 12}`) is added to every frame to give a character its own posture. `showcase.py` combines rendered animations into one GIF.

Limits: side view facing right only. Weapons and stamps are not rotated. A warning is printed when the art touches the canvas edge.

## Cutout characters (wolf2)

Instead of vector shapes, a spec can carry `cutout` layers: pixel art drawn on the canvas in the rest pose, each attached to a bone. Layers are rotated RotSprite-style (8x Scale2x, nearest sampling), and layers that do not rotate are copied exactly. `ramps` (palette symbols dark -> light) keep far legs, separation lines and selective outlines inside the palette. `cleanup` removes stray pixels and fills pinholes. `touchups` holds per-frame hand edits that survive re-renders.

```text
python rig.py examples/wolf2.json --out ../../output/rig2d/wolf2 --rest   # rest pose + skeleton grid
python examples/build_wolf2.py                                           # redraw layers, split onto bones
python rig.py examples/wolf2.json --out ../../output/rig2d/wolf2
python dumpframe.py examples/wolf2.json ../../output/rig2d/wolf2/run/frame-01.png --box 16 30 48 47
```

`gridview.py` enlarges frames over a labeled grid; `dumpframe.py` prints a frame as palette characters so touch-up coordinates can be read exactly.
