"""Built-in rigs and animation presets. Specs refer to these by name; the agent never re-derives them.

Angles are degrees. Limbs: 0 = straight down, positive = toward the facing side.
Spine: 0 = upright, positive = lean forward. knee bends the shin backward, el bends the forearm forward.
"""
import copy
import math


def _limb(bone, r, mat, z, group, far=False, **extra):
    return dict(bone=bone, shape="capsule", r=r, mat=mat, z=z, group=group, far=far, **extra)


def _side(s, z):
    far = s == "f"
    return {
        f"thigh_{s}": _limb(f"thigh_{s}", [2.9, 2.3], "legs", z + 0, f"leg_{s}", far),
        f"shin_{s}": _limb(f"shin_{s}", [2.4, 2.0], "legs", z + 1, f"leg_{s}", far),
        f"foot_{s}": _limb(f"foot_{s}", [2.0, 1.7], "boots", z + 2, f"leg_{s}", far, span=[-1, 3.4]),
    }


def _arm(s, z):
    far = s == "f"
    return {
        f"upper_{s}": _limb(f"upper_{s}", [2.1, 1.8], "body", z + 0, f"arm_{s}", far),
        f"fore_{s}": _limb(f"fore_{s}", [1.8, 1.5], "body", z + 1, f"arm_{s}", far),
        f"hand_{s}": dict(bone=f"hand_{s}", shape="ellipse", at=[0, 0], rx=2.3, ry=2.3, mat="skin", z=z + 3, group=f"arm_{s}", far=far),
    }


RIGS = {
    "humanoid": {
        "family": "humanoid",
        "bones": {"spine": 10, "neck": 0.5, "head": 11, "shoulder_drop": 1.5, "thigh": 6.5, "shin": 6.5, "foot": 3.4,
                  "upper_arm": 5.5, "forearm": 5.5},
        "sole": 1.5,
        "parts": {
            **_arm("f", 10), **_side("f", 20),
            # Hips, narrow waist, chest pushed forward, rounded shoulders (u up the spine, v forward).
            "torso": dict(bone="spine", shape="poly", mat="body", z=30, group="torso",
                          points=[[-1.5, -3.8], [3, -3.3], [7.5, -4.3], [10.5, -3.6], [11.3, 0], [10.5, 4], [7.5, 5.2],
                                  [3, 3.5], [-1.5, 3.9]]),
            "head": dict(bone="head", shape="ellipse", at=[5.6, 0.8], rx=5.6, ry=6, mat="skin", z=40, group="head"),
            **_side("n", 50), **_arm("n", 60),
        },
    },
}
RIGS["chibi"] = copy.deepcopy(RIGS["humanoid"])  # family stays "humanoid"
RIGS["chibi"]["bones"].update({"spine": 7.5, "head": 14, "thigh": 5, "shin": 4.5, "upper_arm": 4.5, "forearm": 4})
RIGS["chibi"]["parts"]["head"].update(at=[7, 0.8], rx=7, ry=7.2)
RIGS["chibi"]["parts"]["torso"]["points"] = [[-1.5, -3.8], [2.5, -3.6], [6, -3.8], [8.3, -2.8], [8.8, 0], [8.3, 3.2],
                                             [6, 4.4], [2.5, 4], [-1.5, 4.2]]


def _quad_leg(leg, z, far):
    kind = "back" if leg[0] == "b" else "front"
    thick = [4.6, 2.6] if kind == "back" else [3.0, 2.2]
    group = "leg_" + leg
    return {
        "upper_" + leg: dict(bone="upper_" + leg, shape="capsule", r=thick, mat="fur", z=z, group=group, far=far),
        "lower_" + leg: dict(bone="lower_" + leg, shape="capsule", r=[2.2, 1.8], mat="fur", z=z + 1, group=group, far=far),
        "foot_" + leg: dict(bone="foot_" + leg, shape="capsule", r=[1.8, 1.7], mat="fur", z=z + 2, group=group, far=far),
        "paw_" + leg: dict(bone="paw_" + leg, shape="ellipse", at=[0.3, 0.2], rx=2.6, ry=1.6, mat="paw", z=z + 3, group=group, far=far),
    }


