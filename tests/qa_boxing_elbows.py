"""Actual skinned-surface regression for the reported guard elbow fold; uppercut trajectory."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import os,json
root=os.environ.get('BOXING_TEST_ORIGIN','http://127.0.0.1:5068');out=Path('work/boxing-elbow-review');out.mkdir(parents=True,exist_ok=True)
measure=r'''()=>{f.root.updateMatrixWorld(true);f.skeleton.update();const result={};for(const side of ['left','right']){const a=f.bones[side+'Arm'],m=f.body.children.find(m=>m.isSkinnedMesh&&m.geometry.attributes.position.count>3000),g=m.geometry,p=g.attributes.position,idx=g.attributes.skinIndex,weights=g.attributes.skinWeight;let vertices=[],ratios=[];for(let i=0;i<p.count;i++){const v=new THREE.Vector3().fromBufferAttribute(p,i),d=v.clone().sub(a.elbowBind);let arm=0;for(let k=0;k<4;k++)if([a.upperIndex,a.lowerIndex,a.elbowIndex].includes(idx.array[i*4+k]))arm+=weights.array[i*4+k];vertices[i]=arm>.9&&d.length()<.30}for(let i=0;i<g.index.count;i+=3){const ids=[0,1,2].map(k=>g.index.getX(i+k));if(!ids.every(j=>vertices[j]))continue;const bind=ids.map(j=>new THREE.Vector3().fromBufferAttribute(p,j)),skin=ids.map((j,k)=>m.applyBoneTransform(j,bind[k].clone())),area=v=>v[1].clone().sub(v[0]).cross(v[2].clone().sub(v[0])).length();if(area(bind)>1e-6)ratios.push(area(skin)/area(bind))}ratios.sort((a,b)=>a-b);result[side]={count:ratios.length,min:ratios[0],p10:ratios[Math.floor(ratios.length*.1)],median:ratios[Math.floor(ratios.length*.5)],max:ratios.at(-1)}}return result}'''
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 errors=[];measurements={}
 for variant in ['male','female']:
  page=b.new_page(viewport={'width':700,'height':850});page.on('pageerror',lambda e:errors.append(str(e)));measurements[variant]={};page.route(root+'/__elbow__',lambda r:r.fulfill(content_type='text/html',body='<div id="arena" style="width:700px;height:850px"></div>'));page.goto(root+'/__elbow__');page.add_style_tag(content='body{margin:0}.cage-canvas{width:700px;height:850px}')
  for asset in ['vendor/three-r160.min.js','character-renderer.js','muscle-progression.js','imported-avatar.js','boxing-motion.js','boxing-world.js']:
   if os.environ.get('BOXING_WORLD_SOURCE') and asset=='boxing-world.js':page.add_script_tag(content=Path(os.environ['BOXING_WORLD_SOURCE']).read_text())
   else:page.add_script_tag(url=root+'/static/'+asset)
  page.evaluate("gender=>{window.I18N={lang:'en'};window.w=new BoxingWorld(document.getElementById('arena'));w.add({appearance:{gender},growth:{},visual:{}},0);w.set([{x:0,z:0,controlMode:'computer'}],false)}",variant);page.wait_for_function("w.actors[0].canvas.dataset.avatarState==='ready'")
  page.evaluate("""w.running=false;cancelAnimationFrame(w.frame);window.f=w.actors[0];window.apply=(state={},kind='none',side='left',age=1000)=>{performance.now=()=>10000;f.punchType=kind;f.punchHand=side;f.punchAt=10000-age;for(let i=0;i<35;i++)f.update({x:0,z:0,controlMode:'computer',...state},{x:0,z:3},.016,0);f.root.updateMatrixWorld(true);f.skeleton.update();w.camera.position.set(2.3,3.7,3.1);w.camera.lookAt(0,1.1,0);w.camera.fov=28;w.camera.updateProjectionMatrix();w.renderer.render(w.scene,w.camera)};apply();void 0""")
  for state in ['idle','both','left','right']:
   page.evaluate('s=>apply(s)',{} if state=='idle' else {'guard':True,'guard_side':state});metrics=page.evaluate(measure);measurements[variant][state]=metrics;
   # A near-zero triangle area exposes the pinched/folded skin even when bone lengths pass.
   for side,result in metrics.items():assert result['count']>200 and result['min']>.2 and result['median']>.9,(variant,side,result)
   page.screenshot(path=str(out/f'{variant}-{state}.png'))
  for side in ['left','right']:
   heights=[]
   for age in [55,180,360]:
    page.evaluate('v=>apply({},"uppercut",v[0],v[1])',[side,age]);heights.append(page.evaluate("s=>{const a=f.bones[s+'Arm'];return a.lower.localToWorld(a.end.clone()).y}",side));page.screenshot(path=str(out/f'{variant}-uppercut-{side}-{age}.png'))
   assert heights[1]-heights[0]>.30,(variant,side,heights)
   assert heights[2]-heights[0]>.08,(variant,side,heights)
  assert not errors,errors
  page.close()
 (out/'measurements.json').write_text(json.dumps(measurements,indent=2))
 b.close()
print('PASS male/female elbow surface area, high-angle idle and three guards, bilateral uppercut chamber/rise/recovery')
