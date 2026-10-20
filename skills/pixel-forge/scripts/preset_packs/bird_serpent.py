"""Bird and serpent preset pack: flight phases and ground behaviour for birds, threat displays and
an alternative travel wave for serpents.

Bird:    glide (loop), takeoff, land, dive, peck_ground (loop), screech.
Serpent: coil (loop), rear_up, spit, hiss (loop), sidewind (loop).
"""
import math

import rig_presets as base


# ---------- bird ----------
# Wings raised up and back are written as negative angles (-160 rather than 200): they stay close to
# the folded rest angle (-100), so blends toward rest fold back over the top instead of sweeping down
# through the legs, and motion personality (which scales the distance from rest) does not push a
# raised wing round into the folded position.

def _tucked(p):
    """Legs folded back under the tail for flight."""
    return dict(p, hip_n=-50, knee_n=-40, hip_f=-55, knee_f=-40)


def glide(frames=6, ms=110, lift=14, bob=1.5, **rest):
    """Wings spread and held in a shallow V, the body riding a slow bob; legs tucked. Airborne.
    lift sets the height (pixels), bob the amplitude of the rise and fall."""
    b = base.pose("bird", **rest)
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        s = math.sin(t)
        out.append((_tucked(dict(b, body=4 + 2 * s, neck=42, head=-4 - 2 * s, tail=2 - 3 * s,
                                 wing_n=-156 + 4 * s, wingtip_n=18 + 3 * s, wing_f=-166 + 4 * s, wingtip_f=20 + 3 * s,
                                 dy=-lift - bob * s)), ms))
    return out


def takeoff(ms=1.0, lift=14, **rest):
    """Crouch, wings up, a big downstroke that throws the bird into the air, then one more flap while
    rising. Ends airborne at `lift` in a flap pose so it chains into fly or glide."""
    b = base.pose("bird", **rest)
    crouch = dict(b, knee_n=72, knee_f=66, hip_n=32, hip_f=22, body=4, neck=24, head=-2, tail=0,
                  wing_n=-80, wing_f=-82)
    wind = dict(crouch, wing_n=-170, wing_f=-178, wingtip_n=20, wingtip_f=18, body=10, tail=6)
    leap = dict(b, body=18, neck=30, head=-6, tail=-6, hip_n=-20, knee_n=20, hip_f=-28, knee_f=24,
                wing_n=25, wing_f=20, wingtip_n=20, wingtip_f=20, dy=-0.35 * lift)
    up = _tucked(dict(b, body=10, neck=36, head=-4, tail=4, wing_n=-172, wing_f=-180, wingtip_n=24,
                      wingtip_f=22, dy=-0.6 * lift))
    down = _tucked(dict(up, wing_n=30, wing_f=25, wingtip_n=18, wingtip_f=18, body=6, dy=-0.85 * lift))
    top = _tucked(dict(up, wing_n=-188, wing_f=-196, wingtip_n=14, wingtip_f=12, body=4, neck=40, dy=-lift))
    return base.timed([(crouch, 140), (wind, 90), (leap, 70), (up, 90), (down, 60), (top, 90)], ms)


def land(ms=1.0, lift=12, **rest):
    """Starts airborne at `lift`: flare the wings high and pitch the chest up to brake, swing the feet
    forward, touch down into a knees-bent squash, then fold the wings back over the top."""
    b = base.pose("bird", **rest)
    approach = _tucked(dict(b, body=6, neck=40, head=-4, tail=2, wing_n=-184, wing_f=-192, wingtip_n=18,
                            wingtip_f=16, dy=-lift))
    flare = dict(b, body=32, neck=10, head=-10, tail=-14, wing_n=-164, wing_f=-172, wingtip_n=26, wingtip_f=24,
                 hip_n=50, knee_n=10, hip_f=42, knee_f=12, dy=-0.5 * lift)
    reach = dict(flare, body=26, wing_n=-176, wing_f=-184, wingtip_n=20, wingtip_f=18, hip_n=40, knee_n=20,
                 hip_f=34, knee_f=22, dy=-0.15 * lift)
    squash = dict(b, body=2, neck=26, head=4, tail=-4, knee_n=74, knee_f=68, hip_n=34, hip_f=26,
                  wing_n=-160, wing_f=-168, wingtip_n=24, wingtip_f=22)
    folding = base.lerp(squash, dict(b, knee_n=50, knee_f=46, hip_n=22, hip_f=14), 0.55)
    return base.timed([(approach, 90), (flare, 100), (reach, 80), (squash, 90), (folding, 90), (b, 130)], ms)


