"""Humanoid melee combat pack: heavy overhead smash, thrust, three-hit combo, block, parry, kick, shield bash.

All presets are one-shots taking ms (timing scale) and **rest (fixed joints from the spec entry).
Timings follow docs/research/animation-timing.md: long held anticipation, a 1-frame strike (40-70 ms)
with a smear, an impact or extension hold, and a recovery longer than the strike.
"""
import rig_presets as base


def _p(rest, **joints):
    return base.pose("humanoid", **dict(joints, **rest))


def _calm(pose):
    """The pose without its smear key (for holds after a strike frame)."""
    return {k: v for k, v in pose.items() if k != "smear"}


def _out(keys, ms, rest):
    """Scale timings and make the spec's fixed joints reach every frame."""
    return [(dict(p, **rest), d) for p, d in base.timed(keys, ms)]


def _guard(rest):
    """Sword-ready stance shared by the combat presets (same as the built-in attack's guard)."""
    return _p(rest, sh_n=15, el_n=50, grip_n=100, hip_n=12, hip_f=-12, knee_n=10, knee_f=10)


def heavy_attack(ms=1.0, **rest):
    """Two-handed overhead smash with weapon_n: long held wind-up behind the head, 1-frame strike
    (smear), heavy crouched impact hold, long recovery. About 880 ms at ms=1."""
    guard = _guard(rest)
    lift = _p(rest, sh_n=100, el_n=40, grip_n=60, sh_f=90, el_f=40, lean=-2,
              hip_n=14, knee_n=14, hip_f=-14, knee_f=12)
    windup = _p(rest, sh_n=140, el_n=30, grip_n=75, sh_f=130, el_f=35, lean=-10, head=-6,
                hip_n=18, knee_n=18, hip_f=-18, knee_f=16)
    strike = _p(rest, sh_n=110, el_n=0, grip_n=10, sh_f=102, el_f=8, lean=10, head=4,
                hip_n=28, knee_n=28, hip_f=-22, knee_f=8, smear="weapon_n")
    impact = _p(rest, sh_n=62, el_n=-4, grip_n=0, sh_f=56, el_f=4, lean=24, head=8,
                hip_n=40, knee_n=48, hip_f=-26, knee_f=14, dx=1)
    settle = dict(impact, lean=22, knee_n=44, sh_n=60, sh_f=54)
    rise = base.lerp(impact, guard, 0.5)
    return _out([(guard, 60), (lift, 90), (windup, 240), (strike, 50), (impact, 160), (settle, 70),
                 (rise, 110), (guard, 110)], ms, rest)


def thrust(ms=1.0, **rest):
    """Spear or sword stab: pull the weapon back to the hip, lunge with the arm straight out
    horizontally (smear), hold at full extension, retract to guard. About 490 ms at ms=1."""
    guard = _guard(rest)
    pull = _p(rest, sh_n=-35, el_n=115, grip_n=10, sh_f=10, el_f=30, lean=-4, head=-2,
              hip_n=18, knee_n=20, hip_f=-14, knee_f=12, dx=-1)
    lunge = _p(rest, sh_n=88, el_n=0, grip_n=2, sh_f=-35, el_f=20, lean=16, head=-4,
               hip_n=44, knee_n=40, hip_f=-36, knee_f=2, dx=3, smear="weapon_n")
    hold = dict(_calm(lunge), lean=15)
    retract = _p(rest, sh_n=20, el_n=75, grip_n=40, sh_f=-15, el_f=25, lean=6,
                 hip_n=22, knee_n=20, hip_f=-18, knee_f=8, dx=1)
    # pull is keyed twice: with follow-through the first copy is the in-between, the second the held pose.
    return _out([(guard, 60), (pull, 70), (pull, 120), (lunge, 50), (hold, 140), (retract, 80), (guard, 70)], ms, rest)


def combo(ms=1.0, **rest):
    """Three-hit chain: forward horizontal slash, rising back-hand slash, overhead finisher.
    Each follow-through is the next hit's anticipation; the finisher has the longest hold.
    About 1040 ms at ms=1."""
    guard = _guard(rest)
    # Hit 1: forward slash (like the built-in attack, faster).
    wind1 = _p(rest, sh_n=-40, el_n=30, grip_n=215, lean=-6, hip_n=16, knee_n=14, hip_f=-18, knee_f=14,
               sh_f=20, el_f=30)
    hit1 = _p(rest, sh_n=80, el_n=-10, grip_n=20, lean=14, hip_n=30, knee_n=26, hip_f=-22, knee_f=6,
              sh_f=-30, smear="weapon_n")
    # Follow-through of hit 1 drops the blade low in front: the wind-up of the rising back-hand.
    low = _p(rest, sh_n=40, el_n=-5, grip_n=45, lean=16, hip_n=30, knee_n=28, hip_f=-22, knee_f=6,
             sh_f=-35)
    hit2 = _p(rest, sh_n=115, el_n=10, grip_n=30, lean=4, head=-4, hip_n=24, knee_n=20, hip_f=-20, knee_f=10,
              sh_f=-10, el_f=40, dx=1, smear="weapon_n")
    # The rising blade carries on over the shoulder: wind-up of the overhead finisher.
    wind3 = _p(rest, sh_n=132, el_n=30, grip_n=80, sh_f=125, el_f=35, lean=-8, head=-6,
               hip_n=20, knee_n=18, hip_f=-20, knee_f=14, dx=2)
    hit3 = _p(rest, sh_n=110, el_n=0, grip_n=10, sh_f=102, el_f=8, lean=12, head=4,
              hip_n=32, knee_n=30, hip_f=-24, knee_f=6, dx=2, smear="weapon_n")
    impact = _p(rest, sh_n=62, el_n=-4, grip_n=0, sh_f=56, el_f=4, lean=24, head=8,
                hip_n=42, knee_n=48, hip_f=-28, knee_f=12, dx=2)
    back = base.lerp(impact, guard, 0.5)
    return _out([(guard, 60), (wind1, 100), (hit1, 50), (low, 90),
                 (hit2, 50), (wind3, 130), (hit3, 50), (impact, 180),
                 (dict(impact, lean=20, knee_n=44), 80), (back, 120), (guard, 130)], ms, rest)


