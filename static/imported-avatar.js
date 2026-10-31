/* Quaternius Universal Base Characters, CC0. See models/quaternius/LICENSE.txt.
   Profile editor renderer. Live pose tracking retains the articulated renderer. */
'use strict';
window.FitnessImportedAvatar=class extends FitnessCharacterRenderer {
 static cache=new Map();
 static asset(name){if(!this.cache.has(name))this.cache.set(name,fetch('/static/models/quaternius/'+name+'.json').then(r=>{if(!r.ok)throw Error('Avatar asset unavailable');return r.json()}).catch(e=>{this.cache.delete(name);throw e}));return this.cache.get(name)}
 set(model){
  this.model=model;if(this.fallback)return this.fallback.set(model);
  const gender=model.appearance?.gender==='female'?'female':'male';
  if(this.loadedGender===gender){this.build();this.draw();return}
  this.canvas.dataset.avatarState='loading';this.canvas.setAttribute('aria-busy','true');
  // Retain a visible avatar while asynchronous assets load, including offline fallback.
  if(!this.body){super.build();this.draw()}
  const serial=this.loadSerial=(this.loadSerial||0)+1;
  Promise.all([FitnessImportedAvatar.asset(gender),...['Hair_Buzzed','Hair_SimpleParted','Hair_Long'].map(n=>FitnessImportedAvatar.asset(n)),this.loadTextures(gender)]).then(([body,...parts])=>{
   if(this.destroyed||serial!==this.loadSerial)return;
   this.assetBody=body;this.assetHair=parts.slice(0,3);this.loadedGender=gender;this.build();this.canvas.dataset.avatarState='ready';this.canvas.setAttribute('aria-busy','false');this.draw();
  }).catch(()=>{if(!this.destroyed&&serial===this.loadSerial){this.canvas.dataset.avatarState='error';this.canvas.setAttribute('aria-busy','false');this.canvas.setAttribute('aria-label','3D asset unavailable. Showing the fallback avatar.');super.build();this.draw()}});
 }
 tint(color,base){const b=new THREE.Color(base);color.r/=b.r;color.g/=b.g;color.b/=b.b;}
 loadTextures(gender){
  this.textures??={};this.textureLoads??={};
  const names=[gender+'-color.jpg',gender+'-normal.png','hair-color.png','hair-normal.png','hair2-color.png','hair2-normal.png','eyes-color.jpg'];
  return Promise.all(names.map(name=>this.textureLoads[name]??=(new Promise((resolve,reject)=>new THREE.TextureLoader().load('/static/models/quaternius/'+name,t=>{if(this.destroyed){t.dispose();resolve();return}if(name.includes('color'))t.colorSpace=THREE.SRGBColorSpace;t.flipY=true;this.textures[name]=t;resolve(t)},undefined,reject)))));
 }
 build(){
  if(!this.assetBody)return super.build();
  this.clear();const T=THREE,a=this.model.appearance||{},v=this.model.visual||{},gender=this.loadedGender;
  this.height=v.height_scale||1;this.body=new T.Group();this.root.add(this.body);
  const bodyData=this.assetBody.find(m=>m.name.includes('Super'));
  const maxY=Math.max(...bodyData.position.filter((_,i)=>i%3===1));const unit=3.7/maxY;
  const full=Math.max(0,Math.min(1,v.fullness??.25));
  const skin=this.material(a.skin_color||'#d79f7a',.78);this.tint(skin.color,'#d8aa87');skin.map=this.textures[gender+'-color.jpg'];skin.normalMap=this.textures[gender+'-normal.png'];skin.normalScale.set(.65-full*.35,.65-full*.35);
  const hair=this.material(a.hair_color||'#302333',.85);hair.map=this.textures['hair-color.png'];hair.normalMap=this.textures['hair-normal.png'];hair.side=T.DoubleSide;hair.alphaTest=.35;
  const hair2=hair.clone();hair2.map=this.textures['hair2-color.png'];hair2.normalMap=this.textures['hair2-normal.png'];this.resources.push(hair2);
  const eyes=this.material('#ffffff',.4);eyes.map=this.textures['eyes-color.jpg'];
  const eyeTint=new T.Color(a.eye_color||'#553521');this.tint(eyeTint,'#553521');
  eyes.onBeforeCompile=shader=>{shader.uniforms.eyeTint={value:eyeTint};shader.fragmentShader='uniform vec3 eyeTint;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
   float saturation = max(diffuseColor.r,max(diffuseColor.g,diffuseColor.b))-min(diffuseColor.r,min(diffuseColor.g,diffuseColor.b));
   diffuseColor.rgb *= mix(vec3(1.0),eyeTint,smoothstep(0.03,0.12,saturation));`)};
  eyes.customProgramCacheKey=()=> 'quaternius-iris-tint-v1';
  const top=this.material(a.top_color||'#284b73',.95),shorts=this.material(a.shorts_color||'#172d4c',.95);top.side=shorts.side=T.DoubleSide;
  const deform=(x,y,z)=>{
   const h=y/maxY;const torso=Math.exp(-Math.pow((h-.60)/.15,2));const head=h>.86;
   // Profile-driven approximate fullness; weight never estimates muscle mass.
   x*=1+full*(head?.08:.15+.40*torso);z*=1+full*(head?.08:.18+.65*torso);
   if(head){const jaw=Math.exp(-Math.pow((h-.89)/.025,2));x*=1+(a.face==='angular'?.06:-.025)*jaw;
    if(z>.075&&Math.abs(x)<.035){const nose=Math.exp(-Math.pow((h-.934)/.016,2));x*=1+(a.nose==='broad'?.32:a.nose==='rounded'?.12:0)*nose;z+=(a.nose==='rounded'?.004:0)*nose;}
    if(Math.abs(x)>.018&&Math.abs(x)<.065&&z>.05){const eye=Math.exp(-Math.pow((h-.938)/.012,2));y+=(y-maxY*.938)*(a.eyes==='round'?.20:a.eyes==='narrow'?-.20:0)*eye;}
   }
   return [x*unit,y*unit,z*unit];
  };
  const make=(data,mat,index=data.index,offset=0)=>{
   const vertices=[];for(let i=0;i<data.position.length;i+=3){const p=deform(...data.position.slice(i,i+3));for(let k=0;k<3;k++)vertices.push(p[k]+offset*data.normal[i+k])}
   const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(vertices,3));geo.setAttribute('uv',new T.Float32BufferAttribute(data.uv,2));geo.setIndex(index);if(offset)geo.setAttribute('normal',new T.Float32BufferAttribute(data.normal,3));else geo.computeVertexNormals();return this.mesh(geo,mat,this.body);
  };
  for(const data of this.assetBody){make(data,data.name.includes('Super')?skin:data.name==='Eyes'?eyes:hair);
   if(data.name.includes('Super')){make(data.clothing.shorts,shorts,data.clothing.shorts.index,.018);const style=a.clothing==='tee'?'tee':a.clothing==='tank'?'tank':gender==='female'?'sports':null;if(style)make(data.clothing[style],top,data.clothing[style].index,.022)}
  }
  const style=a.hair||'short',hairIndex={short:0,swept:1,bob:2,ponytail:0,curly:0}[style];
  if(hairIndex!==undefined)for(const data of this.assetHair[hairIndex]){
   const mesh=make(data,data.material==='MI_Hair_2'?hair2:hair);mesh.position.y=(gender==='female'&&hairIndex<2?-.043:gender==='male'&&hairIndex===2?.043:0)*unit;
  }
  const plainHair=this.material(a.hair_color||'#302333',.9);
  if(style==='curly')for(let i=0;i<60;i++){const theta=i*2.39996,r=.088*Math.sqrt(i/60),x=Math.cos(theta)*r,z=Math.sin(theta)*r;this.ell(x*unit,(maxY-.016+.043*Math.sqrt(1-r*r/.008))*unit,(z-.012)*unit,.018*unit,.022*unit,.018*unit,plainHair,this.body)}
  if(style==='ponytail'){this.ell(0,(maxY-.08)*unit,-.10*unit,.037*unit,.05*unit,.04*unit,plainHair,this.body);this.ell(0,(maxY-.20)*unit,-.12*unit,.035*unit,.13*unit,.036*unit,plainHair,this.body)}
  this.root.scale.setScalar(this.height);this.restPose();
 }
 destroy(){super.destroy();for(const texture of Object.values(this.textures||{}))texture.dispose();this.loadSerial=(this.loadSerial||0)+1}
};
