/* Run against a disposable local server on port 5056. Requires Playwright,
   Chromium and the project's Python/Pillow. Checks rendered pixels, not DOM presence. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),{spawnSync}=require('node:child_process');
const root='http://127.0.0.1:5056';
async function visible(page,label){
 const canvas=page.locator('#characterCanvas');await canvas.scrollIntoViewIfNeeded();
 const size=await canvas.evaluate(c=>({w:c.width,h:c.height,lost:c.getContext('webgl2')?.isContextLost()}));
 assert(size.w>100&&size.h>100&&size.w<=2048&&size.h<=2048,`${label}: runaway/empty buffer ${JSON.stringify(size)}`);assert(!size.lost,`${label}: context lost`);
 const png=await canvas.screenshot();
 require('node:fs').writeFileSync('/tmp/avatar-visibility-'+label.replace(/[^a-z0-9]/gi,'-')+'.png',png);
 const result=spawnSync('.venv/bin/python',['-c',`import sys,io,json
from PIL import Image
im=Image.open(io.BytesIO(sys.stdin.buffer.read())).convert('RGB')
pixels=list(im.getdata());skin=sum(r>70 and r>g*1.15 and g>b*1.08 for r,g,b in pixels)
print(json.dumps({'skin_pixels':skin,'total':len(pixels)}))
assert skin>len(pixels)*.01, 'Avatar pixels missing'
`],{input:png});assert.equal(result.status,0,`${label}: blank rendered image ${result.stderr}`);
 console.log(label,JSON.stringify(size),result.stdout.toString().trim());
}
async function scenario(browser,width,dpr){
 const context=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:dpr,isMobile:width<500,hasTouch:width<500});const page=await context.newPage();const errors=[],failures=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=500)failures.push(r.status()+' '+r.url())});
 page.on('requestfailed',r=>{if(!r.failure()?.errorText.includes('ERR_ABORTED'))failures.push(r.failure()?.errorText+' '+r.url())});
 const email=`visibility-${width}-${Date.now()}@example.com`;
 const reg=await context.request.post(root+'/auth/register',{data:{email,password:'Testing-pass-123',recovery_number:'48'}});assert(reg.ok(),await reg.text());
 const token=(await(await context.request.post(root+'/session')).json()).session_token;
 const profile=await context.request.post(root+'/profiles',{headers:{'X-Coach-Session':token},data:{name:'Visibility '+width+' '+Date.now()}});assert(profile.ok(),await profile.text());
 await page.goto(root+'/45-fitness-coach');await page.waitForTimeout(1500);await page.evaluate(()=>CharacterPage.show());await page.waitForSelector('#characterCanvas');
 const start=Date.now();
 for(const sec of [1,5,15,30,60]){await page.waitForTimeout(Math.max(0,start+sec*1000-Date.now()));await visible(page,`${width}@${dpr} ${sec}s`);}
 const target=page.locator('#characterCanvas');await target.scrollIntoViewIfNeeded();const before=await target.screenshot(),box=await target.boundingBox();
 if(width<500){const cdp=await context.newCDPSession(page);const x=box.x+box.width*.3,y=box.y+box.height*.4;await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});for(let i=1;i<=4;i++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+i*25,y}]});await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await cdp.detach();}
 else{await page.mouse.move(box.x+box.width*.3,box.y+box.height*.4);await page.mouse.down();await page.mouse.move(box.x+box.width*.3+100,box.y+box.height*.4,{steps:4});await page.mouse.up();}
 const after=await target.screenshot();const a='/tmp/avatar-drag-before-'+width+'.png',b='/tmp/avatar-drag-after-'+width+'.png';require('fs').writeFileSync(a,before);require('fs').writeFileSync(b,after);
 const rotated=spawnSync('.venv/bin/python',['-c',`from PIL import Image,ImageChops
import sys
im=ImageChops.difference(Image.open(sys.argv[1]).convert('RGB'),Image.open(sys.argv[2]).convert('RGB'))
assert sum(max(p)>30 for p in im.getdata())>im.width*im.height*.01, 'Drag did not visibly rotate model'
`,a,b]);assert.equal(rotated.status,0,rotated.stderr.toString());console.log(width,'visible pointer/touch rotation passed');
 const form=page.locator('.character-options form');
 for(const gender of ['female','male'])for(const clothing of ['sports','tank','tee']){
  await form.locator('select').nth(0).selectOption(gender);await form.locator('select').nth(4).selectOption(clothing);
  await page.locator('#characterCanvas').focus();for(let i=0;i<12;i++)await page.keyboard.press('ArrowRight');await visible(page,`${width} ${gender}/${clothing}`);
 }
 for(const [i,value]of [[1,'round'],[2,'broad'],[3,'angular'],[5,'curly']])await form.locator('select').nth(i).selectOption(value);
 await form.locator('input[type=number]').nth(0).fill('185');await form.locator('input[type=number]').nth(1).fill('95');
 const response=page.waitForResponse(r=>r.url().endsWith('/character')&&r.request().method()==='POST');await form.locator('button[type=submit]').click();const saved=await response;assert(saved.ok(),await saved.text());const data=await saved.json();assert.equal(data.dimensions.height_cm,185);assert.equal(data.dimensions.weight_kg,95);await visible(page,`${width} saved`);
 await page.reload();await page.waitForTimeout(1500);await page.evaluate(()=>CharacterPage.show());await page.waitForSelector('#characterCanvas');assert.equal(await page.locator('.character-options form select').nth(5).inputValue(),'curly');await visible(page,`${width} restored`);
 for(let i=0;i<4;i++){await page.evaluate(()=>setTab('profile'));await page.waitForTimeout(300);await page.evaluate(()=>CharacterPage.show());await page.waitForSelector('#characterCanvas');await visible(page,`${width} navigation ${i}`);}
 // Real context loss/restoration must redraw without another model edit.
 await page.evaluate(()=>{const c=document.querySelector('#characterCanvas'),gl=c.getContext('webgl2');const ext=gl.getExtension('WEBGL_lose_context');if(!ext)throw Error('Context-loss extension missing');window.testContextExtension=ext;ext.loseContext()});await page.waitForTimeout(300);await page.evaluate(()=>window.testContextExtension.restoreContext());await page.waitForTimeout(1000);await visible(page,`${width} context restored`);
 assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);await context.close();
}
(async()=>{const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});try{await Promise.all([scenario(browser,1280,2),scenario(browser,390,3)])}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
