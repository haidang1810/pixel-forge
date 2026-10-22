"""Built-in rigs and animation presets. Specs refer to these by name; the agent never re-derives them.

Angles are degrees. Limbs: 0 = straight down, positive = toward the facing side.
Spine: 0 = upright, positive = lean forward. knee bends the shin backward, el bends the forearm forward.
"""
import copy
import random
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


# Body types: length factors per bone group, a width factor for every part, and the head size.
BUILDS = {
    "humanoid": {
        "bulky": {"legs": 0.9, "arms": 1.0, "body": 1.0, "head": 0.95, "width": 1.35},
        "slim": {"legs": 1.1, "arms": 1.1, "body": 1.05, "head": 0.95, "width": 0.75},
        "tall": {"legs": 1.2, "arms": 1.15, "body": 1.15, "head": 1.0, "width": 0.95},
        "short": {"legs": 0.75, "arms": 0.85, "body": 0.85, "head": 1.1, "width": 1.1},
        # From docs/research/proportions.md: big head and short limbs; bent, forward posture; a top-heavy giant.
        "child": {"legs": 0.8, "arms": 0.85, "body": 0.85, "head": 1.2, "width": 0.95},
        "elderly": {"legs": 0.95, "arms": 1.0, "body": 0.97, "head": 1.0, "width": 0.9,
                    "pose": {"lean": 10, "head": 6, "knee_n": 8, "knee_f": 8, "hip_n": 4, "hip_f": 4}},
        "brute": {"legs": 0.85, "arms": 1.25, "body": 1.05, "head": 0.8, "width": 1.5,
                  "pose": {"lean": 10, "head": -6, "sh_n": 8, "sh_f": 8}},
    },
    "quadruped": {
        "bulky": {"legs": 0.85, "body": 1.0, "head": 1.05, "width": 1.3},
        "slim": {"legs": 1.15, "body": 1.05, "head": 0.95, "width": 0.8},
        "tall": {"legs": 1.3, "body": 1.1, "head": 1.0, "width": 0.95},
        "short": {"legs": 0.7, "body": 0.9, "head": 1.1, "width": 1.1},
    },
}
BONE_GROUPS = {
    "humanoid": {"thigh": "legs", "shin": "legs", "foot": "legs", "upper_arm": "arms", "forearm": "arms",
                 "spine": "body", "shoulder_drop": "body", "head": "head"},
    "quadruped": {"back_upper": "legs", "back_lower": "legs", "back_foot": "legs", "front_upper": "legs",
                  "front_lower": "legs", "front_foot": "legs", "body": "body", "neck": "body", "tail": "body", "head": "head"},
}
# Which length key each part's bone follows (parts on other bones only change width).
PART_BONE_KEY = {
    "humanoid": {"thigh": "thigh", "shin": "shin", "foot": "foot", "upper": "upper_arm", "fore": "forearm",
                 "spine": "spine", "head": "head"},
    "quadruped": {"spine": "body", "neck": "neck", "head": "head", "tail": "tail"},
}


def _part_length_key(family, bone):
    stem = bone.split("_")[0]
    if family == "quadruped" and stem in ("upper", "lower", "foot") and "_" in bone:
        kind = "back" if bone.split("_")[1].startswith("b") else "front"
        return f"{kind}_{stem}"
    return PART_BONE_KEY.get(family, {}).get(stem)


def apply_build(result, build):
    """Scale bone lengths by group and part thickness by the build's width (heads by head size).
    The factors are kept on the rig so a spec's own extras can follow the same build."""
    family = result["family"]
    b = BUILDS[family][build]
    groups = BONE_GROUPS[family]
    along = {}
    for key in result["bones"]:
        along[key] = b.get(groups.get(key, ""), 1.0)
        result["bones"][key] *= along[key]
    result["build"] = {"along": along, "width": b["width"], "head": b["head"], "pose": dict(b.get("pose", {}))}
    feet = [p for p in result["parts"].values() if p["bone"].startswith("foot_") and "r" in p]
    before = max((max(p["r"]) if isinstance(p["r"], list) else p["r"]) for p in feet) if feet else 0
    for part in result["parts"].values():
        scale_part(part, result)
    after = max((max(p["r"]) if isinstance(p["r"], list) else p["r"]) for p in feet) if feet else 0
    result["sole"] += after - before  # thicker feet need more room under the ankle
    return result


