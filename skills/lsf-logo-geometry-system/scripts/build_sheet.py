#!/usr/bin/env python3
"""Build same-source logo SVGs and a construction sheet; Python standard library."""
import argparse
import html
import json
import math
import re
from pathlib import Path


def num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f'Expected finite number, got {v!r}')
    return f'{v:.8g}'


def xy(r, angle, cx=0, cy=0):
    a = math.radians(angle)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def point(p):
    return ' '.join(num(v) for v in p)


def element(tag, **attrs):
    return '<' + tag + ' ' + ' '.join(f'{k.replace("_", "-")}="{html.escape(str(v), quote=True)}"' for k, v in attrs.items()) + '/>'


def primitive(s):
    t = s['type']
    if t == 'circle':
        if s['r'] <= 0: raise ValueError('Circle radius must be positive')
        return element('circle', cx=num(s['cx']), cy=num(s['cy']), r=num(s['r']))
    if t == 'ellipse':
        if min(s['rx'], s['ry']) <= 0: raise ValueError('Ellipse radii must be positive')
        return element('ellipse', cx=num(s['cx']), cy=num(s['cy']), rx=num(s['rx']), ry=num(s['ry']))
    if t in ('rect', 'capsule'):
        if min(s['width'], s['height']) <= 0: raise ValueError('Rectangle dimensions must be positive')
        r = min(s['width'], s['height']) / 2 if t == 'capsule' else s.get('radius', 0)
        if not 0 <= r <= min(s['width'], s['height']) / 2: raise ValueError('Invalid corner radius')
        return element('rect', x=num(s['x']), y=num(s['y']), width=num(s['width']), height=num(s['height']), rx=num(r))
    if t == 'polygon':
        if len(s['points']) < 3: raise ValueError('Polygon needs 3 points')
        return element('polygon', points=' '.join(point(p) for p in s['points']))
    if t == 'path':
        if not re.fullmatch(r'[MmZzLlHhVvCcSsQqTtAa0-9eE.,+\s-]+', s['d']):
            raise ValueError('Only SVG path commands and numbers are accepted')
        return element('path', d=s['d'], fill_rule=s.get('fill_rule', 'nonzero'))
    if t == 'annular-sector':
        R, r, start, sweep = (s[k] for k in ('outer_radius', 'inner_radius', 'start_deg', 'sweep_deg'))
        if not (0 < r < R and 0 < sweep < 360):
            raise ValueError('Annular sector requires 0 < inner < outer and 0 < sweep < 360')
        cx, cy = s['cx'], s['cy']
        end = start + sweep
        a, b, c, d = (xy(rad, ang, cx, cy) for rad, ang in ((R, start), (R, end), (r, end), (r, start)))
        large = int(sweep > 180)
        path = f'M {point(a)} A {num(R)} {num(R)} 0 {large} 1 {point(b)} L {point(c)} A {num(r)} {num(r)} 0 {large} 0 {point(d)} Z'
        return element('path', d=path)
    raise ValueError(f'Unsupported primitive: {t}')


def wrapped(s, content):
    tr = s.get('rotate', [0, 0, 0])
    if len(tr) != 3: raise ValueError('rotate must be [degrees,cx,cy]')
    return f'<g transform="rotate({point(tr)})">{content}</g>'


def cross(cx, cy, length=.16):
    return element('path', d=f'M {num(cx-length)} {num(cy)} h {num(2*length)} M {num(cx)} {num(cy-length)} v {num(2*length)}')


def guides(s):
    t = s['type']
    out = ''
    if t in ('circle', 'ellipse', 'annular-sector'):
        cx, cy = s['cx'], s['cy']
        out += cross(cx, cy)
        if t == 'annular-sector':
            for radius in (s['inner_radius'], s['outer_radius']):
                out += element('circle', cx=num(cx), cy=num(cy), r=num(radius))
            for angle in (s['start_deg'], s['start_deg'] + s['sweep_deg']):
                out += element('path', d=f'M {point([cx,cy])} L {point(xy(s["outer_radius"]+1,angle,cx,cy))}')
        else:
            out += primitive(s)
    elif t == 'capsule':
        x, y, w, h = (s[k] for k in ('x', 'y', 'width', 'height'))
        r = min(w, h)/2
        centers = [(x+r, y+h/2), (x+w-r, y+h/2)] if w >= h else [(x+w/2, y+r), (x+w/2, y+h-r)]
        for cx, cy in centers:
            out += element('circle', cx=num(cx), cy=num(cy), r=num(r)) + cross(cx, cy)
        out += primitive(s)
    else:
        out += primitive(s)
    return wrapped(s, out)


