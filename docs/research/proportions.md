# Research notes: body proportions for small sprites

Collected by a research subagent on 2026-10-20 and summarized in our own words. Values marked (estimate) are interpolations, not sourced measurements. Several sources were partly inaccessible; treat ranges as guidance.

## Heads tall by style (fractions of total height H)

| Style | Heads | Head | Torso (shoulder–hip) | Legs (hip–ground) | Upper arm | Forearm+hand | Thigh | Shin+foot | Shoulder W | Hip W |
|---|---|---|---|---|---|---|---|---|---|---|
| Chibi / SD (estimate) | 2–3 | 0.33–0.45 | 0.22–0.27 | 0.30–0.36 | 0.11–0.13 | 0.13–0.15 | 0.14–0.16 | 0.16–0.19 | 0.28–0.32 | 0.22–0.26 |
| Cute / stylized (estimate) | 3–4 | 0.25–0.33 | 0.26–0.28 | 0.38–0.43 | 0.14–0.16 | 0.17–0.19 | 0.19–0.21 | 0.20–0.22 | 0.27–0.30 | 0.21–0.23 |
| Game hero (estimate) | 5–6 | 0.17–0.20 | 0.28–0.30 | 0.46–0.50 | 0.17 | 0.22–0.24 | 0.22–0.24 | 0.24–0.26 | 0.28–0.31 | 0.19–0.21 |
| Realistic (Drillis & Contini) | 7–7.5 | 0.13–0.14 | 0.29 | 0.53 | 0.186 | 0.254 | 0.245 | 0.285 | 0.259 | 0.191 |
| Heroic | 8–9 | 0.11–0.125 | 0.28 | 0.53–0.56 | 0.19 | 0.25–0.26 | 0.26 | 0.28–0.30 | 0.29–0.33 | 0.19 |

When the head count drops, length comes mostly out of the legs and neck; the torso stays near 0.25–0.29 H. Elbows sit at the navel and wrists at the groin; Loomis: shoulders about 2⅓ heads wide, hips about 1.5.

## By sprite height

| Sprite H | Heads | Head px | Eyes | Limbs | Notes |
|---|---|---|---|---|---|
| 16 px | 2–3 | 6–8 | 1×1–1×2 | arms 1 px | drop nose, mouth, fingers, neck |
| 32 px | 3–4 | 9–12 | 2×2 | arms 2 px, legs 2–3 px | equipment and expression possible |
| 48 px | 4–5.5 | 10–12 | 2×2–3×3 | 2–3 px | limited face detail |
| 64 px | 5–6.5 | 10–13 | 3×3 | 3–4 px | little to drop |

A face needs roughly 8–12 px of head before it reads (estimate). Exaggerate head, eyes, hair, hands, feet and weapon at small sizes; simplify nose, ears, neck.

## Body types (estimates applied on top of a style)

| Type | Changes |
|---|---|
| Stocky / bulky | −1 to −1.5 heads; shoulders ×1.2–1.35; legs ×0.85; limb width ×1.3; low centre, wide stance |
| Slim / lanky | +0.5 to +1 head; shoulders ×0.85; legs ×1.08; thin limbs; slight slouch |
| Tall | +0.5 head, mostly legs |
| Short | −0.5 head, mostly legs |
| Child | 4–6 heads; big forehead, low eye line, round torso, short limbs |
| Elderly | height −3–5%; head and neck forward (kyphosis), knees slightly bent, shorter stride |
| Giant / brute | small head on bulk; shoulders 0.40–0.50 H; short legs; long heavy arms, hands ×1.5; torso tilted forward |

## Quadrupeds (body length L, chest to rump)

| Animal | Shoulder height | Head length | Tail | Pixel stylization |
|---|---|---|---|---|
| Horse | ≈ 1.0 L | 0.35–0.4 L | ~0.5 L | neck shortened, head enlarged |
| Wolf / dog | 0.8–0.9 L | ~0.33 L | 0.5–0.6 L | head ×1.3, legs −10–20% |
| Cat | 0.6–0.7 L | ~0.25 L | 0.7–0.9 L | round head, big eyes, low body |
| Boar | 0.6–0.7 L | ~0.4 L | ~0.2 L | wedge silhouette, stub legs |
| Bear | 0.55–0.65 L | 0.25–0.3 L | stub | shoulder hump, pillar legs |

General: head 1.2–1.5× real size, legs about 0.8× real, darken the far pair.

## Birds, snakes, slimes (estimates)

- **Bird:** body ellipse 1.6–2 : 1; head 0.3–0.4 of the body length for small birds; wingspan / body length 1.5 for sparrows, 2 for crows, 2.2–2.5 for raptors and gulls.
- **Snake:** length 15–30× thickness; the head is 1.0–1.2× the neck for colubrids and 1.5–2× for vipers; the tail tapers.
- **Slime:** width : height about 1.2–1.5 at rest. A squash goes to about 1.5× width and 0.6× height; a stretch to about 2× height and 0.5× width. The area stays roughly constant.

## Sources read

- [Slynyrd, Pixelblog 17: Human Anatomy](https://www.slynyrd.com/blog/2019/5/21/pixelblog-17-human-anatomy)
- [Slynyrd, Pixelblog 49: Realistic Human Anatomy](https://www.slynyrd.com/blog/2024/3/25/pixelblog-49-realistic-human-anatomy)
- [Proko, Human Proportions: Loomis](https://proko.com/human-figure-proportions-idealistic-loomis)
- [Pixnote, How to Draw Pixel Art Characters](https://pixnote.net/en/learn/character)
- [Art Nerds, Drawing horses: general proportions](https://artnerds.substack.com/p/drawing-horses-general-proportions)
- [itch.io, Pixel tutorial: slimes](https://itch.io/t/1471610/pixel-tutorial-slimes)
