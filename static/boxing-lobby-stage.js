'use strict';
// One lit training room: fighter, equipment and floor share the same perspective.
window.BoxingLobbyStage=class{
 constructor(scene,renderer){
  const T=THREE;this.resources=[];this.room=new T.Group();scene.add(this.room);
  const own=v=>(this.resources.push(v),v),mat=(color,extra={})=>own(new T.MeshStandardMaterial({color,roughness:.8,...extra}));
  const mesh=(g,m,x=0,y=0,z=0,parent=this.room)=>{const o=new T.Mesh(own(g),m);o.position.set(x,y,z);o.castShadow=o.receiveShadow=true;parent.add(o);return o};
  const box=(w,h,d,m,x,y,z,parent)=>mesh(new T.BoxGeometry(w,h,d),m,x,y,z,parent);
  const bar=(a,b,r,m,parent=this.room)=>{const d=b.clone().sub(a),o=mesh(new T.CylinderGeometry(r,r,d.length(),8),m,0,0,0,parent);o.position.copy(a).add(b).multiplyScalar(.5);o.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),d.normalize());return o};
  const texture=(w,h,paint)=>{const c=document.createElement('canvas');c.width=w;c.height=h;paint(c.getContext('2d'),w,h);const t=own(new T.CanvasTexture(c));t.colorSpace=T.SRGBColorSpace;return t};
  const concrete=texture(256,256,c=>{c.fillStyle='#35434a';c.fillRect(0,0,256,256);let seed=45;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296};for(let i=0;i<6000;i++){c.fillStyle=i%3?'#ffffff07':'#00000019';c.fillRect(random()*256,random()*256,1+random()*3,1+random()*3)}});concrete.wrapS=concrete.wrapT=T.RepeatWrapping;concrete.repeat.set(3,2);
  const wall=mat('#6d777a',{map:concrete}),floor=mat('#303c40',{roughness:.94}),steel=mat('#15232a',{metalness:.65,roughness:.4}),metal=mat('#a1aeb0',{metalness:.85,roughness:.3}),gold=mat('#b98e52',{metalness:.45}),red=mat('#822b35'),rubber=mat('#0f181e');
  scene.background=new T.Color('#111c24');scene.fog=new T.Fog('#111c24',8,20);renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;
  scene.add(new T.HemisphereLight(0xb9d3e0,0x32251b,1.8));
  const key=new T.SpotLight(0xffdb9d,65,12,.65,.55,1.4);key.position.set(-1.7,3.5,2);key.target.position.set(-.4,0,0);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.bias=-.0004;key.shadow.normalBias=.015;scene.add(key,key.target);
  const rim=new T.PointLight(0x64caeb,10,7,1.6);rim.position.set(2.1,2.5,-1.7);scene.add(rim);const fill=new T.DirectionalLight(0xd2e5f3,1.3);fill.position.set(1,3,4);scene.add(fill);this.lamps=[key,rim];
  box(16,.12,13,floor,0,-.07,-1).name='lobby-floor';box(16,4,.16,wall,0,2,-3.6);box(.16,4,12,wall,-5.5,2,0);
  // Rubber tiles, inset training zone and brass floor markings are geometry, not a backdrop.
  const seam=mat('#131f25');for(let x=-6;x<=6;x+=1)box(.012,.005,10,seam,x,.002,0);for(let z=-4;z<=5;z+=1)box(13,.005,.012,seam,0,.003,z);
  box(3.4,.018,2.7,rubber,-.3,.004,.1);for(const x of [-2,1.4])box(.025,.004,2.7,gold,x,.016,.1);for(const z of [-1.25,1.45])box(3.4,.004,.025,gold,-.3,.016,z);
  const floorInk=texture(512,256,c=>{c.clearRect(0,0,512,256);c.textAlign='center';c.fillStyle='#6b7b80';c.font='900 88px sans-serif';c.fillText('45',256,110);c.font='700 23px sans-serif';c.fillText('TRAINING FLOOR',256,160)});const decal=mesh(new T.PlaneGeometry(1.2,.6),own(new T.MeshBasicMaterial({map:floorInk,transparent:true,depthWrite:false})),.1,.018,.85);decal.rotation.x=-Math.PI/2;decal.castShadow=false;
  for(const x of [-4,-1.5,1.5,4]){box(.15,3.7,.22,steel,x,1.85,-3.4);box(.7,.018,.25,gold,x,.18,-3.25)}
  for(const y of [.35,2.9])box(12,.06,.12,steel,0,y,-3.4);
  const glow=mat('#9eeaff',{emissive:'#64c9ea',emissiveIntensity:2.5});for(const x of [-3.6,2.6])box(.035,2.2,.025,glow,x,1.6,-3.48);
  const sign=texture(1024,400,c=>{c.fillStyle='#111e26';c.fillRect(0,0,1024,400);c.fillStyle='#dbc28c';c.fillRect(80,45,864,4);c.font='italic 900 210px sans-serif';c.textAlign='center';c.fillText('45',512,240);c.fillStyle='#dce5e4';c.font='700 49px sans-serif';c.fillText('FIGHT CLUB',512,316);c.fillStyle='#708c9b';c.font='18px sans-serif';c.fillText('PRIVATE TRAINING HALL',512,364)});mesh(new T.PlaneGeometry(2.6,1.02),mat('#ffffff',{map:sign,emissive:'#5e563f',emissiveMap:sign,emissiveIntensity:.4}),-.6,2.15,-3.49);
  // Visible overhead steel support, lamp housings and a chain fixed at its anchor.
  box(9,.18,.24,steel,0,2.82,0);for(const x of [-3.4,3.4])box(.14,2.82,.14,steel,x,1.41,0);
  const warm=mat('#ffebc5',{emissive:'#ffcb78',emissiveIntensity:3});for(const x of [-2.4,2.1]){bar(new T.Vector3(x,3.5,1),new T.Vector3(x,2.85,1),.015,metal);mesh(new T.ConeGeometry(.23,.16,24,1,true),steel,x,2.8,1);mesh(new T.CylinderGeometry(.17,.17,.02,20),warm,x,2.73,1)}
  // A distant practice ring adds depth behind the training mat.
  box(2.7,.24,2.2,steel,-3.5,.13,-2);box(2.6,.025,2.1,mat('#74888b'),-3.5,.265,-2);
  for(const x of [-4.8,-2.2])for(const z of [-3,-1]){box(.09,1.25,.09,steel,x,.88,z);for(const y of [.65,1,1.35]){bar(new T.Vector3(-4.8,y,z),new T.Vector3(-2.2,y,z),.015,metal);bar(new T.Vector3(x,y,-3),new T.Vector3(x,y,-1),.015,metal)}}
  // Bench and lockers sit in the same room and catch the room lighting.
  box(1.5,.09,.4,mat('#554638'),2.7,.48,-2.5);for(const x of [2.1,3.3])box(.06,.46,.3,steel,x,.23,-2.5);
  for(const x of [3.4,4,4.6]){box(.55,1.8,.5,steel,x,.9,-3.15);box(.02,.2,.025,metal,x+.16,1.05,-2.885);for(let n=0;n<3;n++)box(.3,.02,.015,seam,x,1.55+n*.06,-2.885)}
  box(.12,.14,.12,metal,.44,2.72,0).name='chain-anchor';
  this.bag=new T.Group();this.bag.name='lobby-heavy-bag';this.bag.position.set(.44,2.65,0);this.room.add(this.bag);const bag=this.bag;
  const leather=mat('#33282c',{roughness:.68});mesh(new T.CylinderGeometry(.235,.25,1.18,32,4),leather,0,1.2-2.65,0,bag);
  for(const y of [.63,1.77]){mesh(new T.CylinderGeometry(.252,.252,.08,32),red,0,y-2.65,0,bag);const stitch=mesh(new T.TorusGeometry(.251,.003,4,48),gold,0,y-2.65,0,bag);stitch.rotation.x=Math.PI/2}
  for(const a of [0,Math.PI/2,Math.PI,Math.PI*1.5]){const x=Math.cos(a)*.237,z=Math.sin(a)*.237;bar(new T.Vector3(x,.7-2.65,z),new T.Vector3(x,1.7-2.65,z),.0035,red,bag)}
  const badge=texture(256,320,c=>{c.fillStyle='#9a2937';c.fillRect(0,0,256,320);c.fillStyle='#f5ebda';c.textAlign='center';c.font='900 140px sans-serif';c.fillText('45',128,170);c.font='700 22px sans-serif';c.fillText('FIGHT CLUB',128,230)});mesh(new T.PlaneGeometry(.19,.24),mat('#ffffff',{map:badge}),0,1.3-2.65,.252,bag);
  const chain=new T.Group();chain.name='bag-chain';bag.add(chain);const linkGeometry=own(new T.TorusGeometry(.024,.006,6,12));
  for(const a of [0,Math.PI*2/3,Math.PI*4/3]){const start=new T.Vector3(Math.cos(a)*.18,1.82-2.65,Math.sin(a)*.18),end=new T.Vector3(0,-.1,0),direction=end.clone().sub(start).normalize(),orientation=new T.Quaternion().setFromUnitVectors(new T.Vector3(0,1,0),direction);for(let i=0;i<19;i++){const link=new T.Mesh(linkGeometry,metal);link.position.copy(start).lerp(end,i/18);link.quaternion.copy(orientation).multiply(new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),i%2*Math.PI/2));link.scale.y=1.35;link.castShadow=true;chain.add(link)}}
  for(let i=0;i<3;i++){const link=new T.Mesh(linkGeometry,metal);link.position.y=-i*.035;link.rotation.y=i%2*Math.PI/2;link.scale.y=1.35;chain.add(link)}
 }
 update(time,height,impact){this.room.scale.setScalar(height);this.bag.rotation.z=impact;this.lamps[0].intensity=65+Math.sin(time*.7)*2;this.lamps[1].intensity=10+Math.sin(time*.5+1)*.5}
 dispose(){for(const light of this.lamps)light.shadow?.dispose();for(const r of this.resources)r.dispose();this.room.removeFromParent()}
};