# Side view facing right. Spine-local u runs hip -> shoulder, +v points down (belly).
RIGS["quadruped"] = {
    "family": "quadruped",
    # Game proportions: big head, short sturdy legs, compact body.
    "bones": {"body": 14, "neck": 6, "head": 8, "tail": 10,
              "back_upper": 5, "back_lower": 5, "back_foot": 3.2,
              "front_upper": 4.4, "front_lower": 5, "front_foot": 2},
    "sole": 1.8,
    "parts": {
        **_quad_leg("bf", 10, True), **_quad_leg("ff", 14, True),
        "tail": dict(bone="tail", shape="capsule", span=[0, 9], r=[1.6, 2.4], mat="fur", z=20, group="tail"),
        "body": dict(bone="spine", shape="poly", mat="fur", z=30, group="body",
                     points=[[-2.8, -3.4], [5, -3.8], [10, -4.6], [15, -4.2], [16.8, 0], [15, 5.6], [10, 5.8],
                             [5, 3.6], [0, 4], [-3, 2]]),
        "neck": dict(bone="neck", shape="capsule", span=[-1, 6], r=[4, 3], mat="fur", z=32, group="body"),
        "head": dict(bone="head", shape="ellipse", at=[1.4, 0], rx=4.8, ry=4.6, mat="fur", z=40, group="head"),
        "snout": dict(bone="head", shape="capsule", span=[3, 8.6], v=1.2, r=[2.9, 1.9], mat="fur", z=41, group="head"),
        "ear": dict(bone="head", shape="poly", points=[[-2.2, -3.2], [-1, -9.2], [2.6, -3.6]], mat="fur", z=42, group="ear"),
        **_quad_leg("bn", 50, False), **_quad_leg("fn", 54, False),
    },
}


def rig(name, proportions):
    result = copy.deepcopy(RIGS[name])
    scale = proportions.get("scale", 1)
    for bone in result["bones"]:
        result["bones"][bone] = proportions.get(bone, result["bones"][bone] * scale)
    return result


# ---------- animations ----------

REST = {"lean": 3, "head": 0, "hip_n": 6, "knee_n": 6, "hip_f": -6, "knee_f": 6,
        "sh_n": 12, "el_n": 40, "grip_n": 110, "sh_f": -8, "el_f": 25, "grip_f": 110}


def _pose(**changes):
    return dict(REST, **changes)


def _lerp(a, b, t):
    """Smoothstep blend of two poses; non-numeric keys (plant) switch at the halfway point."""
    t = t * t * (3 - 2 * t)
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k, 0), b.get(k, 0)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            out[k] = va + (vb - va) * t
        else:
            out[k] = vb if t >= 0.5 else va
    return {k: v for k, v in out.items() if v != 0 or k in a or k in b}


def _timed(keys, ms):
    return [(dict(p), round(d * ms)) for p, d in keys]


def _fade(pose, steps, ms, rise=0):
    """Dissolve a held pose over `steps` frames, optionally drifting upward."""
    return [(dict(pose, dissolve=(i + 1) / steps, dy=pose.get("dy", 0) - rise * (i + 1)), ms) for i in range(steps)]


def idle(frames=4, ms=160, breath=4, **rest):
    out = []
    for i in range(frames):
        t = (1 - math.cos(2 * math.pi * i / frames)) / 2
        out.append((_pose(**rest, knee_n=REST["knee_n"] + breath * t, knee_f=REST["knee_f"] + breath * t,
                          hip_n=REST["hip_n"] + breath * t / 2, hip_f=REST["hip_f"] + breath * t / 2,
                          sh_n=REST["sh_n"] - 3 * t, sh_f=REST["sh_f"] - 3 * t, head=-2 * t), ms))
    return out


def walk(frames=8, ms=90, stride=28, knee=40, arm=22, **rest):
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        legs = {}
        for side, phase in (("n", 0), ("f", math.pi)):
            legs["hip_" + side] = stride * math.sin(t + phase)
            legs["knee_" + side] = 4 + knee * max(0.0, math.cos(t + phase))
        out.append((_pose(**{**rest, **legs}, lean=6, sh_n=REST["sh_n"] - arm * math.sin(t),
                          sh_f=REST["sh_f"] + arm * math.sin(t)), ms))
    return out