def svg(viewbox, content, width=800, height=800):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{point(viewbox)}">{content}</svg>'


def label(x, y, text, size=15, fill='#555e65', weight=400):
    return f'<text x="{x}" y="{y}" font-family="Arial, Microsoft YaHei, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(str(text))}</text>'


def resolve(data, field):
    v = data
    for p in field.split('.'):
        v = v[int(p)] if isinstance(v, list) else v[p]
    num(v)
    return v


def expression(data, value):
    """A number, a source-field name, or a linear expression of one source field."""
    if isinstance(value, str):
        return resolve(data, value)
    if isinstance(value, dict):
        result = resolve(data, value['ref']) * value.get('factor', 1) + value.get('offset', 0)
    else:
        result = value
    num(result)
    return result


def proportion_sheet(data, defs, mark, measurements):
    """B-style positioning sheet. Geometry stays untouched; guides reference its data."""
    x, y, w, h = data['bounds']
    scale = min(440 / w, 440 / h)
    cx, cy = x + w / 2, y + h / 2
    sx = lambda v: 600 + (v - cx) * scale
    sy = lambda v: 520 + (v - cy) * scale
    point_value = lambda p: [expression(data, v) for v in p]
    def line(a, b, color='#b8c0b8', width=.8, dash=None):
        attrs = dict(x1=num(a[0]), y1=num(a[1]), x2=num(b[0]), y2=num(b[1]), stroke=color, stroke_width=width)
        if dash: attrs['stroke_dasharray'] = dash
        return element('line', **attrs)
    def place(body):
        return f'<g transform="translate(600,520) scale({num(scale)}) translate({num(-cx)},{num(-cy)})">{body}</g>'
    def guide_circle(center, radius):
        if radius <= 0: raise ValueError('Construction circle radius must be positive')
        a, b = sx(center[0]), sy(center[1])
        return element('circle', cx=num(a), cy=num(b), r=num(radius*scale), fill='none', stroke='#a4afa5', stroke_width=.8) + line([a-3,b],[a+3,b]) + line([a,b-3],[a,b+3])
    construction = data.get('construction', {})
    if construction.get('evidence_note'):
        note = construction['evidence_note']
    else:
        note = 'Guides use declared geometry. Free curves remain defined by the master SVG.'
    out = '<rect width="1200" height="1120" fill="#f5f6f4"/>'
    out += label(52, 44, 'LSF / PROPORTION + POSITION', 12)
    out += label(52, 88, data['title'], 29, '#333c35', 600)
    out += label(52, 117, data.get('subtitle', 'Same-source construction; master geometry unchanged'), 15)
    # The pattern is page-sized, independent of geometry units.
    out += '<defs><clipPath id="construction-field"><rect x="36" y="155" width="1128" height="710"/></clipPath></defs>'
    # Pattern applied in geometry coordinates, adjusted to a stable visual pitch.
    out += f'<defs><pattern id="geometry-hatch" width="{num(5/scale)}" height="{num(5/scale)}" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><rect width="{num(5/scale)}" height="{num(5/scale)}" fill="#dfe2dc"/><path d="M0 0V{num(5/scale)}" stroke="#aeb5ac" stroke-width="{num(.7/scale)}"/></pattern></defs>'
    guide_layer = ''
    for xx in [x, cx, x+w]:
        guide_layer += line([sx(xx),155],[sx(xx),865],dash='4 5')
    for yy in [y, cy, y+h]:
        guide_layer += line([36,sy(yy)],[1164,sy(yy)],dash='4 5')
    # Only real round primitives supply automatic construction circles.
    primitives = ''.join(guides(s) for s in data['shapes'] if s['type'] in ('circle','ellipse','capsule','annular-sector'))
    geometry_guides = place(f'<g fill="none" stroke="#a4afa5" stroke-width="{num(.8/scale)}">{primitives}</g>')
    for guide in construction.get('guides', []):
        if not guide.get('basis'): raise ValueError('A construction guide needs a basis describing its geometry relationship')
        if guide['type'] == 'line':
            a, b = point_value(guide['from']), point_value(guide['to'])
            a, b = [sx(a[0]),sy(a[1])], [sx(b[0]),sy(b[1])]
            dx, dy = b[0]-a[0], b[1]-a[1]; length = math.hypot(dx,dy)
            if not length: raise ValueError('Construction line endpoints must differ')
            if guide.get('extend', True):
                ux, uy = dx/length, dy/length
                a, b = [a[0]-2400*ux,a[1]-2400*uy], [b[0]+2400*ux,b[1]+2400*uy]
            guide_layer += line(a,b,dash='4 5')
        elif guide['type'] == 'circle':
            geometry_guides += guide_circle(point_value(guide['center']), expression(data,guide['radius']))
        else:
            raise ValueError('Construction guide type must be line or circle')
    out += '<g clip-path="url(#construction-field)">' + guide_layer + '</g>'
    out += place(defs + '<g id="construction-master">' + mark('url(#geometry-hatch)') + '</g>')
    out += '<g clip-path="url(#construction-field)">' + geometry_guides + '</g>'
    defaults = [
        {'from':[x,y+h], 'to':[x+w,y+h], 'offset':58/scale},
        {'from':[x+w,y], 'to':[x+w,y+h], 'offset':-64/scale},
    ]
    for dim in construction.get('dimensions', defaults):
        a, b = point_value(dim['from']), point_value(dim['to'])
        dx, dy = b[0]-a[0], b[1]-a[1]; length = math.hypot(dx,dy)
        if length <= 0: raise ValueError('Dimension endpoints must differ')
        nx, ny = -dy/length, dx/length
        offset = expression(data, dim.get('offset',0))
        aa, bb = [sx(a[0]),sy(a[1])], [sx(b[0]),sy(b[1])]
        da, db = [aa[0]+nx*offset*scale,aa[1]+ny*offset*scale], [bb[0]+nx*offset*scale,bb[1]+ny*offset*scale]
        out += line(aa,da) + line(bb,db) + line(da,db,'#7d897f',1.3)
        for pp in [da,db]:out += line([pp[0]-nx*4,pp[1]-ny*4],[pp[0]+nx*4,pp[1]+ny*4],'#7d897f',1)
        txt = f'{dim.get("prefix", "")}{length:.4g}x'
        tx, ty = dim.get('text_offset',[0,-12])
        mx, my = (da[0]+db[0])/2+tx, (da[1]+db[1])/2+ty
        tw = len(txt)*9+12
        out += element('rect',x=num(mx-tw/2),y=num(my-15),width=tw,height=21,fill='#f5f6f4')
        out += f'<text x="{num(mx)}" y="{num(my)}" text-anchor="middle" font-size="16" font-family="Arial, Microsoft YaHei, sans-serif" fill="#616e64">{html.escape(txt)}</text>'
    out += line([52,900],[1148,900],'#d5dcd3')
    out += label(52,938,construction.get('module_definition',f'x = {data["module"]["value"]:g} {data["module"]["unit"]} / declared design unit'),17)
    out += label(52,969,note,14)
    # Supplementary numbers remain secondary to the on-diagram dimensions.
    for i,m in enumerate(measurements[:8]):
        xx = 52 + (i%4)*281; yy = 1006+(i//4)*30
        out += label(xx,yy,f'{m["label"]}: {m["value"]:.5g}{m.get("unit","x")}',13)
    out += label(52,1090,data.get('status','Proposed construction'),12)
    return svg([0,0,1200,1120],out,1200,1120)


def build(data):
    box = data['bounds']
    if len(box) != 4 or min(box[2:]) <= 0: raise ValueError('bounds must be [x,y,width,height] with positive extent')
    for v in box: num(v)
    if not data['shapes']: raise ValueError('At least one shape is required')
    if data['module']['value'] <= 0: raise ValueError('Module value must be positive')
    ids = [s['id'] for s in data['shapes']]
    if len(set(ids)) != len(ids): raise ValueError('Duplicate shape IDs')
    if any(s.get('operation', 'add') not in ('add', 'subtract') for s in data['shapes']): raise ValueError('Operation must be add or subtract')
    for s in data['shapes']: primitive(s)
    # All additions are united, then all subtractions are removed. This is not an ordered CSG engine.
    add = ''.join(wrapped(s, primitive(s)) for s in data['shapes'] if s.get('operation', 'add') == 'add')
    sub = ''.join(wrapped(s, primitive(s)) for s in data['shapes'] if s.get('operation') == 'subtract')
    x, y, w, h = box
    def mark(color, opacity=1):
        return f'<g fill="{color}" opacity="{opacity}" mask="url(#cut)">{add}</g>'
    defs = f'<defs><mask id="cut" maskUnits="userSpaceOnUse" x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"><rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="white"/><g fill="black">{sub}</g></mask></defs>'
    master = svg(box, defs + mark('#111820'), 800, round(800*h/w))
    reverse = svg(box, defs + mark('#ffffff'), 800, round(800*h/w))
    guide = ''.join(guides(s) for s in data['shapes'])
    guide = f'<g fill="none" stroke="#87939d" stroke-width="0.025">{guide}</g>'
    cx, cy = x+w/2, y+h/2
    axes = f'<path d="M {num(cx-w*.7)} {num(cy)} H {num(cx+w*.7)} M {num(cx)} {num(cy-h*.7)} V {num(cy+h*.7)}" fill="none" stroke="#aab3ba" stroke-width=".022" stroke-dasharray=".14 .12"/>'
    measurements = []
    for m in data.get('measurements', []):
        val = resolve(data, m['ref']) * m.get('factor', 1) + m.get('offset', 0)
        measurements.append({**m, 'value': val})
    # Four panels share exactly the same geometry and numeric references.
    out = '<rect width="1200" height="960" fill="#f5f6f4"/>'
    out += label(56, 49, 'LSF / LOGO GEOMETRY SYSTEM', 12, '#657079', 600)
    out += label(56, 97, data['title'], 32, '#111820', 600)
    out += label(56, 125, data.get('subtitle', 'Reproducible geometric construction'), 14)
    out += '<path d="M56 150H1144 M600 178V865 M56 535H1144" stroke="#d9dfdf" fill="none"/>'
    scale = min(235/w, 235/h)
    def panel(px, py, content):
        return f'<g transform="translate({px},{py}) scale({scale}) translate({num(-cx)},{num(-cy)})">{defs}{content}</g>'
    out += label(56, 189, '01 / MASTER', 12, '#58656c', 600)
    out += panel(315, 357, mark('#111820'))
    out += label(650, 189, '02 / CONSTRUCTION', 12, '#58656c', 600)
    out += panel(892, 357, mark('#111820', .12) + axes + guide)
    out += label(56, 574, '03 / PRIMITIVES + MODULE', 12, '#58656c', 600)
    out += panel(315, 731, axes + guide)
    out += label(650, 574, '04 / DIMENSIONS', 12, '#58656c', 600)
    yy = 613
    for m in measurements:
        unit = m.get('unit', 'x')
        out += label(650, yy, m['label'], 15)
        out += label(978, yy, f'{m["value"]:.5g}{unit}', 17, '#111820', 600)
        yy += 31
    if yy > 842: raise ValueError('Sheet supports at most 8 measurement rows; use a separate spec for more')
    val = data['module']['value']
    out += label(56, 906, f'x = {val:g} {data["module"]["unit"]}  /  coordinates in x  /  +y downward', 13)
    out += label(650, 906, data.get('status', 'Proposed construction - see report'), 12)
    out += label(56, 935, 'Every construction line is derived from the master geometry.', 12, '#78828a')
    style = data.get('sheet_style', 'proportion')
    if style not in ('proportion','path-detail'):raise ValueError('sheet_style must be proportion or path-detail')
    sheet = proportion_sheet(data,defs,mark,measurements) if style == 'proportion' else svg([0,0,1200,960],out,1200,960)
    manifest = {'title': data['title'], 'bounds_in_x': box, 'bounds_status': 'declared; verify against rendered silhouette', 'module': data['module'], 'measurements': measurements, 'shapes': data['shapes'], 'sheet_style':style, 'construction':data.get('construction',{})}
    return {'master.svg': master, 'reverse.svg': reverse, 'construction.svg': sheet, 'geometry.json': json.dumps(manifest, ensure_ascii=False, indent=2)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('spec', type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--overwrite', action='store_true')
    a = p.parse_args()
    results = build(json.loads(a.spec.read_text(encoding='utf-8-sig')))
    if not a.overwrite and any((a.out/k).exists() for k in results):
        p.error('Output exists; choose a fresh directory or explicitly pass --overwrite')
    a.out.mkdir(parents=True, exist_ok=True)
    for name, content in results.items():
        (a.out/name).write_text(content, encoding='utf-8')
    print(json.dumps({'output': str(a.out), 'files': list(results)}, ensure_ascii=False))


if __name__ == '__main__': main()
