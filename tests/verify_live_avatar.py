"""GET-only live deployment smoke test. Never creates accounts or awards EXP.
Usage: .venv/bin/python tests/verify_live_avatar.py EXPECTED_RENDER_COMMIT
"""
import sys,hashlib,io
from pathlib import Path
from urllib.parse import urlparse
import requests
from playwright.sync_api import sync_playwright
from PIL import Image,ImageChops
revision=sys.argv[1];origin='https://four5-fitness-coach.onrender.com'
s=requests.Session()
def read(path):
 r=s.get(origin+path,headers={'Cache-Control':'no-cache'},timeout=45);r.raise_for_status();return r
status=read('/status').json();assert status['ok'] and status['avatar_progression']=='verified-muscle-v1';assert status['revision']==revision,status
html=read('/45-fitness-coach').text
for name in ['muscle-progression.js','imported-avatar.js','character.js']:assert name in html
for name in ['static/muscle-progression.js','static/imported-avatar.js','static/character.js','static/app.js','static/models/quaternius/male.json','static/models/quaternius/female.json']:
 assert hashlib.sha256(read('/'+name+'?release='+revision).content).hexdigest()==hashlib.sha256(Path(name).read_bytes()).hexdigest(),name
out=Path('work/live-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':900},reduced_motion='reduce');page=c.new_page();errors=[];blocked=[]
  def route(req):
   r=req.request
   if r.method!='GET':
    blocked.append(r.url);req.fulfill(status=403,content_type='application/json',body='{"error":"Read-only deployment verification"}');return
   if urlparse(r.url).hostname!=urlparse(origin).hostname:req.abort();return
   response=s.get(r.url,timeout=45)
   req.fulfill(status=response.status_code,headers={'Content-Type':response.headers.get('Content-Type','application/octet-stream')},body=response.content)
  page.route('**/*',route)
  page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'THREE.WebGLProgram' in m.text else None)
  # The full app wraps fetch until /session resolves. Keep this read-only check
  # isolated from authenticated bootstrap while using the exact deployed assets.
  page.goto(origin+'/status',wait_until='domcontentloaded')
  page.set_content('<!doctype html><html><body></body></html>')
  for asset in ['vendor/three-r160.min.js','character-fallback.js','character-renderer.js','muscle-progression.js','imported-avatar.js']:
   page.add_script_tag(url=origin+'/static/'+asset+'?release='+revision)
  # Use actual deployed scripts and assets; levels below are only in this browser.
  page.evaluate('''()=>{document.body.replaceChildren();const canvas=document.createElement('canvas');canvas.width=600;canvas.height=700;canvas.style.width='min(90vw,600px)';canvas.style.background='#122033';document.body.append(canvas);window.reviewRenderer=new FitnessImportedAvatar(canvas);window.reviewModel={appearance:{gender:'male',hair:'swept',clothing:'sports',skin_color:'#c78f68',hair_color:'#292536'},visual:{height_scale:1.03,fullness:.35},growth:{levels:{arms:0,chest:0,back:0,legs:0,shoulders:0},arm_levels:{left:0,right:0}}};reviewRenderer.set(reviewModel)}''')
  page.wait_for_selector('canvas[data-avatar-state=ready]');cv=page.locator('canvas');begin=cv.screenshot(path=str(out/f'{width}-beginner.png'))
  page.evaluate('''()=>{for(const k of Object.keys(reviewModel.growth.levels))reviewModel.growth.levels[k]=.8;reviewModel.growth.arm_levels={left:.8,right:.8};reviewRenderer.set(reviewModel)}''')
  end=cv.screenshot(path=str(out/f'{width}-developed.png'))
  diff=ImageChops.difference(Image.open(io.BytesIO(begin)).convert('RGB'),Image.open(io.BytesIO(end)).convert('RGB'));assert sum(max(p)>15 for p in diff.getdata())>500
  cv.focus();page.keyboard.press('ArrowRight');assert cv.screenshot()!=end
  assert not errors,errors;page.evaluate('reviewRenderer.destroy()');c.close();print(width,'live assets rendered, novice/developed pixels differ, rotation passed; production writes blocked',flush=True)
 b.close()
print('VERIFIED Render revision',revision,flush=True)