def dive(ms=1.0, lift=18, **rest):
    """Airborne the whole time: tilt the nose down, tuck the wings back and drop steeply forward,
    then spread the wings and pull up. lift is the starting height; the dive bottoms out at a third."""
    b = base.pose("bird", **rest)
    cruise = _tucked(dict(b, body=4, neck=40, head=-4, tail=2, wing_n=-182, wing_f=-190, wingtip_n=18,
                          wingtip_f=16, dy=-lift, dx=-4))
    tip = _tucked(dict(cruise, body=-22, neck=62, head=6, tail=10, wing_n=-146, wing_f=-152, wingtip_n=20,
                       wingtip_f=18, dy=-lift * 0.9, dx=-3))
    drop = _tucked(dict(cruise, body=-52, neck=84, head=14, tail=14, wing_n=-112, wing_f=-114, wingtip_n=-10,
                        wingtip_f=-10, dy=-lift * 0.62, dx=0))
    bottom = _tucked(dict(drop, body=-40, dy=-lift * 0.4, dx=3))
    pull = _tucked(dict(cruise, body=26, neck=22, head=-10, tail=-12, wing_n=-168, wing_f=-176, wingtip_n=24,
                        wingtip_f=22, dy=-lift * 0.45, dx=4))
    level = _tucked(dict(cruise, body=8, wing_n=40, wing_f=34, wingtip_n=16, wingtip_f=16, dy=-lift * 0.55, dx=4))
    return base.timed([(cruise, 110), (tip, 80), (drop, 70), (bottom, 70), (pull, 90), (level, 120)], ms)


def peck_ground(frames=4, ms=110, **rest):
    """Feeding: tip forward and bob the head down to the ground, peck twice, lift and look.
    frames: 4 (up, down, peck, down) or more for a slower look-around between pecks."""
    b = base.pose("bird", **rest)
    up = dict(b, body=6, neck=40, head=8, tail=12)
    down = dict(b, body=-18, neck=110, head=50, tail=26, knee_n=48, knee_f=44, hip_n=20, hip_f=12)
    peck = dict(down, neck=118, head=62)
    keys = [up, down, peck, down]
    for _ in range(max(0, frames - 4)):
        keys.insert(1, dict(up, head=0))
    return [(k, ms if k is not peck else round(ms * 0.6)) for k in keys]


def screech(ms=1.0, **rest):
    """Threat call: raise the head, throw the beak forward with the wings half raised, hold, settle."""
    b = base.pose("bird", **rest)
    rise = dict(b, body=26, neck=-6, head=-26, tail=-6, wing_n=-70, wing_f=-72)
    call = dict(b, body=12, neck=48, head=-12, tail=14, wing_n=-154, wing_f=-162, wingtip_n=22, wingtip_f=20,
                knee_n=45, knee_f=40)
    hold = dict(call, head=-18, wing_n=-148, wing_f=-156, tail=18)
    settle = base.lerp(hold, b, 0.6)
    return base.timed([(rise, 160), (call, 60), (hold, 260), (dict(hold, head=-14), 120), (settle, 110), (b, 140)], ms)


# ---------- serpent ----------

def _wave(t, amp, k, start=None):
    start = start or base.RREST
    return {f"seg{i}": start[f"seg{i}"] + amp * math.sin(t - i * k) for i in range(1, 9)}


