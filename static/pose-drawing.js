'use strict';
// Rendering only: no offsets, snapping or enlarged coordinates enter scoring.
window.PoseDrawing=(()=>{
 const pairs=[[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]];
 function contentRect(width,height,sourceWidth,sourceHeight){
  if(!(width>0&&height>0&&sourceWidth>0&&sourceHeight>0))return {x:0,y:0,width:0,height:0,scale:1};
  const scale=Math.min(width/sourceWidth,height/sourceHeight),w=sourceWidth*scale,h=sourceHeight*scale;
  return {x:(width-w)/2,y:(height-h)/2,width:w,height:h,scale};
 }
 function paint(ctx,body,{width,height,scale=1,color='#7be9b2',visible=null,full=true}={}){
  if(!body?.length)return;
  const good=i=>{const p=body[i];return !!p&&Number.isFinite(p[0])&&Number.isFinite(p[1])&&p[2]>=(i===23||i===24?.65:.45)&&(visible?!!visible[i]:p[2]>.5)};
  const edges=pairs.filter(([a,b])=>(full||(a<=24&&b<=24))&&good(a)&&good(b));
  // A readable minimum on phones; larger markers on expanded camera views.
  const unit=1/Math.max(.15,scale),line=Math.min(10,Math.max(4,4.5*scale))*unit,radius=Math.min(12,Math.max(6,7*scale))*unit;
  ctx.save();ctx.lineCap='round';ctx.lineJoin='round';
  const path=()=>{ctx.beginPath();for(const[a,b]of edges){ctx.moveTo(body[a][0]*width,body[a][1]*height);ctx.lineTo(body[b][0]*width,body[b][1]*height)}};
  path();ctx.strokeStyle='rgba(12,20,32,.65)';ctx.lineWidth=line+2*unit;ctx.stroke();
  path();ctx.strokeStyle=color;ctx.lineWidth=line;ctx.stroke();
  const joints=new Set(pairs.flat().filter(i=>(full||i<=24)&&good(i)));
  for(const i of joints){const p=body[i];ctx.beginPath();ctx.arc(p[0]*width,p[1]*height,radius,0,Math.PI*2);ctx.fillStyle=(i===15||i===16)?'#ffd166':color;ctx.fill();ctx.lineWidth=2*unit;ctx.strokeStyle='#ffffff';ctx.stroke();}
  ctx.restore();
 }
 return {contentRect,paint};
})();
