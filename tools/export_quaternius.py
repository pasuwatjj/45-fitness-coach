"""Run with Blender 4.3 from the repository root after extracting the official archive under work/quaternius. Produces CC0 static editor meshes; no runtime database access."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
root=Path('work/quaternius/Universal Base Characters[Standard]')
out=Path('static/models/quaternius');out.mkdir(parents=True,exist_ok=True)
# Repair two broken relative image references shipped in the official glTF.
for p in root.rglob('*.gltf'):
 d=json.loads(p.read_text());changed=False
 for im in d.get('images',[]):
  uri=im.get('uri','')
  if uri and not (p.parent/uri).exists() and (p.parent/uri.replace('_png.png','.png')).exists():im['uri']=uri.replace('_png.png','.png');changed=True
 if changed:p.write_text(json.dumps(d))
def export(path,gender,hair=False):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
 for a in list(bpy.data.objects):
  if a.type!='ARMATURE':continue
  for side,sign in [('l',1),('r',-1)]:
   pb=a.pose.bones.get('upperarm_'+side)
   if pb:
    h=a.matrix_world@pb.head
    r=Matrix.Translation(h)@Matrix.Rotation(sign*math.radians(75),4,'Y')@Matrix.Translation(-h)
    pb.matrix=a.matrix_world.inverted()@r@a.matrix_world@pb.matrix
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();meshes=[]
 for o in list(bpy.data.objects):
  if o.type!='MESH' or not o.data.materials:continue
  obj=o.evaluated_get(dg);m=obj.to_mesh();m.calc_loop_triangles()
  pos=[];norm=[];uv=[];idx=[];masks={k:dict(position=[],normal=[],uv=[],index=[]) for k in ['tee','tank','sports','shorts']};lookup={}
  for tri in m.loop_triangles:
   ids=[];rest=[]
   for li in tri.loops:
    loop=m.loops[li];v=m.vertices[loop.vertex_index];w=obj.matrix_world@v.co
    # Blender Z-up, front -Y -> Three Y-up, front +Z; units remain metres.
    p=(w.x,w.z,-w.y);n=obj.matrix_world.to_3x3()@m.corner_normals[li].vector
    tex=m.uv_layers.active.data[li].uv if m.uv_layers.active else (0,0)
    key=tuple(round(x,6) for x in (*p,n.x,n.z,-n.y,*tex))
    if key not in lookup:
     lookup[key]=len(pos)//3;pos.extend(key[:3]);norm.extend(key[3:6]);uv.extend(key[6:])
    ids.append(lookup[key]);rest.append(o.matrix_world@o.data.vertices[loop.vertex_index].co)
   idx.extend(ids)
   if 'Super' in o.name:
    # Clip triangles at garment boundaries instead of dropping whole faces.
    # Interpolate posed positions, normals and UVs using the original rest coordinates.
    for style,(bottom,top,width) in {'strap_l':(1.40,1.52,.145),'strap_r':(1.40,1.52,.145),'shorts':(.72,1.08,.29),'tee':(1.0,1.52,.39),'tank':(1.0,1.50,.18),'sports':(1.22,1.40,.19)}.items():
     poly=[list(pos[i*3:i*3+3])+list(norm[i*3:i*3+3])+list(uv[i*2:i*2+2])+[r.x,r.z] for i,r in zip(ids,rest)]
     for axis,limit,sign in [(8,-width,1),(8,width,-1),(9,bottom,1),(9,top,-1)]:
      clipped=[]
      for j,b in enumerate(poly):
       a=poly[j-1];da=(a[axis]-limit)*sign;db=(b[axis]-limit)*sign
       if (da>=0)!=(db>=0):
        t=da/(da-db);clipped.append([x+(y-x)*t for x,y in zip(a,b)])
       if db>=0:clipped.append(b)
      poly=clipped
      if not poly:break
     if style.startswith('strap'):
      clipped=[];sign=1 if style=='strap_l' else -1
      for j,b in enumerate(poly):
       a=poly[j-1];da=a[8]*sign-.10;db=b[8]*sign-.10
       if (da>=0)!=(db>=0):
        t=da/(da-db);clipped.append([x+(y-x)*t for x,y in zip(a,b)])
       if db>=0:clipped.append(b)
      poly=clipped
     dest=masks['sports' if style.startswith('strap') else style]
     for j in range(1,len(poly)-1):
      for v in [poly[0],poly[j],poly[j+1]]:
       dest['index'].append(len(dest['position'])//3);dest['position'].extend(v[:3]);dest['normal'].extend(v[3:6]);dest['uv'].extend(v[6:8])
  meshes.append(dict(name=o.name,material=o.data.materials[0].name,position=pos,normal=norm,uv=uv,index=idx,clothing=masks))
  obj.to_mesh_clear()
 dest=out/(gender+'.json');
 def rounded(v):
  if isinstance(v,float):return round(v,6)
  if isinstance(v,list):return [rounded(x) for x in v]
  if isinstance(v,dict):return {k:rounded(x) for k,x in v.items()}
  return v
 dest.write_text(json.dumps(rounded(meshes),separators=(',',':')));print('EXPORTED',dest,dest.stat().st_size)
for gender in ['male','female']:
 export(next(root.rglob('Superhero_'+gender.title()+'_FullBody.gltf')),gender)
for p in (root/'Hairstyles'/'Rigged to Head Bone'/'glTF (Godot -Unreal)').glob('Hair_*.gltf'):
 if p.stem in ['Hair_Buzzed','Hair_SimpleParted','Hair_Long']:export(p,p.stem,True)
