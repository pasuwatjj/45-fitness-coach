"""Cold loads, retry and asynchronous gender races must never draw the retired model."""
from playwright.sync_api import sync_playwright
root='http://127.0.0.1:5055'
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(root+'/status');page.set_content('<canvas width="400" height="500"></canvas>')
 for f in ['vendor/three-r160.min.js','character-fallback.js','character-renderer.js','muscle-progression.js','avatar-pose.js','imported-avatar.js']:page.add_script_tag(url=root+'/static/'+f)
 page.evaluate("()=>{FitnessCharacterRenderer.prototype.build=function(){throw Error('Retired model rendered')}}")
 held=[];page.route('**/male-rig.json',lambda r:held.append(r))
 page.evaluate("window.r=new FitnessImportedAvatar(document.querySelector('canvas'));r.setWorkoutPreview(true);r.set({appearance:{gender:'male'},visual:{height_scale:1,fullness:.3}});r.start()")
 page.wait_for_selector('canvas[data-avatar-state=loading]');page.wait_for_timeout(300)
 assert page.evaluate('!r.body && r.root.children.length===0');assert page.locator('.avatar-load-status').count()==1
 for route in held:route.continue_()
 page.unroute('**/male-rig.json');page.wait_for_selector('canvas[data-avatar-state=ready]');assert page.locator('.avatar-load-status').count()==0
 assert page.evaluate('r.root.children.length===1')
 # A slow gender request must not replace a newer selection that is already cached.
 held=[];page.route('**/female-rig.json',lambda route:held.append(route));page.evaluate("r.set({appearance:{gender:'female'}})");page.wait_for_timeout(200);page.evaluate("r.set({appearance:{gender:'male'}})")
 for route in held:route.continue_()
 page.unroute('**/female-rig.json');page.wait_for_timeout(500);assert page.evaluate("r.loadedGender==='male' && r.model.appearance.gender==='male' && r.root.children.length===1")
 # A failed asset displays a retry, never a procedural fallback. Retrying recovers.
 page.evaluate("r.destroy();r.canvas.replaceWith(r.canvas.cloneNode());FitnessImportedAvatar.cache.clear();window.r=new FitnessImportedAvatar(document.querySelector('canvas'))")
 page.route('**/male-rig.json',lambda route:route.abort());page.evaluate("r.set({appearance:{gender:'male'}})");page.wait_for_selector('canvas[data-avatar-state=error]');assert page.evaluate('!r.body && r.root.children.length===0')
 page.unroute('**/male-rig.json');page.locator('.avatar-load-status button').click();page.wait_for_selector('canvas[data-avatar-state=ready]');assert page.evaluate('r.root.children.length===1')
 # Late asset responses cannot recreate a disposed renderer.
 held=[];page.evaluate("r.destroy();r.canvas.replaceWith(r.canvas.cloneNode());FitnessImportedAvatar.cache.clear();window.r=new FitnessImportedAvatar(document.querySelector('canvas'))");page.route('**/male-rig.json',lambda route:held.append(route));page.evaluate("r.set({appearance:{gender:'male'}})");page.wait_for_timeout(150);page.evaluate('r.destroy()')
 for route in held:route.continue_()
 page.wait_for_timeout(300);assert page.evaluate('r.root.children.length===0 && r.destroyed');assert page.locator('.avatar-load-status').count()==0
 assert not errors,errors;print('PASS cold load has no legacy model, single model after loading, gender race, asset retry, pending-load disposal');b.close()
