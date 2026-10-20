"""Quadruped preset pack: gaits (trot, stalk, sniff), resting poses (sit, lie down, sleep),
expressive actions (howl, shake, rear up) and combat moves (bite combo, charge, leap).

All quadruped angles are absolute (world space): limbs 0 = straight down, positive = forward;
neck from straight up; head > 0 = nose down; tail > 0 = raised. Changing pitch does not rotate
the legs, so seated and rearing poses set the leg angles for the ground directly.
"""
import functools
import inspect
import math

import rig_presets as base

LEGS = ("bn", "bf", "fn", "ff")


def _gait(pose, t, phases, swing, fold):
    """Swing the legs of `pose` on their own phases; fold the lower leg during the forward swing."""
    out = {}
    for leg, phase in phases.items():
        a = t + 2 * math.pi * phase
        lift = max(0.0, math.cos(a))
        out["hip_" + leg] = pose["hip_" + leg] + swing * math.sin(a)
        out["knee_" + leg] = pose["knee_" + leg] - fold * lift
        out["ankle_" + leg] = pose["ankle_" + leg] + fold * 0.8 * lift
    return out


def _back(hip, knee, ankle):
    return {"hip_bn": hip, "knee_bn": knee, "ankle_bn": ankle, "hip_bf": hip - 4, "knee_bf": knee + 4, "ankle_bf": ankle - 4}


def _front(hip, knee, ankle):
    return {"hip_fn": hip, "knee_fn": knee, "ankle_fn": ankle, "hip_ff": hip - 4, "knee_ff": knee - 3, "ankle_ff": ankle}


# ---------- shared key poses ----------

def _sit(rest):
    """Seated on the haunches: body tipped up, hind legs folded flat, front legs straight, tail on the ground."""
    return base.pose("quadruped", **dict(dict(
        pitch=-38, flex=-4, neck=12, head=6, tail=-6, tail2=8, tail3=10,
        **_back(72, -128, 144), **_front(4, 0, 0), plant="all"), **rest))


def _lying(rest):
    """Lying on the belly (sphinx): hind legs folded under, front legs stretched forward, head resting low."""
    return base.pose("quadruped", **dict(dict(
        pitch=2, flex=-2, neck=102, head=12, tail=-4, tail2=6, tail3=8,
        **_back(84, -152, 150), **_front(84, 4, 2), plant="all"), **rest))


def _crouch(rest, **extra):
    p = base.pose("quadruped", flex=8, pitch=3, neck=46, head=12, tail=-30, **_back(34, -90, 62), **_front(-26, 46, -10))
    p.update(extra)
    p.update(rest)
    return p


# ---------- gaits (looping) ----------

def trot(frames=8, ms=80, stride=24, fold=46, **rest):
    """Two-beat trot: diagonal pairs (back near + front far, back far + front near) move together,
    with a short lift at each push-off. Default 8 x 80 ms = 640 ms per cycle."""
    p = base.pose("quadruped", **rest)
    phases = {"bn": 0, "ff": 0, "bf": 0.5, "fn": 0.5}
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        bounce = math.sin(2 * t - 0.6)
        out.append((dict(p, **_gait(p, t, phases, stride, fold), pitch=p["pitch"] + 1.5 * math.sin(2 * t),
                         neck=p["neck"] + 10 + 2 * bounce, head=p["head"] + 4 - 3 * bounce,
                         tail=p["tail"] + 10 + 5 * math.sin(t), tail2=4 * math.sin(t - 1), tail3=5 * math.sin(t - 2),
                         dy=-1.5 * max(0.0, bounce)), ms))
    return out


def stalk(frames=8, ms=150, stride=10, fold=22, **rest):
    """Predator creep: body low on deeply bent legs, head low and level, slow lateral steps, tail low
    and still. Default 8 x 150 ms = 1200 ms per cycle."""
    p = base.pose("quadruped", **dict(dict(
        pitch=2, flex=4, neck=74, head=6, tail=-52, tail2=-4, tail3=4,
        **_back(36, -96, 64), **_front(-30, 54, -12)), **rest))
    phases = {"bn": 0, "fn": 0.25, "bf": 0.5, "ff": 0.75}
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(p, **_gait(p, t, phases, stride, fold), neck=p["neck"] + 1.5 * math.sin(2 * t)), ms))
    return out


