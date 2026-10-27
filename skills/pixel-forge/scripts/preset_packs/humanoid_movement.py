"""Humanoid movement pack: run, jump (full and physics-driven pieces), land, crouch, crouch walk,
sneak, dash, ladder climb and push.

Angles follow rig.md: hip_*/sh_* are world angles (0 = straight down, positive = forward), knee_*
bends the shin back, el_* bends the forearm forward, ankle_* < 0 points the toes down. Negative
dy lifts the whole character. Fixed joints passed in the spec entry (**rest) win over the motion.

Low poses (crouch, crouch_walk, the jump's crouch and landing squash, the dash stretch) use
plant "all", so a long robe or tabard rests on the ground instead of being clipped below it.
Pass "plant": "feet" in the anim entry to ground the feet instead (a deeper crouch for
characters without long hems).
Timings follow docs/research/animation-timing.md.
"""
import math

import rig_presets as base


def _frame(start, rest, **changes):
    """A frame built on the start pose; the spec's fixed joints (rest) always win."""
    return {**start, **changes, **rest}


def _cycle(frames, ms, rest, make):
    start = base.pose("humanoid", **rest)
    return [(_frame(start, rest, **make(2 * math.pi * i / frames)), ms) for i in range(frames)]


def run(frames=8, ms=75, stride=38, knee=95, arm=48, lift=3, **rest):
    """Run cycle with a flight phase: forward lean, arms pumping with bent elbows, knees driving high.
    stride: thigh swing (deg), knee: heel kick on the recovery swing, arm: shoulder swing,
    lift: pixels of flight between steps. Cyclic: frames x ms."""
    def make(t):
        out = {"lean": 16, "head": -12}
        for side, phase in (("n", 0.0), ("f", math.pi)):
            a = t + phase
            out["hip_" + side] = 12 + stride * math.sin(a)
            # Folded tight while the leg swings through, opening as it reaches for the next contact.
            out["knee_" + side] = 14 + knee * max(0.0, math.cos(a - 0.35)) ** 1.4
            out["ankle_" + side] = -12 * max(0.0, -math.sin(a))  # toe pushes off behind the body
        out["sh_n"] = 6 - arm * math.sin(t)
        out["sh_f"] = 6 + arm * math.sin(t)
        out["el_n"] = 85 + 20 * math.sin(t)
        out["el_f"] = 85 - 20 * math.sin(t)
        out["grip_n"] = -10  # a held weapon points forward along the pumping forearm, clear of the face
        # Lowest at mid-stance (frame 0, squash), highest in the split flight pose: two bounces a cycle.
        out["dy"] = -lift * (1 - math.cos(2 * t)) / 2
        return out
    return _cycle(frames, ms, rest, make)


# ---------- jump ----------

def _jump_poses(start):
    """Key poses of a platformer jump. The body squashes deep before takeoff and on landing (knees
    bent, spine compressed with a negative `breathe`), stretches at takeoff, and tucks into a ball at
    the apex. The legs stay asymmetric in the air (one knee leading); both legs folded the same way
    reads as a sitting hop."""
    crouch = dict(start, lean=16, head=-8, hip_n=46, knee_n=88, hip_f=36, knee_f=80, ankle_n=4, ankle_f=4,
                  sh_n=-34, el_n=30, sh_f=-42, el_f=25, breathe=-0.08, plant="all")
    takeoff = dict(start, lean=6, head=-4, hip_n=12, knee_n=8, hip_f=-8, knee_f=6, ankle_n=-28, ankle_f=-32,
                   sh_n=48, el_n=30, sh_f=34, el_f=28, breathe=0.08)
    rise = dict(start, lean=8, head=-4, hip_n=62, knee_n=88, hip_f=-6, knee_f=40, ankle_n=-12, ankle_f=-26,
                sh_n=40, el_n=55, sh_f=24, el_f=50, breathe=0.02)
    apex = dict(start, lean=16, head=-10, hip_n=80, knee_n=118, hip_f=58, knee_f=104, ankle_n=-8, ankle_f=-14,
                sh_n=22, el_n=80, sh_f=10, el_f=74, breathe=-0.06)
    fall = dict(start, lean=4, head=-2, hip_n=24, knee_n=30, hip_f=12, knee_f=22, ankle_n=0, ankle_f=-6,
                sh_n=62, el_n=25, sh_f=-38, el_f=30, breathe=0.04)
    land = dict(start, lean=24, head=-14, hip_n=58, knee_n=104, hip_f=46, knee_f=96, ankle_n=6, ankle_f=6,
                sh_n=18, el_n=45, sh_f=-14, el_f=35, breathe=-0.12, plant="all")
    return crouch, takeoff, rise, apex, fall, land


