import json
import math
import unittest
import xml.etree.ElementTree as ET
from ONeSpineCRxLib.engine import Projection, analyze, study, world_to_anatomical, manual_scale
from ONeSpineCRxLib.report import svg

def fixture(scale=1.,horizontal=True):
    points={}
    for j,v in enumerate(['C2','C3','C4','C5','C6','C7','T1']):
        y=100-j*15
        points.update({v+'_SP':(0.,y),v+'_SA':(20.,y),v+'_IP':(0.,y-10),v+'_IA':(20.,y-10)})
    return Projection(points,scale,horizontal,'test_reference','standing')

def move(p,level,dx):
    for c in ('SA','SP','IA','IP'):
        x,y=p.points[level+'_'+c]; p.points[level+'_'+c]=(x+dx,y)

class GeometryTests(unittest.TestCase):
    def test_parallel_geometry(self):
        r=analyze(fixture()); s=r['segments']['C4_C5']
        self.assertEqual(r['global']['CL_C2_C7_deg']['value'],0)
        self.assertEqual(s['mean_disc_height_mm']['value'],5)
        self.assertEqual(s['IVA_deg']['value'],0)
        self.assertEqual(s['translation_mm']['value'],0)
        self.assertEqual(r['global']['T1_slope_deg']['value'],0)
        self.assertEqual(r['global']['cSVA_C2_C7_mm']['value'],10)
    def test_signed_lordosis(self):
        p=fixture(); p.points['C2_IA']=(20,95)
        self.assertAlmostEqual(analyze(p)['global']['CL_C2_C7_deg']['value'],math.degrees(math.atan2(5,20)))
        p=fixture(); p.points['C7_IA']=(20,10)
        self.assertGreater(analyze(p)['global']['CL_C2_C7_deg']['value'],0)
    def test_no_scale_preserves_angles_ratios(self):
        r=analyze(fixture(None))
        self.assertIsNone(r['global']['cSVA_C2_C7_mm']['value'])
        self.assertIsNone(r['segments']['C4_C5']['mean_disc_height_mm']['value'])
        self.assertEqual(r['segments']['C4_C5']['disc_height_AP_ratio_pct']['value'],25)
        self.assertEqual(r['global']['CL_C2_C7_deg']['value'],0)
    def test_scale_applies_once(self):
        r=analyze(fixture(2))
        self.assertEqual(r['segments']['C4_C5']['mean_disc_height_mm']['value'],10)
        self.assertEqual(r['global']['cSVA_C2_C7_mm']['value'],20)
    def test_horizontal_gate(self):
        r=analyze(fixture(horizontal=False))
        for k in ('T1_slope_deg','C2_slope_deg','cSVA_C2_C7_mm','T1S_minus_CL_deg'): self.assertIsNone(r['global'][k]['value'])
        self.assertIsNotNone(r['global']['CL_C2_C7_deg']['value'])
    def test_missing_t1(self):
        p=fixture(); p.points={k:v for k,v in p.points.items() if not k.startswith('T1')}; r=analyze(p)
        self.assertIsNone(r['global']['T1_slope_deg']['value'])
        self.assertEqual(r['segments']['C7_T1']['status'],'unavailable')
        self.assertIsNotNone(r['global']['CL_C2_C7_deg']['value'])
    def test_ap_swapped(self):
        p=fixture(); p.points['C3_IA'],p.points['C3_IP']=p.points['C3_IP'],p.points['C3_IA']; r=analyze(p)
        self.assertEqual(r['segments']['C3_C4']['status'],'unavailable')
        self.assertIn('AP_ORDER',[q['code'] for q in r['qc']])
    def test_crossed_body(self):
        p=fixture(); p.points['C2_IA']=(20,110); r=analyze(p)
        self.assertIsNone(r['global']['CL_C2_C7_deg']['value'])
        self.assertIn('BODY_GEOMETRY',[q['code'] for q in r['qc']])
    def test_listhetic_height(self):
        p=fixture(); move(p,'C4',8); s=analyze(p)['segments']['C4_C5']
        self.assertEqual(s['translation_mm']['value'],8)
        self.assertEqual(s['translation_pct']['value'],40)
        self.assertAlmostEqual(s['overlap_fraction'],.6)
        self.assertEqual(s['mean_disc_height_mm']['value'],5)
        self.assertEqual(s['debug']['support_interval'],[8,20])
    def test_negative_translation(self):
        p=fixture(); move(p,'C4',-4)
        self.assertEqual(analyze(p)['segments']['C4_C5']['translation_mm']['value'],-4)
    def test_no_overlap(self):
        p=fixture(); move(p,'C4',25)
        self.assertEqual(analyze(p)['segments']['C4_C5']['reason'],'no_overlap')
    def test_crossed_disc(self):
        p=fixture(); p.points['C4_IA']=(20,35); p.points['C4_IP']=(0,35)
        self.assertEqual(analyze(p)['segments']['C4_C5']['reason'],'crossed_endplates')
    def test_rotation_invariance(self):
        p=fixture(horizontal=False); p.points['C4_IA']=(20,64); original=analyze(p)['segments']['C4_C5']; a=.2
        rotated={k:(x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)) for k,(x,y) in p.points.items()}
        s=analyze(Projection(rotated,1,False))['segments']['C4_C5']
        for k in ('mean_disc_height_mm','translation_mm','IVA_deg'): self.assertAlmostEqual(s[k]['value'],original[k]['value'])
    def test_oblique_plane_and_mirror(self):
        for sign in (-1,1):
            w={'ORIGIN':(5,6,7),'ANTERIOR_REF':(5,6+sign*10,7),'CRANIAL_REF':(5,6,17),'C2_SA':(5,6+sign*20,37)}
            self.assertEqual(world_to_anatomical(w)['C2_SA'],(20,30))
    def test_off_plane_and_degenerate(self):
        w={'ORIGIN':(0,0,0),'ANTERIOR_REF':(10,0,0),'CRANIAL_REF':(0,10,0),'C2_SA':(2,3,5)}
        with self.assertRaises(ValueError): world_to_anatomical(w)
        w['CRANIAL_REF']=(20,0,0)
        with self.assertRaises(ValueError): world_to_anatomical(w)
    def test_calibration_and_invalid_input(self):
        self.assertEqual(manual_scale((0,0,0),(3,4,0),25),5)
        with self.assertRaises(ValueError): manual_scale((0,0),(0,0),25)
        for scale in (-1,0,float('nan')):
            with self.assertRaises(ValueError): Projection({},scale)
        with self.assertRaises(ValueError): Projection({'a':(float('nan'),0)})
    def test_dynamic(self):
        f,e=fixture(),fixture(); move(e,'C4',3); r=study({'flex':f,'ext':e})
        d=r['dynamic']['segments']['C4_C5']['translation_mm']
        self.assertEqual(d['delta_ext_minus_flex'],3); self.assertEqual(d['excursion'],3)
        f.mm_per_unit=None
        self.assertIsNone(study({'flex':f,'ext':e})['dynamic']['segments']['C4_C5']['translation_mm']['excursion'])
        self.assertIsNone(study({'lat':e})['dynamic'])
    def test_roundtrip_svg(self):
        r=study({'lat':fixture()}); decoded=json.loads(json.dumps(r,allow_nan=False)); p=Projection(**decoded['inputs']['lat'])
        self.assertEqual(analyze(p)['global'],r['projections']['lat']['global'])
        self.assertEqual(ET.fromstring(svg(decoded,'lat')).tag,'{http://www.w3.org/2000/svg}svg')
        self.assertNotIn('PatientName',json.dumps(decoded))

if __name__=='__main__': unittest.main()