def sniff(frames=8, ms=130, stride=12, fold=26, bob=8, **rest):
    """Slow walk with the nose down at the ground, bobbing as it sniffs (two bobs per cycle).
    Default 8 x 130 ms = 1040 ms per cycle."""
    p = base.pose("quadruped", **dict(dict(pitch=4, neck=104, head=58, tail=-12), **rest))
    phases = {"bn": 0, "fn": 0.25, "bf": 0.5, "ff": 0.75}
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(p, **_gait(p, t, phases, stride, fold), head=p["head"] + bob * math.sin(4 * t),
                         neck=p["neck"] - 3 * math.sin(4 * t), tail=p["tail"] + 8 * math.sin(t),
                         tail2=5 * math.sin(t - 1), tail3=6 * math.sin(t - 2)), ms))
    return out


# ---------- resting (one-shots end held; loops) ----------

def sit(ms=1.0, **rest):
    """Sit down on the haunches and hold (ends seated; chain into sit_idle)."""
    stand = base.pose("quadruped", **rest)
    seated = _sit(rest)
    lowering = dict(base.lerp(stand, seated, 0.5), plant="all")
    settle = dict(seated, pitch=seated["pitch"] - 3, neck=seated["neck"] - 4)
    return base.timed([(stand, 100), (lowering, 130), (settle, 110), (seated, 400)], ms)


def sit_idle(frames=4, ms=240, wag=8, **rest):
    """Seated breathing loop: small head bob and a tail sweep along the ground. Default 4 x 240 ms."""
    p = _sit(rest)
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(p, neck=p["neck"] - 2 * math.sin(t), head=p["head"] + 3 * math.sin(t),
                         flex=p["flex"] + 1.5 * math.sin(t), tail2=p["tail2"] + wag * math.sin(t),
                         tail3=p["tail3"] + wag * math.sin(t - 1)), ms))
    return out


def lie_down(ms=1.0, **rest):
    """Lie down: crouch, sink onto the belly, stretch the front legs forward and rest the head (ends lying)."""
    stand = base.pose("quadruped", **rest)
    lying = _lying(rest)
    crouch = dict(_crouch(rest, neck=60, head=16), plant="all")
    sink = dict(base.lerp(crouch, lying, 0.55), plant="all")
    head_up = dict(lying, neck=80, head=6)
    return base.timed([(stand, 100), (crouch, 140), (sink, 140), (head_up, 160), (lying, 500)], ms)


def sleep(frames=4, ms=350, **rest):
    """Slow breathing while lying (head down on the paws). Default 4 x 350 ms = 1.4 s per breath."""
    p = dict(_lying(rest), neck=108, head=16)
    p.update(rest)
    out = []
    for i in range(frames):
        s = math.sin(2 * math.pi * i / frames)
        out.append((dict(p, flex=p["flex"] - 2.5 * s, neck=p["neck"] - 2 * s, head=p["head"] + 2 * s,
                         tail2=p["tail2"] + 2 * s), ms))
    return out


# ---------- actions (one-shots) ----------

def howl(ms=1.0, **rest):
    """Sit back on the haunches, throw the head up and hold the howl, then stand back up."""
    stand = base.pose("quadruped", **rest)
    seated = _sit(rest)
    inhale = dict(seated, neck=seated["neck"] + 12, head=seated["head"] + 18)
    howl1 = dict(seated, pitch=seated["pitch"] - 4, neck=-6, head=-58, tail2=seated["tail2"] + 4)
    howl2 = dict(howl1, neck=-10, head=-62)
    rise = dict(base.lerp(seated, stand, 0.5), plant="all")
    return base.timed([(stand, 100), (dict(base.lerp(stand, seated, 0.5), plant="all"), 120), (seated, 120),
                       (inhale, 160), (howl1, 300), (howl2, 400), (seated, 160), (rise, 120), (stand, 140)], ms)


