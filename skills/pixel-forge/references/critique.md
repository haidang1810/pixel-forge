# Critique: judging your own work without fooling yourself

The agent that drew an asset is its worst judge: it knows what it meant, so it sees it. In tests, self-scores ran about two points above independent reviewers, single reviewers swung by a point or more between calls, and close to half of a reviewer's specific claims ("no cast shadow", "the fire is static") were contradicted by the pixels. This procedure keeps what is reliable and discards what is not.

## Use an outside reviewer

If you can start a subagent, the reviewer is a fresh one that did not draw the asset and is given only the rendered PNGs (never the source, the brief's adjectives, or your notes). Otherwise, do the cold read below before you look at anything you wrote.

## 1. Cold read first

Before the brief: in one sentence, what does the picture show to someone who was never told what it is, and which three things does the eye land on first? If the cold read does not name the subject, or misses the part the brief makes central (the face, the weapon, the fire), that is the most important defect, whatever else is right.

## 2. Score, with a ship bar

Score silhouette, form, clusters, color and value, design, and animation (if animated), 1–10: 10 is the best hand-made indie pixel art, 8 ships in a good commercial game, 6 is a decent jam game, 4 is programmer art. Every defect must cite a box `[x0, y0, x1, y1]` in native pixels (and a frame), so it can be checked. Then name the single highest-value fix.

## 3. Check claims against the pixels before acting

For each defect you are about to fix, crop the box (`pixel_art.py ascii DOC.json --box x0 y0 x1 y1` or an enlarged crop) and confirm it. Discard claims the pixels contradict. When comparing frames, compare RGB values: `getbbox()` on an RGBA difference only sees alpha and misses opaque pixels that changed color.

## 4. Keep a fix only if it wins blind

Scores out of 10 drift between calls; a choice between two versions is stable. After each fix:

```text
python SKILL_DIR/scripts/abtest.py old.png new.png --dir ab1 [--extra old.strip.png new.strip.png]
```

Give the reviewer `ab1/a.png` and `ab1/b.png` (not `.key.json`) and ask which is the better asset for the brief, in one line why, and whether each named defect is still present in each. Then `abtest.py --reveal ab1`. Keep the new version only if it won; otherwise revert and try a different fix. Keep the two versions comparable (same canvas and frame count), or the difference itself gives away which one is new. Review several assets of a set in one A/B call to save reviewer runs. One fix per round, the highest-value one first.

## 5. Stop

Stop when a fresh reviewer's cold read is right, nothing is blocking, and the scores reach the bar, or after three rounds by default (up to six when the user asks for final quality); each round costs a reviewer run. Report the last scores and what still falls short.

## Reviewer prompt (copy and fill in)

> You are an experienced pixel-art lead reviewing art for a commercial 2D game. You did not make it. Look at FILES (native pixels; enlarge with nearest-neighbour; view at 1x and 2x on a dark background as a player would; step through animation frames). First write a cold read: one sentence of what it shows to someone never told, and the three things the eye lands on first. Then score silhouette, form, clusters, color, design, animation (if animated) from 1 to 10, where 8 ships in a good commercial indie game and 6 is a decent jam game. List defects most costly first, each with a box [x0, y0, x1, y1] in native pixels and a frame index for strips. Only claim what you can point to. End with the single highest-value fix.
