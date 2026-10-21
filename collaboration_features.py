"""Authenticated friend chat, coarse presence and persistent administrator maintenance."""
import time,uuid
from flask import Blueprint,request,jsonify,g
import accounts,community

def schema(store):
    community.schema(store)
    with store.lock,store.connect() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS user_presence(account_id INTEGER PRIMARY KEY,last_seen REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS friend_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,sender INTEGER NOT NULL,receiver INTEGER NOT NULL,body TEXT NOT NULL,client_id TEXT NOT NULL,created REAL NOT NULL,UNIQUE(sender,client_id));
        CREATE INDEX IF NOT EXISTS friend_messages_pair ON friend_messages(sender,receiver,id);
        CREATE TABLE IF NOT EXISTS website_settings(id INTEGER PRIMARY KEY CHECK(id=1),maintenance INTEGER NOT NULL DEFAULT 0);
        INSERT OR IGNORE INTO website_settings VALUES(1,0);''')

def online(store,uid):
    with store.lock,store.connect() as db:
        try:r=db.execute('SELECT last_seen FROM user_presence WHERE account_id=?',(uid,)).fetchone()
        except Exception:return False
    return bool(r and time.time()-r[0]<75)

def is_closed(store):
    schema(store)
    with store.lock,store.connect() as db:return bool(db.execute('SELECT maintenance FROM website_settings WHERE id=1').fetchone()[0])

def register(app,get_store,get_sessions,public_url):
    bp=Blueprint('collaboration_features',__name__)
    @app.before_request
    def maintenance_guard():
        # Leave login/admin accessible: the operator must be able to reopen the site.
        if request.path in ('/start','/cardio/start','/plans/today/start') or request.path.startswith('/social/chat/'):
            if is_closed(get_store()) and not community.is_admin(get_store(),getattr(g,'account',None)):
                return jsonify(error='เว็บกำลังปรับปรุง กรุณากลับมาใหม่ / Site maintenance; please try later',maintenance=True),503
    @app.get('/site/status')
    def site_status():return jsonify(maintenance=is_closed(get_store()))
    @bp.post('/social/presence')
    def presence():
        store=get_store();schema(store)
        if not getattr(g,'account',None):return jsonify(error='Sign in first'),401
        with store.lock,store.connect() as db:
            db.execute('INSERT INTO user_presence VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET last_seen=excluded.last_seen',(g.account['id'],time.time()))
        return jsonify(ok=True)
    @bp.route('/social/chat/<int:uid>',methods=['GET','POST'])
    def chat(uid):
        store=get_store();schema(store);me=getattr(g,'account',None)
        if not me:return jsonify(error='Sign in first'),401
        sender=me['id']
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute("SELECT 1 FROM friend_requests WHERE status='accepted' AND ((sender=? AND receiver=?) OR (sender=? AND receiver=?))",(sender,uid,uid,sender)).fetchone():return jsonify(error='แชตได้เฉพาะเพื่อนที่ตอบรับแล้ว / Accepted friends only'),403
            if request.method=='POST':
                data=request.get_json(silent=True)
                if not isinstance(data,dict):return jsonify(error='Invalid message'),400
                text=data.get('body');key=data.get('client_id')
                if not isinstance(text,str) or not 1<=len(text.strip())<=2000 or not isinstance(key,str) or not 16<=len(key)<=80:return jsonify(error='Message must be 1–2000 characters'),400
                old=db.execute('SELECT receiver,body FROM friend_messages WHERE sender=? AND client_id=?',(sender,key)).fetchone()
                if old and (old['receiver']!=uid or old['body']!=text.strip()):return jsonify(error='Message ID conflict'),409
                if not old:
                    if db.execute('SELECT COUNT(*) FROM friend_messages WHERE sender=? AND created>?',(sender,time.time()-60)).fetchone()[0]>=30:return jsonify(error='ส่งถี่เกินไป รอสักครู่ / Please slow down'),429
                    db.execute('INSERT INTO friend_messages(sender,receiver,body,client_id,created) VALUES(?,?,?,?,?)',(sender,uid,text.strip(),key,time.time()))
            try:before=max(0,int(request.args.get('before','0')))
            except ValueError:return jsonify(error='Invalid cursor'),400
            rows=[dict(r) for r in db.execute('SELECT id,sender,receiver,body,created FROM friend_messages WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND (?=0 OR id<?) ORDER BY id DESC LIMIT 60',(sender,uid,uid,sender,before,before))]
        return jsonify(messages=list(reversed(rows)),me=sender,online=online(store,uid),older_before=rows[-1]['id'] if len(rows)==60 else None)
    @bp.route('/admin/site',methods=['GET','POST'])
    def admin_site():
        store=get_store();schema(store)
        if not community.is_admin(store,getattr(g,'account',None)):return jsonify(error='Administrators only'),403
        registry=get_sessions()
        with registry.lock:
            active=sum(bool(x['coach'].state['running']) for x in registry.items.values())
            if request.method=='POST':
                data=request.get_json(silent=True)
                if not isinstance(data,dict) or type(data.get('maintenance')) is not bool:return jsonify(error='Invalid maintenance value'),400
                if data['maintenance'] and active:return jsonify(error='ยังมีคนเปิดกล้องอยู่ ให้หยุดและบันทึกเซตก่อน / Stop active cameras before maintenance',active_cameras=active),409
                with store.lock,store.connect() as db:
                    db.execute('UPDATE website_settings SET maintenance=? WHERE id=1',(int(data['maintenance']),))
                    db.execute('INSERT INTO admin_audit VALUES(?,?,?,?,?)',(str(uuid.uuid4()),g.account['id'],'maintenance',str(data['maintenance']),time.time()))
            return jsonify(maintenance=is_closed(store),active_cameras=active,sessions=len(registry.items),permanent_url=public_url() or None)
    app.register_blueprint(bp)
