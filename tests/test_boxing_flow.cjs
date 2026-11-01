const vm=require('vm'),fs=require('fs'),assert=require('assert');const env={window:{},setTimeout,clearTimeout};
for(const name of ['boxing-playback','boxing-training'])vm.runInNewContext(fs.readFileSync('static/'+name+'.js','utf8'),env);
const p=new env.window.BoxingPlayback();p.push([{uid:1,x:0,z:0,move:1}],1000,0);p.push([{uid:1,x:.2,z:0,move:1}],1200,200);
assert(Math.abs(p.sample(1,180).x-.1)<1e-9);assert(p.sample(1,250).x<p.sample(1,300).x);assert(p.sample(1,5000).x<=.32+.0001);
p.push([{uid:1,x:4,z:0,move:1}],1100,300);assert(p.sample(1,5000).x<1); // Old packet ignored.
p.push([{uid:1,x:.22,z:0,move:0}],1400,400);assert.equal(p.sample(1,2000).x,.22);
p.push([{uid:1,x:.4,z:0,move:1,hit_at:1}],1600,600);assert.equal(p.sample(1,2000).x,.4); // No extra knockback from extrapolation.
p.reset();assert.equal(p.sample(1,1000),null);p.push([{uid:1,x:4.9,z:0,move:1}],1000,0);p.push([{uid:1,x:5,z:0,move:1}],1100,100);assert(p.sample(1,1000).x<=5);
(async()=>{let fail=true,stored=0,seq=0,updates=[],failures=[],activeToken=0;const api=async(path,data)=>{if(path.endsWith('start'))return{token:String(++activeToken),progress:{total_hits:stored}};assert.equal(data.token,String(activeToken));for(const e of data.events)if(e.seq>seq){seq=e.seq;stored++}if(fail){fail=false;throw Error('lost reply')}return{ack_seq:seq,progress:{total_hits:stored}}};
 const trainer=new env.window.BoxingTraining(api,d=>updates.push(d.total_hits),e=>failures.push(e.message));await trainer.start(1);assert(trainer.ready);trainer.hit('left','straight',1);trainer.hit('right','hook',1);trainer.hit('left','kick',1);trainer.hit('left','straight',3);
 await assert.rejects(trainer.flush());await trainer.flush();assert.equal(stored,2);assert.equal(trainer.run.events.length,0);trainer.run.updated=Date.now()-130000;trainer.hit('left','uppercut',1);await trainer.run.ready;assert.equal(activeToken,2);await trainer.stop();assert.equal(stored,3);assert(!trainer.ready);assert.equal(failures.length,1);
 console.log('PASS interpolation, bounded extrapolation, stale packets, knockback/stop/cage bounds; training lost-response retry, no duplicates, punches-only and final flush');
})().catch(e=>{console.error(e);process.exitCode=1});
