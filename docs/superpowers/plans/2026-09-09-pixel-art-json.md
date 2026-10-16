# Pixel Art JSON Implementation Plan

**Goal:** Install a reusable personal skill that authors small pixel game assets as editable JSON and renders them without image-generation models or reference art.

**Architecture:** A concise skill and schema reference guide a multimodal agent through silhouette, palette, layers, render, inspect, and local revision. A Python/Pillow CLI validates deterministic drawing data, exports transparent PNG and inspection previews, and applies layer-local edits. Evaluation outputs live outside the installed skill.

**Tech stack:** Python 3.10+, Pillow, JSON, unittest; existing bundled runtime on this machine.

**Scope approved in conversation:** First experimental skill; no sample images or training library. Native pixel resolution, editability, visible demonstrations, and honest quality assessment. No image-generation service. No animation subsystem in version one.

## Files

- `skills/pixel-art-json/SKILL.md`: discovery and authoring workflow.
- `skills/pixel-art-json/references/format.md`: exact JSON and patch contract.
- `skills/pixel-art-json/agents/openai.yaml`: invocation metadata.
- `skills/pixel-art-json/scripts/pixel_art.py`: validation, rendering, previews, CLI.
- `skills/pixel-art-json/scripts/tests/test_pixel_art.py`: observable pixel, mutation, and CLI error contracts.
- `evaluation/`: baseline and forward-test artifacts, outside the skill.

## Tasks

- [x] Run an independent no-skill baseline while preparing the runtime. Record observed gaps without claiming a statistically established quality improvement.
- [x] Write runtime tests first. A tiny hand-specified image must preserve palette colors, transparent holes, layer ordering, and rectangle dimensions. Malformed rows, colors, duplicate layer names, and out-of-bounds coordinates must fail. Patches must preserve the source and unrelated layers. CLI export must produce readable PNGs and avoid overwriting input JSON.
- [x] Run tests and observe the missing renderer failure, then implement the CLI. Use `python -m unittest discover -s skills/pixel-art-json/scripts/tests -v` from this project.
- [x] Write the skill and format reference from the approved design and actual baseline observations. No artistic exemplar files are bundled. Include minimal geometric syntax examples only.
- [x] Have an independent agent use the completed skill on an original sprite. Parent authors separate small item demos, checks renderer behavior, and examines the output images.
- [x] Run `quick_validate.py`, tests, and package checks. Install to `C:/Users/dangh/.codex/skills/pixel-art-json`; keep evaluation outputs in this project and provide a preview plus invocation example.

## Acceptance

The new skill can be read and used without the prior conversation. Its tool runs on this machine, preserves exact RGBA pixels, provides actionable validation failures, and exports editable source plus native PNG. Installation does not alter existing skills. Visual quality is shown for user judgment rather than presented as guaranteed professional quality.

Verified: 17 tests pass against the installed copy; all four demo PNGs exactly match their editable JSON. The package has six files and zero reference images. Independent tool review reproduced four issues (file aliases, stale grids, scale-one grid visibility, non-finite JSON); targeted failing tests were added and all four corrected before installation.