def bite_combo(ms=1.0, **rest):
    """Two quick snapping bites in place: guard, lunge-snap, pull back, second harder snap, recover."""
    stand = base.pose("quadruped", **rest)
    guard = _crouch(rest, flex=4, pitch=2, neck=52, head=10, tail=-26, **_back(28, -76, 54), **_front(-20, 36, -6))
    snap1 = dict(guard, pitch=7, neck=86, head=30, tail=-18, dx=2, smear="head",
                 **_back(10, -50, 38), **_front(22, 6, 0))
    pull = dict(guard, neck=60, head=12, dx=1)
    snap2 = dict(snap1, pitch=9, neck=90, head=36, dx=3, smear="head")
    hold = dict(snap2)
    del hold["smear"]
    bite1 = dict(snap1, head=34)
    del bite1["smear"]
    return base.timed([(guard, 120), (snap1, 50), (bite1, 70), (pull, 90),
                       (snap2, 50), (hold, 110), (base.lerp(hold, stand, 0.5), 110), (stand, 120)], ms)


def charge(ms=1.0, **rest):
    """Lowered-head charge (boar or ram): head down, paw the ground twice, rock back, lunge forward,
    impact, bounce back and recover."""
    stand = base.pose("quadruped", **rest)
    low = base.pose("quadruped", **dict(dict(pitch=6, neck=96, head=44, tail=-10,
                                              **_back(28, -78, 54), **_front(-12, 18, 0)), **rest))
    paw_up = dict(low, hip_fn=34, knee_fn=-60, ankle_fn=24)
    scrape = dict(low, hip_fn=-34, knee_fn=14, ankle_fn=0)
    windup = dict(low, pitch=3, neck=90, dx=-1, **_back(40, -100, 68), **_front(-28, 50, -10))
    lunge = dict(low, pitch=4, neck=100, head=50, dx=3, dy=-1, smear="head",
                 **_back(-32, -14, 14), **_front(44, 10, 0))
    impact = dict(low, pitch=10, neck=104, head=56, dx=5, **_back(-14, -30, 22), **_front(-6, 20, 0))
    bounce = dict(low, pitch=-2, neck=72, head=30, dx=3, **_back(30, -82, 58), **_front(-22, 36, -6))
    for p in (paw_up, scrape, windup, impact, bounce):
        p.update(rest)
    return base.timed([(low, 120), (paw_up, 110), (scrape, 90), (paw_up, 110), (scrape, 90), (windup, 160),
                       (lunge, 60), (impact, 70), (dict(impact, pitch=11), 110), (bounce, 120),
                       (dict(base.lerp(bounce, stand, 0.5), dx=1), 120), (stand, 140)], ms)


def rear_up(ms=1.0, **rest):
    """Rear up on the hind legs with the front legs pawing the air (horse or bear), hold, come down."""
    stand = base.pose("quadruped", **rest)
    gather = dict(_crouch(rest, flex=4, pitch=6, neck=40, head=8, tail=-26, **_front(-20, 36, -6)), dx=-1)
    up = base.pose("quadruped", **dict(dict(
        pitch=-36, flex=-6, neck=50, head=-4, tail=4, tail2=6, tail3=8,
        **_back(44, -112, 80), plant="all"), **rest))
    paw_a = dict(up, hip_fn=118, knee_fn=-96, ankle_fn=30, hip_ff=72, knee_ff=-70, ankle_ff=24)
    paw_b = dict(up, hip_fn=78, knee_fn=-74, ankle_fn=26, hip_ff=112, knee_ff=-92, ankle_ff=30, neck=42, head=-10)
    rise = dict(base.lerp(gather, paw_a, 0.55), plant="all")
    fall = dict(base.lerp(paw_b, stand, 0.5), plant="all", **_front(30, 0, 0))
    land = base.pose("quadruped", **dict(dict(pitch=6, flex=4, neck=40, head=12, tail=-26, dx=1,
                                               **_back(24, -66, 48), **_front(-18, 40, -8)), **rest))
    return base.timed([(stand, 100), (gather, 140), (rise, 90), (paw_a, 120), (paw_b, 120), (paw_a, 120),
                       (paw_b, 160), (fall, 90), (land, 80), (base.lerp(land, stand, 0.5), 110), (stand, 120)], ms)


