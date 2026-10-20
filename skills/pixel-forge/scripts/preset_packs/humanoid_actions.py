"""Humanoid action pack: spell casting, bow, throw, emotes, sitting, sleeping, stun and knockback.

Angles follow references/rig.md: limbs 0 = straight down, 90 = straight forward, 180 = straight up,
negative = backward. Every frame starts from base.pose("humanoid", **rest) and the spec entry's fixed
joint values (**rest) are applied last, so they reach every frame. Held items (weapon_n, weapon_f) are
aimed at a world angle per key pose, so a staff or sword stays sensible while the arm moves; a fixed
grip_n / grip_f in the spec entry overrides that.
"""
import math

import rig_presets as base

H = "humanoid"


def _keyer(rest):
    """Return (start pose, key builder). key(**changes) = rest pose + changes, with fixed values on top.
    key(aim_n=deg) points the near held item (weapon_n) at a world angle by solving grip_n."""
    start = base.pose(H, **rest)

    def key(aim_n=None, aim_f=None, **changes):
        pose = {**start, **changes}
        # aim_*: the held item's world angle (limb convention); grip is solved from the arm unless fixed.
        for side, aim in (("n", aim_n), ("f", aim_f)):
            if aim is not None:
                pose["grip_" + side] = aim - pose["sh_" + side] - pose["el_" + side]
        return {**pose, **rest}

    return start, key


def _fix(frames, rest):
    """Keep the entry's fixed joint values on every frame (lerp output included)."""
    return [({**p, **rest}, d) for p, d in frames]


# ---------- spell casting ----------

def cast(ms=1.0, charge=300, **rest):
    """Spell cast with the near hand: raise and gather, hold the charge, thrust the hand forward to
    release, recover. charge: milliseconds the gathered pose is held (split into ~120 ms shimmer frames;
    0 skips the hold); it is not scaled by ms. ms scales the other timings."""
    start, key = _keyer(rest)
    ready = key(hip_n=10, knee_n=12, hip_f=-10, knee_f=10, sh_n=40, el_n=60, sh_f=10, el_f=40, aim_n=145)
    gather_legs = dict(lean=-7, hip_n=14, knee_n=18, hip_f=-14, knee_f=14)
    gather = key(**gather_legs, head=-8, sh_n=100, el_n=60, sh_f=50, el_f=75, aim_n=158)
    gather2 = key(**gather_legs, head=-10, sh_n=103, el_n=57, sh_f=54, el_f=70, aim_n=161)
    thrust_legs = dict(hip_n=28, knee_n=24, hip_f=-20, knee_f=6, sh_f=-30, el_f=30)
    thrust = key(**thrust_legs, lean=12, head=4, sh_n=86, el_n=-6, aim_n=134)
    extend = key(**thrust_legs, lean=14, head=4, sh_n=84, el_n=-2, aim_n=138)
    keys = [(start, 90), (ready, 90), (base.lerp(ready, gather, 0.5), 70), (gather, 140)]
    if charge > 0:
        steps = max(1, round(charge / 120))
        for i in range(steps):
            keys.append((gather2 if i % 2 == 0 else gather, charge / steps / ms))
    keys += [(thrust, 60), (extend, 170), (base.lerp(extend, start, 0.5), 120), (start, 130)]
    return _fix(base.timed(keys, ms), rest)


def cast_loop(frames=6, ms=110, sway=5, **rest):
    """Channeling a sustained spell: both arms raised forward, slight sway. Looping."""
    _, key = _keyer(rest)
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        s = math.sin(t)
        out.append((key(lean=-4 + 2 * s, head=-7 + 2 * math.sin(t - 0.8),
                        hip_n=10, knee_n=14 + 3 * s, hip_f=-12, knee_f=12 + 3 * s,
                        sh_n=118 + sway * s, el_n=28 + sway * 0.6 * math.sin(t - 0.6),
                        sh_f=105 + sway * math.sin(t + 0.5), el_f=32 + sway * 0.6 * math.sin(t - 0.1),
                        aim_n=128 + 3 * s), ms))
    return out