def attack(ms=1.0, **rest):
    """Horizontal slash with the near hand. ms scales all timings."""
    guard = _pose(**rest, sh_n=15, el_n=50, grip_n=100, hip_n=12, hip_f=-12, knee_n=10, knee_f=10)
    windup = _pose(**rest, sh_n=-55, el_n=30, grip_n=235, lean=-6, hip_n=16, knee_n=14, hip_f=-18, knee_f=14, sh_f=20, el_f=30)
    strike = _pose(**rest, sh_n=80, el_n=-10, grip_n=30, lean=14, hip_n=32, knee_n=28, hip_f=-24, knee_f=4, sh_f=-30)
    follow = _pose(**rest, sh_n=40, el_n=-5, grip_n=30, lean=16, hip_n=32, knee_n=30, hip_f=-24, knee_f=4, sh_f=-35)
    keys = [(guard, 120), (_lerp(guard, windup, 0.5), 70), (windup, 160), (strike, 60),
            (follow, 120), (_lerp(follow, guard, 0.5), 100), (guard, 140)]
    return [(p, round(d * ms)) for p, d in keys]


def float_(frames=8, ms=110, bob=2, sway=8, wave=16, **rest):
    """Hover in place for floating creatures (ghosts, spirits, wisps).

    The body bobs; the legs act as trailing wisps whose wave runs from hip to tip.
    Lift the creature off the ground with pose_offset dy (negative is up).
    Fixed joint values in **rest override the per-frame motion.
    """
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        frame = {"dy": -bob * (1 + math.sin(t)) / 2, "lean": 4 + 2 * math.sin(t - 0.6),
                 "head": -2 * math.sin(t - 1.2),
                 "sh_n": 25 + sway * math.sin(t + 0.4), "el_n": 35 + sway * 0.6 * math.sin(t - 0.4),
                 "sh_f": -15 + sway * math.sin(t + 0.9), "el_f": 30 + sway * 0.6 * math.sin(t + 0.1),
                 "hip_n": -30 + wave * math.sin(t), "knee_n": 20 + wave * 0.8 * math.sin(t - 1.2),
                 "hip_f": -45 + wave * math.sin(t - 0.8), "knee_f": 20 + wave * 0.8 * math.sin(t - 2.0)}
        out.append(({**REST, **frame, **rest}, ms))
    return out


def hurt(ms=1.0, style="stand", **rest):
    """Hit reaction: white flash, knocked back away from the facing side, recover.
    style "float" keeps a floating creature's hover pose (trailing wisps) as the base."""
    base = float_(frames=8, **rest)[0][0] if style == "float" else _pose(**rest)
    hit = dict(base, lean=-12, head=-12, sh_n=-25, el_n=60, sh_f=-40, el_f=50, hip_n=14, knee_n=18,
               hip_f=-14, knee_f=14, dx=-1, flash=1)
    recoil = dict(base, lean=-8, head=-6, sh_n=-10, el_n=50, sh_f=-25, el_f=40, hip_n=10, knee_n=14, dx=-2)
    return _timed([(hit, 70), (recoil, 100), (_lerp(recoil, base, 0.5), 90), (base, 120)], ms)


