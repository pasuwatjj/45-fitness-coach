import unittest,subprocess,sys,tempfile,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class InstallerTests(unittest.TestCase):
 def test_missing_base_stops_before_write(self):
  with tempfile.TemporaryDirectory() as d:
   result=subprocess.run([sys.executable,str(ROOT/'tools/apply_v44.py'),d],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn('Incomplete base',result.stderr);self.assertEqual(list(Path(d).iterdir()),[])
 def test_unknown_local_edits_are_preserved(self):
  m=json.loads((ROOT/'MANIFEST_V44.json').read_text())
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   for name in m['required_base_files']:
    dest=p/name;dest.parent.mkdir(parents=True,exist_ok=True)
    if (ROOT/name).exists():shutil.copy2(ROOT/name,dest)
    else:dest.write_text('base fixture')
   (p/'app.py').write_text('TEAM LOCAL EDIT')
   result=subprocess.run([sys.executable,str(ROOT/'tools/apply_v44.py'),d],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn('Local edits',result.stderr);self.assertEqual((p/'app.py').read_text(),'TEAM LOCAL EDIT');self.assertFalse((p/'activity_energy.py').exists())
