import unittest
from ONeSpineCRxLib.calculation_core_v1 import angle, segment, analyze

class TestCore(unittest.TestCase):
    def test_angle(self):
        self.assertAlmostEqual(angle((1,0),(0,1)),90)
    def test_synthetic_segment(self):
        p={"C2_IP":(0,2),"C2_IA":(10,2),"C3_SP":(0,0),"C3_SA":(10,0)}
        s=segment(p,"C2","C3",0.5)
        self.assertAlmostEqual(s["iva_deg"],0)
        self.assertEqual(len(s["height_profile"]),5)
        self.assertAlmostEqual(abs(s["height_mm"][2]),1)
    def test_missing_points(self):
        x=analyze({"lat":{"points":{}}})
        self.assertEqual(x["projections"]["lat"]["segments"]["C2_C3"]["status"],"unavailable")
if __name__=="__main__": unittest.main()
