"""Profile-owned bag-training HP, with idempotent batches and a shared pace budget."""
import math,uuid
from flask import g,request,jsonify
BASE_HP=10
HP_PER_LEVEL=2
FIRST_GOAL=10
MAX_HITS=2**52-1
HIT_INTERVAL=.25
BURST=4


def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS boxing_training_stats(account_id INTEGER NOT NULL,profile_id INTEGER NOT NULL,total_hits INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(account_id,profile_id))')
    db.execute('CREATE TABLE IF NOT EXISTS boxing_training_sessions(account_id INTEGER PRIMARY KEY,profile_id INTEGER NOT NULL,token TEXT NOT NULL,seen REAL NOT NULL,credit REAL NOT NULL,credit_at REAL NOT NULL,last_seq INTEGER NOT NULL)')


def progress(total=0):
    total=max(0,min(MAX_HITS,int(total)))
    level=(total//FIRST_GOAL+1).bit_length()-1
    floor=FIRST_GOAL*(2**level-1);goal=FIRST_GOAL*2**level
    return dict(total_hits=total,level=level,max_hp=BASE_HP+HP_PER_LEVEL*level,
                progress_hits=total-floor,next_goal=goal,hits_to_next=goal-(total-floor),hp_per_level=HP_PER_LEVEL)


def owned(db,uid,pid):
    return bool(db.execute('SELECT 1 FROM profile_owners WHERE owner=? AND profile_id=?',('account:'+str(uid),pid)).fetchone())


def read(db,uid,pid):
    row=db.execute('SELECT total_hits FROM boxing_training_stats WHERE account_id=? AND profile_id=?',(uid,pid)).fetchone()
    return progress(row[0] if row else 0)


def register(bp,get_store,clock):
    @bp.get('/social/boxing/training/<int:pid>')
    def training_status(pid):
        uid=g.account['id']
        with get_store().connect() as db:
            if not owned(db,uid,pid):return jsonify(error='Profile not found'),404
            return jsonify(read(db,uid,pid))

    @bp.post('/social/boxing/training/<int:pid>/start')
    def start(pid):
        store=get_store();uid=g.account['id'];now=clock()
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not owned(db,uid,pid):return jsonify(error='Profile not found'),404
            row=db.execute('SELECT * FROM boxing_training_sessions WHERE account_id=?',(uid,)).fetchone()
            # Starting again or opening another tab never resets the shared pace budget.
            credit=min(BURST,row['credit']+max(0,now-row['credit_at'])/HIT_INTERVAL) if row else 1
            token=uuid.uuid4().hex
            db.execute('INSERT INTO boxing_training_sessions VALUES(?,?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET profile_id=excluded.profile_id,token=excluded.token,seen=excluded.seen,credit=excluded.credit,credit_at=excluded.credit_at,last_seq=0',(uid,pid,token,now,credit,now,0))
            return jsonify(token=token,progress=read(db,uid,pid))

    @bp.post('/social/boxing/training/<int:pid>/hits')
    def hits(pid):
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or not isinstance(data.get('token'),str) or not isinstance(data.get('events'),list) or not 1<=len(data['events'])<=16:return jsonify(error='Invalid training batch'),400
        events=data['events']
        for e in events:
            if not isinstance(e,dict) or type(e.get('seq'))!=int or not 1<=e['seq']<=MAX_HITS or e.get('hand') not in ('left','right') or e.get('kind') not in ('straight','hook','uppercut') or type(e.get('distance')) not in (int,float) or not math.isfinite(e['distance']) or not .70<=e['distance']<=1.65:return jsonify(error='Only punches that reach the bag count'),400
        if any(a['seq']>=b['seq'] for a,b in zip(events,events[1:])):return jsonify(error='Invalid event order'),400
        store=get_store();uid=g.account['id'];now=clock()
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not owned(db,uid,pid):return jsonify(error='Profile not found'),404
            row=db.execute('SELECT * FROM boxing_training_sessions WHERE account_id=?',(uid,)).fetchone()
            if not row or row['profile_id']!=pid or row['token']!=data['token'] or now-row['seen']>120:return jsonify(error='Training session ended. Start training again.'),409
            credit=min(BURST,row['credit']+max(0,now-row['credit_at'])/HIT_INTERVAL)
            new=[e for e in events if e['seq']>row['last_seq']]
            accepted=min(len(new),max(0,int(credit+1e-8)))
            # Acknowledged sequences are never credited twice, including after a lost response.
            last_seq=max(row['last_seq'],events[-1]['seq'])
            db.execute('UPDATE boxing_training_sessions SET credit=?,credit_at=?,seen=?,last_seq=? WHERE account_id=?',(credit-accepted,now,now,last_seq,uid))
            db.execute('INSERT INTO boxing_training_stats VALUES(?,?,?) ON CONFLICT(account_id,profile_id) DO UPDATE SET total_hits=MIN(?,total_hits+excluded.total_hits)',(uid,pid,accepted,MAX_HITS))
            return jsonify(progress=read(db,uid,pid),ack_seq=last_seq,accepted=accepted,limited=len(new)-accepted)
