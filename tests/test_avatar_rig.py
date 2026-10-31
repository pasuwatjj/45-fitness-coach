"""Catch malformed authored weights before they reach WebGL skinning."""
import json,math,unittest
from pathlib import Path
class AvatarRigTests(unittest.TestCase):
 def test_bind_weights_match_body_and_clothes(self):
  root=Path(__file__).resolve().parents[1]/'static/models/quaternius'
  for gender in ['male','female']:
   rig=json.loads((root/f'{gender}-rig.json').read_text());body=json.loads((root/f'{gender}.json').read_text());count=9+len(rig['fingers'])
   for mesh in body:
    for geometry,skin in [(mesh,rig['meshes'][mesh['name']]['skin'])]+[(g,rig['meshes'][mesh['name']]['clothing'][k]) for k,g in mesh['clothing'].items()]:
     self.assertEqual(len(skin['index']),len(geometry['position'])//3*4)
     self.assertEqual(len(skin['weight']),len(skin['index']))
     self.assertTrue(all(isinstance(i,int) and 0<=i<count for i in skin['index']))
     self.assertTrue(all(math.isfinite(w) and 0<=w<=1 for w in skin['weight']))
     for i in range(0,len(skin['weight']),4):self.assertAlmostEqual(sum(skin['weight'][i:i+4]),1,places=5)
   parents={'hand_l','hand_r'}
   for finger in rig['fingers']:
    self.assertIn(finger['parent'],parents);parents.add(finger['name'])
