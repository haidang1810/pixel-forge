"""Arrange actual JSON-rendered results for inspection; never modify sprite pixels."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "output/pixel-art-json-demo"
OUT.mkdir(parents=True, exist_ok=True)


def font(size, bold=False):
    path = Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default(size=size)


entries = [
    ("01", "JADE SWORD", "Steel / jade / gold", ROOT / "items/jade-sword.png"),
    ("02", "EMBER POTION", "Glass / liquid / cork", ROOT / "items/ember-potion.png"),
    ("03", "TREASURE CHEST", "Wood / brass / lock", ROOT / "items/treasure-chest.png"),
    ("04", "FOREST SPIRIT", "Leaves / amber eyes / scarf", ROOT / "with-skill/forest-spirit-v2.png"),
]
page = Image.new("RGB", (1200, 544), "#111822")
draw = ImageDraw.Draw(page)
draw.text((34, 25), "PIXEL ART / JSON", font=font(32, True), fill="#F3F1DF")
draw.text((36, 74), "Original 32 x 32 assets drawn with code. No image model. No reference artwork.", font=font(17), fill="#A8B6C5")
draw.line((36, 116, 1164, 116), fill="#334354")

for i, (number, title, subtitle, path) in enumerate(entries):
    x, y = 36 + i * 288, 138
    draw.rounded_rectangle((x, y, x + 264, y + 319), radius=10, fill="#1A2532", outline="#31404F")
    draw.text((x + 16, y + 12), number + "  /  32 x 32", font=font(13), fill="#7BCBB6")
    with Image.open(path) as native:
        native = native.convert("RGBA")
        # 6x integer enlargement preserves every original pixel exactly.
        sprite = native.resize((192, 192), Image.Resampling.NEAREST)
        page.paste(sprite, (x + 36, y + 42), sprite)
    draw.text((x + 16, y + 252), title, font=font(17, True), fill="#F3F1DF")
    draw.text((x + 16, y + 279), subtitle, font=font(13), fill="#A8B6C5")

draw.text((36, 486), "pixel-art-json  /  v1", font=font(14, True), fill="#7BCBB6")
draw.text((344, 486), "Editable JSON + transparent PNG. Enlarged 6x for inspection.", font=font(14), fill="#A8B6C5")
page.save(OUT / "preview.png")
print(OUT / "preview.png")
