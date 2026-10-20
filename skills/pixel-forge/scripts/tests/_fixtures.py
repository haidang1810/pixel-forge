"""Test characters: the repository's example specs when present, else small built-in stand-ins.

The skill can be installed without the repository's examples/ folder, so pack tests must not
depend on it.
"""
import json
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[4] / "examples" / "characters"

_GREYS = ["#203040", "#405060", "#6080A0"]
FALLBACKS = {
    "raven.json": {"name": "raven", "size": [44, 48], "rig": "bird", "root_x": 0.42, "outline": "#08080E",
                   "materials": {"body": _GREYS, "wing": ["#202030", "#404060", "#606090"],
                                 "beak": ["#806020", "#C09040", "#F0C060"], "leg": ["#604020", "#806040", "#A08060"]}},
    "serpent.json": {"name": "serpent", "size": [64, 40], "rig": "serpent", "root_x": 0.62, "outline": "#10160C",
                     "materials": {"body": ["#2B3A1E", "#46602E", "#6F8F3E"]}},
    "slime.json": {"name": "slime", "size": [44, 32], "rig": "slime", "root_x": 0.5, "outline": "#0E1F18",
                   "materials": {"body": ["#1E4D3A", "#2F7A55", "#4FB57A"]}},
}
_GHOST = {"name": "ghost", "size": [48, 48], "rig": "humanoid", "root_x": 0.45, "outline": "#06040C",
          "pose_offset": {"dy": -5},
          "materials": {"body": ["#110C1C", "#1F1730", "#33284C"], "skin": ["#3A4A66", "#6F86A8", "#A9C2DC"],
                        "legs": ["#110C1C", "#1F1730", "#33284C"], "boots": ["#110C1C", "#1F1730", "#33284C"]},
          "parts": {"foot_n": {"hidden": True}, "foot_f": {"hidden": True}}}
FALLBACKS["ghost.json"] = dict(_GHOST)
FALLBACKS["ghost-vector.json"] = dict(_GHOST, name="ghost-vector")


def load_example(name):
    path = EXAMPLES / name
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(json.dumps(FALLBACKS[name]))
