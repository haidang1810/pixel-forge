# Focused renderer review

Reviewed the skill, format contract, renderer, and tests. Ran the existing tests: 13 passed. Used only this directory for new fixtures and results; no renderer or skill files were modified, and no with-skill evaluation outputs were inspected.

## Reproduced findings

1. P2 — Source protection misses hard-linked output aliases (`scripts/pixel_art.py:273`; equivalent render guard at 286). An output path can resolve to a different name while referencing the same file as the source. `patch source.json edits.json --output revision.json` returned 0 with revision.json hard-linked to source.json, and the source bytes changed. This contradicts the guarantee of keeping the original revision. Compare existing files with samefile as well as resolved path equality. Reproduction fixtures: hardlink-source.json, hardlink-revision.json, goodpatch.json; results key hardlink_patch. This is an edge case requiring a preexisting hardlink.

2. P2 — Reusing an output prefix without --grid leaves a grid from the previous revision (`scripts/pixel_art.py:283-294`). Rendered red art with --grid, then blue art to the same prefix without --grid. The native PNG became blue while normal.grid.png remained byte-identical and red. An agent opening the conventional grid path can correct coordinates against stale artwork; the format states rendered outputs at the prefix are replaced on rerun. Remove stale optional output safely or clearly report it as stale. Results key stale_grid; fixture normal.grid.png versus normal.png.

3. P3 — The documented minimum scale loses all artwork in grid export (`scripts/pixel_art.py:238,243`). --scale 1 --grid succeeds, but each cell is covered by horizontal/vertical grid lines; every canvas pixel becomes RGB (69,75,90). Native PNG and ordinary preview remain correct. Require a usable minimum grid scale or enlarge the grid independently. Results key grid_scale_one; fixture scale-one.grid.png.

4. P3 — Non-JSON numeric constants pass validation and are emitted into JSON reports (`scripts/pixel_art.py:46,252`). A source with meta.value set to the bare token NaN returned success and created nan-export.report.json containing NaN. Strict JSON readers reject that report. The contract calls these UTF-8 JSON documents. Reject nonfinite values during input validation, before exporting any images; serialization should also reject nonfinite numbers. Results key nonfinite_json; fixtures nan.json and nan-export.report.json.

## Additional checks that passed

Boolean canvas dimensions, unsupported hidden-layer operation fields, partial alpha, and duplicate JSON keys all failed cleanly. An out-of-bounds patch returned 2 and preserved the bytes of an existing output revision. Normal render and the supplied tests passed.

## Evidence and command

- results.json records return codes, diagnostics, pixel comparisons, and original-file comparisons.
- existing_tests.txt contains the supplied-test output.
- review.py creates fixtures and runs these checks. It uses the known Python interpreter and explicit subprocess cwd. The hardlink reproduction is deliberately single-run because its output alias already exists afterward.

PowerShell invocation from this folder:

```powershell
& 'C:/Users/dangh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B './review.py'
```
