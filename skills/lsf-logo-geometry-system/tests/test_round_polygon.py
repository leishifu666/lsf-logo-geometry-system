import importlib.util
import json
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('round_polygon',ROOT/'scripts/round_polygon.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)

class RoundedCornerTests(unittest.TestCase):
    def test_known_right_angle_tangent_geometry(self):
        f=r.fillet([0,10],[0,0],[10,0],2)
        for actual,expected in [(f['entry'],[0,2]),(f['exit'],[2,0]),(f['center'],[2,2])]:
            for x,y in zip(actual,expected):self.assertAlmostEqual(x,y)
        self.assertLess(f['tangent_residual'],1e-12)
    def test_reflex_corner_has_opposite_sweep(self):
        f=r.fillet([10,0],[0,0],[0,10],2)
        self.assertEqual(f['sweep'],0)
        self.assertAlmostEqual(r.length(r.sub(f['entry'],f['center'])),2)
        self.assertAlmostEqual(r.length(r.sub(f['exit'],f['center'])),2)
    def test_zero_radius_preserves_vertex_without_arc(self):
        f=r.fillet([0,10],[0,0],[10,0],0)
        self.assertIsNone(f['center']);self.assertEqual(f['entry'],[0,0]);self.assertEqual(f['exit'],[0,0])
    def test_two_fillets_consuming_one_edge_rejected(self):
        with self.assertRaises(ValueError):r.rounded_polygon([[0,0],[10,0],[10,10],[0,10]],[6,6,6,6])
    def test_degenerate_and_nonfinite_rejected(self):
        for args in [([0,0],[0,0],[10,0],2),([-1,0],[0,0],[1,0],2),([0,1],[0,0],[1,0],-1),([0,1],[0,0],[1,0],math.nan)]:
            with self.assertRaises(ValueError):r.fillet(*args)
    def test_clockwise_and_counterclockwise(self):
        v=[[0,0],[20,0],[20,20],[0,20]]
        _,a=r.rounded_polygon(v,[2]*4);_,b=r.rounded_polygon(v[::-1],[2]*4)
        self.assertTrue(all(f['sweep']==1 for f in a));self.assertTrue(all(f['sweep']==0 for f in b))
    def test_parameter_change_rebuilds_paths_and_guides(self):
        spec=json.loads((ROOT/'examples/rounded-corner.json').read_text(encoding='utf-8'));a=r.build(spec);spec['radii'][0]=3;b=r.build(spec)
        self.assertNotEqual(a['master.svg'],b['master.svg']);self.assertNotEqual(a['construction.svg'],b['construction.svg'])
        g=json.loads(b['geometry.json']);self.assertEqual(g['fillets'][0]['radius'],3)
        for key,value in b.items():
            if key.endswith('.svg'):ET.fromstring(value)
        self.assertIsNone(g['fillets'][4]['center'])

if __name__=='__main__':unittest.main()
