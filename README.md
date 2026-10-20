<div align="center">

# Pixel Forge

**Pixel art game assets from editable JSON and code. No image-generation model.**

Every pixel comes from a short spec your agent writes and a renderer that runs locally with Python and Pillow.
It makes static items as well as animated characters and mobs, with sprite sheets ready for a game.

<img src="docs/images/wolf.gif" alt="Wolf: idle, run, pounce attack, hurt and death animations" width="100%">

</div>

## Showcase

### Mobs

Each mob has a full set of animations: idle, a move, attack, hurt and die.

<img src="docs/images/orc.gif" alt="Orc: idle, walk, axe attack, hurt and death" width="100%">

<img src="docs/images/ghost.gif" alt="Ghost: float, fly, hurt and dissolving death" width="80%">

<img src="docs/images/critters.gif" alt="Slime hop and attack, serpent slither and strike, raven flight and peck" width="100%">

### One spec, many creatures

These four orcs come from one spec. Each one changes only its `build`, `motion` personality, `style` and skin palette. The skill makes the agent pick traits like these from each request, so different users get different creatures rather than the same default orc.

<img src="docs/images/variety.gif" alt="Four orc variants walking: slim scout, bulky brute, tall warlord, short grunt" width="100%">

### Polish

Left of each pair: plain shading. Right: hue-shifted color ramps, `style.polish` (clean-up, manual anti-aliasing, ambient occlusion, cast shadows, rim light, slash smear), material textures and follow-through.

<img src="docs/images/polish.gif" alt="Knight and orc attacks before and after polish" width="100%">

### Heroes

<img src="docs/images/heroes.gif" alt="Knight idle, walk and attack; mage idle and walk" width="100%">

### Items

<img src="docs/images/items.png" alt="Treasure chest, jade sword, ember potion, key, gem, shield, scroll, coin and bomb" width="100%">

<img src="docs/images/items.gif" alt="Chest opening, coin spinning and bomb fuse animations" width="60%">

## What it does

| | |
|---|---|
| **Static assets** | Items, icons and tiles drawn as palette-indexed layers (rows of symbols plus polygons, rects, lines and pixels). Each one is rendered to a native transparent PNG, an enlarged preview and a coordinate grid, and stays patchable by layer. |
| **Rigged characters** | `humanoid`, `chibi`, `quadruped`, `bird`, `serpent` and `slime` skeletons, posed by animation presets: idle, walk, run, hop, fly, slither, float, attack, hurt and die. Effects include squash and stretch, a hit flash, a dither dissolve and lying poses that rest on the ground line. |
| **Polish** | Hue-shifted color ramps generated from one base color; clean-up, manual anti-aliasing, ambient occlusion, cast shadows, rim light and slash smears; fur, scales, cloth and metal textures; follow-through. `lint.py` reports stray pixels, muddy tones, pillow shading, thin silhouettes, clipping and ground drift. |
| **Variety** | Body types (`bulky`, `slim`, `tall`, `short`), a motion personality (`weight`, `energy`, `exaggeration`, `seed`) and render styles (outline, number of shades, dither, light direction). |
| **Two quality paths** | **Vector parts** (shapes on bones, auto-shaded) are quick for prototypes. **Cutout layers** are pixel regions painted once in the rest pose and rotated RotSprite-style, for final art. |
| **Game-ready output** | Each animation is exported as a sprite sheet, plus `animation.json` with frame rects, timings and a pivot per frame, a preview GIF and a contact sheet. |
| **Editable to the pixel** | Per-frame `touchups` live in the spec and survive re-renders. Every frame is also exported as editable JSON and checked to reproduce exactly. |

## How it works

<img src="docs/images/wolf-rig.png" alt="Wolf rest pose drawn over its skeleton on a coordinate grid" width="420" align="right">

1. **Pick a rig and pose it.** The spec names a skeleton, its proportions and a posture. Run `--rest` to see the bones on a labeled grid.
2. **Attach the art.** You either give each bone a vector shape, or paint cutout regions around the bones with `draw` ops (`poly`, `band`, `clip`, `rim`, `px`). The renderer splits each region onto the nearest bones by itself.
3. **List the animations.** Each animation is a preset with a few parameters, for example `{"preset": "run", "stride": 36}`. The presets compute every frame.
4. **Render, inspect, touch up.** Check the key frames, then fix individual pixels with `touchups`.

A whole animated character fits in a few dozen lines of JSON. The agent never has to write frames by hand.

<br clear="right">

## Quick start

You need Python 3.10+ and Pillow 9.1+.

```bash
git clone https://github.com/haidang1810/pixel-forge.git
cd pixel-forge
python -m unittest discover -s skills/pixel-forge/scripts/tests
```

Render the wolf, then make a preview GIF:

```bash
python skills/pixel-forge/scripts/rig2d.py examples/characters/wolf.json --out output/wolf
python skills/pixel-forge/scripts/showcase.py wolf/idle wolf/run wolf/attack --root output --out wolf.gif
```

Render a static item:

```bash
python skills/pixel-forge/scripts/pixel_art.py render demo/items/key.json --out output/key --scale 8 --grid
```

Regenerate every image in this README:

```bash
python demo/make_readme_media.py
```

## Use it as an agent skill

Copy `skills/pixel-forge` into your agent's skills folder (for Codex, `~/.codex/skills/pixel-forge`), then ask for an asset:

> `$pixel-forge` make a dark hooded ghost that floats above the ground, with float, hurt and death animations.

> `$pixel-forge` make a set of 32×32 dungeon items: a chest, a key and a health potion.

The skill reads `SKILL.md` and the references (`format.md` for static JSON, `rig.md` for characters and animation). It writes the spec, renders, inspects the frames and delivers the sheets.

## Repository layout

```text
skills/pixel-forge/          the skill: SKILL.md, references, scripts and tests
  scripts/pixel_art.py       static renderer and patch tool
  scripts/rig2d.py           rigged characters and animation export
  scripts/rig_presets.py     rigs and animation presets
  scripts/cutout_tools.py    draw ops and splitting cutout regions onto bones
  scripts/palette_tools.py   hue-shifted color ramps
  scripts/polish.py          clean-up, anti-aliasing, lighting passes, textures, smears
  scripts/lint.py            aesthetic lint for rendered sprites
examples/characters/          character specs: knight, mage, sorceress, orc, slime, serpent,
                             raven, wolf and ghost (cutout), wolf-vector and ghost-vector
demo/items/                  item sources (editable JSON) and their build script
demo/make_readme_media.py    rebuilds docs/images
evaluation/                  early baseline and tool-review material
```

## Limits

- Characters are side view, facing right. Turnarounds and top-down directions are not generated.
- Pixels are opaque or transparent; there is no blended alpha.
- Motions beyond the presets need a new preset function.
- Generated characters reach clean indie quality, especially with cutout layers and hand touch-ups, but are not guaranteed to match hand-made commercial pixel art.

## License

[MIT](LICENSE). The code, the skill and the example assets may be used in your own projects, including commercial games.
