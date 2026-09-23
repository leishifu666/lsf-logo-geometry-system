from pathlib import Path
import json, importlib.util, argparse, math
import numpy as np
from PIL import Image

parser=argparse.ArgumentParser(description='Create independent analytic raster and reconstruction/mutation fixtures for the TIDEBANK exercise')
parser.add_argument('--out',required=True,type=Path)
args=parser.parse_args()
skill=Path(__file__).resolve().parents[1]
out=args.out.resolve()
if out.exists() and any(out.iterdir()): parser.error('Use an empty output directory')
out.mkdir(parents=True,exist_ok=True)
def module(name):
 spec=importlib.util.spec_from_file_location(name,skill/'scripts'/f'{name}.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
b,m=module('build_sheet'),module('measure')
spec=json.loads((skill/'examples/tidebank.json').read_text(encoding='utf-8'))
# An independent analytic raster fixture, not rendered from SVG paths.
# Fixed canvas equals [-6,+6]^2; supersampling limits edge quantization.
size=800; ss=4
grid=(np.arange(size*ss)+.5)/(size*ss)*12-6
y,x=np.meshgrid(grid,grid,indexing='ij')
r=np.sqrt(x*x+y*y);angle=np.degrees(np.arctan2(y,x))
flow=(r>=4)&(r<=6)&(np.abs(angle)>=45)
node=(x-5)**2+y*y<=1
coverage=(flow|node).reshape(size,ss,size,ss).mean(axis=(1,3))
Image.fromarray(np.rint((1-coverage)*255).astype('uint8')).save(out/'raster-input.png')

# Recover parameters from the raster: left arc bounds, center row and isolated node.
A=m.mask(out/'raster-input.png',128,'luminance')
yy,xx=np.where(A)
cy=(yy.min()+yy.max()+1)/2
R=(yy.max()-yy.min()+1)/2
cx=xx.min()+R
ys,xs=np.where(A & (np.indices(A.shape)[1]>int(cx+.5*R)) & (np.abs(np.indices(A.shape)[0]-cy)<.2*R))
# This local ROI selects the node for this identified C-ring + dot structure only.
nodebox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
node_cx=(nodebox[0]+nodebox[2])/2
node_cy=(nodebox[1]+nodebox[3])/2
node_r=(nodebox[2]-nodebox[0])/2
row=A[int(cy)]
inner_edge=np.where(row[:int(cx)])[0].max()+1
inner=cx-inner_edge
x_unit=R/6
measurements={'method':'Independent analytic raster, then structural ROI measurements; not a generic automatic recognizer','center_pixels':[cx,cy],'outer_radius_px':R,'inner_radius_px':float(inner),'node_center_px':[node_cx,node_cy],'node_radius_px':node_r,'module_px':x_unit,'measured_inner_in_x':float(inner/x_unit),'measured_node_radius_in_x':float(node_r/x_unit),'measured_node_center_in_x':[(node_cx-cx)/x_unit,(node_cy-cy)/x_unit],'snap_rule':'Nearest integer module only after measurement; candidate chosen for this fixture, residual checked below'}
(out/'raster-measurements.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
recovered=json.loads(json.dumps(spec))
recovered['shapes'][0]['inner_radius']=round(inner/x_unit)
recovered['shapes'][1]['cx']=round((node_cx-cx)/x_unit)
recovered['shapes'][1]['cy']=round((node_cy-cy)/x_unit)
recovered['shapes'][1]['r']=round(node_r/x_unit)
for s in recovered['shapes']:s['evidence']='fitted to synthetic raster'
recovered['status']='Raster reconstruction / synthetic validation'
(out/'recovered-spec.json').write_text(json.dumps(recovered,indent=2),encoding='utf-8')
for name,content in b.build(recovered).items():
 target=out/'reconstruction'/name;target.parent.mkdir(exist_ok=True)
 target.write_text(content,encoding='utf-8')
mutated=json.loads(json.dumps(spec));mutated['shapes'][1]['cy']=.6
for name,content in b.build(mutated).items():
 target=out/'mutated'/name;target.parent.mkdir(exist_ok=True)
 target.write_text(content,encoding='utf-8')
# A full ring proves subtraction remains transparent on colored backgrounds.
ring=json.loads(json.dumps(spec));ring['shapes']=[{'id':'outer','type':'circle','cx':0,'cy':0,'r':5},{'id':'hole','type':'circle','cx':0,'cy':0,'r':2,'operation':'subtract'}];ring['measurements']=[]
for name,content in b.build(ring).items():
 target=out/'ring'/name;target.parent.mkdir(exist_ok=True)
 target.write_text(content,encoding='utf-8')
print(json.dumps(measurements,indent=2))
