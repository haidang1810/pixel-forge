#!/usr/bin/env python3
"""Hue-shifted color ramps: give one base color, get pixel-art shading tones.

Shadows drift toward blue-violet and gain a little saturation; highlights drift toward warm yellow
and lose saturation, the way pixel artists build ramps by hand instead of only darkening.

    python palette_tools.py "#4F7A34" --tones 5        # print a ramp dark -> light
"""
import argparse
import colorsys
import json
from functools import lru_cache
from pathlib import Path

COOL = 250.0  # hue that shadows lean toward (degrees)
WARM = 55.0   # hue that highlights lean toward


def _toward(hue, target, amount):
    """Move `hue` toward `target` by `amount` degrees along the shorter way round."""
    diff = (target - hue + 180) % 360 - 180
    step = max(-abs(amount), min(abs(amount), diff))
    return (hue + step) % 360


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c * 255))) for c in rgb)


def ramp(base, tones=4, shift=24, spread=0.36, base_index=None):
    """Return `tones` hex colors dark -> light. The base color sits at `base_index`
    (default: second tone for 3-4 tones, middle for more), so a 4-tone ramp is dark, base, light, highlight."""
    r, g, b = (int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360
    if base_index is None:
        base_index = 1 if tones <= 4 else tones // 2
    out = []
    for i in range(tones):
        t = (i - base_index) / max(1, tones - 1) * 2  # -1 .. +1 roughly
        if t < 0:
            hue = _toward(h, COOL, -t * shift)
            sat = min(1.0, s + (-t) * 0.10)
            val = max(0.04, v + t * spread * (0.6 + 0.4 * v))
        elif t > 0:
            hue = _toward(h, WARM, t * shift * 0.6)
            sat = max(0.0, s - t * 0.22)
            val = min(1.0, v + t * spread * (1.1 - 0.5 * v))
        else:
            hue, sat, val = h, s, v
        out.append(_hex(colorsys.hsv_to_rgb(hue / 360, sat, val)))
    return out


def outline_for(base):
    """A dark, slightly cool outline that suits a ramp built from `base`."""
    return ramp(base, tones=5, shift=30, spread=0.9, base_index=3)[0]


def _check(where, value):
    ok = isinstance(value, str) and len(value) == 7 and value[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    if not ok:
        raise ValueError(f"{where}: expected a base color #RRGGBB")


@lru_cache(maxsize=None)
def kits():
    """Bundled palette kits from palettes.json: {slug: {name, author, url, terms, colors, outline, ramps}}."""
    return json.loads((Path(__file__).resolve().parent / "palettes.json").read_text(encoding="utf-8"))["kits"]


def kit(slug):
    if slug not in kits():
        raise ValueError(f"palette_kit: unknown kit {slug!r}; bundled kits are {sorted(kits())}")
    return kits()[slug]


def expand_materials(materials, kit_slug=None):
    """Materials may be a list of colors, {"base": "#RRGGBB", "tones": 3|4, "shift": degrees}, or
    {"kit": "<ramp name>"} taking a named ramp from the spec's palette_kit."""
    out = {}
    for name, value in materials.items():
        if isinstance(value, dict) and "kit" in value:
            if not kit_slug:
                raise ValueError(f"materials.{name}: a kit ramp needs a palette_kit in the spec")
            ramps = kit(kit_slug)["ramps"]
            if value["kit"] not in ramps or set(value) != {"kit"}:
                raise ValueError(f"materials.{name}.kit: choose from {sorted(ramps)} of {kit_slug}")
            out[name] = ramps[value["kit"]]
        elif isinstance(value, dict):
            _check(f"materials.{name}.base", value.get("base"))
            if set(value) - {"base", "tones", "shift"} or value.get("tones", 4) not in (3, 4):
                raise ValueError(f"materials.{name}: expected {{\"base\": \"#RRGGBB\", \"tones\": 3 or 4, \"shift\": degrees}}")
            out[name] = ramp(value["base"], value.get("tones", 4), value.get("shift", 24))
        else:
            out[name] = value
    return out


def expand_palette(spec):
    """spec["palette_gen"] = {"1234": "#4F7A34", ...} or {"1234": {"base": ..., "shift": ...}}: each
    key's symbols get a generated ramp (dark -> light) and become a ramp too."""
    gen = spec.get("palette_gen")
    if not gen:
        return spec
    palette = dict(spec.get("palette", {}))
    ramps = list(spec.get("ramps", []))
    for symbols, value in gen.items():
        base, shift = (value, 24) if isinstance(value, str) else (value.get("base"), value.get("shift", 24))
        _check(f"palette_gen.{symbols}", base)
        if len(symbols) < 2 or len(set(symbols)) != len(symbols) or "." in symbols:
            raise ValueError(f"palette_gen.{symbols}: expected two or more distinct symbols other than '.'")
        for symbol, color in zip(symbols, ramp(base, len(symbols), shift)):
            palette[symbol] = color
        ramps.append(symbols)
    return dict(spec, palette=palette, ramps=ramps)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base")
    parser.add_argument("--tones", type=int, default=4)
    parser.add_argument("--shift", type=float, default=24)
    args = parser.parse_args(argv)
    print(" ".join(ramp(args.base, args.tones, args.shift)), " outline:", outline_for(args.base))


if __name__ == "__main__":
    main()