# ---------- ranged ----------

def shoot_bow(ms=1.0, **rest):
    """Bow shot: far arm forward holding the bow (weapon_f is aimed straight up, so a bow drawn along
    weapon_f stands upright), near hand draws back to the cheek, hold at full draw, release snap,
    follow-through, recover. ms scales all timings."""
    start, key = _keyer(rest)
    stance = dict(hip_n=14, knee_n=10, hip_f=-16, knee_f=10)
    nock = key(**stance, lean=2, sh_f=75, el_f=15, aim_f=175, sh_n=70, el_n=20, aim_n=150)
    draw = key(**stance, lean=0, head=-1, sh_f=86, el_f=4, aim_f=180, sh_n=-20, el_n=130, aim_n=170)
    full = key(**stance, lean=-2, head=-2, sh_f=90, el_f=0, aim_f=180, sh_n=-100, el_n=178, aim_n=180)
    release = key(**stance, lean=-2, head=-3, sh_f=93, el_f=0, aim_f=182, sh_n=-128, el_n=105, aim_n=150)
    follow = key(**stance, lean=-1, head=-2, sh_f=88, el_f=2, aim_f=180, sh_n=-120, el_n=88, aim_n=140)
    keys = [(start, 70), (nock, 100), (draw, 90), (full, 240), (release, 50),
            (follow, 140), (base.lerp(follow, start, 0.5), 100), (start, 90)]
    return _fix(base.timed(keys, ms), rest)


def throw(ms=1.0, **rest):
    """Overhand throw: wind back overhead (hold), release with a smear on weapon_n, follow-through.
    ms scales all timings."""
    start, key = _keyer(rest)
    legs = dict(hip_n=22, knee_n=10, hip_f=-24, knee_f=18)
    cock = key(**legs, lean=-4, head=-4, sh_n=130, el_n=60, sh_f=40, el_f=30, aim_n=230)
    windup = key(**legs, lean=-5, head=-2, sh_n=186, el_n=45, sh_f=75, el_f=10, aim_n=212)
    release = key(hip_n=30, knee_n=26, hip_f=-26, knee_f=6, lean=14, head=4,
                  sh_n=100, el_n=-5, sh_f=-30, el_f=30, aim_n=110, smear="weapon_n")
    follow = key(hip_n=32, knee_n=30, hip_f=-24, knee_f=6, lean=18, head=6,
                 sh_n=35, el_n=10, sh_f=-40, el_f=30, aim_n=80)
    keys = [(start, 40), (cock, 60), (windup, 120), (release, 50), (follow, 90),
            (base.lerp(follow, start, 0.5), 70), (start, 60)]
    return _fix(base.timed(keys, ms), rest)


# ---------- emotes ----------

def wave(frames=6, ms=110, swing=30, **rest):
    """Friendly wave: near arm raised in front of the face, forearm swinging. Looping."""
    _, key = _keyer(rest)
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        s = math.sin(t)
        out.append((key(lean=-2, head=-6 + 2 * s, sh_n=112 + 8 * s, el_n=48 + swing * s,
                        sh_f=-6, el_f=25, aim_n=134 + swing * 0.4 * s), ms))
    return out


