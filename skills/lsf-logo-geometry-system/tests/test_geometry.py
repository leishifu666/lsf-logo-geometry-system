"""Behavioral regression tests. Run with: python -m unittest discover -s tests -v"""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    s = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m
b, m = module('build_sheet'), module('measure')

class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
    def save(self,name,arr):
        p=self.dir/name
        Image.fromarray(np.where(arr,0,255).astype('uint8')).save(p)
        return p
    def compare(self,a,c):
        return m.compare(argparse.Namespace(original=a,rebuilt=c,threshold=128,mask='luminance',max_points=6000,max_mean_pct=.5,max_p95_pct=1,diff=None))
    def test_identity(self):
        a=np.zeros((40,40),bool);a[5:35,5:35]=True
        p=self.save('a.png',a);r=self.compare(p,p)
        self.assertEqual(r['iou'],1);self.assertEqual(r['max_px'],0)
    def test_shift_detected_without_auto_registration(self):
        a=np.zeros((80,80),bool);a[20:60,20:60]=True
        c=np.zeros_like(a);c[20:60,25:65]=True
        r=self.compare(self.save('a.png',a),self.save('b.png',c))
        self.assertEqual(r['max_px'],5);self.assertFalse(r['passed_requested_checks'])
    def test_hole_loss_detected(self):
        a=np.zeros((40,40),bool);a[5:35,5:35]=True;a[15:25,15:25]=False
        c=a.copy();c[15:25,15:25]=True
        r=self.compare(self.save('a.png',a),self.save('b.png',c))
        self.assertEqual(r['original_topology']['holes'],1)
        self.assertEqual(r['rebuilt_topology']['holes'],0)
        self.assertFalse(r['topology_equal'])
    def test_canvas_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.compare(self.save('a.png',np.ones((20,20),bool)),self.save('b.png',np.ones((21,20),bool)))
    def test_white_mark_alpha_mode(self):
        a=np.zeros((20,20,4),dtype='uint8');a[:,:,:3]=255;a[4:16,4:16,3]=255
        p=self.dir/'alpha.png';Image.fromarray(a).save(p)
        self.assertEqual(m.mask(p,128,'alpha').sum(),144)
        self.assertEqual(m.mask(p,128,'luminance').sum(),0)
    def test_circle_fit(self):
        angles=np.linspace(0,2*np.pi,90,endpoint=False)
        p=self.dir/'arc.csv';np.savetxt(p,np.c_[3+7*np.cos(angles),-2+7*np.sin(angles)],delimiter=',')
        r=m.fit_circle(argparse.Namespace(points=p))
        self.assertTrue(np.allclose(r['center'],[3,-2]));self.assertAlmostEqual(r['radius'],7)
    def test_collinear_circle_rejected(self):
        p=self.dir/'line.csv';np.savetxt(p,[[0,0],[1,1],[2,2]],delimiter=',')
        with self.assertRaises(ValueError):m.fit_circle(argparse.Namespace(points=p))
    def test_numeric_source_updates_diagram_and_dimensions(self):
        d=json.loads((ROOT/'examples/tidebank.json').read_text())
        d['shapes'][0]['outer_radius']=5.8
        result=b.build(d)
        self.assertIn('5.8',result['master.svg'])
        self.assertIn('5.8x',result['construction.svg'])
        self.assertEqual(json.loads(result['geometry.json'])['measurements'][0]['value'],5.8)
        for k,v in result.items():
            if k.endswith('.svg'):ET.fromstring(v)
    def test_subtraction_is_mask_and_custom_curve_survives(self):
        d=json.loads((ROOT/'examples/tidebank.json').read_text())
        d['shapes']=[{'id':'a','type':'circle','cx':0,'cy':0,'r':5},{'id':'b','type':'circle','cx':0,'cy':0,'r':2,'operation':'subtract'}]
        d['measurements']=[]
        result=b.build(d)['master.svg']
        self.assertIn('<mask ',result);self.assertIn('fill="black"',result)
        path={'id':'organic','type':'path','d':'M0 0 C1 0 2 4 3 1 L0 0 Z'}
        self.assertIn(path['d'],b.primitive(path))
    def test_invalid_sector_rejected(self):
        d=json.loads((ROOT/'examples/tidebank.json').read_text());d['shapes'][0]['inner_radius']=7
        with self.assertRaises(ValueError):b.build(d)

if __name__=='__main__':unittest.main()
