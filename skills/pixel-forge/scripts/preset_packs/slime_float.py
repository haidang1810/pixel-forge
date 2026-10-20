"""Slime and floating-humanoid (ghost, spirit) presets.

Slime: bounce_slam, wobble, spit, split, melt_in, rise, crawl.
Floating humanoid: float_attack, vanish, appear, haunt. These start from the hover pose of the
built-in "float" preset, so the legs keep trailing as wisps.

Slime ratios follow docs/research/proportions.md: a squash goes to about 0.6x height (here down to
0.46 for a puddle, which is about 40 px wide on the standard 12 px slime), a stretch to about 1.3-1.4x.
"""
import math

import rig_presets as base


def _slime(**rest):
    return base.pose("slime", **rest)


def _hover(**rest):
    """The first frame of the built-in float preset: the hover pose with trailing wisps."""
    return base.float_(frames=8, **rest)[0][0]


# ---------- slime ----------

def bounce_slam(ms=1.0, height=11, **rest):
    """Big jump attack: deep squash, high stretched leap, squash slam on landing with a short hold.
    height: apex lift in pixels (keep within the canvas; 11 fits a 32 px tall slime canvas)."""
    b = _slime(**rest)
    keys = [(b, 90),
            (dict(b, stretch=0.78, lean=-3), 70),
            (dict(b, stretch=0.6, lean=-5), 220),                          # deep squash, held (telegraph)
            (dict(b, stretch=1.38, lean=4, dy=-2), 60),                     # launch, 1 frame
            (dict(b, stretch=1.22, lean=5, dy=-0.7 * height), 80),
            (dict(b, stretch=1.05, lean=2, dy=-height), 130),               # apex hold
            (dict(b, stretch=1.3, lean=6, dy=-0.45 * height), 50),          # dive, stretched
            (dict(b, stretch=0.5, lean=0, dx=1), 60),                       # slam
            (dict(b, stretch=0.52, dx=1), 200),                             # impact hold
            (dict(b, stretch=1.12, lean=-2), 100),
            (dict(b, stretch=0.94), 90),
            (b, 120)]
    return base.timed(keys, ms)


def wobble(frames=8, ms=110, amp=0.22, lean=10, decay=0.72, **rest):
    """Jelly jiggle (idle variant): alternating tall/lean-forward and flat/lean-back at decaying
    amplitude; each loop restarts the jiggle. amp: first stretch offset; lean: first lean in degrees;
    decay: amplitude kept per frame."""
    out = []
    for i in range(frames):
        k = decay ** i * (1 - i / frames)
        sign = 1 if i % 2 == 0 else -1
        out.append((_slime(**{"stretch": 1 + sign * amp * k, "lean": sign * lean * k, **rest}), ms))
    return out


def spit(ms=1.0, **rest):
    """Puff up (stretch, lean back), spit forward (lean forward, squash), recover.
    The projectile itself is a separate sprite in the game; spawn it on the 4th frame."""
    b = _slime(**rest)
    keys = [(b, 90),
            (dict(b, stretch=1.18, lean=-8), 110),
            (dict(b, stretch=1.3, lean=-14, dx=-1), 200),                   # puffed, held
            (dict(b, stretch=0.74, lean=16, dx=1), 60),                     # spit
            (dict(b, stretch=0.8, lean=12, dx=1), 140),
            (dict(b, stretch=1.08, lean=-3), 100),
            (dict(b, stretch=0.96, lean=1), 90),
            (b, 120)]
    return base.timed(keys, ms)


def split(ms=1.0, **rest):
    """Prepare to split: pulse tall and wide with growing amplitude, ending flat and wide.
    The game spawns two small slimes on the last frame."""
    b = _slime(**rest)
    keys = [(b, 100),
            (dict(b, stretch=0.88, lean=-2), 90), (dict(b, stretch=1.08, lean=2), 80),
            (dict(b, stretch=0.78, lean=-4, dx=-1), 90), (dict(b, stretch=1.16, lean=4, dx=1), 80),
            (dict(b, stretch=0.66, lean=-6, dx=-1), 90), (dict(b, stretch=1.26, lean=6, dx=1), 70),
            (dict(b, stretch=0.52, flash=1), 60),
            (dict(b, stretch=0.52), 300)]
    return base.timed(keys, ms)


def melt_in(ms=1.0, puddle=0.46, **rest):
    """Sink into a puddle and stay there (pair with rise). puddle: final stretch."""
    b = _slime(**rest)
    keys = [(b, 100),
            (dict(b, stretch=1.08), 80),                                    # small anticipation up
            (dict(b, stretch=0.82, lean=-3), 100),
            (dict(b, stretch=0.66, lean=2), 100),
            (dict(b, stretch=0.54, lean=-1), 110),
            (dict(b, stretch=puddle), 400)]
    return base.timed(keys, ms)