def cheer(ms=1.0, **rest):
    """Victory jump-pump: crouch, hop with both arms thrown up, land, pump the fists, settle.
    ms scales all timings."""
    start, key = _keyer(rest)
    crouch = key(lean=14, head=6, hip_n=50, knee_n=70, hip_f=40, knee_f=64, sh_n=-30, el_n=30, sh_f=-40, el_f=25,
                 aim_n=150, plant="all")
    jump = key(lean=-2, head=-12, hip_n=14, knee_n=34, hip_f=-6, knee_f=44, sh_n=142, el_n=12,
               sh_f=138, el_f=12, aim_n=108, dy=-3)
    apex = key(lean=-3, head=-12, hip_n=20, knee_n=44, hip_f=0, knee_f=50, sh_n=148, el_n=12,
               sh_f=144, el_f=12, aim_n=110, dy=-4)
    land = key(lean=10, head=-4, hip_n=50, knee_n=60, hip_f=40, knee_f=55, sh_n=135, el_n=12, sh_f=125, el_f=12,
               aim_n=132)
    pump_up = key(lean=-3, head=-10, hip_n=8, knee_n=10, hip_f=-8, knee_f=10, sh_n=160, el_n=12,
                  sh_f=152, el_f=12, aim_n=128)
    pump_down = key(lean=-1, head=-6, hip_n=10, knee_n=16, hip_f=-8, knee_f=16, sh_n=118, el_n=12,
                    sh_f=110, el_f=12, aim_n=130)
    keys = [(start, 70), (crouch, 110), (jump, 90), (apex, 110), (land, 90), (pump_up, 130),
            (pump_down, 90), (pump_up, 160), (base.lerp(pump_up, start, 0.5), 110), (start, 110)]
    return _fix(base.timed(keys, ms), rest)


def taunt(ms=1.0, **rest):
    """Provoking gesture: chest out, chin up, far hand on the hip, beckon twice with the near hand.
    ms scales all timings."""
    start, key = _keyer(rest)
    smug = dict(lean=-8, head=-10, hip_n=12, knee_n=6, hip_f=-12, knee_f=6, sh_f=-40, el_f=95)
    open_ = key(**smug, sh_n=62, el_n=22, aim_n=120)
    curl = key(**smug, sh_n=56, el_n=118, aim_n=200)
    hold = key(**dict(smug, head=-13, lean=-9), sh_n=50, el_n=40, aim_n=150)
    keys = [(start, 80), (open_, 140), (curl, 110), (open_, 90), (curl, 110), (open_, 90), (hold, 220),
            (base.lerp(hold, start, 0.5), 110), (start, 100)]
    return _fix(base.timed(keys, ms), rest)


# ---------- sitting and sleeping ----------

LIE_DX = 10  # lying poses move the hip forward so the head stays on the canvas (the pivot records it)


def _squat(key):
    """Feet planted, thighs forward, shins upright: the way down to the ground."""
    return key(lean=26, head=4, hip_n=72, knee_n=76, hip_f=64, knee_f=70, sh_n=50, el_n=30, sh_f=35, el_f=30,
               aim_n=150, plant="all")


def _seated(key, breath=0.0):
    """Seated on the ground: near knee raised, far leg out, near hand on the knee, leaning on the far hand."""
    return key(lean=-8 + breath * 1.5, head=-2 * breath, hip_n=95, knee_n=105, hip_f=92, knee_f=18,
               sh_n=55 - breath * 2, el_n=25, sh_f=-30 - breath, el_f=10, aim_n=140, plant="all")


def _lying(key, breath=0.0):
    """Asleep on the back: near knee up, hands on the belly, held item laid along the body."""
    return key(lean=-88 + breath, head=-6 + breath, hip_n=120, knee_n=95, hip_f=92, knee_f=8,
               sh_n=92 + breath * 3, el_n=50, sh_f=86 + breath * 2, el_f=40, aim_n=165, dx=LIE_DX, plant="all")


def sit(ms=1.0, **rest):
    """Sit down on the ground and stay seated (one-shot ending seated; follow with sit_idle).
    ms scales all timings."""
    start, key = _keyer(rest)
    seated = _seated(key)
    settle = dict(seated, lean=-12, head=-3)
    keys = [(start, 80), (_squat(key), 130), (settle, 110), (seated, 400)]
    return _fix(base.timed(keys, ms), rest)


def sit_idle(frames=4, ms=220, **rest):
    """Seated breathing loop for after sit. Looping."""
    _, key = _keyer(rest)
    return [(_seated(key, (1 - math.cos(2 * math.pi * i / frames)) / 2), ms) for i in range(frames)]


