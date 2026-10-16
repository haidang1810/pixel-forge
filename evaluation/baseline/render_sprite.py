from pathlib import Path
import json
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
SIZE = (32, 32)
PALETTE = [
    ('transparent', '#00000000'),
    ('outline', '#193b36ff'),
    ('deep_moss', '#285547ff'),
    ('moss_shadow', '#3e7456ff'),
    ('moss', '#659b60ff'),
    ('young_leaf', '#92bd72ff'),
    ('sunlit_leaf', '#bdd88bff'),
    ('face_light', '#d2df9aff'),
    ('scarf_shadow', '#792f3aff'),
    ('scarf_red', '#bc4749ff'),
    ('scarf_light', '#ed7660ff'),
    ('amber_shadow', '#a9672aff'),
    ('amber', '#efb83eff'),
    ('eye_glint', '#fff0b4ff'),
]
COLORS = [tuple(bytes.fromhex(v[1:])) for _, v in PALETTE]
layers = []

def layer(name):
    im = Image.new('RGBA', SIZE, (0,0,0,0))
    layers.append((name,im))
    return ImageDraw.Draw(im)

def poly(d, coords, color):
    d.polygon(coords, fill=COLORS[color])

def line(d, coords, color, width=1):
    d.line(coords, fill=COLORS[color], width=width)

def box(d, coords, color):
    d.rectangle(coords, fill=COLORS[color])

def dot(d,x,y,color):
    d.point((x,y), fill=COLORS[color])

# Far leaf ear: a narrow leaf tilting out beyond the skull.
d = layer('01_far_leaf_ear')
poly(d,[(20,9),(20,6),(22,4),(26,2),(26,6),(25,9),(22,11)],1)
poly(d,[(21,8),(22,5),(25,3),(25,6),(24,8),(22,10)],3)
line(d,[(22,9),(23,6),(25,4)],5)
dot(d,24,7,4)

# Body, arms, and roots. The rear foot sits one pixel higher.
d = layer('02_body_and_feet')
poly(d,[(12,19),(22,19),(23,21),(25,23),(25,25),(23,26),(23,28),(20,29),(18,28),(17,29),(12,29),(11,28),(12,26),(9,25),(8,23),(9,21)],1)
poly(d,[(13,21),(21,21),(22,24),(21,27),(18,28),(14,27),(12,24)],3)
poly(d,[(14,22),(19,21),(21,24),(20,26),(16,27),(14,26)],4)
box(d,(15,23,18,25),5)
line(d,[(10,22),(9,23),(10,24),(12,24)],4)
line(d,[(23,22),(24,23),(24,24),(23,24)],3)
poly(d,[(13,27),(16,27),(16,28),(12,28)],3)
poly(d,[(20,27),(22,26),(22,27),(21,28),(20,28)],2)
dot(d,13,27,5)

# Main head: offset to the right of the torso to establish a turn.
d = layer('03_head')
poly(d,[(12,7),(17,6),(21,7),(23,8),(25,10),(25,12),(26,13),(26,16),(25,17),(24,19),(21,20),(15,20),(12,19),(10,17),(9,14),(9,11)],1)
poly(d,[(13,8),(17,7),(21,8),(23,9),(24,11),(24,13),(25,14),(25,16),(23,18),(21,19),(15,19),(12,18),(11,16),(10,14),(10,11)],3)
poly(d,[(13,9),(17,8),(20,8),(23,10),(24,12),(24,16),(22,18),(16,18),(13,17),(11,14),(11,11)],4)
poly(d,[(14,9),(18,8),(21,9),(22,10),(22,12),(20,13),(16,13),(13,12)],5)
poly(d,[(14,10),(17,9),(20,9),(21,10),(18,10),(17,11),(14,11)],6)
poly(d,[(15,14),(18,12),(22,12),(24,13),(24,16),(22,18),(17,18),(15,17)],5)
poly(d,[(17,15),(20,14),(22,15),(22,17),(19,18),(17,17)],6)
line(d,[(11,14),(12,16),(14,17)],2)
dot(d,14,9,7)

