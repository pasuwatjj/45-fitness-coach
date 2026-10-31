/* Real mesh raycasts ensure skin cannot protrude in front of the fitted shirt. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),THREE=require(path.join(root,'static/vendor/three-r160.min.js'));
const context={window:{},THREE,console};vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'static/character-renderer.js'),'utf8'),context);
let checks=0;
for(const gender of ['male','female'])for(const fullness of [0,.5,1]){
 const r=Object.create(context.window.FitnessCharacterRenderer.prototype);r.root=new THREE.Group();r.resources=[];r.bones={};r.model={appearance:{gender,clothing:'tee',build:1,top_color:'#284b73'},visual:{fullness,height_scale:1},growth:{levels:{arms:1,chest:1,shoulders:1}}};r.build();r.root.updateMatrixWorld(true);
 for(const y of [2,2.13,2.35,2.56,2.72])for(const x of [-.2,0,.2]){
  const hits=new THREE.Raycaster(new THREE.Vector3(x,y,3),new THREE.Vector3(0,0,-1)).intersectObject(r.root,true);assert(hits.length,'Missing torso surface');assert.equal(hits[0].object.material.color.getHex(),0x284b73,`${gender}/${fullness}: skin through shirt at ${x},${y}`);checks++;
 }
 for(const side of ['left','right']){
  const shoulder=r.bones[side+'Arm'].upper.localToWorld(new THREE.Vector3(0,-.055,0));const hits=new THREE.Raycaster(new THREE.Vector3(shoulder.x,shoulder.y,3),new THREE.Vector3(0,0,-1)).intersectObject(r.root,true);assert.equal(hits[0].object.material.color.getHex(),0x284b73,'Skin through shoulder sleeve');checks++;
 }r.clear();
}
console.log('PASS',checks,'shirt and shoulder coverage raycasts across both genders and three body sizes');