def sleep(ms=1.0, **rest):
    """Sit, lie back and fall asleep (one-shot ending lying; follow with sleep_idle). The lying pose is
    shifted forward by LIE_DX pixels. ms scales all timings."""
    start, key = _keyer(rest)
    recline = key(lean=-50, head=-6, hip_n=110, knee_n=100, hip_f=95, knee_f=20, sh_n=60, el_n=30,
                  sh_f=-20, el_f=20, aim_n=150, dx=LIE_DX, plant="all")
    keys = [(start, 80), (_squat(key), 130), (_seated(key), 160), (recline, 120), (_lying(key), 600)]
    return _fix(base.timed(keys, ms), rest)


def sleep_idle(frames=4, ms=350, **rest):
    """Slow sleeping breath while lying on the back. Looping."""
    _, key = _keyer(rest)
    return [(_lying(key, 1 - math.cos(2 * math.pi * i / frames)), ms) for i in range(frames)]


# ---------- reactions ----------

def stunned(frames=8, ms=110, wobble=9, **rest):
    """Dizzy loop: wobbling lean, head lolling behind the body, arms hanging loose. Looping."""
    _, key = _keyer(rest)
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        s = math.sin(t)
        out.append((key(lean=4 + wobble * s, head=12 - 2 * wobble * math.sin(t - 1.1),
                        hip_n=12 + 4 * s, knee_n=20 + 6 * math.sin(2 * t), hip_f=-8 + 4 * s,
                        knee_f=18 - 6 * math.sin(2 * t),
                        sh_n=2 - 12 * math.sin(t - 0.9), el_n=10 + 8 * math.sin(t - 1.4),
                        sh_f=-6 - 12 * math.sin(t - 1.3), el_f=8 + 8 * math.sin(t - 1.8),
                        aim_n=110 - 12 * math.sin(t - 1.2), dx=round(math.sin(t))), ms))
    return out


def knockback(ms=1.0, distance=6, lift=4, **rest):
    """Heavy hit: flash, thrown backward (dx) and briefly airborne (dy), land on the feet, stagger, rest.
    distance: pixels travelled backward; lift: peak height in pixels. Ends at rest shifted by -distance
    (the pivot records the shift); give the anim a pose_offset dx if the canvas is tight behind.
    ms scales all timings."""
    start, key = _keyer(rest)
    d = distance
    hit = key(lean=-12, head=-12, sh_n=60, el_n=30, sh_f=40, el_f=30, hip_n=20, knee_n=20, hip_f=8, knee_f=20,
              dx=-1, flash=1)
    fly = key(lean=-22, head=-8, sh_n=95, el_n=25, sh_f=70, el_f=25, hip_n=40, knee_n=34, hip_f=22, knee_f=44,
              dx=-0.55 * d, dy=-lift)
    fall = key(lean=-16, head=-4, sh_n=80, el_n=25, sh_f=55, el_f=25, hip_n=30, knee_n=24, hip_f=10, knee_f=30,
               dx=-0.85 * d, dy=-0.5 * lift)
    land = key(lean=4, head=6, sh_n=40, el_n=30, sh_f=20, el_f=30, hip_n=30, knee_n=56, hip_f=12, knee_f=50,
               dx=-d)
    stagger = key(lean=-8, head=-4, sh_n=20, el_n=30, sh_f=-10, el_f=25, hip_n=16, knee_n=18, hip_f=-22,
                  knee_f=14, dx=-d - 1)
    end = dict(start, dx=-d)
    keys = [(hit, 60), (fly, 70), (fall, 50), (land, 60), (stagger, 80), (base.lerp(stagger, end, 0.5), 70),
            (end, 80)]
    return _fix(base.timed(keys, ms), rest)


ANIMS = {H: {"cast": cast, "cast_loop": cast_loop, "shoot_bow": shoot_bow, "throw": throw, "wave": wave,
             "cheer": cheer, "sit": sit, "sit_idle": sit_idle, "sleep": sleep, "sleep_idle": sleep_idle,
             "stunned": stunned, "knockback": knockback, "taunt": taunt}}
LOOPING = {"cast_loop", "wave", "sit_idle", "sleep_idle", "stunned"}
