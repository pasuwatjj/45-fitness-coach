/* Geometry-only tests. Real Three.js math/meshes; no browser or GPU claimed. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),T=require(path.join(root,'static/vendor/three-r160.min.js'));
const context={window:{},THREE:T,console};vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'static/character-renderer.js'),'utf8'),context);
const C=context.window.FitnessCharacterRenderer;let variants=0;
for(const fullness of [0,.4,1])for(const eyes of ['almond','round','narrow'])for(const nose of ['straight','rounded','broad']){
 const r=Object.create(C.prototype);r.root=new T.Group();r.resources=[];r.bones={};r.model={appearance:{gender:'male',eyes,nose,hair:'swept',build:.8},visual:{fullness,height_scale:1},growth:{levels:{}}};r.build();let vertices=0;
 r.root.traverse(o=>{if(o.isMesh){const pos=o.geometry.attributes.position;vertices+=pos.count;assert([...pos.array].every(Number.isFinite));assert([...o.geometry.attributes.normal.array].every(Number.isFinite));assert(o.material)}});
 const box=new T.Box3().setFromObject(r.root),size=box.getSize(new T.Vector3());assert(size.y>3&&size.y<5);assert(size.x>1&&size.x<3);assert(vertices>30000);assert.equal(Object.keys(r.bones).length,4);
 // The shoulder/head/limb transforms can be retargeted without invalid matrices.
 for(const bone of Object.values(r.bones)){bone.upper.quaternion.setFromUnitVectors(new T.Vector3(0,-1,0),new T.Vector3(.2,-.9,.4).normalize());bone.lower.rotation.x=.7}
 r.root.updateMatrixWorld(true);r.root.traverse(o=>assert(o.matrixWorld.elements.every(Number.isFinite)));r.clear();assert.equal(r.resources.length,0);variants++;
}
console.log(JSON.stringify({geometryVariants:variants,finiteVertices:true,finiteNormals:true,articulatedJoints:true,resourceDisposal:true,browserRendered:false}));
