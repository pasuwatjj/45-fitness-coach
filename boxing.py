"""Private casual boxing matches. No images/landmarks leave the browser."""
import json,time,uuid,math
from flask import Blueprint,g,request,jsonify
import character,collaboration_features,boxing_cage
MATCH_RULES=4

def clock():return time.time()
def schema(store):
    collaboration_features.schema(store)
    with store.lock,store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS boxing_trophies(match_id TEXT PRIMARY KEY,account_id INTEGER NOT NULL,profile_id INTEGER NOT NULL,created REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS boxing_matches(id TEXT PRIMARY KEY,host INTEGER NOT NULL,guest INTEGER NOT NULL,state TEXT NOT NULL,updated REAL NOT NULL)')
def fighter(store,uid,pid):
    with store.connect() as db:
        if not db.execute('SELECT 1 FROM profile_owners WHERE owner=? AND profile_id=?',('account:'+str(uid),pid)).fetchone():raise ValueError('Choose your own profile')
    model=character.overview(store,pid)
    if not model['created']:raise ValueError('Save your avatar first')
    return dict(profile_id=pid,wins=0,crouch=0,position=None,move=0,control_at=0,guard_since=None,arms=None,uid=uid,name=model['profile']['name'],model={k:model[k] for k in ['appearance','growth','visual']},damage={s:model['growth']['arm_parts'][s]['level'] for s in ['left','right']},hp=10,armor=10,ready=False,seen=clock(),seq=0,last_punch=0,last_dodge=0,guard_until=0,dodge_until=0,pose='idle')
def motion(m,now):
    if m.get('rules',2)>=4:return boxing_cage.motion(m,now)
    players=m['players']
    for i,p in enumerate(players):
        if p.get('position') is None:p['position']=.35 if i==0 else .65
        dt=max(0,min(now,p.get('control_at',0)+.65)-max(m.get('motion_at',now),m.get('start') or now))
        p['position']=max(.12,min(.88,p['position']+p.get('move',0)*(.14 if i==0 else -.14)*dt))
    if len(players)==2 and players[1]['position']-players[0]['position']<.24:
        center=max(.24,min(.76,(players[0]['position']+players[1]['position'])/2))
        players[0]['position']=center-.12;players[1]['position']=center+.12
    m['motion_at']=now

def advance(m,now):
    if m['status'] in ['finished','declined','expired']:return
    if now-m['created']>1800 or (m['status']=='invited' and now-m['created']>120):m['status']='expired';return
    if m['status']=='countdown' and now>=m['start']:m['status']='active';m['round_start']=m['start']
    if m['status']=='round_break' and now>=m['next_round_at']:
        m.update(status='active',round=m['round']+1,round_start=m['next_round_at'],motion_at=now)
        m.pop('knockdown',None)
        for i,p in enumerate(m['players']):
            p.update(x=-.7 if i==0 else .7,z=0,slip=0,bend=0,side=0,side_since=None,hp=10,armor=10,position=.35 if i==0 else .65,move=0,crouch=0,arms=None,guard_since=None,guard_until=0,last_punch=0,last_hand=None,control_at=0)
    if m['status']=='active':
        motion(m,now)
        if m.get('rules',2)>=4:boxing_cage.resolve(m,now,knockout)
    if m['status'] in ['countdown','active','round_break']:
        gone=[p for p in m['players'] if now-p['seen']>20]
        if gone:finish(m,next((p['uid'] for p in m['players'] if p not in gone),None),'disconnect',now)

def finish(m,winner,result,now):
    if m['status']=='active':m['elapsed']=m.get('elapsed',0)+max(0,now-m.get('round_start',m.get('start') or now))
    m['pending_strikes']=[]
    m.update(status='finished',winner=winner,result=result,ended_at=now)
    if result not in ['best_of_three','knockout']:m.pop('knockdown',None)
    for p in m['players']:p.update(move=0,crouch=0,slip=0,bend=0,side=0,side_since=None,guard_until=0)

def knockout(m,winner,now):
    if m.get('rules',2)<3:finish(m,winner['uid'],'knockout',now);return
    duration=max(0,now-m['round_start']);m['elapsed']=m.get('elapsed',0)+duration
    winner['wins']=winner.get('wins',0)+1
    m.setdefault('rounds',[]).append(dict(number=m['round'],winner=winner['uid'],duration=duration))
    m.update(status='round_break',round_winner=winner['uid'],round_ended_at=now,next_round_at=now+5)
    loser=next(p for p in m['players'] if p['uid']!=winner['uid'])
    m['knockdown']=dict(uid=loser['uid'],at=now,recover_at=None if winner['wins']>=2 else now+5)
    for p in m['players']:p.update(move=0,crouch=0,slip=0,bend=0,side=0,side_since=None,guard_until=0)
    if winner['wins']>=2:finish(m,winner['uid'],'best_of_three',now)

def award(db,m,now):
    if m.get('rules') not in [2,3,4] or m['status']!='finished' or not m.get('start') or now<m['start'] or len(m['players'])!=2:return
    winner=next((p for p in m['players'] if p['uid']==m.get('winner') and p.get('profile_id')),None)
    if winner:
        db.execute('INSERT OR IGNORE INTO boxing_trophies VALUES(?,?,?,?)',(m['id'],winner['uid'],winner['profile_id'],now));m['trophy_awarded']=True;m['belt_awarded']=True

def action(m,uid,data,now):
    p=next(p for p in m['players'] if p['uid']==uid);kind=data.get('action');p['seen']=now
    if kind=='heartbeat':return
    if kind=='leave':finish(m,next((v['uid'] for v in m['players'] if v['uid']!=uid),None),'leave',now);return
    if kind=='ready':
        if m['status']!='lobby':raise ValueError('Not in the lobby')
        p['ready']=True
        if all(v['ready'] for v in m['players']):m.update(status='countdown',start=now+5,round_start=now+5,motion_at=now+5)
        return
    if m['status']!='active':raise ValueError('Match not active')
    seq=data.get('seq')
    if type(seq)!=int or seq<1:raise ValueError('Invalid event sequence')
    if seq<=p['seq']:return
    if kind not in ['idle','control','left','right']:raise ValueError('Invalid action')
    slip=data.get('slip',0);bend=data.get('bend',0)
    if any(type(v) not in (int,float) or not math.isfinite(v) or not -1<=v<=1 for v in [slip,bend]):raise ValueError('Invalid body control')
    move=data.get('move',0);guard=data.get('guard',False);arms=data.get('arms');crouch=data.get('crouch',0);punch_type=data.get('punch_type','straight')
    if type(crouch) not in (int,float) or not math.isfinite(crouch) or not 0<=crouch<=1 or punch_type not in ['straight','hook','uppercut']:raise ValueError('Invalid posture')
    if type(move)!=int or move not in [-1,0,1] or type(guard)!=bool:raise ValueError('Invalid control')
    if arms is not None:
        if not isinstance(arms,dict) or set(arms)!={'left','right'}:raise ValueError('Invalid arms')
        for side in arms.values():
            if not isinstance(side,dict) or set(side)!={'upper','lower'}:raise ValueError('Invalid arms')
            for v in side.values():
                if not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1.01 for x in v):raise ValueError('Invalid vector')
    if now-p.get('control_at',0)>.7:p['guard_since']=None
    if m.get('rules',2)>=4:boxing_cage.control(p,slip,bend,now)
    p.update(seq=seq,pose=kind,move=move,control_at=now,arms=arms,crouch=crouch)
    if guard and kind=='control':
        if p.get('guard_since') is None:p['guard_since']=now
        p['guard_until']=now+.65 if now-p['guard_since']>=3 else 0
    else:p['guard_since']=None;p['guard_until']=0
    if kind not in ['left','right']:return
    token=data.get('strike_id')
    if m.get('rules',2)>=4:
        if not isinstance(token,str) or not 1<=len(token)<=100:raise ValueError('Invalid strike ID')
        if token in p.get('strike_ids',[]):return
    if now-p['last_punch']<.4:return
    if m.get('rules',2)>=4:p['strike_ids']=(p.get('strike_ids',[])+[token])[-64:]
    p['last_punch']=now;p['last_hand']=kind;p['punch_type']=punch_type;q=next(v for v in m['players'] if v['uid']!=uid);hit='hit'
    if m.get('rules',2)>=4:
        boxing_cage.queue(m,p,q,kind,punch_type,now,token);return
    if abs(q.get('position',.65)-p.get('position',.35))>.44:hit='miss'
    elif q['guard_until']>now and q['armor']>0:q['armor']-=1;hit='block'
    else:q['hp']=max(0,q['hp']-p['damage'][kind])
    m['event']=dict(id=uuid.uuid4().hex,attacker=uid,target=q['uid'],hand=kind,punch_type=punch_type,result=hit,time=now,damage=p['damage'][kind])
    m['events']=(m.get('events',[])+[m['event']])[-12:]
    if q['hp']==0:knockout(m,p,now)

