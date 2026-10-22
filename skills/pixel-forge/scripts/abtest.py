#!/usr/bin/env python3
"""Prepare a blind A/B comparison of two versions of an asset.

    python abtest.py OLD.png NEW.png --dir AB_DIR [--extra OLD.strip.png NEW.strip.png]
    python abtest.py --reveal AB_DIR

Copies the two versions to AB_DIR as a.png and b.png in a random order (and a.strip.png and
b.strip.png for --extra), so a critic cannot tell which one is newer. The order is kept in
AB_DIR/.key.json; do not show that file to the critic. After the critic picks a or b, --reveal
says whether it picked the new version. Keep a fix only when it wins.
"""
import argparse
import json
from pathlib import Path
import secrets
import shutil
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old", nargs="?")
    parser.add_argument("new", nargs="?")
    parser.add_argument("--dir")
    parser.add_argument("--extra", nargs=2, metavar=("OLD_EXTRA", "NEW_EXTRA"), help="a second pair, e.g. animation strips")
    parser.add_argument("--reveal", metavar="AB_DIR", help="print which letter is the new version")
    args = parser.parse_args(argv)
    if args.reveal:
        key = json.loads((Path(args.reveal) / ".key.json").read_text(encoding="utf-8"))
        print(f"new version is {key['new']}, old is {key['old']}")
        return 0
    if not (args.old and args.new and args.dir):
        print("error: give OLD NEW --dir AB_DIR (or --reveal AB_DIR)", file=sys.stderr)
        return 2
    out = Path(args.dir)
    out.mkdir(parents=True, exist_ok=True)
    new_letter = secrets.choice("ab")
    old_letter = "b" if new_letter == "a" else "a"
    pairs = [(args.old, args.new, "")] + ([(args.extra[0], args.extra[1], ".strip")] if args.extra else [])
    for old, new, suffix in pairs:
        shutil.copy(old, out / f"{old_letter}{suffix}.png")
        shutil.copy(new, out / f"{new_letter}{suffix}.png")
    (out / ".key.json").write_text(json.dumps({"new": new_letter, "old": old_letter, "old_file": str(args.old),
                                               "new_file": str(args.new)}), encoding="utf-8")
    print(f"wrote {out / 'a.png'} and {out / 'b.png'} (order hidden in .key.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
