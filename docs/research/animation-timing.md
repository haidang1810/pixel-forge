# Research notes: action timing for side-view pixel sprites

Collected by a research subagent on 2026-10-20 and summarized in our own words. At 60 fps 1F = 16.7 ms; at 24 fps 1F = 41.7 ms. "(estimate)" = judgement, not a sourced figure; [2nd] = secondary source.

| Action | Frames | Total ms | Phase split / notes |
|---|---|---|---|
| Idle / breathing | 2–4 (6–8 rich) | 1000–2000 loop | ping-pong, 1 px body motion, frames held 300–800 ms |
| Walk (biped) | 8 sweet spot (4–8) | 500–1000 cycle | contact, down, pass, up per step; triangle-wave bob, lowest at contact/down |
| Run | 6–8 | 400–700 cycle | contact, down (squash), push-off, airborne (stretch); 50–100 ms per frame |
| Jump takeoff | 1–2 | 60–160 | crouch squash then launch stretch (Celeste 0.6×1.4, eased back over ~230 ms) |
| Jump rise | 1–2 or held | ~200–400 (estimate) | stretched pose held |
| Jump apex | 1 held | 120–200 | neutral or tucked hold |
| Jump fall | 1–2 loop | physics | stretched or flailing |
| Landing | 1–2 | 80–200 | squash (Celeste up to 1.6×0.4 by fall speed), recover ~340 ms |
| Light attack | 3–6 | 200–400 | startup 3–4F / active 2–4F / recovery 5–8F @60fps; strike frame 30–60 ms, wind-up 60–150, recovery 80–150 |
| Heavy attack | 6–10 | 500–900 | anticipation 35–45% / active 10–15% / recovery 40–50%; hold wind-up 150–300, strike 1 frame (smear), hold impact 120–200 |
| Thrust / stab | 3–5 | 250–500 (estimate) | pull-back 1–2F / lunge 1F / hold at full extension / retract |
| Combo | 2–4 hits × 3–6 frames | 250–450 per hit, 0.8–1.5 s (estimate) | each recovery becomes the next anticipation; last hit longer |
| Bow | 4–7 | 500–900 (estimate) | draw 40% / hold at full draw / release 1F / follow-through |
| Throw | 3–5 | 300–500 (estimate) | wind-back hold / release 1F (smear) / follow-through |
| Spell cast | 4–6 + charge loop | 500–1200 (estimate) | charge (loop or hold) / release 1–2F / recovery; VFX carries impact |
| Block / guard | 1–3 enter + hold | enter 50–100 | fast raise, hold; 1–2 frame shudder on a blocked hit |
| Dodge / roll | 4–8 | 400–700 | invulnerable first half (Enter the Gungeon ~0.7 s) |
| Dash | 2–4 | 150–250 | 1-frame freeze at start (Celeste 50 ms), stretched streak, brake frame |
| Hit-stop | freeze current frame | light 50–130, heavy 130–330 | both attacker and victim; ~100–200 ms tested best |
| Hurt | 1–3 | 150–400 + flash | snap to the recoil pose, hold, return |
| Knockback | 1–2 held | 200–500 (estimate) | recoil, slide/airborne pose, recover |
| Death | 4–8, last held | 600–1500 (estimate) | fast impact, progressively slower frames, long hold or fade |
| Quadruped walk | 8 (16–24 smooth) | ~1000 | footfall LR, LF, RR, RF; hips, chest and head as offset bounces |
| Trot | 6–8 | 500–700 | diagonal pairs together |
| Gallop | 6–8 | 300–500 | rotary: LR, RR, RF, LF; gather (squash) then extension (stretch) |
| Pounce / bite | 4–7 | 500–900 (estimate) | crouch hold 200–400 (telegraph) / leap 1–2F / snap 1F / land 2F |
| Bird flap | 2–8 | 250–500 per flap | fast downstroke (fewer frames), slow upstroke; offset flocks |
| Glide | 1–2 | hold, slow bob every 400–600 (estimate) | wings spread |
| Bird takeoff | 3–5 | 300–500 (estimate) | crouch, big downstroke leap, join flap |
| Bird landing | 3–4 | 250–400 (estimate) | flare, feet forward, touch-down squash, fold |
| Slime hop | 4–6 | 500–900 (estimate) | squash 150–250 / stretch launch 1F / round airborne / landing squash / jiggle settle |

## Rules of thumb

1. About 100 ms per frame (8–12 fps) is the pixel-art norm. Vary the frame time rather than using uniform timing.
2. Attacks have three parts: startup, active and recovery. Recovery and hitstun sell the weight.
3. Keep the wind-up long, the strike 1–2 frames and the impact or extension hold 120–200 ms. The strike frame itself lasts 30–60 ms.
4. Hit-stop scales with damage: about 3–8F for light hits and 12–20F+ for heavy ones.
5. A 1-frame freeze adds punch to a dash or launch. Apply squash and stretch instantly, then ease it back over 200–350 ms.
6. Holds should run at least about 250 ms. In pixel art, use one frame with a long duration rather than duplicated frames.
7. Ease in and out by holding the first and last frames longer and playing the middle fast.
8. Use pose-to-pose keys, with in-betweens only near the keys (Dead Cells).
9. **Quadrupeds:** hips and chest are offset bouncing balls, and the head is a third. Gallops gather (squash) before they stretch.
10. **Wings:** fast downstroke, slow upstroke.
11. The principles that matter most at this scale: anticipation, holds and timing, squash and stretch, smear frames on the strike, follow-through and overlap on hair, capes and tails, and arcs on swings.

## Sources read

- [Capcom SFV column: frame data and hit stop](https://game.capcom.com/cfn/sfv/column/131545)
- [Slynyrd, Pixelblog 50: Human Walk Cycle](https://slynyrd.com/blog/2024/5/24/pixelblog-50-human-walk-cycle)
- [Celeste source, Player.cs](https://raw.githubusercontent.com/NoelFB/Celeste/master/Source/Player/Player.cs)
- [SmashWiki, Hitlag](https://www.ssbwiki.com/Hitlag)
- [Brian LeMay, Principles of Animation: Timing](https://www.brianlemay.com/Pages/animationschool/animation/lipsyncbook/timing.html)
- [Game Developer, Animating Four-Legged Beasts](https://www.gamedeveloper.com/art/animating-four-legged-beasts)
- [Game Developer, Dead Cells 3D-to-2D pipeline](https://www.gamedeveloper.com/production/art-design-deep-dive-using-a-3d-pipeline-for-2d-animation-in-i-dead-cells-i-)
- [sprite-ai, sprite animation frames](https://www.sprite-ai.art/blog/sprite-animation-frames) [2nd]
- [sprite-ai, animation principles](https://www.sprite-ai.art/guides/animation-principles) [2nd]
- [Pixnote, Pixel Art Animation Basics](https://pixnote.net/en/learn/animation) [2nd]
- [itch.io, Pixel tutorial: slimes](https://itch.io/t/1471610/pixel-tutorial-slimes)