# Near ear is a broad leaf, with a clear stepped spine and side veins.
d = layer('04_near_leaf_ear')
poly(d,[(12,11),(9,10),(7,8),(6,5),(5,2),(9,3),(12,5),(14,8),(14,10)],1)
poly(d,[(11,10),(8,8),(7,5),(6,3),(9,4),(11,5),(13,8),(13,10)],4)
poly(d,[(8,4),(10,5),(12,7),(12,9),(10,8),(9,6)],5)
line(d,[(7,4),(8,6),(10,8),(12,10)],2)
line(d,[(8,6),(8,4)],3)
line(d,[(10,8),(11,6)],3)
dot(d,10,5,6)

# Eyes are unequal in width to suggest the far side of the face.
d = layer('05_face')
poly(d,[(15,12),(18,12),(19,13),(19,15),(18,16),(15,16),(14,15),(14,13)],1)
box(d,(15,13,18,15),12)
box(d,(17,13,18,14),11)
line(d,[(17,13),(17,15)],1)
dot(d,15,13,13)
dot(d,16,15,12)
poly(d,[(22,12),(23,12),(24,13),(24,15),(23,16),(22,15)],1)
box(d,(22,13,23,14),12)
line(d,[(23,13),(23,14)],1)
dot(d,22,13,13)
dot(d,22,15,11)
dot(d,21,16,2)
line(d,[(20,18),(21,18),(22,17)],2)
dot(d,14,16,5)
dot(d,13,15,5)

# The scarf crosses the neck; its hanging end is visibly fabric shaped.
d = layer('06_scarf')
poly(d,[(11,18),(13,18),(15,19),(20,19),(23,18),(24,19),(23,21),(20,22),(14,22),(12,21),(10,20)],8)
poly(d,[(12,19),(15,20),(20,20),(23,19),(22,20),(19,21),(14,21),(11,20)],9)
line(d,[(13,19),(15,20),(19,20)],10)
poly(d,[(12,21),(15,22),(14,24),(13,27),(10,26),(11,23)],8)
poly(d,[(12,22),(14,22),(13,24),(12,26),(11,25)],9)
line(d,[(12,22),(12,24)],10)
poly(d,[(11,20),(13,20),(14,21),(13,22),(11,22),(10,21)],9)
dot(d,11,20,10)
dot(d,13,21,8)

# Export actual editable raster layers, palette indices, and exact composition.
color_index = {c:i for i,c in enumerate(COLORS)}
result = Image.new('RGBA', SIZE, (0,0,0,0))
records = []
for name, im in layers:
    result = Image.alpha_composite(result, im)
    pixels = list(im.getdata())
    rows = [[color_index[pixels[y*32+x]] for x in range(32)] for y in range(32)]
    records.append({'name':name, 'visible':True, 'opacity':1, 'pixels':rows})
data = {
    'format':'indexed-pixel-layers-v1',
    'name':'Amberleaf forest spirit',
    'width':32, 'height':32, 'transparent_index':0,
    'layer_order':'bottom_to_top',
    'palette':[{'index':i,'name':n,'rgba':v} for i,(n,v) in enumerate(PALETTE)],
    'layers':records,
}
(OUT/'forest_spirit.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
result.save(OUT/'forest_spirit.png')
result.resize((512,512),Image.Resampling.NEAREST).save(OUT/'forest_spirit_preview.png')
# A review sheet exposes edges on both a light and a dark solid ground.
review = Image.new('RGBA',(1024,512))
preview = result.resize((512,512),Image.Resampling.NEAREST)
for x,bg in [(0,'#e9ead8'),(512,'#24313f')]:
    tile = Image.new('RGBA',(512,512),bg)
    tile.alpha_composite(preview)
    review.alpha_composite(tile,(x,0))
review.convert('RGB').save(OUT/'review_backgrounds.png')
assert result.size == (32,32)
assert set(result.getchannel('A').getdata()) == {0,255}
# Verify JSON reconstruction against the exported PNG.
restored = Image.new('RGBA',SIZE,(0,0,0,0))
for rec in data['layers']:
    lay = Image.new('RGBA',SIZE)
    lay.putdata([COLORS[v] for row in rec['pixels'] for v in row])
    restored = Image.alpha_composite(restored,lay)
assert restored.tobytes() == result.tobytes()
print(json.dumps({'dimensions':result.size,'palette_entries':len(PALETTE),'layers':len(layers),'opaque_pixels':sum(a>0 for a in result.getchannel('A').getdata()),'json_roundtrip':'pass','outputs':['forest_spirit.json','forest_spirit.png','forest_spirit_preview.png','review_backgrounds.png']}))
