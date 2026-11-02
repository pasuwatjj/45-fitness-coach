"""Disposable-local browser checks for seasonal navigation, contrast and grounded steps."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=os.environ['BOXING_TEST_ORIGIN'];assert root.startswith('http://127.0.0.1:')
out=Path('work/festival-review');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']);p=b.new_page(viewport={'width':1440,'height':1058});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto(root+'/45-fitness-coach');p.wait_for_timeout(1200)
 for width,theme in [(1440,'power'),(390,'power'),(390,'spicy'),(768,'spicy')]:
  p.set_viewport_size({'width':width,'height':1058 if width>600 else 844});p.locator('#'+theme+'Theme').click();p.wait_for_timeout(1000)
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert p.locator('.festival-hero h2').evaluate("e=>getComputedStyle(e).color")=='rgb(255, 231, 167)'
  assert p.locator('.festival-feature strong').first.evaluate("e=>getComputedStyle(e).color")=='rgb(255, 242, 216)'
  assert p.locator('.account-bar').bounding_box()['y']>p.locator('.brand-home').bounding_box()['height']
  p.screenshot(path=str(out/f'home-{theme}-{width}.png'),full_page=True)
 p.locator('#homeStartTraining').click();assert p.locator('.home-categories').is_visible()
 p.locator('#effectsSettingsButton').click();assert p.locator('#effectsSettings').is_visible();assert p.locator('.effect-preview img').get_attribute('src').endswith('lightning.svg');p.keyboard.press('Escape')
 p.emulate_media(reduced_motion='reduce');p.locator('#effectsSettingsButton').click();assert p.locator('#clickEffectsEnabled').is_disabled();assert p.locator('.click-particle').count()==0;p.keyboard.press('Escape')
 p.locator('.festival-actions .secondary').click();assert p.locator('#calendarPage').is_visible();assert p.locator('body').get_attribute('data-home-active')=='false'
 p.evaluate("setTab('home')");assert p.locator('body').get_attribute('data-home-active')=='true'
 p.goto(root+'/45-fitness-coach?lang=en');assert p.locator('#homeStartTraining').inner_text()=='Start training'
 # Actual bone trajectories at two update rates: a planted foot stays on the mat,
 # rather than sliding with the fighter's root. This never changes authoritative movement.
 p.route(root+'/__gait__',lambda r:r.fulfill(content_type='text/html',body='<div id="arena" style="width:900px;height:600px"></div>'))
 p.goto(root+'/__gait__')
 for name in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-motion.js','boxing-finale.js','boxing-world.js']:p.add_script_tag(url=root+'/static/'+name)
 p.evaluate("window.I18N={lang:'en'};window.scene=new BoxingWorld(document.querySelector('#arena'));scene.add({appearance:{},growth:{},visual:{}},0);scene.set([{x:-1,z:0,controlMode:'computer'}],true)")
 p.wait_for_function("scene.actors[0].canvas.dataset.avatarState==='ready'",timeout=60000)
 result=p.evaluate("""()=>{scene.running=false;cancelAnimationFrame(scene.frame);const a=scene.actors[0],results=[];for(const fps of [30,60]){a.position.set(-1,0);a.previousStep=null;a.footPlants={};a.stepPhase=0;a.gait=0;a.walkSpeed=0;let prev={},maxDrift=0,samples=0;for(let i=0;i<fps*2;i++){const state={x:-1+i/fps*.6,z:0,move:1,strafe:0,controlMode:'computer'};a.update(state,{x:3,z:0},1/fps,i/fps);for(const side of ['left','right']){const anchor=a.footPlants[side],pos=a.bones[side+'Leg'].foot.getWorldPosition(new THREE.Vector3());if(anchor&&prev[side]&&anchor.distanceTo(prev[side].anchor)<1e-8){maxDrift=Math.max(maxDrift,pos.distanceTo(prev[side].pos));samples++}prev[side]=anchor?{anchor:anchor.clone(),pos}:null}}results.push({fps,maxDrift,samples});a.update({x:a.position.x,z:0,move:0,controlMode:'computer'},{x:3,z:0},1/fps,3);if(Object.keys(a.footPlants).length)throw Error('Stale plant after stop');a.update({x:0,z:0,move:1,controlMode:'tracking'},{x:3,z:0},1/fps,4);if(Object.keys(a.footPlants).length)throw Error('Plant overrode tracking')}return results}""")
 for r in result:assert r['samples']>15 and r['maxDrift']<.025,r
 p.evaluate('scene.destroy()');assert not errors,errors;print('PASS seasonal CTAs, desktop/tablet/mobile themes and contrast, lightning/reduced motion, bilingual navigation, no JS errors; stance drift:',result);b.close()
