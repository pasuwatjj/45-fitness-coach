"""Private casual boxing matches. No images/landmarks leave the browser."""
import json,time,uuid,math
from flask import Blueprint,g,request,jsonify
import character,collaboration_features

def clock():return time.time()
def schema(store):
    collaboration_features.schema(store)
    with store.lock,store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS boxing_trophies(match_id TEXT PRIMARY KEY,account_id INTEGER NOT NULL,profile_id INTEGER NOT NULL,created REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS boxing_matches(id TEXT PRIMARY KEY,host INTEGER NOT NULL,guest INTEGER NOT NULL,state TEXT NOT NULL,updated REAL NOT NULL)')
def fighter(store,uid,pid):
    with store.connect() as db:
        if not db.execute('SELECT 1 FROM profile_owners WHERE owner=? AND profile_id=?',('account:'+str(uid),pid)).fetchone():raise ValueError('เลือกโปรไฟล์ของคุณ / Choose your own profile')
    model=character.overview(store,pid)
    if not model['created']:raise ValueError('สร้างตัวละครในโปรไฟล์ก่อน / Save your avatar first')
    return dict(profile_id=pid,position=None,move=0,control_at=0,guard_since=None,arms=None,uid=uid,name=model['profile']['name'],model={k:model[k] for k in ['appearance','growth','visual']},damage={s:model['growth']['arm_parts'][s]['level'] for s in ['left','right']},hp=10,armor=10,ready=False,seen=clock(),seq=0,last_punch=0,last_dodge=0,guard_until=0,dodge_until=0,pose='idle')
def motion(m,now):
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
    if m['status']=='countdown' and now>=m['start']:m['status']='active'
    if m['status']=='active':motion(m,now)
    if m['status'] in ['countdown','active']:
        gone=[p for p in m['players'] if now-p['seen']>20]
        if gone:m.update(status='finished',winner=next((p['uid'] for p in m['players'] if p not in gone),None),result='disconnect')

def award(db,m,now):
    if m.get('rules')!=2 or m['status']!='finished' or not m.get('start') or now<m['start'] or len(m['players'])!=2:return
    winner=next((p for p in m['players'] if p['uid']==m.get('winner') and p.get('profile_id')),None)
    if winner:
        db.execute('INSERT OR IGNORE INTO boxing_trophies VALUES(?,?,?,?)',(m['id'],winner['uid'],winner['profile_id'],now));m['trophy_awarded']=True

def action(m,uid,data,now):
    p=next(p for p in m['players'] if p['uid']==uid);kind=data.get('action');p['seen']=now
    if kind=='heartbeat':return
    if kind=='leave':m.update(status='finished',winner=next((v['uid'] for v in m['players'] if v['uid']!=uid),None),result='leave');return
    if kind=='ready':
        if m['status']!='lobby':raise ValueError('ยังไม่อยู่ในห้องเตรียมพร้อม')
        p['ready']=True
        if all(v['ready'] for v in m['players']):m.update(status='countdown',start=now+5,motion_at=now+5)
        return
    if m['status']!='active':raise ValueError('แมตช์ยังไม่เริ่ม / Match not active')
    seq=data.get('seq')
    if type(seq)!=int or seq<1:raise ValueError('Invalid event sequence')
    if seq<=p['seq']:return
    if kind not in ['idle','control','left','right']:raise ValueError('Invalid action')
    move=data.get('move',0);guard=data.get('guard',False);arms=data.get('arms')
    if type(move)!=int or move not in [-1,0,1] or type(guard)!=bool:raise ValueError('Invalid control')
    if arms is not None:
        if not isinstance(arms,dict) or set(arms)!={'left','right'}:raise ValueError('Invalid arms')
        for side in arms.values():
            if not isinstance(side,dict) or set(side)!={'upper','lower'}:raise ValueError('Invalid arms')
            for v in side.values():
                if not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1.01 for x in v):raise ValueError('Invalid vector')
    if now-p.get('control_at',0)>.7:p['guard_since']=None
    p.update(seq=seq,pose=kind,move=move,control_at=now,arms=arms)
    if guard and kind=='control':
        if p.get('guard_since') is None:p['guard_since']=now
        p['guard_until']=now+.65 if now-p['guard_since']>=3 else 0
    else:p['guard_since']=None;p['guard_until']=0
    if kind not in ['left','right']:return
    if now-p['last_punch']<.4:return
    p['last_punch']=now;p['last_hand']=kind;q=next(v for v in m['players'] if v['uid']!=uid);hit='hit'
    if abs(q.get('position',.65)-p.get('position',.35))>.44:hit='miss'
    elif q['guard_until']>now and q['armor']>0:q['armor']-=1;hit='block'
    else:q['hp']=max(0,q['hp']-p['damage'][kind])
    m['event']=dict(id=uuid.uuid4().hex,attacker=uid,target=q['uid'],hand=kind,result=hit,time=now,damage=p['damage'][kind])
    m['events']=(m.get('events',[])+[m['event']])[-12:]
    if q['hp']==0:m.update(status='finished',winner=uid,result='knockout')

def register(app,get_store):
    bp=Blueprint('boxing',__name__)
    @bp.before_request
    def guard():
        if not getattr(g,'account',None):return jsonify(error='กรุณาเข้าสู่ระบบ / Sign in'),401
        schema(get_store())
    @bp.get('/social/boxing/trophies/<int:pid>')
    def trophies(pid):
        with get_store().connect() as db:
            if not db.execute('SELECT 1 FROM profile_owners WHERE profile_id=? AND owner=?',(pid,'account:'+str(g.account['id']))).fetchone():return jsonify(error='Profile not found'),404
            return jsonify(trophies=db.execute('SELECT COUNT(*) FROM boxing_trophies WHERE profile_id=? AND account_id=?',(pid,g.account['id'])).fetchone()[0])
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
            if db.execute("SELECT 1 FROM boxing_matches WHERE host=? AND json_extract(state,'$.created')>?",(uid,now-5)).fetchone():return jsonify(error='รอสักครู่ก่อนชวนอีกครั้ง'),429
            for r in db.execute('SELECT state FROM boxing_matches WHERE (host IN (?,?) OR guest IN (?,?)) AND updated>?',(uid,guest,uid,guest,now-1800)):
                old=json.loads(r[0]);advance(old,now)
                if old['status'] not in ['finished','declined','expired']:return jsonify(error='มีแมตช์อยู่แล้ว กรุณาจบหรือออกจากห้องเดิมก่อน'),409
            mid=uuid.uuid4().hex;m=dict(rules=2,id=mid,host=uid,guest=guest,created=now,status='invited',players=[p],start=None,event=None)
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