def block(ms=1.0, hold=300, **rest):
    """Raise the guard fast (about 90 ms) and hold it: weapon upright in front of the face, the far
    (shield) arm raised forward, knees bent. hold sets the last frame's ms; loop or hold that frame
    in the game while blocking."""
    start = base.pose("humanoid", **rest)
    guard = _p(rest, sh_n=55, el_n=80, grip_n=45, sh_f=75, el_f=55, lean=-3, head=-4,
               hip_n=16, knee_n=18, hip_f=-16, knee_f=14)
    over = dict(guard, sh_n=60, el_n=84, sh_f=80, lean=-5, head=-6)
    return _out([(base.lerp(start, guard, 0.5), 40), (over, 50), (guard, hold)], ms, rest)


def parry(ms=1.0, **rest):
    """Quick deflect: snap into an upright guard, flick the blade sharply outward and down (smear),
    snap back to guard. About 460 ms at ms=1."""
    guard = _p(rest, sh_n=50, el_n=80, grip_n=45, sh_f=40, el_f=55, lean=-2, head=-3,
               hip_n=16, knee_n=16, hip_f=-16, knee_f=12)
    start = base.pose("humanoid", **rest)
    flick = _p(rest, sh_n=95, el_n=10, grip_n=5, sh_f=20, el_f=50, lean=6, head=-2,
               hip_n=22, knee_n=20, hip_f=-18, knee_f=10, dx=1, smear="weapon_n")
    follow = dict(_calm(flick), sh_n=88, grip_n=0, lean=7)
    return _out([(base.lerp(start, guard, 0.6), 40), (guard, 90), (flick, 50), (follow, 90),
                 (base.lerp(follow, guard, 0.5), 70), (guard, 120)], ms, rest)


def kick(ms=1.0, **rest):
    """Front kick with the near leg: chamber the knee, snap the leg out straight (smear on the
    foot), hold, re-chamber and step down. The body leans back for balance. About 620 ms at ms=1."""
    start = base.pose("humanoid", **rest)
    lift = _p(rest, hip_n=50, knee_n=85, ankle_n=10, hip_f=-4, knee_f=10, lean=-4, head=2,
              sh_n=25, el_n=75, grip_n=65, sh_f=-25, el_f=40)
    chamber = _p(rest, hip_n=85, knee_n=110, ankle_n=10, hip_f=-4, knee_f=12, lean=-8, head=4,
                 sh_n=35, el_n=90, grip_n=50, sh_f=-40, el_f=40)
    extend = _p(rest, hip_n=100, knee_n=0, ankle_n=-35, hip_f=-8, knee_f=6, lean=-18, head=10,
                sh_n=30, el_n=100, grip_n=45, sh_f=-55, el_f=35, smear="foot_n")
    hold = dict(_calm(extend), lean=-19)
    return _out([(start, 60), (lift, 50), (chamber, 90), (extend, 50), (hold, 130),
                 (dict(chamber, lean=-6), 90), (base.lerp(chamber, start, 0.6), 70), (start, 80)], ms, rest)


def shield_bash(ms=1.0, arm="f", **rest):
    """Shield shove: draw the shield arm in, then lunge (dx) with the forearm driven forward and the
    body behind it, hold the impact, step back. arm "f" (default) bashes with the far arm, where a
    shield is usually held; "n" uses the near arm. About 620 ms at ms=1."""
    o = "n" if arm == "f" else "f"
    start = base.pose("humanoid", **rest)
    coil = _p(rest, **{f"sh_{arm}": 10, f"el_{arm}": 110, f"sh_{o}": -25, f"el_{o}": 60},
              lean=-6, head=-2, hip_n=20, knee_n=22, hip_f=-16, knee_f=14, dx=-1)
    shove = _p(rest, **{f"sh_{arm}": 70, f"el_{arm}": 30, f"sh_{o}": -35, f"el_{o}": 55},
               lean=20, head=-6, hip_n=42, knee_n=40, hip_f=-36, knee_f=2, dx=4)
    hold = dict(shove, lean=21, dx=5)
    back = base.lerp(hold, start, 0.5)
    return _out([(start, 60), (coil, 160), (shove, 50), (hold, 150), (back, 100), (start, 100)], ms, rest)


ANIMS = {"humanoid": {"heavy_attack": heavy_attack, "thrust": thrust, "combo": combo, "block": block,
                      "parry": parry, "kick": kick, "shield_bash": shield_bash}}
LOOPING = set()