def scale_part(part, rig):
    """Apply the rig's build and uniform scale (if any) to one of the spec's extras, in place."""
    if rig.get("uniform", 1) != 1:
        uniform_scale(part, rig["uniform"])
    build = rig.get("build")
    if not build:
        return part
    key = _part_length_key(rig["family"], part["bone"])
    on_head = part["bone"] == "head"
    along = build["head"] if on_head else build["along"].get(key, 1.0)
    across = build["head"] if on_head else build["width"]
    if "r" in part:
        part["r"] = [r * across for r in part["r"]] if isinstance(part["r"], list) else part["r"] * across
    if "span" in part:
        part["span"] = [u * along for u in part["span"]]
    if "v" in part:
        part["v"] *= across
    if part.get("shape") == "ellipse":
        part["rx"] *= across
        part["ry"] *= along
        if "at" in part:
            part["at"] = [part["at"][0] * along, part["at"][1] * across]
    if part.get("shape") == "poly":
        part["points"] = [[u * along, v * across] for u, v in part["points"]]
    return part


def rig(name, proportions, build=None):
    result = copy.deepcopy(RIGS[name])
    if build:
        apply_build(result, build)
    scale = proportions.get("scale", 1)
    for bone in result["bones"]:
        result["bones"][bone] = proportions.get(bone, result["bones"][bone] * scale)
    if scale != 1:  # a uniformly bigger character: thicker parts and room under the feet as well
        result["uniform"] = scale
        for part in result["parts"].values():
            uniform_scale(part, scale)
        result["sole"] *= scale
    return result


def uniform_scale(part, k):
    if "r" in part:
        part["r"] = [r * k for r in part["r"]] if isinstance(part["r"], list) else part["r"] * k
    for key in ("span", "at"):
        if key in part:
            part[key] = [c * k for c in part[key]]
    for key in ("v", "rx", "ry"):
        if key in part:
            part[key] *= k
    if "points" in part:
        part["points"] = [[u * k, v * k] for u, v in part["points"]]
    return part


# ---------- animations ----------

REST = {"lean": 3, "head": 0, "hip_n": 6, "knee_n": 6, "hip_f": -6, "knee_f": 6,
        "sh_n": 12, "el_n": 40, "grip_n": 60, "sh_f": -8, "el_f": 25, "grip_f": 60}


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


