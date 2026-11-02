'use strict';
// Choreography of the reference pose on the existing rig. Damage is server-owned.
window.BoxingSpecial=class{
 constructor(world){this.world=world;this.data=null;this.active=false}
 set(data){this.data=data||null}
 clear(){this.data=null;this.active=false;this.world.container.closest('.boxing-arena')?.classList.remove('boxing-ruesi-cinematic')}
 sample(wall,states){
  const d=this.data;this.age=d?Math.max(0,wall/1000-d.started_at):Infinity;this.active=!!d&&this.age<d.duration&&states.length===2;
  this.world.container.closest('.boxing-arena')?.classList.toggle('boxing-ruesi-cinematic',this.active);
  if(!this.active)return states;
  this.attacker=d.players.findIndex(p=>p.uid===d.attacker);this.defender=d.players.findIndex(p=>p.uid===d.target);
  if(this.attacker<0||this.defender<0){this.active=false;return states}
  const a=this.age,s=BoxingMotion.smooth,p=d.players[this.attacker],q=d.players[this.defender],length=Math.hypot(q.x-p.x,q.z-p.z)||1;
  this.dir={x:(q.x-p.x)/length,z:(q.z-p.z)/length};this.center={x:q.x,z:q.z};this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches||document.body.dataset.effects==='off';
  this.step=s((a-.9)/.9);this.climb=s((a-1.9)/.9);this.exit=s((a-4.8)/1.4);this.hold=(1-this.exit);
  this.stage=a<.9?'approach':a<1.9?'thigh':a<2.9?'shoulder':a<3.9?'prepare':a<4.35?'elbow':'recover';
  return states.map((state,i)=>{
   const attacking=i===this.attacker,actor=this.world.actors[i],approach=s(a/.9)*(1-this.exit),close=.72-this.climb*.17;
   actor.punchAt=-1000;
   const x=attacking?p.x+(q.x-this.dir.x*close-p.x)*approach:q.x,z=attacking?p.z+(q.z-this.dir.z*close-p.z)*approach:q.z;
   return{...state,x,z,controlMode:'computer',arms:null,posture:null,lowerBody:attacking?null:{confidence:1,stance:.65,stagger:-.9,drop:.85*s((a-.35)/.65)*this.hold,leftKnee:0,rightKnee:0},move:attacking&&a<.85?1:0,strafe:0,guard:!attacking,crouch:attacking?0:.85*s((a-.35)/.65)*this.hold,bend:attacking?0:.12*this.hold,slip:0,hitAt:-1000,clashAt:-1000,dashVisualUntil:0,timeScale:1,presentation:null};
  });
 }
 leg(actor,side,target){
  const T=THREE,b=actor.bones[side+'Leg'],start=b.upper.getWorldPosition(new T.Vector3()),l1=b.lower.position.length()*actor.root.scale.x,l2=b.end.length()*actor.root.scale.x,axis=target.clone().sub(start),distance=T.MathUtils.clamp(axis.length(),Math.abs(l1-l2)+.001,l1+l2-.001);axis.normalize();
  const along=(l1*l1-l2*l2+distance*distance)/(2*distance),height=Math.sqrt(Math.max(0,l1*l1-along*along)),pole=new T.Vector3(side==='left'?.15:-.15,.1,1).applyQuaternion(actor.root.quaternion);pole.addScaledVector(axis,-pole.dot(axis)).normalize();
  const knee=start.clone().addScaledVector(axis,along).addScaledVector(pole,height),end=start.clone().addScaledVector(axis,distance),inv=b.upper.parent.getWorldQuaternion(new T.Quaternion()).invert(),upper=knee.clone().sub(start).normalize().applyQuaternion(inv),lower=end.clone().sub(knee).normalize().applyQuaternion(inv),uq=new T.Quaternion().setFromUnitVectors(b.restUpper,upper);
  b.upper.quaternion.copy(uq);b.lower.quaternion.copy(uq.clone().invert().multiply(new T.Quaternion().setFromUnitVectors(b.restLower,lower)));actor.root.updateMatrixWorld(true);b.foot.quaternion.copy(b.lower.getWorldQuaternion(new T.Quaternion()).invert().multiply(actor.root.quaternion));actor.root.updateMatrixWorld(true);
 }
 aim(){
  if(!this.active)return;const T=THREE,w=this.world.actors[this.attacker],l=this.world.actors[this.defender];if(!w?.body||!l?.body)return;
  const a=this.age,s=BoxingMotion.smooth,impact=s((a-3.9)/.2)*(1-s((a-4.35)/.5)),contact=this.step*this.hold,grip=this.climb*this.hold;
  // The receiver keeps staggered feet on the floor while lowering into the stance.
  l.chest.rotation.x+=.16*impact;l.neck.rotation.x+=.20*impact;l.root.updateMatrixWorld(true);
  const feet={};for(const side of ['left','right'])feet[side]=w.bones[side+'Leg'].foot.getWorldPosition(new T.Vector3());
  const thigh=l.bones.rightLeg.upper.getWorldPosition(new T.Vector3()).lerp(l.bones.rightLeg.lower.getWorldPosition(new T.Vector3()),.55).add(new T.Vector3(-this.dir.x*.04,.04,-this.dir.z*.04));
  const shoulder=l.bones.leftArm.upper.getWorldPosition(new T.Vector3()).add(new T.Vector3(-this.dir.x*.03,.05,-this.dir.z*.03));
  // Lift the pelvis continuously before solving both fixed-length leg chains.
  const lift=(.20*this.step+.16*this.climb-.22*impact)*this.hold;
  w.body.position.y+=lift/w.root.scale.y;w.body.position.z+=.10*impact/w.root.scale.y;w.root.updateMatrixWorld(true);
  this.leg(w,'left',feet.left.lerp(thigh,contact));this.leg(w,'right',feet.right.lerp(shoulder,grip));
  const neck=l.neck.getWorldPosition(new T.Vector3()).add(new T.Vector3(-this.dir.x*.08,.08,-this.dir.z*.08));
  const left=w.bones.leftArm,hand=left.lower.localToWorld(left.contactEnd.clone());BoxingContact.solve(w,'left',hand.lerp(neck,grip));
  // Right elbow descends onto the crown; the forearm stays folded across the chest.
  const arm=w.bones.rightArm,start=arm.upper.getWorldPosition(new T.Vector3()),crown=l.neck.localToWorld(new T.Vector3(0,.26,0)),windup=s((a-2.6)/.6),drop=s((a-3.9)/.2),blend=windup*this.hold;
  const raised=start.clone().add(new T.Vector3(this.dir.z*.25,.26,-this.dir.x*.25)),elbow=raised.lerp(crown,drop),inv=arm.upper.parent.getWorldQuaternion(new T.Quaternion()).invert(),up=elbow.sub(start).normalize().applyQuaternion(inv),uq=new T.Quaternion().setFromUnitVectors(arm.restUpper,up);
  const lower=new T.Vector3(-.65,.65,.25).applyQuaternion(w.root.quaternion).applyQuaternion(inv).normalize(),lq=new T.Quaternion().setFromUnitVectors(arm.restLower,lower.applyQuaternion(uq.clone().invert()));
  arm.upper.quaternion.slerp(uq,blend);arm.lower.quaternion.slerp(lq,blend);w.relaxElbows();w.root.updateMatrixWorld(true);
  const support=l.bones.rightArm,from=support.lower.localToWorld(support.contactEnd.clone()),ankle=w.bones.leftLeg.foot.getWorldPosition(new T.Vector3());BoxingContact.solve(l,'right',from.lerp(ankle,contact*.85));l.relaxElbows();
  this.contacts={thigh,shoulder,crown};w.canvas.dataset.specialStage=this.stage;l.canvas.dataset.specialStage='receiving-'+this.stage;
 }
 camera(dt){
  if(!this.active)return false;const T=THREE,w=this.world,d=this.dir,side=new T.Vector3(-d.z,0,d.x),forward=new T.Vector3(d.x,0,d.z),focus=new T.Vector3(this.center.x-d.x*.2,1.05+this.climb*.25,this.center.z-d.z*.2),radius=(this.reduced?4.4:4.1)/Math.min(1,Math.max(.55,w.camera.aspect));
  const position=focus.clone().addScaledVector(side,radius).addScaledVector(forward,-.9).add(new T.Vector3(0,.42,0));
  w.camera.position.lerp(position,1-Math.exp(-dt*(this.reduced?4:7)));w.focus.lerp(focus,1-Math.exp(-dt*7));w.camera.lookAt(w.focus);return true;
 }
};