def die(ms=1.0, style="fall", fade=0, **rest):
    """Death. style "fall": stagger, buckle to the knees, fall on the back and lie still.
    style "fade": for floating creatures; flash, then dissolve while drifting up.
    fade: extra dissolve frames after the fall (0 = the body stays)."""
    if style == "fade":
        float_pose = float_(frames=8, **rest)[0][0]
        hit = dict(float_pose, lean=-10, head=-12, sh_n=-30, sh_f=-45, flash=1)
        recoil = dict(float_pose, lean=-14, head=-8, sh_n=-40, sh_f=-50, dx=-1)
        return _timed([(hit, 70), (recoil, 110)], ms) + _fade(recoil, 5, round(90 * ms), rise=0.5)
    base = _pose(**rest)
    hit = dict(base, lean=-12, head=-12, sh_n=-30, el_n=60, sh_f=-40, el_f=50, dx=-1, flash=1)
    stagger = dict(base, lean=-18, head=-14, sh_n=-45, el_n=35, sh_f=-55, el_f=30, hip_n=22, knee_n=30,
                   hip_f=-10, knee_f=24, dx=-2)
    kneel = dict(base, lean=-6, head=22, sh_n=8, el_n=15, sh_f=-4, el_f=12, hip_n=75, knee_n=115,
                 hip_f=65, knee_f=105, dx=-2, plant="all")
    falling = dict(base, lean=-55, head=-6, sh_n=40, el_n=20, sh_f=20, el_f=10, hip_n=70, knee_n=70,
                   hip_f=60, knee_f=60, dx=-2, plant="all")
    lying = dict(base, lean=-90, head=-4, sh_n=75, el_n=8, sh_f=100, el_f=6, hip_n=88, knee_n=10,
                 hip_f=80, knee_f=14, dx=-3, plant="all")
    frames = _timed([(hit, 70), (stagger, 110), (kneel, 140), (falling, 90), (lying, 600)], ms)
    return frames + (_fade(lying, fade, round(90 * ms)) if fade else [])


# ---------- quadruped animations ----------

QREST = {"pitch": 0, "neck": 24, "head": 2, "tail": -22,
         "hip_bn": 18, "knee_bn": -55, "ankle_bn": 40, "hip_bf": 18, "knee_bf": -55, "ankle_bf": 40,
         "hip_fn": -10, "knee_fn": 12, "ankle_fn": 0, "hip_ff": -10, "knee_ff": 12, "ankle_ff": 0}


def _legs(t, phases, swing, fold):
    """Swing each leg on its own phase; fold the lower leg while it moves forward (swing phase)."""
    out = {}
    for leg, phase in phases.items():
        a = t + 2 * math.pi * phase
        lift = max(0.0, math.cos(a))
        out["hip_" + leg] = QREST["hip_" + leg] + swing * math.sin(a)
        out["knee_" + leg] = QREST["knee_" + leg] - fold * lift
        out["ankle_" + leg] = QREST["ankle_" + leg] + fold * 0.8 * lift
    return out


def q_idle(frames=4, ms=200, wag=10, **rest):
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(QREST, **rest, tail=QREST["tail"] + wag * math.sin(t), tail2=4 * math.sin(t - 1),
                         tail3=5 * math.sin(t - 2), head=QREST["head"] + 3 * math.sin(t),
                         neck=QREST["neck"] - 2 * math.sin(t)), ms))
    return out


def q_walk(frames=8, ms=100, stride=18, fold=35, **rest):
    # Lateral-sequence walk: back near, front near, back far, front far, a quarter cycle apart.
    phases = {"bn": 0, "fn": 0.25, "bf": 0.5, "ff": 0.75}
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(QREST, **rest, **_legs(t, phases, stride, fold), head=QREST["head"] + 4 * math.sin(2 * t),
                         tail=QREST["tail"] + 6 * math.sin(t), tail2=4 * math.sin(t - 1),
                         tail3=5 * math.sin(t - 2)), ms))
    return out


def q_run(frames=6, ms=70, stride=34, fold=60, flex=14, **rest):
    # Rotary gallop: back legs together, front legs half a cycle later; body rocks and leaves the ground.
    phases = {"bn": 0, "bf": 0.08, "fn": 0.5, "ff": 0.58}
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        # flex: back arches while the legs gather under the body, flattens while they stretch out.
        out.append((dict(QREST, **rest, **_legs(t, phases, stride, fold), pitch=6 * math.sin(t + 1.2),
                         flex=flex * math.cos(t + 0.3), neck=QREST["neck"] + 20 + 6 * math.sin(t),
                         head=QREST["head"] + 8, tail=QREST["tail"] + 14 + 8 * math.sin(t),
                         tail2=6 * math.sin(t - 1.0), tail3=8 * math.sin(t - 2.0),
                         dy=-2 * max(0.0, math.sin(t + 2.4))), ms))
    return out