def idle(frames=4, ms=280, breath=4, **rest):
    """Breathing idle: knees settle, the chest rises, the head nods a beat later and the arms and
    weapon sway with it, so even 4 frames read as alive. breath scales all of it."""
    out = []
    k = breath / 3
    for i in range(frames):
        a = 2 * math.pi * i / frames
        t = (1 - math.cos(a)) / 2
        late = (1 - math.cos(a - 0.9)) / 2  # head and hands lag the breath
        # Feet apart and the far hand forward of the body, so both legs and both arms read.
        base = _pose(**dict(dict(hip_n=REST["hip_n"] + 6, hip_f=REST["hip_f"] - 4, sh_f=28, el_f=45), **rest))
        out.append((dict(base, breathe=0.1 * k * t, knee_n=base["knee_n"] + 7 * k * t, knee_f=base["knee_f"] + 7 * k * t,
                         hip_n=base["hip_n"] + 3.5 * k * t, hip_f=base["hip_f"] + 3.5 * k * t,
                         lean=base["lean"] + 2 * k * t, head=base["head"] - 4 * k * late,
                         sh_n=base["sh_n"] - 6 * k * late, sh_f=base["sh_f"] - 6 * k * late,
                         el_n=base["el_n"] + 6 * k * late, el_f=base["el_f"] + 5 * k * late,
                         grip_n=base["grip_n"] - 8 * k * late), ms))
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
    strike = _pose(**rest, sh_n=80, el_n=-10, grip_n=30, lean=14, hip_n=32, knee_n=28, hip_f=-24, knee_f=4, sh_f=-30,
                   smear="weapon_n")
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
    hit = dict(base, lean=-16, head=-8, sh_n=-30, el_n=65, sh_f=-45, el_f=55, hip_n=16, knee_n=20,
               hip_f=-16, knee_f=16, dx=-1, flash=1)
    recoil = dict(base, lean=-20, head=-10, sh_n=-40, el_n=70, sh_f=-55, el_f=60, hip_n=20, knee_n=26,
                  hip_f=-20, knee_f=18, dx=-4)
    brace = dict(base, lean=-10, head=-8, sh_n=-12, el_n=55, sh_f=-28, el_f=45, hip_n=22, knee_n=30,
                 hip_f=-12, knee_f=24, dx=-4)
    return _timed([(hit, 70), (recoil, 110), (brace, 100), (_lerp(brace, base, 0.5), 90), (base, 110)], ms)


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
    hit = dict(base, lean=-12, head=-6, sh_n=-30, el_n=60, sh_f=-40, el_f=50, dx=-1, flash=1)
    stagger = dict(base, lean=-18, head=-8, sh_n=-45, el_n=35, sh_f=-55, el_f=30, hip_n=22, knee_n=30,
                   hip_f=-10, knee_f=24, dx=-2)
    kneel = dict(base, lean=-6, head=22, sh_n=8, el_n=15, sh_f=-4, el_f=12, hip_n=75, knee_n=115,
                 hip_f=65, knee_f=105, dx=-2, plant="all")
    falling = dict(base, lean=-55, head=12, grip_n=40, sh_n=40, el_n=20, sh_f=20, el_f=10, hip_n=70, knee_n=70,
                   hip_f=60, knee_f=60, dx=-2, plant="all")
    lying = dict(base, lean=-90, head=30, grip_n=7, sh_n=75, el_n=8, sh_f=100, el_f=6, hip_n=88, knee_n=10,
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


def q_idle(frames=4, ms=300, wag=10, **rest):
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(QREST, **rest, tail=QREST["tail"] + wag * math.sin(t), tail2=4 * math.sin(t - 1),
                         tail3=5 * math.sin(t - 2), head=QREST["head"] + 3 * math.sin(t),
                         neck=QREST["neck"] - 2 * math.sin(t)), ms))
    return out


def q_walk(frames=8, ms=100, stride=22, fold=38, **rest):
    # Lateral-sequence walk: back near, front near, back far, front far, a quarter cycle apart. The
    # shoulders rock and the head nods twice a cycle, once per front footfall.
    phases = {"bn": 0, "fn": 0.25, "bf": 0.5, "ff": 0.75}
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(QREST, **rest, **_legs(t, phases, stride, fold), pitch=QREST["pitch"] + 2.5 * math.sin(2 * t),
                         neck=QREST["neck"] - 3 * math.sin(2 * t + 0.6), head=QREST["head"] + 4 * math.sin(2 * t),
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
                  hip_fn=62, knee_fn=22, ankle_fn=0, hip_ff=55, knee_ff=26, ankle_ff=0, dx=1, dy=-2, smear="head")
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


# ---------- slime, serpent and bird ----------

RIGS["slime"] = {
    "family": "slime",
    "bones": {"height": 12},
    "sole": 0,
    "ground_bones": ["body"],
    "parts": {
        # A dome on the "body" bone (u up from the ground, v forward); squash and stretch scale it.
        "body": dict(bone="body", shape="poly", mat="body", z=30, group="body",
                     points=[[0, -9], [0, 9], [4, 9.2], [8.4, 7.2], [11, 4], [12, 0], [11, -4], [8.4, -7.2], [4, -9.2]]),
    },
}

