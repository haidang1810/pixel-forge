# Designing a character before drawing it

Use this file while choosing identity traits (SKILL.md, *Make it this user's asset*). It condenses design and proportion research, summarized in our own words. The source notes with links are in the repository's `docs/research/`.

## Shape language

- **Round** shapes read as friendly, soft, young or cute.
- **Square** shapes read as stable, strong, heavy or stubborn: tanks, guardians.
- **Triangles and spikes** read as dangerous, fast or sly, and they point in a direction.
- **Broken, asymmetric** forms read as wrong: undead, corrupted.
- **Clean geometry** reads as manufactured: golems, robots.
- **Flowing curves with a few controlled spikes** read as elegant power: mages, fae.

Give one shape about 60–70% of the mass, add one secondary shape and at most one accent. Contradict on purpose when it says something, for example a round body with angled eyes and claws for something cute but dangerous. Props either echo the main shape or contradict it deliberately: a brute carries a blocky hammer, a rogue a thin dagger, a mage a vertical staff with a round orb.

## Role table

| Role | Shapes | Proportions and posture | Color | Motion (`motion`, `build`) |
|---|---|---|---|---|
| Hero | inverted-triangle torso on a stable base, mostly round | mid-large head; upright, slight lean forward | saturated signature accent, highest contrast on face and weapon | medium-fast, clear anticipation, snappy recovery |
| Villain | spikes, long points, capes | small head on a tall frame, or a huge upper mass; looming or predatory lean | dark, desaturated, one toxic accent | controlled, sudden bursts, long telegraphs |
| Tank / brute | squares, wide block | `bulky` or `brute`; small head, thick limbs, wide stance, hunched | muted earth or metal | `weight` 0.8–1, `energy` low |
| Scout / rogue | slim triangles, pointed hood | `slim`; crouched, leaning forward | dark base, one sharp accent | `weight` 0.1–0.3, `energy` 0.8–1 |
| Mage | tall triangle (robe, hat) plus circles (orb) | small body under a big robe | cool arcane hues, glowing focus as the brightest pixel | floaty, low energy, visible charge-up |
| Healer / support | circles, soft ovals | rounded, bigger head and eyes, upright | light warm pastels | gentle, soft bounce |
| Cute critter | a ball with nubs | huge head, big low eyes, squat | bright, saturated | bouncy squash and stretch, high energy |
| Basic hostile mob | one simple shape plus a hostile accent | small, leaning toward the player | muted base, warm warning accent shared by the family | simple cycles, short telegraphs |
| Elite / boss | the family's shapes plus crown, horns, plates or a back piece | larger, one exaggerated part | the base recolored with trim or glow | slower, heavier, long readable telegraphs |
| Undead | broken, jagged, asymmetric | gaunt, uneven, hunched with arms forward | desaturated sickly hues, one glowing eye | jerky: use `exaggeration` and a `seed` |
| Beast | horizontal mass; triangle head and claws for predators | front-heavy, head forward | natural hues, a high-contrast eye | a predator stalks then pounces; prey is skittish |

## Readability

- Design the silhouette before the detail, and check it as a solid shape. The read order is: friend or foe (colour), then role (silhouette, proportions, weapon, headgear), then what it holds.
- Headgear, shoulders, the weapon and a back attachment separate types most at small sizes.
- In a mob family, each type differs in at least one large-mass trait: height/width ratio, orientation, an appendage or a weapon outline. A recolor alone makes a variant, not a new type.
- Keep negative space between the limbs and the body. Use asymmetry, and one clear line of action: forward diagonal means aggressive, vertical means proud, a drooping curve means weak or undead.
- Value first: the sprite must read in grayscale. Put the highest contrast on the face and the weapon, and keep the feet darker and quieter.

## Proportions by sprite height

| Height | Heads tall | Notes |
|---|---|---|
| 16 px | 2–3 | 1 px arms, 1–2 px eyes; drop nose, mouth, fingers and neck |
| 32 px | 3–4 (`chibi`) | 2 px arms, 2×2 eyes; equipment and expression become possible |
| 48 px | 4–5.5 | the standard `humanoid` rig fits here |
| 64 px | 5–6.5 | little needs dropping; use `tall` for a heroic look |

At small sizes, exaggerate the head, eyes, hands, feet and weapon; simplify the nose, ears and neck. A face needs about 8–12 px of head to read.

**Builds:**
- `bulky`: stocky, a wide block, low centre of mass.
- `slim`: lanky, narrow.
- `tall` / `short`: the difference is mostly in the legs.
- `child`: big head, short limbs.
- `elderly`: head and neck forward, knees slightly bent.
- `brute`: a giant; small head on a wide torso, long heavy arms, leaning forward.

**Quadrupeds:** in pixel art, draw the head about 1.2–1.5× its real size, the legs about 0.8× their real length, and the far legs darker.

## Color

- Build every material from hue-shifted ramps. Do not darken toward black.
- Keep most colours muted and put one accent on about 5–10% of the pixels, at the focal point.
- **Friendly:** round, warm, light values, big bright eyes.
- **Hostile:** a darker base, desaturated or sickly hues, a saturated warning accent on the eyes, mouth, claws or weapon. Never rely on red versus green alone.
- **A set of assets** shares one `palette_kit`, light direction, outline treatment and scale.

## Common mistakes

1. Detail before silhouette.
2. No dominant shape.
3. Shapes or motion that contradict the role, such as a light floaty walk on a brute.
4. Details too small to read.
5. Limbs merging into the body.
6. Types told apart only by colour.
7. Pillow shading.
8. Too many colours, or ramps so close that they band.
9. Contrast in the wrong place.
10. Attacks with no telegraph.
11. Never checking at 1x, in grayscale and in motion.
