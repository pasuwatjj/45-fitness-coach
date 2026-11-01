'use strict';
// Presentation only: the server already resolved the deciding hit and owns rewards.
window.BoxingFinale=class{
 constructor(world){this.world=world;this.data=null;this.active=false;this.resources=[]}
 set(data){if(this.data?.id!==data?.id)this.clear();this.data=data||null}
 clear(){this.data=null;this.active=false;this.stage=null;this.world.container.closest('.boxing-arena')?.classList.remove('boxing-cinematic');this.effect?.removeFromParent();for(const r of this.resources)r.dispose();this.resources=[];this.effect=null;this.origin=null}
 sample(wall,states){
  const d=this.data;this.age=d?Math.max(0,wall/1000-d.started_at):Infinity;
  this.active=!!d&&this.age<d.duration&&states.length===2;this.stage=this.active?(this.age<1.8?'strike':this.age<4.5?'impact':'settle'):null;
  this.world.container.closest('.boxing-arena')?.classList.toggle('boxing-cinematic',this.active);
  if(!this.active){if(this.effect)this.effect.visible=false;return states}
  const smooth=BoxingMotion.smooth,a=this.age;this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches||document.body.dataset.effects==='off';
  if(this.reduced&&this.effect)this.effect.visible=false;
  this.winner=d.players.findIndex(p=>p.uid===d.winner);this.loser=d.players.findIndex(p=>p.uid===d.target);
  if(this.winner<0||this.loser<0){this.active=false;return states}
  const w=d.players[this.winner],l=d.players[this.loser],length=Math.hypot(l.x-w.x,l.z-w.z)||1;
  this.direction={x:(l.x-w.x)/length,z:(l.z-w.z)/length};this.center={x:(w.x+l.x)/2,z:(w.z+l.z)/2};
  // Stretch the original strike into a single slow-motion beat, with no repeat.
  this.strikeAge=a<.6?a/.6*55:a<1.8?55+(a-.6)/1.2*125:a<2.1?180:205+(a-2.1)*300;
  return states.map((s,i)=>{
   const losing=i===this.loser,actor=this.world.actors[i],push=losing?.30*smooth((a-1.8)/2):0,side=losing?.48+push:-.48;
   const falling=losing&&(a>=2.1||this.reduced),kind=falling?'down':losing||a>=2.8||this.reduced?'waiting':null;
   if(!losing&&!this.reduced){actor.punchHand=d.hand;actor.punchType=d.punch_type==='uppercut'?'uppercut':d.punch_type==='hook'?'hook':'straight';actor.punchAt=actor.now()-this.strikeAge}
   return{...s,x:this.center.x+this.direction.x*side,z:this.center.z+this.direction.z*side,controlMode:'computer',arms:null,posture:null,lowerBody:null,move:0,strafe:0,guard:false,crouch:0,bend:0,slip:0,hitAt:-1000,dashVisualUntil:0,timeScale:1,presentation:kind,presentationAt:actor.now()-(this.reduced?1200:Math.max(0,a-2.1)*340),recoverAfter:null};
  });
 }
 aim(){
  if(!this.active||this.reduced)return;const T=THREE,w=this.world.actors[this.winner],l=this.world.actors[this.loser];if(!w?.body||!l?.body)return;
  const a=this.age,recoil=BoxingMotion.smooth((a-1.72)/.12)*(1-BoxingMotion.smooth((a-2.1)/.45));l.neck.rotation.x-=.22*recoil;l.neck.rotation.y+=(this.data.hand==='left'?1:-1)*.18*recoil;l.chest.rotation.x-=.08*recoil;l.root.updateMatrixWorld(true);
  const head=l.neck.localToWorld(new T.Vector3(0,.22,0));
  if(a>1&&a<2.45){const arm=w.bones[this.data.hand+'Arm'],from=arm.lower.localToWorld(arm.contactEnd.clone()),weight=BoxingMotion.smooth((a-1)/.8)*(1-BoxingMotion.smooth((a-2.1)/.35));const contact=head.clone().add(new T.Vector3(-this.direction.x*.14,0,-this.direction.z*.14));BoxingContact.solve(w,this.data.hand,from.lerp(contact,weight));}
  if(a>=1.8&&!this.origin)this.origin=head.clone();
  if(this.origin)this.particles(a-1.8);
 }
 particles(age){
  const T=THREE;if(!this.effect){
   this.effect=new T.Group();this.world.scene.add(this.effect);const sprite=document.createElement('canvas');sprite.width=sprite.height=32;const context=sprite.getContext('2d'),glow=context.createRadialGradient(16,16,1,16,16,15);glow.addColorStop(0,'#ffffff');glow.addColorStop(.3,'#e5f8ffd9');glow.addColorStop(1,'#b5eaff00');context.fillStyle=glow;context.fillRect(0,0,32,32);const texture=new T.CanvasTexture(sprite);this.resources.push(texture);const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(new Float32Array(108),3));const material=new T.PointsMaterial({color:'#dcf7ff',map:texture,size:.035,transparent:true,opacity:.85,depthWrite:false,depthTest:false});this.drops=new T.Points(geometry,material);this.drops.frustumCulled=false;this.effect.add(this.drops);
   const ringGeometry=new T.TorusGeometry(.14,.008,6,48),ringMaterial=new T.MeshBasicMaterial({color:'#ffe4ad',transparent:true,opacity:.65,depthWrite:false,depthTest:false});this.ring=new T.Mesh(ringGeometry,ringMaterial);this.effect.add(this.ring);this.resources.push(geometry,material,ringGeometry,ringMaterial);
  }
  this.effect.visible=age>=0&&age<2.3;this.effect.position.copy(this.origin);const t=age*.42,positions=this.drops.geometry.attributes.position;
  for(let i=0;i<36;i++){const angle=i*2.399963,speed=.45+(i%7)*.09,side=Math.sin(angle)*speed;positions.setXYZ(i,this.direction.x*t*speed+this.direction.z*side*t,Math.cos(angle)*t*.5+t*.55-t*t*.9,this.direction.z*t*speed-this.direction.x*side*t)}positions.needsUpdate=true;
  this.drops.material.opacity=.85*(1-BoxingMotion.smooth((age-1)/1.3));this.ring.scale.setScalar(1+Math.max(0,age)*3);this.ring.quaternion.copy(this.world.camera.quaternion);this.ring.material.opacity=.65*(1-BoxingMotion.smooth(age/.65));
 }
 camera(dt){
  if(!this.active||this.reduced)return false;const T=THREE,w=this.world,a=this.age,zoom=BoxingMotion.smooth(a/.75),pull=BoxingMotion.smooth((a-3)/2),dir=this.direction;
  const focus=new T.Vector3(this.center.x+dir.x*pull*.5,1.25-pull*.65,this.center.z+dir.z*pull*.5),radius=(3.5-.75*zoom+pull*2.6)/Math.min(1,Math.max(.45,w.camera.aspect));
  // Cross-ring angle keeps both faces and the contact point visible.
  const side=new T.Vector3(dir.z,0,-dir.x),forward=new T.Vector3(dir.x,0,dir.z);const position=focus.clone().addScaledVector(side,radius).addScaledVector(forward,-.45).add(new T.Vector3(0,.35+pull*.7,0));
  w.camera.position.lerp(position,1-Math.exp(-dt*7));w.focus.lerp(focus,1-Math.exp(-dt*7));w.camera.lookAt(w.focus);return true;
 }
};