RIGS["serpent"] = {
    "family": "serpent",
    "bones": {"neck": 9, "head": 6.5, "seg": 4, "segments": 8},
    "sole": 0,
    "ground_bones": ["seg", "neck"],
    "parts": {
        **{f"seg{i}": dict(bone=f"seg{i}", shape="capsule", r=[3.6 - 0.36 * (i - 1), 3.24 - 0.36 * (i - 1)],
                           mat="body", z=30 - i, group="body") for i in range(1, 9)},
        "neck": dict(bone="neck", shape="capsule", span=[-0.5, 9], r=[3.6, 2.6], mat="body", z=32, group="body"),
        "jaw": dict(bone="jaw", shape="capsule", span=[0.5, 5], r=[1.4, 0.8], mat="body", z=39, group="head"),
        "head": dict(bone="head", shape="ellipse", at=[3.2, 0], rx=3.1, ry=4.3, mat="body", z=40, group="head"),
    },
}

# Wing pieces: a broad inner wing and a feathered outer wing with a notched trailing edge.
WING = [[0, -2.6], [5.5, -2.8], [5.5, 2.8], [0, 2.8]]
WINGTIP = [[0, -2.8], [5, -2.6], [8, -1], [7, -0.2], [8.2, 0.8], [6.4, 1.4], [7, 2.6], [4.4, 2.6], [2.4, 3.2], [0, 2.8]]

RIGS["bird"] = {
    "family": "bird",
    "bones": {"body": 8, "neck": 4, "head": 5, "tail": 7, "wing_upper": 5.5, "wing_fore": 7.5,
              "thigh": 3, "shin": 4, "foot": 2.5},
    "sole": 0.8,
    "parts": {
        "wing_f": dict(bone="wing_f", shape="poly", points=WING, mat="wing", z=12, group="wing_f", far=True),
        "wingtip_f": dict(bone="wingtip_f", shape="poly", points=WINGTIP,
                          mat="wing", z=13, group="wing_f", far=True),
        "thigh_f": _limb("thigh_f", [1.4, 0.9], "body", 18, "leg_f", True),
        "shin_f": _limb("shin_f", [0.6, 0.6], "leg", 19, "leg_f", True),
        "foot_f": _limb("foot_f", [0.55, 0.55], "leg", 20, "leg_f", True, span=[-1, 2.5]),
        "tail": dict(bone="tail", shape="poly", points=[[0, -1.4], [5, -2.6], [6.5, -0.5], [6.5, 0.8], [5, 2.4], [0, 1.4]],
                     mat="wing", z=25, group="tail"),
        "body": dict(bone="body", shape="ellipse", at=[4, 0.6], rx=4.3, ry=5.8, mat="body", z=30, group="body"),
        "neck": dict(bone="neck", shape="capsule", span=[-0.5, 3], r=[2.4, 2.0], mat="body", z=31, group="body"),
        "head": dict(bone="head", shape="ellipse", at=[1, 0], rx=3.1, ry=3.3, mat="body", z=40, group="head"),
        "beak": dict(bone="head", shape="poly", points=[[2.2, -0.6], [5.6, 0.6], [2.2, 1.6]], mat="beak", z=41, group="head"),
        "thigh_n": _limb("thigh_n", [1.4, 0.9], "body", 50, "leg_n"),
        "shin_n": _limb("shin_n", [0.6, 0.6], "leg", 51, "leg_n"),
        "foot_n": _limb("foot_n", [0.55, 0.55], "leg", 52, "leg_n", span=[-1, 2.5]),
        "wing_n": dict(bone="wing_n", shape="poly", points=WING, mat="wing", z=60, group="wing_n"),
        "wingtip_n": dict(bone="wingtip_n", shape="poly", points=WINGTIP,
                          mat="wing", z=61, group="wing_n"),
    },
}

SREST = {"stretch": 1.0, "lean": 0}
RREST = {"neck": 18, "head": 4, "jaw": 0, "seg1": 8, "seg2": -6, "seg3": -6, "seg4": 4, "seg5": 6, "seg6": -4,
         "seg7": -6, "seg8": -2}
