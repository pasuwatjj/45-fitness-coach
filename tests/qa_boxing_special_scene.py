"""Deterministic public-asset visual/rig inspection of every cinematic beat."""
import os,json
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
out=Path('work/boxing-special-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 p=b.new_page(viewport={'width':1200,'height':820});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.route(root+'/__special_scene__',lambda r:r.fulfill(content_type='text/html',body='<html><body style="margin:0;background:#07121e"><div class="boxing-arena" style="width:1200px;height:780px;max-height:none"><div class="boxing-fighters" id="scene"></div></div></body></html>'))
 p.goto(root+'/__special_scene__');p.add_style_tag(url=root+'/static/boxing.css')
 for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-motion.js','boxing-finale.js','boxing-special.js','boxing-world.js']:p.add_script_tag(url=root+'/static/'+asset)
 p.evaluate("window.I18N={lang:'en'};window.scene=new BoxingWorld(document.getElementById('scene'));scene.add({appearance:{},growth:{},visual:{}},0);scene.add({appearance:{gender:'female'},growth:{},visual:{}},1);window.states=[{x:-1.3,z:0,controlMode:'computer'},{x:.7,z:0,controlMode:'computer'}];scene.set(states,false);scene.serverNow=()=>1000500;scene.special.set({id:'fixture',attacker:1,target:2,started_at:1000,duration:6.2,players:[{uid:1,x:-1.3,z:0},{uid:2,x:.7,z:0}]})")
 p.wait_for_function('scene.actors.every(a=>a.body)',timeout=60000);measurements=[]
 for name,age in [('approach',.5),('thigh',1.6),('shoulder',2.7),('prepare',3.6),('elbow',4.1),('recover',5.7)]:
  p.evaluate('age=>scene.serverNow=()=>(1000+age)*1000',age);p.wait_for_timeout(650)
  p.locator('.boxing-arena').screenshot(path=str(out/('scene-'+name+'.png')))
  measurements.append(p.evaluate("()=>{const a=scene.actors[0],d=scene.actors[1],v=()=>new THREE.Vector3(),c=scene.special.contacts;return {stage:scene.special.stage,leftFoot:a.bones.leftLeg.foot.getWorldPosition(v()).toArray(),rightFoot:a.bones.rightLeg.foot.getWorldPosition(v()).toArray(),thigh:c.thigh.toArray(),shoulder:c.shoulder.toArray(),leftError:a.bones.leftLeg.foot.getWorldPosition(v()).distanceTo(c.thigh),rightError:a.bones.rightLeg.foot.getWorldPosition(v()).distanceTo(c.shoulder),receiverFeet:['left','right'].map(s=>d.bones[s+'Leg'].foot.getWorldPosition(v()).y),elbowError:a.bones.rightArm.lower.getWorldPosition(v()).distanceTo(c.crown),finite:a.skeleton.bones.every(b=>b.matrixWorld.elements.every(Number.isFinite))}}"))
 assert all(m['finite'] for m in measurements)
 for m in measurements:
  if m['stage'] in ['prepare','elbow']:assert m['leftError']<.03 and m['rightError']<.03,m
  if m['stage']=='elbow':assert m['elbowError']<.08,m
  assert all(abs(y-.06)<.01 for y in m['receiverFeet']),m
 (out/'rig-measurements.json').write_text(json.dumps(measurements,indent=2))
 p.set_viewport_size({'width':390,'height':700});p.evaluate("document.querySelector('.boxing-arena').style.width='390px';document.querySelector('.boxing-arena').style.height='600px';scene.serverNow=()=>1003600");p.wait_for_timeout(700);p.locator('.boxing-arena').screenshot(path=str(out/'scene-mobile.png'))
 p.emulate_media(reduced_motion='reduce');p.wait_for_function('scene.special.reduced')
 p.evaluate('scene.serverNow=()=>1007000');p.wait_for_function('!scene.special.active');p.evaluate('scene.destroy()');assert p.locator('canvas').count()==0
 assert not errors,errors
 print('PASS cinematic scene phases, finite rig, mobile/reduced-motion and renderer cleanup; inspect rig-measurements.json for contact tolerances')
 b.close()
