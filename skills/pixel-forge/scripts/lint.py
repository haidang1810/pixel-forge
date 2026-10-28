#!/usr/bin/env python3
"""Aesthetic lint for pixel sprites: findings an artist would flag, with numbers to act on.

    python lint.py OUT_DIR                 # a rig2d output folder (reads animation.json and the sheets)
    python lint.py sprite.png other.png    # single images
    python lint.py OUT_DIR --json report.json

Checks (warnings, not failures; judge them against the intent):
  colors      more opaque colors than a small sprite usually needs
  stray       pixels unlike all 8 neighbours (noise, broken clusters); clear highlights such as
              glints, sparks and rivets (lighter than every neighbour) are not counted
  muddy       touching colors so close in value that shapes blur together
  lighting    top-facing edges no lighter than bottom-facing ones (pillow shading or a flipped light)
  thin        silhouette made mostly of outline (noodle limbs, unreadable at 1x)
  edge        art touching the frame edge (clipping)
  ground      grounded frames of one animation ending on different rows
  duplicates  colors so close they read as one (Lab distance < 4): one of them does no work
  flat_ramp   shading that only changes value, not hue (shadows should cool, lights warm)
  banding     parallel same-length runs of two colors with aligned ends (reads as stripes)
"""
import colorsys
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def luminance(c):
    r, g, b = (v / 255 for v in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def lab(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in c[:3])
    x, y, z = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.9505, r * 0.2126 + g * 0.7152 + b * 0.0722,         (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.089
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def generated_tells(fill, colors, w):
    """Checks borrowed from catalogues of machine-made pixel art: near-duplicate colors, value-only
    shading and banding."""
    findings = []
    labs = {c: lab(c) for c in colors}
    listed = sorted(colors)
    dupes = [(a, b) for i, a in enumerate(listed) for b in listed[i + 1:]
             if sum((p - q) ** 2 for p, q in zip(labs[a], labs[b])) ** 0.5 < 4]
    if dupes:
        hexes = lambda c: f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}"
        listed_pairs = ", ".join(f"{hexes(a)}/{hexes(b)}" for a, b in dupes[:6])
        findings.append(f"duplicates: {len(dupes)} color pair(s) a viewer cannot tell apart ({listed_pairs}"
                        f"{', ...' if len(dupes) > 6 else ''}); merge them")
    shading = flat = 0
    for (x, y), c in fill.items():
        for dx, dy in ((1, 0), (0, 1)):
            d = fill.get((x + dx, y + dy))
            if not d or d == c:
                continue
            hc, sc, vc = colorsys.rgb_to_hsv(*(v / 255 for v in c[:3]))
            hd, sd, vd = colorsys.rgb_to_hsv(*(v / 255 for v in d[:3]))
            if sc < 0.2 or sd < 0.2 or abs(vc - vd) < 0.08:
                continue
            hue = min(abs(hc - hd), 1 - abs(hc - hd)) * 360
            if hue > 40:
                continue  # different materials, not a shading step
            shading += 1
            flat += hue < 3
    if shading > 30 and flat / shading > 0.6:
        findings.append(f"flat_ramp: {round(100 * flat / shading)}% of shading steps keep the same hue; "
                        "shift shadows toward blue-violet and lights toward warm")
    rows = {}
    for (x, y), c in fill.items():
        rows.setdefault(y, {})[x] = c
    runs = {}
    for y, cells in rows.items():
        x = min(cells)
        while x <= max(cells):
            if x not in cells:
                x += 1
                continue
            start, c = x, cells[x]
            while cells.get(x) == c:
                x += 1
            if x - start >= max(6, w // 4):
                runs.setdefault(y, []).append((start, x, c))
    bands = sum(1 for y, rs in runs.items() for a in rs for b in runs.get(y + 1, [])
                if a[2] != b[2] and a[0] == b[0] and a[1] == b[1])
    if bands >= 2:
        findings.append(f"banding: {bands} pairs of long same-length color runs stacked with aligned ends; "
                        "stagger the ends so tone boundaries follow the form")
    return findings


def lint_frame(image):
    """Return (metrics, findings) for one RGBA frame."""
    w, h = image.size
    px = image.load()
    opaque = {(x, y): px[x, y] for y in range(h) for x in range(w) if px[x, y][3]}
    findings = []
    if not opaque:
        return {"opaque": 0}, ["empty frame"]
    colors = set(opaque.values())
    # The outline is the most common color on the silhouette edge.
    edge = [p for p in opaque if any((p[0] + dx, p[1] + dy) not in opaque for dx, dy in N4)]
    edge_colors = [opaque[p] for p in edge]
    outline = max(set(edge_colors), key=edge_colors.count)
    fill = {p: c for p, c in opaque.items() if c != outline}
    metrics = {"opaque": len(opaque), "colors": len(colors), "outline_share": round(1 - len(fill) / len(opaque), 2)}

    budget = max(24, round(24 * (image.width * image.height / 4096) ** 0.5))  # scenes may use more than sprites
    if len(colors) > budget:
        findings.append(f"colors: {len(colors)} opaque colors; art this size reads better with at most about {budget}")

    def corner(p):  # boxed in by outline on two perpendicular sides: an anti-aliasing position
        x, y = p
        return any(opaque.get((x + ax, y)) == outline and opaque.get((x, y + ay)) == outline
                   for ax in (1, -1) for ay in (1, -1))
    def glint(p, c):  # a deliberate highlight: clearly lighter than everything around it (sparks, rivets)
        around = [opaque.get((p[0] + dx, p[1] + dy)) for dx, dy in N8]
        return all(a is None or luminance(c) > luminance(a) + 0.12 for a in around)
    stray = [p for p, c in fill.items()
             if all(opaque.get((p[0] + dx, p[1] + dy)) != c for dx, dy in N8) and not corner(p) and not glint(p, c)]
    metrics["stray"] = len(stray)
    if fill and len(stray) > max(3, 0.02 * len(fill)):
        findings.append(f"stray: {len(stray)} lone pixels (e.g. at {stray[0]}); merge them into clusters")

    pairs = close = 0
    for (x, y), c in fill.items():
        for dx, dy in ((1, 0), (0, 1)):
            d = fill.get((x + dx, y + dy))
            if d and d != c:
                pairs += 1
                close += abs(luminance(c) - luminance(d)) < 0.03
    metrics["muddy_share"] = round(close / pairs, 2) if pairs else 0
    if pairs > 20 and close / pairs > 0.35:
        findings.append(f"muddy: {round(100 * close / pairs)}% of color boundaries differ by <3% in value; "
                        "push neighbouring tones further apart")

    top = [luminance(c) for (x, y), c in fill.items() if (x, y - 1) not in fill]
    bottom = [luminance(c) for (x, y), c in fill.items() if (x, y + 1) not in fill]
    if len(top) > 8 and len(bottom) > 8:
        diff = sum(top) / len(top) - sum(bottom) / len(bottom)
        metrics["top_minus_bottom"] = round(diff, 3)
        if diff <= 0.0:
            findings.append("lighting: top-facing edges are not lighter than bottom-facing ones "
                            "(pillow shading, or the light points up)")

    if metrics["outline_share"] > 0.55 and len(opaque) > 40:
        findings.append(f"thin: {round(100 * metrics['outline_share'])}% of the sprite is outline; "
                        "thicken limbs or drop interior outlines")

    findings += generated_tells(fill, set(fill.values()), w)

    box = image.getbbox()
    metrics["bbox"] = list(box)
    if box[0] == 0 or box[1] == 0 or box[2] == w or box[3] == h:
        findings.append(f"edge: art touches the frame edge {list(box)}")
    return metrics, findings


def frames_of(folder):
    manifest = json.loads((folder / "animation.json").read_text(encoding="utf-8"))
    for name, anim in manifest["animations"].items():
        with Image.open(folder / anim["sheet"]) as sheet:
            sheet = sheet.convert("RGBA")
            yield name, [(sheet.crop((x, y, x + w, y + h)), f.get("effects", []))
                         for f in anim["frames"] for x, y, w, h in [f["rect"]]]


GROUNDED = {"idle", "walk", "attack", "hurt"}


def summarize(entries):
    """One line per kind of finding across an animation, naming the frames it occurs in."""
    by_kind = {}
    for i, (_, findings) in enumerate(entries):
        for text in findings:
            by_kind.setdefault(text.split(":")[0], []).append((i, text))
    notes = []
    for kind, hits in by_kind.items():
        frames = [i for i, _ in hits]
        where = "all frames" if len(frames) == len(entries) else f"frames {frames}"
        notes.append(f"{hits[0][1]} [{where}]" if len(hits) > 1 else f"{hits[0][1]} [frame {frames[0]}]")
    return notes


def lint_path(path):
    path = Path(path)
    report = {}
    if path.is_dir():
        for name, frames in frames_of(path):
            entries = []
            for image, effects in frames:
                metrics, findings = lint_frame(image)
                # Intended effects are not defects: a flash frame has no lighting, a dissolve is speckled
                # by design and may end empty.
                if "flash" in effects:
                    findings = [f for f in findings if not f.startswith("lighting")]
                if "dissolve" in effects:
                    findings = [f for f in findings if not f.startswith(("stray", "empty", "lighting"))]
                entries.append((metrics, findings))
            notes = summarize(entries)
            bottoms = {m.get("bbox", [0, 0, 0, 0])[3] for m, _ in entries if m.get("opaque")}
            if name in GROUNDED and len(bottoms) > 1:
                notes.append(f"ground: grounded frames end on rows {sorted(bottoms)}; the feet should stay on one row")
            report[name] = {"frames": [m for m, _ in entries], "findings": notes}
    elif path.name.endswith(".anim.json"):  # a pixel_art animation: lint every frame of its strip
        anim = json.loads(path.read_text(encoding="utf-8-sig"))
        with Image.open(path.with_name(path.name[:-len(".anim.json")] + ".strip.png")) as sheet:
            sheet = sheet.convert("RGBA")
            entries = [lint_frame(sheet.crop((x, y, x + w, y + h))) for x, y, w, h in (f["rect"] for f in anim["frames"])]
        report[path.name[:-len(".anim.json")]] = {"frames": [m for m, _ in entries], "findings": summarize(entries)}
    else:
        with Image.open(path) as image:
            metrics, findings = lint_frame(image.convert("RGBA"))
        report[path.name] = {"frames": [metrics], "findings": findings}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", help="also write the full report here")
    args = parser.parse_args(argv)
    full = {}
    total = 0
    for p in args.paths:
        if not Path(p).exists() or (Path(p).is_dir() and not (Path(p) / "animation.json").is_file()):
            print(f"error: {p}: expected a PNG, a PREFIX.anim.json or a folder with animation.json", file=sys.stderr)
            return 2
        report = lint_path(p)
        full[str(p)] = report
        for name, entry in report.items():
            total += len(entry["findings"])
            status = "ok" if not entry["findings"] else f"{len(entry['findings'])} finding(s)"
            print(f"{Path(p).name}/{name}: {status}")
            for f in entry["findings"]:
                print(f"  - {f}")
    if args.json:
        Path(args.json).write_text(json.dumps(full, indent=1), encoding="utf-8")
    print(f"{total} finding(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