BREST = {"body": 14, "neck": 8, "head": 0, "tail": 8, "wing_n": -100, "wingtip_n": -6, "wing_f": -100,
         "wingtip_f": -6, "hip_n": 10, "knee_n": 35, "ankle_n": -5, "hip_f": 0, "knee_f": 30, "ankle_f": -5}


def s_idle(frames=4, ms=170, wobble=0.06, **rest):
    return [(dict(SREST, **rest, stretch=1 + wobble * math.sin(2 * math.pi * i / frames),
                  lean=2 * math.sin(2 * math.pi * i / frames + 1)), ms) for i in range(frames)]


def s_hop(ms=1.0, height=7, **rest):
    """Squash, launch stretched, arc through the air, land squashed, settle."""
    b = dict(SREST, **rest)
    keys = [(dict(b, stretch=0.72), 110), (dict(b, stretch=1.28, dy=-2), 70), (dict(b, stretch=1.12, dy=-0.8 * height, lean=4), 80),
            (dict(b, stretch=1.0, dy=-height), 90), (dict(b, stretch=1.1, dy=-0.6 * height, lean=-3), 80),
            (dict(b, stretch=0.7), 90), (dict(b, stretch=1.08), 90), (dict(b), 100)]
    return _timed(keys, ms)


def s_attack(ms=1.0, **rest):
    b = dict(SREST, **rest)
    return _timed([(dict(b, stretch=0.8, lean=-12), 120), (dict(b, stretch=1.35, lean=28, dx=3), 70),
                   (dict(b, stretch=1.15, lean=18, dx=3), 110), (dict(b, stretch=0.9, lean=4, dx=1), 100), (b, 120)], ms)


def s_hurt(ms=1.0, **rest):
    b = dict(SREST, **rest)
    return _timed([(dict(b, stretch=0.75, lean=-14, dx=-1, flash=1), 70), (dict(b, stretch=0.85, lean=-8, dx=-2), 100),
                   (dict(b, stretch=1.05, dx=-1), 90), (b, 120)], ms)


def s_die(ms=1.0, fade=0, **rest):
    """Melt into a puddle."""
    b = dict(SREST, **rest)
    puddle = dict(b, stretch=0.48)
    frames = _timed([(dict(b, stretch=0.8, lean=-10, flash=1), 70), (dict(b, stretch=0.62), 110),
                     (dict(b, stretch=0.5), 120), (puddle, 600)], ms)
    return frames + (_fade(puddle, fade, round(90 * ms)) if fade else [])


def _wave(t, amp, k=0.9):
    return {f"seg{i}": RREST[f"seg{i}"] + amp * math.sin(t - i * k) for i in range(1, 9)}


def r_idle(frames=6, ms=140, **rest):
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(RREST, **rest, **_wave(t, 4), neck=RREST["neck"] + 4 * math.sin(t), head=RREST["head"] - 4 * math.sin(t),
                         jaw=8 if i == frames // 2 else 0), ms))
    return out


def r_slither(frames=8, ms=90, amp=14, **rest):
    """A wave travels from the neck to the tail; the head stays level."""
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(RREST, **rest, **_wave(t, amp), neck=RREST["neck"] + 3 * math.sin(t), head=RREST["head"] - 3 * math.sin(t)), ms))
    return out


def r_attack(ms=1.0, **rest):
    """Coil back, strike forward with the jaw open, bite, return."""
    b = dict(RREST, **rest)
    coil = dict(b, neck=-15, head=-10, seg1=30, seg2=-20, dx=-2)
    strike = dict(b, neck=68, head=6, jaw=32, dx=4, seg1=-4, smear="head")
    bite = dict(b, neck=66, head=14, jaw=4, dx=4, seg1=-2)
    return _timed([(coil, 140), (strike, 70), (bite, 120), (_lerp(bite, b, 0.5), 110), (b, 120)], ms)


