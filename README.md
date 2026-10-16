# Pixel Forge

An agent skill for making 2D pixel game assets from editable JSON and code, with no image-generation model. It covers static items, icons and tiles, as well as side-view characters and mobs with skeletal animation exported as sprite sheets.

- **Static assets.** `scripts/pixel_art.py` renders palette-indexed layers (rows and drawing ops) to a native transparent PNG, an enlarged preview and a coordinate grid, and patches named layers.
- **Characters and animation.** `scripts/rig2d.py` poses built-in rigs with animation presets and redraws the attached parts for every frame:
  - **Rigs:** `humanoid`, `chibi`, `quadruped`.
  - **Animations:** idle, walk, run, attack, float.
  - **Parts:** either vector shapes (quick) or cutout pixel layers painted once in the rest pose and rotated RotSprite-style (higher quality).
  - **Hand edits:** per-frame touch-ups are stored in the spec, so they survive re-renders.
  - **Exact export:** every frame is also exported in the static JSON format and checked to reproduce exactly.

## Layout

- `skills/pixel-forge/`: the skill itself. It contains `SKILL.md`, the references (`format.md` for static JSON, `rig.md` for characters and animation), the scripts and the tests.
- `prototype/rig2d/examples/`: example character specs. These are a knight, a mage, an orc, three wolves (vector, cutout rows, cutout `draw`) and two ghosts (vector and cutout). The folder also holds the scripts that built the cutout wolf.
- `evaluation/`: early baseline and tool-review material from the first version.
- `docs/`: the original implementation plan.

## Use

You need Python 3.10+ and Pillow 9.1+.

```text
python -m unittest discover -s skills/pixel-forge/scripts/tests
python skills/pixel-forge/scripts/rig2d.py prototype/rig2d/examples/wolf3.json --out output/rig2d/wolf3
python skills/pixel-forge/scripts/showcase.py wolf3/idle wolf3/walk wolf3/run --root output/rig2d --out wolf3.gif
```

To install the skill, copy `skills/pixel-forge` into your agent's skills folder (for Codex, `~/.codex/skills/pixel-forge`) and invoke it as `$pixel-forge`.

Generated characters reach clean indie quality, especially with cutout layers and hand touch-ups, but are not guaranteed to match hand-made commercial pixel art.
