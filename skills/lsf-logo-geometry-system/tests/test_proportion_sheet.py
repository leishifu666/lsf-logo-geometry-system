import copy
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sheet',ROOT/'scripts/build_sheet.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
NS={'s':'http://www.w3.org/2000/svg'}

class ProportionTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'examples/proportion-guides.json').read_text(encoding='utf-8'))
    def test_default_switch_does_not_change_master_or_inverse(self):
        default=b.build(self.data)
        self.data['sheet_style']='path-detail';detail=b.build(self.data)
        self.assertEqual(default['master.svg'],detail['master.svg'])
        self.assertEqual(default['reverse.svg'],detail['reverse.svg'])
        self.assertNotEqual(default['construction.svg'],detail['construction.svg'])
        root=ET.fromstring(default['construction.svg'])
        self.assertIsNotNone(root.find('.//s:g[@id="construction-master"]',NS))
    def test_parameter_changes_master_dimension_and_guide_coordinate(self):
        first=b.build(self.data)
        self.data['shapes'][0]['width']=9
        second=b.build(self.data)
        self.assertNotEqual(first['master.svg'],second['master.svg'])
        root=ET.fromstring(second['construction.svg'])
        self.assertIn('9x',[n.text for n in root.findall('.//s:text',NS)])
        # Bounds retain scale 55: right cap center now x=8 -> page x=820.
        self.assertTrue(any(n.get('x1')=='820' and n.get('x2')=='820' for n in root.findall('.//s:line',NS)))
    def test_dimension_uses_euclidean_not_horizontal_length(self):
        self.data['construction']['dimensions']=[{'from':[0,0],'to':[3,4]}]
        root=ET.fromstring(b.build(self.data)['construction.svg'])
        self.assertIn('5x',[n.text for n in root.findall('.//s:text',NS)])
    def test_free_curve_gets_no_fake_circle(self):
        self.data['shapes']=[{'id':'free','type':'path','d':'M0 0 C2 0 4 3 8 2 L0 0Z'}]
        self.data['measurements']=[];self.data['construction']={}
        root=ET.fromstring(b.build(self.data)['construction.svg'])
        self.assertEqual(root.findall('.//s:circle',NS),[])
    def test_guide_without_basis_is_rejected(self):
        del self.data['construction']['guides'][0]['basis']
        with self.assertRaises(ValueError):b.build(self.data)
    def test_degenerate_dimension_is_rejected(self):
        self.data['construction']['dimensions']=[{'from':[1,1],'to':[1,1]}]
        with self.assertRaises(ValueError):b.build(self.data)
    def test_unknown_style_rejected(self):
        self.data['sheet_style']='imaginary'
        with self.assertRaises(ValueError):b.build(self.data)

if __name__=='__main__':unittest.main()