def q_attack(ms=1.0, **rest):
    """Pounce and bite: crouch, launch forward, snap the head down, step back to rest."""
    base = dict(QREST, **rest)
    crouch = dict(base, flex=10, pitch=4, neck=48, head=14, tail=-30,
                  hip_bn=34, knee_bn=-90, ankle_bn=62, hip_bf=30, knee_bf=-86, ankle_bf=58,
                  hip_fn=-28, knee_fn=48, ankle_fn=-10, hip_ff=-24, knee_ff=44, ankle_ff=-10, dx=-1)
    launch = dict(base, flex=-10, pitch=-8, neck=68, head=0, tail=-5, tail2=-6, tail3=-8,
                  hip_bn=-35, knee_bn=-12, ankle_bn=14, hip_bf=-28, knee_bf=-16, ankle_bf=16,
                  hip_fn=62, knee_fn=22, ankle_fn=0, hip_ff=55, knee_ff=26, ankle_ff=0, dx=1, dy=-2)
    bite = dict(base, flex=4, pitch=10, neck=78, head=28, tail=-14,
                hip_bn=8, knee_bn=-48, ankle_bn=36, hip_bf=2, knee_bf=-44, ankle_bf=34,
                hip_fn=32, knee_fn=4, ankle_fn=0, hip_ff=26, knee_ff=8, ankle_ff=0, dx=2)
    snap = dict(bite, head=34, neck=82)
    return _timed([(crouch, 160), (launch, 70), (bite, 70), (snap, 110), (_lerp(snap, base, 0.4), 110),
                   (_lerp(snap, base, 0.8), 110), (base, 120)], ms)


def q_hurt(ms=1.0, **rest):
    """Flinch: flash, rear back with the head up and the tail tucked, recover."""
    base = dict(QREST, **rest)
    hit = dict(base, pitch=-7, neck=4, head=-12, tail=-50, flex=6, hip_bn=26, knee_bn=-70, ankle_bn=50,
               hip_fn=-18, knee_fn=24, dx=-1, flash=1)
    recoil = dict(base, pitch=-4, neck=12, head=-6, tail=-42, hip_bn=22, knee_bn=-64, ankle_bn=46, dx=-1)
    return _timed([(hit, 70), (recoil, 110), (_lerp(recoil, base, 0.5), 100), (base, 120)], ms)


def q_die(ms=1.0, fade=0, **rest):
    """Collapse: flash, front legs buckle, drop, then lie on the side with the legs out and the head down."""
    base = dict(QREST, **rest)
    hit = dict(base, pitch=-6, neck=6, head=-12, tail=-50, dx=-1, flash=1)
    buckle = dict(base, pitch=12, neck=58, head=26, tail=-40,
                  hip_fn=-30, knee_fn=70, ankle_fn=-20, hip_ff=-26, knee_ff=66, ankle_ff=-20, dx=-1, plant="all")
    drop = dict(base, pitch=4, neck=72, head=30, tail=-30, flex=-6,
                hip_bn=40, knee_bn=-110, ankle_bn=80, hip_bf=36, knee_bf=-106, ankle_bf=76,
                hip_fn=-40, knee_fn=95, ankle_fn=-30, hip_ff=-36, knee_ff=90, ankle_ff=-30, dx=-1, plant="all")
    # Lying on the side, seen from the side: legs stick out level with the body, head stretched forward.
    lying = dict(base, pitch=0, neck=92, head=2, tail=-2, tail2=2, tail3=2, flex=-6,
                 hip_bn=-88, knee_bn=-4, ankle_bn=4, hip_bf=-78, knee_bf=-8, ankle_bf=6,
                 hip_fn=88, knee_fn=4, ankle_fn=0, hip_ff=78, knee_ff=8, ankle_ff=0, dx=-1, plant="all")
    frames = _timed([(hit, 70), (buckle, 110), (drop, 120), (lying, 600)], ms)
    return frames + (_fade(lying, fade, round(90 * ms)) if fade else [])


REST_POSES = {"humanoid": REST, "quadruped": QREST}


ANIMS = {"humanoid": {"idle": idle, "walk": walk, "attack": attack, "float": float_, "hurt": hurt, "die": die},
         "quadruped": {"idle": q_idle, "walk": q_walk, "run": q_run, "attack": q_attack, "hurt": q_hurt, "die": q_die}}


def anim(family, name, **params):
    return ANIMS[family][name](**params)
