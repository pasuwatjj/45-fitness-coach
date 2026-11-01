'use strict';
// Saving is independent of animation. Retry the same sequence after a lost response.
window.BoxingTraining=class{
 constructor(api,update,error){this.api=api;this.update=update;this.error=error;this.run=null;this.closing=Promise.resolve()}
 get ready(){return !!(this.run?.active&&this.run.token)}
 async start(pid){await this.stop();const r={pid,active:true,events:[],seq:0,token:null,timer:null,pending:null};this.run=r;
  return this.renew(r);
 }
 renew(r){r.token=null;r.updated=Date.now();r.ready=this.api('/training/'+r.pid+'/start',{}).then(d=>{r.token=d.token;r.updated=Date.now();if(this.run===r)this.update(d.progress,r.pid);if(r.events.length)this.schedule(r);return d.progress}).catch(e=>{r.active=false;if(this.run===r)this.error(e);throw e});return r.ready;}
 hit(hand,kind,distance){const r=this.run;if(!r?.active||kind==='kick'||distance>1.65)return;if(!r.events.length&&!r.pending&&Date.now()-r.updated>100000)this.renew(r).catch(()=>{});if(r.events.length>=32){this.error(Error('Training connection interrupted'));return}r.events.push({seq:++r.seq,hand,kind,distance});if(r.token)this.schedule(r)}
 schedule(r,delay=450){if(r.timer||!r.active)return;r.timer=setTimeout(()=>{r.timer=null;this.flush(r).catch(()=>{})},delay)}
 flush(r=this.run){if(!r?.token||!r.events.length)return Promise.resolve();if(r.pending)return r.pending;const events=r.events.slice(0,16);
  r.pending=this.api('/training/'+r.pid+'/hits',{token:r.token,events}).then(d=>{r.updated=Date.now();r.events=r.events.filter(e=>e.seq>d.ack_seq);if(this.run===r)this.update(d.progress,r.pid);return d}).catch(e=>{if(e.status===409)r.active=false;if(this.run===r)this.error(e);throw e}).finally(()=>{r.pending=null;if(r.active&&r.events.length)this.schedule(r,1500)});return r.pending;
 }
 stop(){const r=this.run;if(!r)return this.closing;r.active=false;clearTimeout(r.timer);r.timer=null;this.run=null;if(r.token&&r.events.length&&!r.pending)this.flush(r).catch(()=>{});
  this.closing=(async()=>{try{await r.ready;if(r.pending)await r.pending;while(r.events.length)await this.flush(r)}catch(e){this.error(e)}})();return this.closing;
 }
};