def r_hurt(ms=1.0, **rest):
    b = dict(RREST, **rest)
    hit = dict(b, neck=10, head=-15, dx=-1, flash=1, seg1=18)
    return _timed([(hit, 70), (dict(hit, flash=0, dx=-2), 100), (_lerp(hit, b, 0.5), 90), (b, 120)], ms)


def r_die(ms=1.0, fade=0, **rest):
    b = dict(RREST, **rest)
    flat = {f"seg{i}": 0 for i in range(1, 9)}
    limp = dict(b, **flat, neck=100, head=10, jaw=12, plant="all")
    frames = _timed([(dict(b, neck=10, head=-15, flash=1), 70), (dict(b, neck=60, head=30, jaw=20), 110), (limp, 600)], ms)
    return frames + (_fade(limp, fade, round(90 * ms)) if fade else [])


def _over_the_top(pose):
    """Folded wings expressed past 180 degrees, so blending from raised wings folds them back over
    the top instead of sweeping down through the legs."""
    return dict(pose, wing_n=pose["wing_n"] + 360, wing_f=pose["wing_f"] + 360)


def b_idle(frames=4, ms=180, **rest):
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(BREST, **rest, neck=BREST["neck"] + 5 * math.sin(t), head=BREST["head"] + 6 * math.sin(2 * t),
                         tail=BREST["tail"] + 6 * math.sin(t + 1)), ms))
    return out


def b_hop(ms=1.0, height=4, **rest):
    b = dict(BREST, **rest)
    crouch = dict(b, knee_n=70, knee_f=65, hip_n=30, hip_f=20, body=6, tail=0)
    air = dict(b, knee_n=50, knee_f=50, hip_n=-10, hip_f=-20, dy=-height, wing_n=-60, wing_f=-60, tail=16)
    return _timed([(crouch, 110), (air, 90), (dict(air, dy=-0.5 * height), 80), (crouch, 90), (b, 120)], ms)


def b_fly(frames=6, ms=80, lift=14, **rest):
    """Flap: the outer wing lags the inner one; the body rises on the downstroke; legs tucked."""
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(BREST, **rest, wing_n=90 + 70 * math.cos(t), wingtip_n=-25 * math.sin(t),
                         wing_f=85 + 70 * math.cos(t), wingtip_f=-25 * math.sin(t), body=4, neck=40, head=-4, tail=2,
                         hip_n=-50, knee_n=-40, hip_f=-55, knee_f=-40, dy=-lift - 1.5 * math.sin(t)), ms))
    return out


def b_attack(ms=1.0, **rest):
    """Rear up with the wings raised, then peck down and forward."""
    b = dict(BREST, **rest)
    rear = dict(b, body=28, neck=5, head=-12, wing_n=150, wing_f=145, wingtip_n=-20, wingtip_f=-20, tail=-4)
    peck = dict(b, body=-14, neck=58, head=28, dx=3, wing_n=125, wing_f=120, wingtip_n=10, wingtip_f=10, tail=24,
                smear="head")
    return _timed([(rear, 130), (peck, 70), (dict(peck, head=34), 110), (_lerp(peck, _over_the_top(b), 0.5), 100), (b, 120)], ms)


def b_hurt(ms=1.0, **rest):
    b = dict(BREST, **rest)
    hit = dict(b, body=26, neck=-5, head=-14, wing_n=120, wing_f=115, dx=-1, flash=1)
    return _timed([(hit, 70), (dict(hit, flash=0, dx=-2, wing_n=150, wing_f=145), 100), (_lerp(hit, _over_the_top(b), 0.6), 90), (b, 120)], ms)


def b_die(ms=1.0, fade=0, **rest):
    """Flash, flutter and drop, then lie with the wings spread and the head down."""
    b = dict(BREST, **rest)
    lying = dict(b, body=-8, neck=100, head=20, wing_n=30, wingtip_n=10, wing_f=40, wingtip_f=10, tail=-10,
                 hip_n=120, knee_n=10, hip_f=110, knee_f=10, plant="all")
    frames = _timed([(dict(b, body=26, head=-14, wing_n=130, wing_f=125, flash=1), 70),
                     (dict(b, body=-30, neck=70, head=30, wing_n=70, wing_f=65, plant="all"), 110), (lying, 600)], ms)
    return frames + (_fade(lying, fade, round(90 * ms)) if fade else [])


