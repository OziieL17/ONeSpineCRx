import unittest
from ONeSpineCRxLib.view import image_plane
from ONeSpineCRxLib.engine import dot
IDENTITY=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
class ViewTests(unittest.TestCase):
    def test_raster_axes_and_center(self):
        b=image_plane(IDENTITY,(101,201,1))
        self.assertEqual(b['x'],(1,0,0)); self.assertEqual(b['y'],(0,1,0)); self.assertEqual(b['center'],(50,100,0))
    def test_reverse_metadata(self):
        m=[[1,0,0,0],[0,-1,0,200],[0,0,1,0],[0,0,0,1]]
        self.assertEqual(image_plane(m,(101,201,1))['y'],(0,-1,0))
        self.assertEqual(image_plane(m,(101,201,1),flip_vertical=True)['y'],(0,1,0))
    def test_180_turn_preserves_center(self):
        b=image_plane(IDENTITY,(101,201,1),quarter_turns=2)
        self.assertEqual(b['x'],(-1,0,0)); self.assertEqual(b['y'],(0,-1,0)); self.assertEqual(b['center'],(50,100,0))
    def test_all_corrections_orthonormal(self):
        for turn in range(4):
            for h in (True,False):
                for v in (True,False):
                    b=image_plane(IDENTITY,(101,201,1),turn,h,v)
                    for key in ('x','y','normal'): self.assertAlmostEqual(dot(b[key],b[key]),1)
                    self.assertAlmostEqual(dot(b['x'],b['y']),0)
    def test_other_singleton_axes(self):
        b=image_plane(IDENTITY,(1,101,201)); self.assertEqual(b['x'],(0,1,0)); self.assertEqual(b['y'],(0,0,1))
    def test_3d_and_degenerate_rejected(self):
        for dims in ((10,10,10),(1,1,10),(1,1,1)):
            with self.assertRaises(ValueError): image_plane(IDENTITY,dims)
    def test_oblique_plane(self):
        m=[[2,0,0,10],[0,0,-1,20],[0,3,0,30],[0,0,0,1]]
        b=image_plane(m,(11,21,1)); self.assertEqual(b['center'],(20,20,60)); self.assertEqual(b['normal'],(0,-1,0))
