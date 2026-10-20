# Preset packs

Every `*.py` file in this folder (except names starting with `_`) is loaded by `rig_presets.load_packs()` at import time. A pack adds animation presets without touching the built-in ones.

## Contract

```python
import math
import rig_presets as base

def heavy_slash(ms=1.0, **rest):
    """Two-handed overhead smash: long windup, fast strike, heavy recovery. ms scales all timings."""
    guard = base.pose("humanoid", **rest, sh_n=15, el_n=50, grip_n=100)
    windup = dict(guard, sh_n=190, el_n=20, grip_n=60, lean=-8)
    strike = dict(guard, sh_n=95, el_n=-5, grip_n=20, lean=16, smear="weapon_n")
    return base.timed([(guard, 100), (windup, 220), (strike, 60), (dict(strike, lean=18), 160), (guard, 140)], ms)

ANIMS = {"humanoid": {"heavy_slash": heavy_slash}}
LOOPING = set()            # names of cyclic animations (they wrap for follow-through)
```

- **Families:** `humanoid` (also used by `chibi`), `quadruped`, `bird`, `serpent`, `slime`. Joint names and conventions are in `references/rig.md`.
- **Return value:** a list of `(pose, milliseconds)`.
  - A pose is a dict of joint angles plus optional keys: `dx`/`dy` (shift in pixels, negative `dy` is up), `flash: 1`, `dissolve: 0..1`, `plant: "all"` and `smear: "<bone>"`.
- **Signature:**
  - Every preset takes `**rest`: fixed joint values from the spec entry, which must reach every frame (start from `base.pose(family, **rest)`).
  - One-shot presets take `ms=1.0`, a timing scale.
  - Cyclic presets take `frames` and `ms` (per frame).
  - Extra parameters are allowed; give them defaults and document them in the docstring.
- **Helpers:**
  - `base.pose(family, **changes)`: the family's rest pose with some joints changed.
  - `base.lerp(a, b, t)`: a smoothstep blend of two poses.
  - `base.timed(keys, ms)`: scales the durations.
  - `base.fade(pose, steps, ms, rise=0)`: dissolve frames.
  - `base.over_the_top(pose)`: lets bird wings fold back over the top.
  - The rest poses themselves are `base.REST`, `base.QREST`, `base.BREST`, `base.RREST` and `base.SREST`.
- **Names:** new names only (a clash with an existing preset is an error). Use lower_snake_case.
- **Timing:** hold key poses and keep strike frames short (about 40–70 ms). Anticipation should be longer than the strike, and recovery longer than the strike. One-shot animations should end in, or near, the rest pose so they chain back to idle.

## Quality bar

Each preset must:
1. Read clearly as the named action in a side view at 1x and enlarged.
2. Keep feet on the ground (the renderer grounds them) except for deliberate airborne frames with negative `dy`.
3. Not push limbs, weapons or the head below the ground line or off a reasonable canvas. Weapons below the ground are clipped.
4. Avoid joints that flip through impossible angles. When blending wings or arms across 180°, pick the direction of travel explicitly.

## Checking a pack

Render a test character for every preset and inspect the result:

```text
python skills/pixel-forge/scripts/rig2d.py <spec>.json --out <scratch>/out --scale 6
python skills/pixel-forge/scripts/lint.py <scratch>/out
```

Look at `contact.png` and at least the key frames enlarged. Fix edge warnings. The example specs in `examples/characters/` make good test characters, but copy them into a scratch folder and change only `anims` there. Add a test file `scripts/tests/test_pack_<pack>.py` that renders every preset of the pack with `unittest`, and checks that the exit code is 0 and that grounded frames rest on the ground row.