REST_POSES = {"humanoid": REST, "quadruped": QREST, "slime": SREST, "serpent": RREST, "bird": BREST}


ANIMS = {"humanoid": {"idle": idle, "walk": walk, "attack": attack, "float": float_, "hurt": hurt, "die": die},
         "quadruped": {"idle": q_idle, "walk": q_walk, "run": q_run, "attack": q_attack, "hurt": q_hurt, "die": q_die},
         "slime": {"idle": s_idle, "hop": s_hop, "attack": s_attack, "hurt": s_hurt, "die": s_die},
         "serpent": {"idle": r_idle, "slither": r_slither, "attack": r_attack, "hurt": r_hurt, "die": r_die},
         "bird": {"idle": b_idle, "hop": b_hop, "fly": b_fly, "attack": b_attack, "hurt": b_hurt, "die": b_die}}


def anim(family, name, **params):
    return ANIMS[family][name](**params)


# ---------- motion personality ----------

MOTION_DEFAULTS = {"weight": 0.5, "energy": 0.5, "exaggeration": 1.0, "follow": 0.0}
MAX_CHANGE = 25  # degrees personality may add to or take from any joint of a preset pose
# Joints that trail the ones before them (follow-through), from the root of each chain outward.
FOLLOW_CHAINS = {
    "humanoid": [["el_n"], ["el_f"], ["knee_n"], ["knee_f"]],
    "quadruped": [["tail", "tail2", "tail3"]],
    "serpent": [[f"seg{i}" for i in range(3, 9)]],
    "bird": [["wingtip_n"], ["wingtip_f"], ["tail"]],
    "slime": [],
}
LOOPING = {"idle", "walk", "run", "float", "hop", "fly", "slither"}  # any family (packs add names)
# Cyclic animations per family: a name can loop for one family and be one-shot for another.
LOOPING_BY_FAMILY = {"humanoid": {"idle", "walk", "float"}, "quadruped": {"idle", "walk", "run"},
                     "slime": {"idle", "hop"}, "serpent": {"idle", "slither"}, "bird": {"idle", "hop", "fly"}}
SPECIAL_KEYS = {"flash", "plant", "dissolve", "smear"}
LINEAR_KEYS = {"dx", "dy", "stretch", "breathe"}  # not angles
SWING = ("sh_", "el_", "head", "neck", "tail", "wing", "jaw", "seg")
BEND = ("knee_", "ankle_", "stretch")


def follow_through(frames, family, amount, loop):
    """Each chain joint takes part of its value from the previous frame: the further out along the
    chain, the more it lags. Loops wrap around; one-shot animations hold the first frame."""
    if amount <= 0 or len(frames) < 2:
        return frames
    poses = [p for p, _ in frames]
    out = [dict(p) for p in poses]
    for chain in FOLLOW_CHAINS.get(family, []):
        for depth, key in enumerate(chain, 1):
            lag = min(0.85, amount * depth / len(chain) if len(chain) > 1 else amount)
            for i, pose in enumerate(poses):
                if key not in pose or pose.get("smear"):
                    continue  # a strike frame keeps its exact pose: the blade lands where the preset aims it
                before = poses[i - 1] if (i > 0 or loop) else pose
                if key in before:
                    out[i][key] = pose[key] * (1 - lag) + before[key] * lag
    return [(p, ms) for p, (_, ms) in zip(out, frames)]