def register(app,get_store):
    bp=Blueprint('boxing',__name__)
    @bp.before_request
    def guard():
        if not getattr(g,'account',None):return jsonify(error='Sign in'),401
        schema(get_store())
    @bp.get('/social/boxing/belts/<int:pid>')
    @bp.get('/social/boxing/trophies/<int:pid>')
    def trophies(pid):
        with get_store().connect() as db:
            if not db.execute('SELECT 1 FROM profile_owners WHERE profile_id=? AND owner=?',(pid,'account:'+str(g.account['id']))).fetchone():return jsonify(error='Profile not found'),404
            # Keep the historical ledger so existing victories remain owned; the old route is compatible.
            count=db.execute('SELECT COUNT(*) FROM boxing_trophies WHERE profile_id=? AND account_id=?',(pid,g.account['id'])).fetchone()[0]
            return jsonify(belts=count,trophies=count)
    @bp.get('/social/boxing')
    def listing():
        store=get_store();uid=g.account['id'];now=clock();rows=[]
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for r in db.execute('SELECT * FROM boxing_matches WHERE (host=? OR guest=?) AND updated>? ORDER BY updated DESC LIMIT 20',(uid,uid,now-1800)).fetchall():
                m=json.loads(r['state']);advance(m,now);award(db,m,now);db.execute('UPDATE boxing_matches SET state=? WHERE id=?',(json.dumps(m),r['id']))
                if m['status'] not in ['finished','declined','expired']:rows.append(m)
        return jsonify(matches=rows,me=uid,now=now)
    @bp.post('/social/boxing/invite')
    def invite():
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):return jsonify(error='Invalid invitation'),400
        store=get_store();uid=g.account['id'];guest=data.get('friend');pid=data.get('profile');now=clock()
        if type(guest)!=int or type(pid)!=int or guest==uid:return jsonify(error='Invalid invitation'),400
        try:p=fighter(store,uid,pid)
        except ValueError as e:return jsonify(error=str(e)),400
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute("SELECT 1 FROM friend_requests WHERE status='accepted' AND ((sender=? AND receiver=?) OR (sender=? AND receiver=?))",(uid,guest,guest,uid)).fetchone():return jsonify(error='Accepted friends only'),403
            if db.execute("SELECT 1 FROM boxing_matches WHERE host=? AND json_extract(state,'$.created')>?",(uid,now-5)).fetchone():return jsonify(error='Please wait before inviting again'),429
            for r in db.execute('SELECT state FROM boxing_matches WHERE (host IN (?,?) OR guest IN (?,?)) AND updated>?',(uid,guest,uid,guest,now-1800)):
                old=json.loads(r[0]);advance(old,now)
                if old['status'] not in ['finished','declined','expired']:return jsonify(error='Finish or leave your existing match first'),409
            mid=uuid.uuid4().hex;m=dict(rules=MATCH_RULES,round=1,rounds=[],elapsed=0,id=mid,host=uid,guest=guest,created=now,status='invited',players=[p],start=None,event=None)
            db.execute('INSERT INTO boxing_matches VALUES(?,?,?,?,?)',(mid,uid,guest,json.dumps(m),now))
            db.execute('INSERT INTO friend_messages(sender,receiver,body,client_id,created) VALUES(?,?,?,?,?)',(uid,guest,'🥊 ชวนเล่น Boxing / Boxing invitation\n#boxing:'+mid,'boxing:'+mid,now))
        return jsonify(m)
    @bp.route('/social/boxing/<mid>',methods=['GET','POST'])
    def match(mid):
        store=get_store();uid=g.account['id'];now=clock();data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):return jsonify(error='Invalid action'),400
        new=None
        if request.method=='POST' and data.get('action')=='accept':
            if type(data.get('profile'))!=int:return jsonify(error='Choose profile'),400
            try:new=fighter(store,uid,data['profile'])
            except ValueError as e:return jsonify(error=str(e)),400
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM boxing_matches WHERE id=? AND (host=? OR guest=?)',(mid,uid,uid)).fetchone()
            if not row:return jsonify(error='Match not found'),404
            m=json.loads(row['state']);advance(m,now)
            if request.method=='POST':
                if data.get('action') in ['accept','decline']:
                    if uid!=m['guest'] or m['status']!='invited':return jsonify(error='Invitation unavailable'),409
                    if new:m['players'].append(new);m['status']='lobby';m['players'][0]['seen']=now
                    else:m['status']='declined'
                elif m['status'] not in ['finished','declined','expired']:
                    if not any(p['uid']==uid for p in m['players']):return jsonify(error='Accept invitation first'),409
                    try:action(m,uid,data,now)
                    except ValueError as e:return jsonify(error=str(e)),400
            award(db,m,now)
            db.execute('UPDATE boxing_matches SET state=?,updated=? WHERE id=?',(json.dumps(m),now,mid))
        return jsonify(match=m,me=uid,now=now)
    app.register_blueprint(bp)
