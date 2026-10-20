# Research notes: shape language and character design for small sprites

Collected by a research subagent on 2026-10-20 and summarized in our own words. Points marked [craft] are standard practice rather than cited.

## Shapes

- **Circle / oval:** friendly, soft, safe, young, cute.
- **Square / rectangle:** stable, strong, heavy, stubborn. Use it for brutes, guardians and obstacles.
- **Triangle / spike:** dangerous, dynamic, sly, fast. It is directional and implies motion.
- **Irregular / broken / asymmetric:** unease. Use it for undead and corrupted creatures.
- **Clean geometry:** manufactured. Use it for golems and robots.
- **Flowing curves with controlled spikes:** elegant power. Use it for mages, fae and elegant bosses.

**Mixing.** Use one dominant shape (about 60–70% of the mass), one secondary shape and at most one accent. Contradict deliberately, for example a round body with triangle eyes and claws for something cute but dangerous. Props either echo the dominant shape or contradict it on purpose. A family shares one shape vocabulary, and rival factions contrast with each other.

## Silhouette and readability

- Design the silhouette first (as a solid shape), then large color regions, then the details that survive at 1x.
- **Read order** (TF2): friend or foe (colour), then role (silhouette, proportions, weapon, headgear), then what it holds (contrast at chest or weapon level).
- **Head, shoulders, headgear and weapon** separate types the most. Back attachments help too.
- **Family members** differ in at least one large-mass trait: height/width ratio, orientation, number of legs, an appendage or a weapon outline. A recolor alone is not a new type.
- **Asymmetry** gives direction and personality; negative space between limbs and body prevents blobs.
- **Line of action:** a forward diagonal reads aggressive or fast, a vertical proud or stable, a drooping curve weak or undead.
- **Tests:** a solid-black silhouette, grayscale, squinting, a horizontal flip, 1x on the real background, and in motion.

## Role / trait table

| Role | Shapes | Proportions | Posture | Color | Motion |
|---|---|---|---|---|---|
| Hero | inverted triangle torso on a stable base, mostly rounded | mid-large head, clear hands and weapon | upright, open chest, slight lean forward | saturated distinctive accent, highest contrast on face and weapon, warm bias | confident, medium-fast, clear anticipation, snappy recovery |
| Villain | triangles, spikes, long points | small head on a tall body; or long thin limbs, or a huge upper mass | looming, or predatory forward lean, chin down | dark, desaturated, one toxic accent, cool shadows | controlled, sudden bursts, long telegraphs |
| Tank / brute | squares, wide block, low centre | small head, huge torso, thick short limbs, big fists | wide stance, hunched shoulders, arms out | muted earthy or metal, strong dark mass | heavy and slow, more sink, long wind-up, big impact |
| Scout / rogue | triangles, slim diagonals, pointed hood and daggers | thin long limbs, compact frame | crouched, leaning forward | dark base, one small sharp accent | light and quick, little anticipation, darting, idle fidgets |
| Mage | tall vertical triangle plus circles (orb), flowing curves | small body under a big robe, a long staff | upright or slightly hunched, hands forward when casting | cool arcane hues, glowing focus as the brightest pixel | floaty, minimal leg motion, visible charge-up |
| Healer / support | circles, soft ovals | rounded body, larger head and eyes | upright, open, calm | light, warm pastel, white/gold/green accents | gentle, smooth eases, soft bounce |
| Cute critter | ball, nubs for limbs | head 1:1 to 1:2 with the body, big low eyes | squat, bottom-heavy | bright, saturated, high-contrast eyes | bouncy squash and stretch, fast idle bob |
| Basic hostile mob | a simple shape plus one hostile accent | small and simple | leaning toward the player | muted base, warm hostile accent, shared across the family | simple cycles, 2–3 frame telegraphs |
| Elite / boss | family shapes plus sharp accents (crown, horns, plates, a back piece) | larger, one exaggerated part | dominant, wide, looming | recolored base plus trim or glow; a signature hue for a boss | bigger, slower, long readable telegraphs |
| Undead | broken, jagged, asymmetric | gaunt, uneven limbs, big skull or hollow eyes | hunched with arms forward, or stiff vertical | desaturated sickly greens, greys, bone, a glowing eye accent | jerky, uneven timing, held frames then snaps |
| Beast | horizontal mass; triangle head and claws for predators, rounder for prey | front-heavy, tail as counterweight | low horizontal spine, head forward | natural hues, markings and a high-contrast eye | predators stalk then explode, prey is skittish |

## Color tied to character

- Value comes first: the sprite must read in grayscale. Put the highest contrast on the face, eyes and weapon. Keep the feet darker and quieter (TF2's dark-feet-to-light-chest gradient).
- Shadows shift cool, never toward black, with saturation rising near the terminator. Highlights shift warm.
- Mostly muted, with one accent on about 5–10% of the pixels at the focal point [craft].
- **Friendly:** round, warm, light values, low internal contrast, big bright eyes.
- **Hostile:** darker base, desaturated or sickly hues, a saturated warning accent on eyes, mouth, claws or weapon. Do not rely on red versus green alone.
- **Mob families:** share the base palette and shapes per tier. Elites change their accent and trim plus the head, shoulders or a back attachment. A tier change should add a silhouette change, not only a recolor.

## Common small-sprite mistakes

1. Detail before the silhouette.
2. No dominant shape, or conflicting shapes.
3. Shapes or motion that do not match the role.
4. Sub-readable details.
5. Limbs merging into the body.
6. Types told apart only by colour, or every mob coloured differently.
7. Pillow shading, or an inconsistent light.
8. Too many colours, or ramps so close they band.
9. Pure black outlines everywhere.
10. Jagged curves.
11. Focal contrast in the wrong place.
12. Mixed scale or detail density in a set.
13. Attacks with no telegraph.
14. Static symmetrical poses.
15. Never testing at 1x, in grayscale or in motion.

## Sources read

- [Mitchell, Francke, Eng (Valve), Illustrative Rendering in Team Fortress 2](https://www.cs.princeton.edu/courses/archive/fall07/cos597B/papers/mitchell-team-fortress.pdf)
- [Jason Mitchell (Valve), Stylization with a Purpose, GDC 2008](https://cdn.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf)
- [Fatshark, Darktide 101: Enemy Character Art](https://devtrackers.gg/darktide/p/67a2496a-darktide-101-enemy-character-art-dev-blog)
- [Mike Stout, Enemy Attacks and Telegraphing](https://gamedeveloper.com/design/enemy-attacks-and-telegraphing)
- [Derek Yu, Pixel Art Tutorial](https://www.derekyu.com/makegames/pixelart.html)
- [RocketBrush, Shape Language in Game Character Design](https://rocketbrush.com/blog/shape-language-in-game-character-design-how-to-make-characters-readable-and-consistent)
- [CG Wire, Character Shape Language](https://blog.cg-wire.com/character-shape-language/)
- [Wayline, Pixel Art for Games, Lesson 5](https://www.wayline.io/learn/pixel-art/4)
- [Sydney Padua, A Matter of Proportion](https://sydneypadua.com/2dgoggles/a-matter-of-proportion/)
- [Blizzard, Overwatch 2: Evolving the Art](https://news.blizzard.com/en-us/article/23189038/2)
