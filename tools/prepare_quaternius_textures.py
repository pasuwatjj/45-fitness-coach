"""Run with Pillow from the repository root after tools/export_quaternius.py."""
from pathlib import Path
from PIL import Image
import shutil,json,hashlib
root=Path('work/quaternius/Universal Base Characters[Standard]');out=Path('static/models/quaternius')
files={
'male-color.jpg':'T_Superhero_Male_Ligh.png','female-color.jpg':'T_Superhero_Female_Light_BaseColor.png',
'male-normal.png':'T_Superhero_Male_Normal.png','female-normal.png':'T_Superhero_Female_Normal.png',
'hair2-color.png':'T_Hair_2_BaseColor.png','hair2-normal.png':'T_Hair_2_Normal.png',
'hair-color.png':'T_Hair_1_BaseColor.png','hair-normal.png':'T_Hair_1_Normal.png','eyes-color.jpg':'T_Eye_Brown.png'}
for name,source in files.items():
 paths=list((root/'Base Characters'/'Textures').rglob(source))
 p=paths[-1]
 if 'normal' in name:p=root/'Base Characters'/'Textures'/'Normals Unity - Godot'/source
 im=Image.open(p);im.thumbnail((512,512) if name.startswith('hair') else (1024,1024))
 if name.endswith('.jpg'):im=im.convert('RGB')
 im.save(out/name,quality=90,optimize=True)
shutil.copy(root/'License_Standard.txt',out/'LICENSE.txt')
for p in out.glob('*.json'):
 d=json.loads(p.read_text());print(p.name,[(m['name'],len(m['position'])//3,min(m['position'][1::3]),max(m['position'][1::3])) for m in d])
print('archive SHA256',hashlib.sha256(Path('work/quaternius.zip').read_bytes()).hexdigest())
