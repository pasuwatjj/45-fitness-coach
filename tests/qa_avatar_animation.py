"""Local visual/retargeting QA. Synthetic poses never enter the workout counter."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image,ImageChops
import io
root='http://127.0.0.1:5055';out=Path('work/animation-review');out.mkdir(parents=True,exist_ok=True)
def difference(a,b):
 d=ImageChops.difference(Image.open(io.BytesIO(a)).convert('RGB'),Image.open(io.BytesIO(b)).convert('RGB'))
 return sum(max(p)>20 for p in d.getdata())
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':900});page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(root+'/status');page.set_content('<canvas width="420" height="500" style="width:min(90vw,420px);background:#30263e"></canvas>')
  for f in ['vendor/three-r160.min.js','character-fallback.js','character-renderer.js','muscle-progression.js','avatar-pose.js','imported-avatar.js']:page.add_script_tag(url=root+'/static/'+f)
  for gender in ['male','female']:
   page.evaluate('''gender=>{window.r?.destroy();const old=document.querySelector('canvas'),cv=old.cloneNode();old.replaceWith(cv);window.r=new FitnessImportedAvatar(cv);r.setWorkoutPreview(true);r.set({appearance:{gender,hair:'swept',clothing:'tee',skin_color:'#c78f68',top_color:'#634590'},visual:{height_scale:1.02,fullness:.3},growth:{levels:{arms:.3,chest:.2,legs:.1}}})}''',gender)
   page.wait_for_selector('canvas[data-avatar-state=ready]');cv=page.locator('canvas')
   page.evaluate('r.phase=-Math.PI/3.4;r.draw()');a=cv.screenshot(path=str(out/f'{width}-{gender}-lowered.png'))
   page.evaluate('r.phase=Math.PI/3.4;r.draw()');up=cv.screenshot(path=str(out/f'{width}-{gender}-curl.png'));assert difference(a,up)>500,'Curl not visible'
   assert page.evaluate("r.bones.leftArm.lower.children.some(x=>x.name==='preview-dumbbell')")
   # Actual scheduler advances; stop freezes it. Reduced motion keeps a steady curl.
   page.evaluate('r.start()');before=page.evaluate('r.phase');page.wait_for_timeout(250);assert page.evaluate('r.phase')!=before
   page.evaluate('r.stop()');before=page.evaluate('r.phase');page.wait_for_timeout(100);assert page.evaluate('r.phase')==before
   page.emulate_media(reduced_motion='reduce');page.evaluate('r.start()');before=cv.screenshot();page.wait_for_timeout(150);assert cv.screenshot()==before;page.evaluate('r.stop()');page.emulate_media(reduced_motion='no-preference')
   page.evaluate('r.setWorkoutPreview(false);r.setLivePose(AvatarPose.neutral({exercise:"curl"}))');neutral=cv.screenshot()
   for label,expr in [('curl',"p.arms.left.lower=[0,1,.2];p.arms.right.lower=[0,1,.2]"),('raise',"p.arms.left.upper=[1,0,0];p.arms.left.lower=[1,0,0];p.arms.right.upper=[-1,0,0];p.arms.right.lower=[-1,0,0]"),('squat',"p.legs.left.upper=[.2,-.5,.8];p.legs.right.upper=[-.2,-.5,.8]"),('floor',"p=AvatarPose.neutral({exercise:'pushup'})")]:
    page.evaluate("()=>{let p=AvatarPose.neutral({exercise:'curl',focus:'full'});"+expr+";r.setLivePose(p)}")
    shot=cv.screenshot(path=str(out/f'{width}-{gender}-live-{label}.png'));assert difference(neutral,shot)>300,label
    assert page.evaluate('''()=>{r.root.updateMatrixWorld(true);const b=r.bones.leftArm,p=r.livePose;const inv=r.body.quaternion.clone().invert();const wanted=new THREE.Vector3(...p.arms.left.lower).applyQuaternion(inv).normalize();const got=b.restLower.clone().applyQuaternion(b.lower.quaternion).applyQuaternion(b.upper.quaternion);return got.distanceTo(wanted)<.001}'''),'Retargeted forearm direction incorrect'
   page.evaluate("r.setLivePose({...AvatarPose.neutral({exercise:'curl'}),mirror:true})");assert difference(neutral,cv.screenshot())>50
   page.evaluate('r.setLivePose(null)');cv.focus();before=page.evaluate('r.yaw');page.keyboard.press('ArrowRight');assert page.evaluate('r.yaw')>before
   page.evaluate('r.destroy()')
  assert not errors,errors;c.close();print(width,'PASS authored rig, curl animation, reduced motion, independent limbs, floor framing, mirror, rotation, disposal',flush=True)
 b.close()
