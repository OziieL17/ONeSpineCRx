"""Controller regression with small UI doubles; not a Slicer integration test."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from ONeSpineCRxLib.engine import LABELS

source=ast.parse(Path(__file__).resolve().parents[1].joinpath('ONeSpineCRx.py').read_text())
widget=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='ONeSpineCRxWidget')
errors=[]
namespace={'ScriptedLoadableModuleWidget':object,'LABELS':LABELS,'slicer':NS(util=NS(errorDisplay=errors.append))}
exec(compile(ast.Module(body=[widget],type_ignores=[]),'<controller>','exec'),namespace)
Widget=namespace['ONeSpineCRxWidget']

class Selector:
    def __init__(self): self.id=None
    def blockSignals(self,value): pass
    def setCurrentNodeID(self,value): self.id=value
class Node:
    def __init__(self,id): self.id=id; self.removed=0
    def GetID(self): return self.id
    def GetImageData(self): return NS(GetDimensions=lambda:(100,200,1))
    def RemoveAllControlPoints(self): self.removed+=1

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        errors.clear(); self.w=Widget(); w=self.w
        w.busy=False; w.active=NS(currentText='flex')
        w.assignedVolumeIDs={'lat':'lat-img','flex':None,'ext':'ext-img'}
        w.nodes={n:Node(n) for n in ('lat','flex','ext')}
        w.volumes={n:Selector() for n in w.nodes}
        w.settings={n:{'mm_per_unit':1,'horizontal_confirmed':True,'calibration_source':'test'} for n in w.nodes}
        w.calibrationLengths={};w.confirmedOrientations={};w.viewSettings={};w.skipped={n:set() for n in w.nodes}
        w.stopPlacement=lambda:None; w.switchProjection=lambda:None; w.schedule=lambda:None
    def test_duplicate_does_not_delete_points(self):
        self.w.volumeChanged('flex',Node('lat-img'))
        self.assertIsNone(self.w.assignedVolumeIDs['flex']); self.assertEqual(self.w.nodes['flex'].removed,0)
        self.assertEqual(len(errors),1)
    def test_other_projection_preserved(self):
        self.w.volumeChanged('flex',Node('flex-img'))
        self.assertEqual(self.w.nodes['flex'].removed,1); self.assertEqual(self.w.nodes['lat'].removed,0)
        self.assertEqual(self.w.settings['lat']['mm_per_unit'],1);self.assertIsNone(self.w.settings['flex']['mm_per_unit'])
    def test_repeated_same_assignment_preserves(self):
        self.w.assignedVolumeIDs['flex']='flex-img'
        self.w.volumeChanged('flex',Node('flex-img'))
        self.assertEqual(self.w.nodes['flex'].removed,0)
    def test_skipped_points_are_projection_specific(self):
        self.w.points=lambda name:{'ORIGIN':(0,0,0)}
        self.w.skipped['flex'].add('ANTERIOR_REF')
        self.assertEqual(self.w.missingLabels()[0],'CRANIAL_REF')
        self.w.active.currentText='lat';self.assertEqual(self.w.missingLabels()[0],'ANTERIOR_REF')
    def test_cancelled_auto_advance_does_not_place(self):
        self.w.autoMarking=False;self.w.startPlacement=lambda:self.fail('unexpected placement')
        self.w.continuePlacement()
        self.w.calibrating=False;self.w.expected='CAL_B';self.w.continueCalibration()