def jump(ms=1.0, height=6, **rest):
    """Full one-shot jump in place: squash anticipation (knees deep, arms back), takeoff stretch (legs
    straight, toes down, arms up), rise with one knee leading, a tucked ball at the apex, fall with the
    legs reaching for the ground and the arms open, a deep landing squash, a small rebound, recover.
    height: apex lift in pixels (dy); about a fifth of the character's height reads well (the default 6
    suits a 40-pixel character; raise it for bigger ones and leave headroom in the canvas).
    ms scales all timings."""
    start = base.pose("humanoid", **rest)
    crouch, takeoff, rise, apex, fall, land = (_frame(p, rest) for p in _jump_poses(start))
    reach = _frame(dict(base.lerp(fall, start, 0.5), sh_n=fall["sh_n"] - 15, sh_f=fall["sh_f"] + 10), rest)
    touch = _frame(base.lerp(reach, land, 0.5), rest)
    rebound = _frame(dict(base.lerp(land, start, 0.75), breathe=0.04), rest)
    keys = [(_frame(base.lerp(start, crouch, 0.5), rest), 60), (crouch, 120),
            (dict(takeoff, dy=-0.3 * height), 50),
            (dict(rise, dy=-0.75 * height), 80),
            (dict(apex, dy=-height), 150),
            (dict(fall, dy=-0.7 * height), 80),
            (dict(reach, dy=-0.25 * height), 50),
            (touch, 50), (land, 120), (rebound, 90), (start, 110)]
    return base.timed(keys, ms)


def jump_rise(frames=2, ms=110, **rest):
    """Airborne rising pose for physics-driven jumps (the game moves the character; dy stays 0).
    Loopable: 1 or 2 frames (the second lets the arms and legs drift slightly)."""
    start = base.pose("humanoid", **rest)
    rise = _frame(_jump_poses(start)[2], rest)
    drift = _frame(dict(rise, sh_n=rise["sh_n"] + 8, sh_f=rise["sh_f"] + 8, knee_n=rise["knee_n"] + 6,
                        hip_n=rise["hip_n"] + 4), rest)
    return [(rise, ms), (drift, ms)][:max(1, min(2, frames))]


def jump_fall(frames=2, ms=110, **rest):
    """Airborne falling pose for physics-driven jumps: arms up and out, legs reaching for the ground.
    Loopable: 1 or 2 frames (the second flails the arms a little)."""
    start = base.pose("humanoid", **rest)
    fall = _frame(_jump_poses(start)[4], rest)
    flail = _frame(dict(fall, sh_n=fall["sh_n"] + 12, sh_f=fall["sh_f"] - 12, el_n=fall["el_n"] + 10,
                        hip_n=fall["hip_n"] - 4, hip_f=fall["hip_f"] + 4), rest)
    return [(fall, ms), (flail, ms)][:max(1, min(2, frames))]


def land(ms=1.0, **rest):
    """Landing: knees buckle into a squash, then recover to rest. ms scales all timings."""
    start = base.pose("humanoid", **rest)
    squash = _frame(_jump_poses(start)[5], rest)
    keys = [(squash, 120), (_frame(base.lerp(squash, start, 0.45), rest), 110),
            (_frame(base.lerp(squash, start, 0.8), rest), 110), (start, 120)]
    return base.timed(keys, ms)


# ---------- low and quiet movement ----------

def _crouched(start):
    return dict(start, lean=26, head=-20, hip_n=72, knee_n=125, hip_f=58, knee_f=118, ankle_n=8, ankle_f=8,
                sh_n=30, el_n=55, sh_f=10, el_f=45, plant="all")


def crouch(ms=1.0, **rest):
    """Drop into a crouch and hold it (ends crouched by design; play crouch_walk or reverse it to stand).
    ms scales all timings."""
    start = base.pose("humanoid", **rest)
    low = _frame(_crouched(start), rest)
    dip = _frame(dict(low, lean=30, head=-22, hip_n=76, knee_n=132, hip_f=62, knee_f=126), rest)
    return base.timed([(_frame(base.lerp(start, low, 0.5), rest), 70), (dip, 80), (low, 240)], ms)


def crouch_walk(frames=8, ms=110, stride=20, knee=28, **rest):
    """Cyclic low walk in a crouch: short steps, body kept low and level. stride: thigh swing (deg),
    knee: extra bend on the forward swing."""
    def make(t):
        out = {"lean": 26, "head": -20, "sh_n": 28 - 10 * math.sin(t), "el_n": 55,
               "sh_f": 12 + 10 * math.sin(t), "el_f": 45, "plant": "all"}
        for side, phase in (("n", 0.0), ("f", math.pi)):
            a = t + phase
            out["hip_" + side] = 58 + stride * math.sin(a)
            out["knee_" + side] = 108 + knee * max(0.0, math.cos(a)) - 10 * max(0.0, -math.sin(a))
            out["ankle_" + side] = 6
        return out
    return _cycle(frames, ms, rest, make)


