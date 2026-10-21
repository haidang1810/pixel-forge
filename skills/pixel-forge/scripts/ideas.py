#!/usr/bin/env python3
"""Roll fresh design directions for a character, so repeated requests do not converge.

Language models asked for "a goblin" tend to pick the same traits, colors and even the same seed
every time. This tool draws from real randomness (the operating system), not from the agent:

    python ideas.py --role brute --rig humanoid --count 3

Each direction names a dominant shape, a signature feature, a base hue (as a color to feed
{"base": ...} materials), an accent, a build, a temperament with matching motion values, a style,
and a fresh motion seed. Adapt a direction to the subject; do not paste it blindly. Pass --seed to
reproduce a roll.
"""
import argparse
import colorsys
import json
import secrets
import random

SHAPES = {
    "round": "soft circles and ovals (friendly, cute, harmless-looking)",
    "square": "blocky rectangles, a wide stable base (sturdy, stubborn, heavy)",
    "triangle": "spikes and wedges pointing forward (dangerous, quick, sly)",
    "broken": "asymmetric, jagged, chunks missing (wrong, cursed, decayed)",
    "flowing": "long curves with a few sharp accents (elegant, magical)",
    "inverted-triangle": "wide shoulders over a narrow base (heroic, top-heavy, imposing)",
}
FEATURES = [
    "an oversized head piece (hood, helmet, hat, mane or crest)",
    "one exaggerated limb or claw on one side only",
    "a long tail or trailing appendage that shows follow-through",
    "something carried on the back (pack, shell, banner, wings, spikes)",
    "a single glowing eye or glowing mark as the brightest pixel",
    "bold body markings: stripes, spots or a pale mask",
    "tattered cloth: a cape, scarf or rags with a jagged hem",
    "mismatched armor plates or patches on one side",
    "horns, antlers or ears that break the silhouette upward",
    "a tool or weapon much larger or much smaller than expected",
    "a belly or chest of a contrasting pale color",
    "a hunched neck with the head carried low and forward",
]
TEMPERAMENTS = {
    "heavy and sluggish": {"weight": 0.9, "energy": 0.2, "exaggeration": 0.9, "follow": 0.4},
    "nervy and darting": {"weight": 0.15, "energy": 0.95, "exaggeration": 1.2, "follow": 0.3},
    "proud and deliberate": {"weight": 0.6, "energy": 0.4, "exaggeration": 0.85, "follow": 0.5},
    "bouncy and playful": {"weight": 0.25, "energy": 0.85, "exaggeration": 1.35, "follow": 0.6},
    "stiff and jerky": {"weight": 0.5, "energy": 0.6, "exaggeration": 1.4, "follow": 0.1},
    "calm and floaty": {"weight": 0.3, "energy": 0.3, "exaggeration": 1.0, "follow": 0.75},
    "aggressive and driven": {"weight": 0.7, "energy": 0.8, "exaggeration": 1.2, "follow": 0.45},
    "tired and droopy": {"weight": 0.75, "energy": 0.15, "exaggeration": 0.8, "follow": 0.6},
}
BUILDS = {
    "humanoid": ["bulky", "slim", "tall", "short", "child", "elderly", "brute", None],
    "chibi": ["bulky", "slim", "short", None],
    "quadruped": ["bulky", "slim", "tall", "short", None],
}
STYLES = [
    {"outline": "black", "shades": 4, "light": "upper-front"},
    {"outline": "selout", "shades": 3, "light": "upper-front"},
    {"outline": "black", "shades": 3, "dither": True, "light": "top"},
    {"outline": "selout", "shades": 4, "light": "upper-back"},
    {"outline": "black", "shades": 2, "light": "front"},
]
KITS = ["pico-8", "dawnbringer-16", "dawnbringer-32", "aap-64", "sweetie-16", "endesga-32"]
# Preferred shapes and temperaments per role (from references/design.md); used about 70% of the time.
ROLES = {
    "hero": (["inverted-triangle", "round"], ["proud and deliberate", "aggressive and driven", "bouncy and playful"]),
    "villain": (["triangle", "flowing"], ["proud and deliberate", "stiff and jerky", "calm and floaty"]),
    "brute": (["square", "inverted-triangle"], ["heavy and sluggish", "aggressive and driven"]),
    "scout": (["triangle"], ["nervy and darting", "bouncy and playful"]),
    "mage": (["flowing", "triangle"], ["calm and floaty", "proud and deliberate"]),
    "healer": (["round", "flowing"], ["calm and floaty", "bouncy and playful"]),
    "critter": (["round"], ["bouncy and playful", "nervy and darting"]),
    "mob": (["round", "triangle", "square"], ["aggressive and driven", "stiff and jerky", "nervy and darting"]),
    "elite": (["inverted-triangle", "triangle"], ["proud and deliberate", "aggressive and driven"]),
    "undead": (["broken"], ["stiff and jerky", "tired and droopy"]),
    "beast": (["triangle", "square"], ["aggressive and driven", "nervy and darting", "heavy and sluggish"]),
}


def hsv_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def roll(rng, role=None, rig="humanoid"):
    shapes, tempers = ROLES.get(role, (list(SHAPES), list(TEMPERAMENTS)))
    shape = rng.choice(shapes if rng.random() < 0.7 else list(SHAPES))
    temper = rng.choice(tempers if rng.random() < 0.7 else list(TEMPERAMENTS))
    hue = rng.random()
    base = hsv_hex(hue, rng.uniform(0.35, 0.75), rng.uniform(0.45, 0.8))
    accent_offset = rng.choice([0.5, 0.42, 0.58, 0.33, 0.67])  # complementary or split-complementary
    accent = hsv_hex(hue + accent_offset, rng.uniform(0.6, 0.95), rng.uniform(0.75, 1.0))
    motion = dict(TEMPERAMENTS[temper], seed=rng.randrange(1, 1_000_000))
    return {
        "dominant_shape": f"{shape}: {SHAPES[shape]}",
        "signature_feature": rng.choice(FEATURES),
        "base_color": base,
        "accent_color": accent,
        "palette_kit_option": rng.choice(KITS),
        "build": rng.choice(BUILDS.get(rig, [None])),
        "temperament": temper,
        "motion": motion,
        "style": rng.choice(STYLES),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--role", choices=sorted(ROLES), help="bias the roll toward a role from references/design.md")
    parser.add_argument("--rig", default="humanoid", help="rig name, for the build suggestion")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--seed", type=int, help="reproduce a previous roll (default: fresh OS randomness)")
    args = parser.parse_args(argv)
    seed = args.seed if args.seed is not None else secrets.randbelow(2**31)
    rng = random.Random(seed)
    directions = [roll(rng, args.role, args.rig) for _ in range(args.count)]
    print(json.dumps({"roll_seed": seed, "directions": directions}, indent=1))


if __name__ == "__main__":
    main()
