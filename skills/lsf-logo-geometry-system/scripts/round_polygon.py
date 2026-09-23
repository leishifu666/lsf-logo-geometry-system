#!/usr/bin/env python3
"""Construct circular fillets on a simple polygon (Python standard library).
This is a component builder, not an image tracer or a global self-intersection solver.
"""
import argparse
import json
import math
from pathlib import Path

def add(a,b):return [a[0]+b[0],a[1]+b[1]]
def sub(a,b):return [a[0]-b[0],a[1]-b[1]]
def mul(a,s):return [a[0]*s,a[1]*s]
def dot(a,b):return a[0]*b[0]+a[1]*b[1]
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def length(a):return math.hypot(*a)
def unit(a):
    v=length(a)
    if v<=1e-12:raise ValueError('Duplicate adjacent vertices')
    return mul(a,1/v)
def num(x):return f'{x:.9f}'.rstrip('0').rstrip('.') or '0'
def point(p):return ' '.join(num(x) for x in p)

def fillet(prev,vertex,nxt,radius):
    if not math.isfinite(radius) or radius<0:raise ValueError('Radius must be finite and nonnegative')
    u,w=unit(sub(prev,vertex)),unit(sub(nxt,vertex))
    if radius==0:
        return {'entry':vertex[:],'exit':vertex[:],'center':None,'radius':0,'cutback':0,'sweep':None,'tangent_residual':0}
    theta=math.acos(max(-1,min(1,dot(u,w))))
    if theta<1e-9 or abs(math.pi-theta)<1e-9:raise ValueError('Positive fillet radius requires a genuine nondegenerate corner')
    cutback=radius/math.tan(theta/2)
    a=add(vertex,mul(u,cutback));b=add(vertex,mul(w,cutback))
    center=add(vertex,mul(unit(add(u,w)),radius/math.sin(theta/2)))
    return {'entry':a,'exit':b,'center':center,'radius':radius,'cutback':cutback,
            'sweep':int(cross(sub(vertex,prev),sub(nxt,vertex))>0),
            'tangent_residual':max(abs(dot(sub(a,center),u)),abs(dot(sub(b,center),w)))}

def rounded_polygon(vertices,radii):
    vertices=[[float(x),float(y)] for x,y in vertices]
    if len(vertices)<3 or len(radii)!=len(vertices):raise ValueError('Need at least 3 vertices and one radius per vertex')
    if not all(math.isfinite(x) for p in vertices for x in p):raise ValueError('Non-finite vertex coordinate')
    fs=[fillet(vertices[i-1],v,vertices[(i+1)%len(vertices)],float(radii[i])) for i,v in enumerate(vertices)]
    # Two individually valid radii may still consume the same shared edge.
    for i,f in enumerate(fs):
        edge=length(sub(vertices[(i+1)%len(vertices)],vertices[i]))
        if f['cutback']+fs[(i+1)%len(fs)]['cutback']>=edge-1e-10:
            raise ValueError(f'Fillets overlap or consume edge {i}->{(i+1)%len(fs)}; reduce radii')
    d='M '+point(fs[-1]['exit'])
    for f in fs:
        d+=' L '+point(f['entry'])
        if f['radius']>0:d+=f' A {num(f["radius"])} {num(f["radius"])} 0 0 {f["sweep"]} '+point(f['exit'])
    return d+' Z',fs

def build(spec):
    d,fs=rounded_polygon(spec['vertices'],spec['radii'])
    # Include complete construction circles in the component sheet's viewBox.
    pts=list(spec['vertices'])
    for f in fs:
        if f['center'] is not None:
            c=f['center'];r=f['radius'];pts.extend([[c[0]-r,c[1]-r],[c[0]+r,c[1]+r]])
    lo=[min(p[i] for p in pts) for i in [0,1]];hi=[max(p[i] for p in pts) for i in [0,1]]
    pad=max(hi[0]-lo[0],hi[1]-lo[1])*.08
    box=[lo[0]-pad,lo[1]-pad,hi[0]-lo[0]+2*pad,hi[1]-lo[1]+2*pad]
    def svg(body):return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="'+' '.join(map(num,box))+'">'+body+'</svg>'
    def mark(color):return f'<path d="{d}" fill="{color}"/>'
    guides=''
    for f in fs:
        if f['center'] is None:continue
        c=f['center'];r=f['radius'];guides+=f'<circle cx="{num(c[0])}" cy="{num(c[1])}" r="{num(r)}" fill="none" stroke="#227d85" stroke-width="{num(pad*.025)}"/>'
        for v in [f['entry'],f['exit']]:guides+=f'<path d="M{point(c)}L{point(v)}" fill="none" stroke="#227d85" stroke-width="{num(pad*.015)}"/>'
    geometry={'input':spec,'path':d,'fillets':fs,'viewbox':box,'checks':{'max_tangent_residual':max(f['tangent_residual'] for f in fs),'adjacent_cutbacks_checked':True,'global_arc_intersections_checked':False}}
    return {'master.svg':svg(mark('#000')),'inverse.svg':svg(mark('#fff')),'construction.svg':svg(mark('#d9e2df')+guides),'geometry.json':json.dumps(geometry,ensure_ascii=False,indent=2)}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('spec',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--overwrite',action='store_true');a=p.parse_args()
    outputs=build(json.loads(a.spec.read_text(encoding='utf-8')))
    if not a.overwrite and any((a.out/k).exists() for k in outputs):raise FileExistsError('Output exists; choose another directory or explicitly pass --overwrite')
    a.out.mkdir(parents=True,exist_ok=True)
    for name,body in outputs.items():(a.out/name).write_text(body,encoding='utf-8')
    print(a.out)
if __name__=='__main__':main()
