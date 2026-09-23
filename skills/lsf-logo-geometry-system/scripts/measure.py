#!/usr/bin/env python3
"""Measure registered monochrome rasters or fit a circle to selected contour points."""
import argparse
from collections import deque
import json
from pathlib import Path
import numpy as np
from PIL import Image


def mask(path, threshold, mode):
    im = Image.open(path).convert('RGBA')
    if mode == 'alpha': return np.asarray(im.getchannel('A')) >= threshold
    bg = Image.new('RGBA', im.size, 'white')
    bg.alpha_composite(im)
    return np.asarray(bg.convert('L')) < threshold


def boundary(a):
    p = np.pad(a, 1)
    interior = a & p[:-2,1:-1] & p[2:,1:-1] & p[1:-1,:-2] & p[1:-1,2:]
    return np.argwhere(a & ~interior).astype(float)


def topology(a):
    def count(v, diagonal):
        seen = np.zeros_like(v, dtype=bool)
        n, enclosed = 0, 0
        H,W = v.shape
        steps = [(-1,0),(1,0),(0,-1),(0,1)]
        if diagonal: steps += [(-1,-1),(-1,1),(1,-1),(1,1)]
        for yy,xx in np.argwhere(v):
            if seen[yy,xx]: continue
            n += 1
            touches = False
            q = deque([(int(yy),int(xx))]); seen[yy,xx] = True
            while q:
                y,x = q.popleft()
                touches |= y in (0,H-1) or x in (0,W-1)
                for dy,dx in steps:
                    ny,nx = y+dy,x+dx
                    if 0 <= ny < H and 0 <= nx < W and v[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx] = True; q.append((ny,nx))
            enclosed += not touches
        return n,enclosed
    return {'components': count(a,True)[0], 'holes': count(~a,False)[1]}


def distances(a,b):
    out = []
    for i in range(0,len(a),96):
        delta = a[i:i+96,None,:] - b[None,:,:]
        out.extend(np.sqrt((delta*delta).sum(axis=2).min(axis=1)).tolist())
    return np.asarray(out)


def compare(a):
    A,B = mask(a.original,a.threshold,a.mask), mask(a.rebuilt,a.threshold,a.mask)
    if A.shape != B.shape: raise ValueError('Inputs must have identical canvas size and registration; no implicit resizing')
    if not A.any() or not B.any(): raise ValueError('Both masks must contain foreground')
    pa,pb = boundary(A), boundary(B)
    original_counts = [len(pa),len(pb)]
    if a.max_points < 4: raise ValueError('--max-points must be at least 4')
    def sample(p): return p[np.linspace(0,len(p)-1,min(len(p),a.max_points),dtype=int)]
    pa,pb = sample(pa),sample(pb)
    d = np.concatenate([distances(pa,pb),distances(pb,pa)])
    yy,xx = np.where(A)
    D = max(int(xx.max()-xx.min()+1),int(yy.max()-yy.min()+1))
    ta,tb = topology(A),topology(B)
    result = {'method':'bidirectional boundary-pixel center distance; no alignment', 'mask':a.mask, 'threshold':a.threshold, 'canvas':[A.shape[1],A.shape[0]], 'D_pixels':D, 'boundary_points_original':original_counts, 'boundary_points_used':[len(pa),len(pb)], 'sampled': any(n>a.max_points for n in original_counts), 'iou':float((A&B).sum()/(A|B).sum()), 'mean_px':float(d.mean()), 'p95_px':float(np.percentile(d,95)), 'max_px':float(d.max()), 'original_topology':ta, 'rebuilt_topology':tb, 'topology_equal':ta==tb}
    for k in ('mean','p95','max'): result[k+'_pct_D'] = result[k+'_px']/D*100
    checks = {'topology_equal':ta==tb}
    if a.max_mean_pct is not None: checks['mean_within_limit'] = result['mean_pct_D'] <= a.max_mean_pct
    if a.max_p95_pct is not None: checks['p95_within_limit'] = result['p95_pct_D'] <= a.max_p95_pct
    result['checks'] = checks
    result['passed_requested_checks'] = all(checks.values())
    if a.diff:
        rgb = np.full((*A.shape,3),255,dtype=np.uint8)
        rgb[A&B] = [70,76,80]; rgb[A&~B] = [224,78,57]; rgb[B&~A] = [30,133,204]
        a.diff.parent.mkdir(parents=True,exist_ok=True)
        Image.fromarray(rgb).save(a.diff)
        result['diff_legend'] = {'dark':'intersection','red':'original only','blue':'rebuilt only'}
    return result


def fit_circle(a):
    points = np.loadtxt(a.points, delimiter=',', ndmin=2)
    if points.shape[1] != 2 or len(points)<3 or not np.isfinite(points).all(): raise ValueError('CSV must contain at least 3 finite x,y rows without a header')
    origin = points.mean(axis=0)
    p = points-origin
    mat = np.column_stack([2*p[:,0],2*p[:,1],np.ones(len(p))])
    sol,res,rank,sing = np.linalg.lstsq(mat,(p*p).sum(axis=1),rcond=None)
    if rank<3: raise ValueError('Degenerate/collinear points do not determine a circle')
    center = origin+sol[:2]
    r = np.sqrt(sol[2]+np.dot(sol[:2],sol[:2]))
    residual = np.linalg.norm(points-center,axis=1)-r
    angles = np.sort(np.mod(np.arctan2(points[:,1]-center[1],points[:,0]-center[0]),2*np.pi))
    span = 360-np.degrees(np.diff(np.r_[angles, angles[0]+2*np.pi]).max())
    return {'method':'algebraic least squares; circle is a hypothesis','center':center.tolist(),'radius':float(r),'points':len(p),'covered_arc_deg':float(span),'mean_abs_radial_error':float(np.abs(residual).mean()),'max_abs_radial_error':float(np.abs(residual).max()),'warning':'Short arc: unstable radius; compare alternative models' if span<60 else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode',required=True)
    c = sub.add_parser('compare',help='Compare same-size registered monochrome PNGs')
    c.add_argument('original',type=Path); c.add_argument('rebuilt',type=Path)
    c.add_argument('--mask',choices=['luminance','alpha'],default='luminance')
    c.add_argument('--threshold',type=int,default=128)
    c.add_argument('--max-points',type=int,default=6000)
    c.add_argument('--max-mean-pct',type=float); c.add_argument('--max-p95-pct',type=float)
    c.add_argument('--diff',type=Path); c.add_argument('--out',type=Path)
    f = sub.add_parser('fit-circle',help='Fit selected contour points from headerless x,y CSV')
    f.add_argument('points',type=Path); f.add_argument('--out',type=Path)
    a = p.parse_args()
    if a.mode=='compare' and not 1<=a.threshold<=254: p.error('threshold must be 1..254')
    result = compare(a) if a.mode=='compare' else fit_circle(a)
    value = json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(value,encoding='utf-8')
    print(value)
    if result.get('passed_requested_checks') is False: raise SystemExit(2)


if __name__=='__main__': main()