def rise(ms=1.0, puddle=0.46, **rest):
    """Rise out of a puddle back to rest (pair with melt_in). puddle: starting stretch."""
    b = _slime(**rest)
    keys = [(dict(b, stretch=puddle), 200),
            (dict(b, stretch=0.56), 100),
            (dict(b, stretch=0.78, lean=-2), 80),
            (dict(b, stretch=1.2, lean=2), 80),                             # overshoot
            (dict(b, stretch=0.9, lean=-1), 100),
            (dict(b, stretch=1.05), 90),
            (b, 120)]
    return base.timed(keys, ms)


def crawl(frames=8, ms=110, reach=0.14, lean=12, **rest):
    """Slow inching crawl in place: the top stretches forward, then the body squashes and pulls up.
    reach: stretch offset; lean: forward lean while reaching."""
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        s = math.sin(t)
        frame = {"stretch": 1 + reach * s, "lean": lean * max(0.0, s) - 4 * max(0.0, -s) + 2,
                 "dx": 1 if s > 0.5 else 0}
        out.append((_slime(**{**frame, **rest}), ms))
    return out


# ---------- floating humanoid ----------

def float_attack(ms=1.0, smear="hand_n", **rest):
    """Hover lunge: pull back, swoop forward reaching with both arms, return.
    smear: bone traced on the strike frame (needs style polish smear)."""
    b = _hover(**rest)
    back = dict(b, lean=-10, head=-6, dx=-2, dy=b.get("dy", 0) - 1, sh_n=-35, el_n=70, sh_f=-50, el_f=60,
                hip_n=-15, hip_f=-30)
    swoop = dict(b, lean=22, head=8, dx=4, sh_n=95, el_n=0, sh_f=75, el_f=5,
                 hip_n=-60, knee_n=30, hip_f=-75, knee_f=30, smear=smear)
    reach = dict(swoop, lean=24, dx=5, sh_n=90, el_n=5, sh_f=70)
    del reach["smear"]
    keys = [(b, 100), (base.lerp(b, back, 0.5), 80), (back, 220), (swoop, 60), (reach, 140),
            (base.lerp(reach, b, 0.5), 110), (b, 140)]
    return base.timed(keys, ms)


def vanish(ms=1.0, steps=5, rise=1, **rest):
    """Fade out with a dissolve while drifting up; ends invisible. steps: dissolve frames;
    rise: pixels up per frame."""
    b = _hover(**rest)
    lift = dict(b, lean=-2, head=-4, sh_n=40, el_n=30, sh_f=10, el_f=25)
    return base.timed([(b, 120), (lift, 120)], ms) + base.fade(lift, steps, round(90 * ms), rise=rise)


def appear(ms=1.0, steps=5, rise=1, **rest):
    """Fade in from fully dissolved, settling down into the hover pose; starts invisible."""
    b = _hover(**rest)
    lift = dict(b, lean=-2, head=-4, sh_n=40, el_n=30, sh_f=10, el_f=25)
    fading = list(reversed(base.fade(lift, steps, round(90 * ms), rise=rise)))
    return fading + base.timed([(lift, 120), (base.lerp(lift, b, 0.5), 90), (b, 140)], ms)


def haunt(frames=8, ms=150, sway=12, bob=2, wave=20, **rest):
    """Slow menacing hover with arms raised forward and a wide side-to-side sway."""
    out = []
    for (p, _), i in zip(base.float_(frames=frames, bob=bob, wave=wave), range(frames)):
        t = 2 * math.pi * i / frames
        frame = dict(p, dx=1.5 * math.sin(t), lean=4 + 3 * math.sin(t - 0.6), head=-2 * math.sin(t - 1.2),
                     sh_n=80 + sway * math.sin(t + 0.4), el_n=10 + sway * 0.5 * math.sin(t - 0.4),
                     sh_f=70 + sway * math.sin(t + 0.9), el_f=10 + sway * 0.5 * math.sin(t + 0.1))
        out.append(({**frame, **rest}, ms))
    return out


ANIMS = {
    "slime": {"bounce_slam": bounce_slam, "wobble": wobble, "spit": spit, "split": split,
              "melt_in": melt_in, "rise": rise, "crawl": crawl},
    "humanoid": {"float_attack": float_attack, "vanish": vanish, "appear": appear, "haunt": haunt},
}
LOOPING = {"wobble", "crawl", "haunt"}