def shake(ms=1.0, **rest):
    """Shake off water: brace, then the body, head and tail wobble rapidly with a rising and fading swing."""
    stand = base.pose("quadruped", **rest)
    brace = base.pose("quadruped", **dict(dict(flex=2, neck=30, head=6, **_back(24, -62, 44), **_front(-16, 18, 0)), **rest))
    keys = [(stand, 90), (brace, 100)]
    for i, amp in enumerate((0.6, 1.0, 1.0, 1.0, 0.9, 0.7, 0.45, 0.25)):
        s = amp * (1 if i % 2 == 0 else -1)
        keys.append((dict(brace, flex=brace["flex"] + 9 * s, pitch=2.5 * s, neck=brace["neck"] + 16 * s,
                          head=brace["head"] - 22 * s, tail=brace["tail"] + 28 * s, tail2=-18 * s, tail3=22 * s,
                          dx=round(s) if abs(s) > 0.5 else 0,), 50))
    keys += [(base.lerp(brace, stand, 0.5), 110), (stand, 120)]
    return base.timed(keys, ms)


def leap(ms=1.0, **rest):
    """Long jump over a gap: gather low, push off, fly fully stretched (negative dy), reach down with the
    front legs, land front-first and absorb into a crouch, recover."""
    stand = base.pose("quadruped", **rest)
    gather = dict(_crouch(rest, flex=10, pitch=4, neck=40, head=10, tail=-32,
                          **_back(38, -100, 70), **_front(-30, 56, -12)), dx=-1)
    push = base.pose("quadruped", **dict(dict(pitch=-12, flex=-6, neck=52, head=2, tail=-12, dy=-3, smear="spine",
                                               **_back(-34, -12, 12), **_front(58, 22, 0)), **rest))
    fly = base.pose("quadruped", **dict(dict(pitch=-3, flex=-12, neck=62, head=4, tail=-2, tail2=-4, tail3=-6, dy=-9, dx=1,
                                              **_back(-58, -4, 10), **_front(76, 6, 0)), **rest))
    reach = base.pose("quadruped", **dict(dict(pitch=8, flex=4, neck=58, head=14, tail=-8, dy=-5, dx=2,
                                                **_back(16, -50, 40), **_front(30, -6, 0)), **rest))
    land = base.pose("quadruped", **dict(dict(pitch=12, flex=6, neck=62, head=20, tail=2, dx=2,
                                               **_back(44, -96, 66), **_front(-4, 30, -6)), **rest))
    absorb = dict(_crouch(rest, pitch=5, neck=50, tail=-20), dx=2)
    return base.timed([(stand, 100), (gather, 180), (push, 70), (fly, 140), (dict(fly, dy=-8, pitch=1, dx=2), 100),
                       (reach, 80), (land, 70), (absorb, 130), (dict(base.lerp(absorb, stand, 0.5), dx=1), 120),
                       (stand, 140)], ms)


def _keep_rest(fn):
    """Fixed joint values from the spec entry win over every frame's own value."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        params = inspect.signature(fn).parameters
        rest = {k: v for k, v in kwargs.items() if k not in params}
        return [(dict(p, **rest), d) for p, d in fn(*args, **kwargs)]
    return wrapper


ANIMS = {"quadruped": {
    "trot": trot, "stalk": stalk, "sniff": sniff, "howl": howl, "sit": sit, "sit_idle": sit_idle,
    "lie_down": lie_down, "sleep": sleep, "bite_combo": bite_combo, "charge": charge, "rear_up": rear_up,
    "shake": shake, "leap": leap,
}}
ANIMS["quadruped"] = {name: _keep_rest(fn) for name, fn in ANIMS["quadruped"].items()}
LOOPING = {"trot", "stalk", "sniff", "sit_idle", "sleep"}
