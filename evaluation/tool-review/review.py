from pathlib import Path
import copy, importlib.util, io, json, os, subprocess, sys, tempfile, unittest
from PIL import Image

ROOT=Path(__file__).resolve().parent
TOOL=Path('D:/dev/projects/draw-2d-asset/skills/pixel-forge/scripts/pixel_art.py')
TMP=ROOT/'tmp'
TMP.mkdir(exist_ok=True)
tempfile.tempdir=str(TMP)
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('renderer_tests', TOOL.parent/'tests'/'test_pixel_art.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
buffer=io.StringIO()
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
run=unittest.TextTestRunner(stream=buffer,verbosity=2).run(suite)
(ROOT/'existing_tests.txt').write_text(buffer.getvalue(),encoding='utf-8')
print('existing tests:',run.testsRun,'failures:',len(run.failures),'errors:',len(run.errors))

base={'version':1,'size':[4,4],'palette':{'.':'#00000000','r':'#ff0000','b':'#0000ff'},'layers':[{'name':'base','rows':['rr..','rr..','....','....']}]}

def write(name,doc):
    p=ROOT/name
    p.write_text(json.dumps(doc),encoding='utf-8')
    return p

def cli(*args):
    cp=subprocess.run([sys.executable,'-B',str(TOOL),*map(str,args)],capture_output=True,text=True,cwd=ROOT)
    return {'returncode':cp.returncode,'stdout':cp.stdout.strip(),'stderr':cp.stderr.strip()}

results={}
source=write('source.json',base)
results['normal_export']=cli('render',source,'--out',ROOT/'normal','--scale','4','--grid')
# Malformed input should fail cleanly and produce no outputs.
for name,mutate in [
    ('boolean_size',lambda d:d.update(size=[True,4])),
    ('unknown_hidden_op',lambda d:d['layers'][0].update(visible=False,ops=[{'op':'polygon','points':[[0,0],[1,1],[2,0]],'color':'r','outline':'b'}])),
    ('partial_alpha',lambda d:d['palette'].update(r='#ff000080')),
]:
    doc=copy.deepcopy(base); mutate(doc)
    path=write(name+'.json',doc)
    results[name]=cli('render',path,'--out',ROOT/name)
    results[name]['outputs_present']=bool(list(ROOT.glob(name+'.*png')))

dup=ROOT/'duplicate.json'; dup.write_text('{"version":1,"version":1}',encoding='utf-8')
results['duplicate']=cli('validate',dup)
# Patch rejection must keep an existing destination unchanged.
badpatch=write('badpatch.json',{'edits':[{'layer':'base','op':'pixels','points':[[4,0]],'color':'r'}]})
destination=ROOT/'prior-revision.json'; destination.write_text('SENTINEL',encoding='utf-8')
results['invalid_patch']=cli('patch',source,badpatch,'--output',destination)
results['invalid_patch']['prior_revision_intact']=destination.read_text()=='SENTINEL'
# Non-finite numeric tokens are not valid JSON, but Python defaults accept them.
nan_source=ROOT/'nan.json'
nan_source.write_text(json.dumps(dict(base,meta={'value':float('nan')})),encoding='utf-8')
results['nonfinite_json']=cli('render',nan_source,'--out',ROOT/'nan-export')
results['nonfinite_json']['report_contains_NaN']=(ROOT/'nan-export.report.json').exists() and 'NaN' in (ROOT/'nan-export.report.json').read_text()
# Grid at the documented minimum scale.
results['grid_scale_one']=cli('render',source,'--out',ROOT/'scale-one','--scale','1','--grid')
with Image.open(ROOT/'scale-one.grid.png') as im:
    results['grid_scale_one']['canvas_colors']=sorted(set(im.crop((24,24,28,28)).getdata()))
# A prefix reused without --grid retains a grid showing the old revision.
write('blue.json',dict(base,palette={'.':'#00000000','r':'#0000ff','b':'#0000ff'}))
oldgrid=(ROOT/'normal.grid.png').read_bytes()
results['stale_grid']=cli('render',ROOT/'blue.json','--out',ROOT/'normal','--scale','4')
results['stale_grid']['grid_unchanged']=(ROOT/'normal.grid.png').read_bytes()==oldgrid
with Image.open(ROOT/'normal.png') as im:
    results['stale_grid']['new_native_pixel']=im.getpixel((0,0))
with Image.open(ROOT/'normal.grid.png') as im:
    results['stale_grid']['old_grid_pixel']=im.getpixel((26,26))
# Source-protection guard uses resolved paths, which do not detect hardlinks.
goodpatch=write('goodpatch.json',{'edits':[{'layer':'base','op':'pixels','points':[[3,3]],'color':'b'}]})
hard_source=write('hardlink-source.json',base)
hard_output=ROOT/'hardlink-revision.json'
os.link(hard_source,hard_output)
original=hard_source.read_bytes()
results['hardlink_patch']=cli('patch',hard_source,goodpatch,'--output',hard_output)
results['hardlink_patch']['original_changed']=hard_source.read_bytes()!=original
results['hardlink_patch']['source_and_output_samefile']=hard_source.samefile(hard_output)

(ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
for name,result in results.items():
    print(name, json.dumps(result))