def sneak(frames=8, ms=140, stride=24, lift=55, **rest):
    """Slow tip-toe walk: hunched forward, hands raised in front, knees lifted high, toes pointed.
    stride: thigh swing (deg), lift: knee bend while a foot is raised."""
    def make(t):
        out = {"lean": 20, "head": -18, "sh_n": 55 + 6 * math.sin(t), "el_n": 75,
               "sh_f": 45 - 6 * math.sin(t), "el_f": 70}
        for side, phase in (("n", 0.0), ("f", math.pi)):
            a = t + phase
            raised = max(0.0, math.cos(a))
            out["hip_" + side] = 18 + stride * math.sin(a) + 22 * raised
            out["knee_" + side] = 22 + lift * raised
            out["ankle_" + side] = -30 - 10 * raised  # on the toes the whole time
        return out
    return _cycle(frames, ms, rest, make)


# ---------- bursts and effort ----------

def dash(ms=1.0, reach=7, **rest):
    """Short dash: a 1-frame freeze-like anticipation, a strongly leaning stretched pose moving
    forward by dx, a brake frame, then settle. reach: pixels travelled (dx). ms scales all timings.
    The last frames keep the dx; align by the manifest pivot in the engine."""
    start = base.pose("humanoid", **rest)
    gather = _frame(start, rest, lean=-4, head=4, hip_n=26, knee_n=40, hip_f=-10, knee_f=30,
                    sh_n=-20, el_n=50, sh_f=-30, el_f=40)
    stretch = _frame(start, rest, lean=38, head=-26, hip_n=55, knee_n=30, hip_f=-45, knee_f=20, ankle_f=-30,
                     sh_n=-60, el_n=45, sh_f=-75, el_f=20, dx=0.55 * reach, plant="all")
    brake = _frame(start, rest, lean=-14, head=8, hip_n=50, knee_n=4, ankle_n=22, hip_f=-4, knee_f=70,
                   sh_n=60, el_n=20, sh_f=35, el_f=25, dx=reach)
    keys = [(gather, 50), (stretch, 60), (dict(stretch, dx=0.9 * reach), 60), (brake, 90),
            (_frame(base.lerp(brake, dict(start, dx=reach), 0.6), rest), 100), (dict(start, dx=reach), 120)]
    return base.timed(keys, ms)


def climb(frames=6, ms=120, reach=30, knee=45, **rest):
    """Ladder climb in place, seen from the side (facing the ladder): hands reach up alternately,
    the opposite knee lifts to the next rung. The game moves the character up. reach: arm swing (deg),
    knee: knee lift (deg)."""
    def make(t):
        s = math.sin(t)
        hi_n, hi_f = max(0.0, s), max(0.0, -s)
        return {"lean": 4, "head": -8,
                "sh_n": 140 + reach * s, "el_n": 30 - 25 * s,
                "sh_f": 140 - reach * s, "el_f": 30 + 25 * s,
                # contralateral: the far knee lifts while the near hand reaches up, and the reverse.
                "hip_f": 15 + 50 * hi_n, "knee_f": 15 + 2 * knee * hi_n, "ankle_f": 4,
                "hip_n": 15 + 50 * hi_f, "knee_n": 15 + 2 * knee * hi_f, "ankle_n": 4}
    return _cycle(frames, ms, rest, make)


def push(frames=8, ms=140, stride=20, **rest):
    """Leaning into a heavy object: both arms forward, slow digging steps. stride: thigh swing (deg)."""
    def make(t):
        shove = math.sin(2 * t)
        out = {"lean": 30, "head": -26, "sh_n": 80 + 4 * shove, "el_n": 22 - 8 * shove,
               "sh_f": 74 + 4 * shove, "el_f": 26 - 8 * shove, "dy": 0}
        for side, phase in (("n", 0.0), ("f", math.pi)):
            a = t + phase
            out["hip_" + side] = -10 + stride * math.sin(a)
            out["knee_" + side] = 12 + 40 * max(0.0, math.cos(a)) ** 1.5
            out["ankle_" + side] = -10 * max(0.0, -math.sin(a))
        return out
    return _cycle(frames, ms, rest, make)


ANIMS = {"humanoid": {"run": run, "jump": jump, "jump_rise": jump_rise, "jump_fall": jump_fall, "land": land,
                      "crouch": crouch, "crouch_walk": crouch_walk, "sneak": sneak, "dash": dash,
                      "climb": climb, "push": push}}
LOOPING = {"run", "jump_rise", "jump_fall", "crouch_walk", "sneak", "climb", "push"}