COILED = {"seg1": 60, "seg2": 0, "seg3": -120, "seg4": 0, "seg5": 120, "seg6": 0, "seg7": -60, "seg8": -4}


def coil(frames=6, ms=180, sway=8, **rest):
    """Resting coiled: a tight S near the root lifts the neck, which sways slowly; the tail tip twitches."""
    b = base.pose("serpent", **dict(COILED, **rest))
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        s = math.sin(t)
        out.append((dict(b, neck=4 + sway * s, head=10 - 0.8 * sway * s, seg7=b["seg7"] + 6 * math.sin(t + 1),
                         seg8=b["seg8"] + 8 * math.sin(t + 1.6), jaw=6 if i == frames // 2 else 0), ms))
    return out


RAISED = {"seg1": 76, "seg2": -12, "seg3": -62, "seg4": -2, "seg5": 4, "seg6": -4, "seg7": -4, "seg8": -2}


def rear_up(ms=1.0, **rest):
    """Threat display: lift the front of the body high with the neck nearly vertical, hold with the head
    swaying side to side (nose dips and rises), then lower back to rest."""
    b = base.pose("serpent", **rest)
    gather = dict(b, neck=8, head=0, seg1=22, seg2=-18, seg3=-12)
    high = dict(b, **RAISED, neck=-4, head=14, jaw=0)
    sway_a = dict(high, neck=4, head=8)
    sway_b = dict(high, neck=-8, head=18, jaw=10)
    lower = base.lerp(high, b, 0.6)
    return base.timed([(gather, 120), (high, 140), (sway_a, 160), (sway_b, 160), (sway_a, 160),
                       (dict(high, jaw=14), 200), (lower, 120), (b, 140)], ms)


def spit(ms=1.0, **rest):
    """Venom spit: rear back, snap the head forward with the jaw wide open (the projectile spawns on
    this lunge frame, index 2), hold it open, then recover to rest."""
    b = base.pose("serpent", **rest)
    rear = dict(b, neck=-22, head=-8, seg1=30, seg2=-20, dx=-2)
    cock = dict(rear, neck=-30, head=-14, jaw=10)
    lunge = dict(b, neck=44, head=-14, jaw=38, seg1=4, dx=2)
    hold = dict(lunge, neck=42, head=-10, jaw=32)
    return base.timed([(rear, 120), (cock, 100), (lunge, 60), (hold, 180), (base.lerp(hold, b, 0.5), 110),
                       (b, 130)], ms)


def hiss(frames=4, ms=90, **rest):
    """Quick hiss: the neck pulls back a little as the jaw snaps open, then closes."""
    b = base.pose("serpent", **rest)
    shut = dict(b)
    pull = dict(b, neck=b["neck"] - 10, head=b["head"] - 8, jaw=34, seg1=b["seg1"] + 6)
    keys = [shut, pull, dict(pull, jaw=20), dict(b, neck=b["neck"] - 2, jaw=6)]
    for _ in range(max(0, frames - 4)):
        keys.append(dict(shut))
    return [(k, ms) for k in keys]


def sidewind(frames=10, ms=110, amp=10, k=0.5, **rest):
    """Alternative travel: a bigger, slower travelling wave with a longer wavelength than slither;
    the head stays level. amp is the bend amplitude, k the phase step per segment (smaller = longer)."""
    b = base.pose("serpent", **rest)
    out = []
    for i in range(frames):
        t = 2 * math.pi * i / frames
        out.append((dict(b, **_wave(t, amp, k, b), neck=b["neck"] + 4 * math.sin(t),
                         head=b["head"] - 4 * math.sin(t)), ms))
    return out


ANIMS = {
    "bird": {"glide": glide, "takeoff": takeoff, "land": land, "dive": dive, "peck_ground": peck_ground,
             "screech": screech},
    "serpent": {"coil": coil, "rear_up": rear_up, "spit": spit, "hiss": hiss, "sidewind": sidewind},
}
LOOPING = {"glide", "peck_ground", "coil", "hiss", "sidewind"}