def personalize(frames, family, motion, loop=False):
    """Give a preset its character. At the defaults (weight 0.5, energy 0.5, exaggeration 1, no seed)
    every factor is 1 and the frames come back unchanged.

    weight        0 light .. 1 heavy: slower tempo, deeper knee bend, less time in the air
    energy        0 sluggish .. 1 lively: faster tempo, bigger arm/head/tail swing, more bounce
    exaggeration  scales every joint's swing away from the rest pose (0.5 subtle, 1.5 cartoony)
    seed          a fixed quirk per joint (small angle offset and gain) and uneven frame timing,
                  so two creatures of one kind never move identically; the same seed repeats exactly
    follow        0..1 follow-through: forearms, tails, wingtips and snake tails trail behind
    """
    m = dict(MOTION_DEFAULTS, **(motion or {}))
    frames = follow_through(frames, family, m["follow"], loop)
    w, e, x, seed = m["weight"], m["energy"], m["exaggeration"], m.get("seed")
    if (w, e, x) == (0.5, 0.5, 1.0) and seed is None:
        return frames
    rest = REST_POSES[family]
    tempo = (0.8 + 0.4 * w) * (1.3 - 0.6 * e)
    keys = sorted({k for pose, _ in frames for k, v in pose.items()
                   if k not in SPECIAL_KEYS and isinstance(v, (int, float))})
    rng = random.Random(seed) if seed is not None else None
    # Quirks are angle offsets, so they only apply to joint angles (never to stretch, dx or dy).
    quirks = {k: (rng.uniform(-3, 3), rng.uniform(0.85, 1.15)) for k in keys if k not in LINEAR_KEYS} if rng else {}
    out = []
    for pose, ms in frames:
        new = dict(pose)
        for k in keys:
            if k not in pose:
                continue
            base = rest.get(k, 0)
            gain = x
            if k == "dy":
                gain *= min(1.5, (1.5 - w) * (0.5 + e))  # livelier hops, but never launched off the canvas
            elif k.startswith(BEND):
                gain *= 0.6 + 0.8 * w
            elif k.startswith(SWING):
                gain *= 0.5 + e
            if k.startswith("grip_"):
                continue  # how the weapon is held is the preset's intent (a thrust stays horizontal)
            offset, quirk = quirks.get(k, (0.0, 1.0))
            delta = pose[k] - base
            if k not in LINEAR_KEYS:  # angles: scale the short way round, so +200 and -160 behave alike
                delta = (delta + 180) % 360 - 180
            change = delta * gain * quirk - delta
            if k not in LINEAR_KEYS:  # personality bends a preset, it never turns a pose inside out
                change = max(-MAX_CHANGE, min(MAX_CHANGE, change))
            new[k] = base + delta + change + offset
        jitter = 1 + rng.uniform(-0.08, 0.08) if rng else 1
        out.append((new, max(20, round(ms * tempo * jitter))))
    return out


# ---------- preset packs ----------
# Public helpers for pack authors (stable names; the underscored originals stay for this file).
lerp, timed, fade, over_the_top = _lerp, _timed, _fade, _over_the_top


def pose(family, **changes):
    """A family's rest pose with some joints changed."""
    return dict(REST_POSES[family], **changes)


def load_packs(folder=None):
    """Import every scripts/preset_packs/*.py. A pack defines ANIMS = {family: {name: function}} and
    may define LOOPING = {names of cyclic animations}. Names must not collide with existing presets."""
    import importlib.util
    import sys
    from pathlib import Path
    folder = Path(folder or Path(__file__).resolve().parent / "preset_packs")
    loaded = []
    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"preset_packs.{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        looping = getattr(module, "LOOPING", set())
        for family, anims in getattr(module, "ANIMS", {}).items():
            if family not in ANIMS:
                raise ValueError(f"preset pack {path.name}: unknown family {family!r}")
            clash = set(anims) & set(ANIMS[family])
            if clash:
                raise ValueError(f"preset pack {path.name}: {family} presets {sorted(clash)} already exist")
            ANIMS[family].update(anims)
            # A pack's LOOPING names count only for the families where that pack defines them.
            LOOPING_BY_FAMILY[family].update(n for n in looping if n in anims)
        LOOPING.update(looping)
        loaded.append(path.stem)
    return loaded


PACKS = load_packs()
