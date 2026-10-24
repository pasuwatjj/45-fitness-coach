"""Account roles, administrator review and minimal public social profiles."""
import time
import uuid
from flask import Blueprint, request, jsonify, g, Response
import membership
import accounts
from sessions import owned_profiles


def schema(store):
    with store.lock, store.connect() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS account_roles(account_id INTEGER PRIMARY KEY,role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS friend_requests(sender INTEGER NOT NULL,receiver INTEGER NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(sender,receiver));
        CREATE TABLE IF NOT EXISTS admin_audit(id TEXT PRIMARY KEY,actor INTEGER NOT NULL,action TEXT NOT NULL,target TEXT NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS profile_sharing(profile_id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS admin_operations(id TEXT PRIMARY KEY,actor INTEGER NOT NULL,target INTEGER NOT NULL,days INTEGER NOT NULL);
        ''')


def is_admin(store, account):
    if not account:return False
    schema(store)
    with store.lock,store.connect() as db:
        return db.execute("SELECT 1 FROM account_roles WHERE account_id=? AND role='admin'",(account['id'],)).fetchone() is not None


def grant_admin(store,email):
    accounts.schema(store);schema(store)
    with store.lock,store.connect() as db:
        row=db.execute('SELECT id FROM accounts WHERE email=? COLLATE NOCASE',(email.strip(),)).fetchone()
        if not row:raise ValueError('Account not found. Sign in/create this account on your computer first, then run Setup-Admin.ps1 again.')
        db.execute("INSERT INTO account_roles VALUES(?,'admin') ON CONFLICT(account_id) DO UPDATE SET role='admin'",(row['id'],))
        db.execute('INSERT INTO admin_audit VALUES(?,?,?,?,?)',(str(uuid.uuid4()),row['id'],'local-admin-grant',str(row['id']),time.time()))


def register(app,get_store):
    bp=Blueprint('community',__name__)
    @bp.before_request
    def guard():
        if not getattr(g,'account',None):return jsonify(error='กรุณาเข้าสู่ระบบ / Please sign in'),401
        if request.path.startswith('/admin/') and not is_admin(get_store(),g.account):return jsonify(error='เฉพาะแอดมิน / Administrators only'),403
        if request.method=='POST' and not isinstance(request.get_json(silent=True),dict):return jsonify(error='Expected a JSON object'),400
        schema(get_store())

    def public_card(account_id):
        store=get_store();owner='account:'+str(account_id)
        with store.lock,store.connect() as db:
            if not db.execute('SELECT 1 FROM accounts WHERE id=?',(account_id,)).fetchone():return None
        profiles=owned_profiles(store,owner)
        from profile_data import get_avatar
        from collaboration_features import online
        return dict(online=online(store,account_id),id=account_id,name=profiles[0]['name'] if profiles else 'Player '+str(account_id),
                    vip=membership.active(store,owner),admin=is_admin(store,{'id':account_id}),
                    profiles=[dict(id=p['id'],name=p['name'],has_avatar=bool(get_avatar(store,p['id']))) for p in profiles])

    @bp.get('/social/me')
    def me():
        return jsonify(account_id=g.account['id'],admin=is_admin(get_store(),g.account),vip=membership.active(get_store(),g.account['owner']),online=True)

    @bp.get('/social/players')
    def players():
        q=request.args.get('q','').strip()[:50]
        with get_store().lock,get_store().connect() as db:
            ids=[r[0] for r in db.execute('''SELECT DISTINCT a.id FROM accounts a JOIN profile_owners o ON o.owner='account:'||a.id
                JOIN profiles p ON p.id=o.profile_id WHERE instr(lower(p.name),lower(?))>0 ORDER BY a.id LIMIT 50''',(q,))]
        return jsonify(players=[public_card(i) for i in ids if i!=g.account['id']])

    @bp.get('/social/players/<int:account_id>')
    def player(account_id):
        card=public_card(account_id)
        if not card:return jsonify(error='Player not found'),404
        store=get_store()
        for p in card['profiles']:
            _,p['shared_details']=sharing(p['id'])
            with store.lock,store.connect() as db:
                p['totals']=dict(db.execute('SELECT COUNT(*) AS sets,COALESCE(SUM(reps),0) AS reps FROM workout_sets WHERE profile_id=?',(p['id'],)).fetchone())
            from planner import today_thailand
            p['streak']=store.plan_month(p['id'],today_thailand().strftime('%Y-%m'))['streak']
        # Public profiles deliberately contain no email, health, receipts or login data.
        return jsonify(card)

    def sharing(pid):
        with get_store().connect() as db:
            owner=db.execute("SELECT owner FROM profile_owners WHERE profile_id=? AND owner LIKE 'account:%'",(pid,)).fetchone()
            row=db.execute('SELECT enabled FROM profile_sharing WHERE profile_id=?',(pid,)).fetchone()
        return owner, bool(row and row['enabled'])

    @bp.route('/social/sharing/<int:pid>',methods=['GET','POST'])
    def share_settings(pid):
        owner,enabled=sharing(pid)
        if not owner or owner['owner']!=g.account['owner']:return jsonify(error='Not found'),404
        if request.method=='POST':
            enabled=request.get_json().get('enabled')
            if type(enabled) is not bool:return jsonify(error='Invalid setting'),400
            with get_store().lock,get_store().connect() as db:
                db.execute('INSERT INTO profile_sharing VALUES(?,?) ON CONFLICT(profile_id) DO UPDATE SET enabled=excluded.enabled',(pid,int(enabled)))
        return jsonify(enabled=enabled)

    @bp.get('/social/characters/<int:pid>')
    def public_character(pid):
        from character import overview
        try:return jsonify(overview(get_store(),pid,False))
        except ValueError as error:return jsonify(error=str(error)),404

    @bp.get('/social/profiles/<int:pid>/<view>')
    def shared_profile(pid,view):
        owner,enabled=sharing(pid)
        if not owner:return jsonify(error='Not found'),404
        if not enabled and owner['owner']!=g.account['owner']:return jsonify(error='เจ้าของยังไม่ได้เปิดแชร์รายละเอียด / Owner has not shared detailed data'),403
        if view=='overview':
            from profile_data import overview
            data=overview(get_store(),pid)
        elif view=='progress':
            from progress_analysis import report
            data=report(get_store(),pid)
        elif view=='angles':
            from angles import history
            data=history(get_store(),pid,request.args.get('day'))
        else:return jsonify(error='Not found'),404
        response=jsonify(data);response.headers['Cache-Control']='private, no-store'
        return response

    @bp.get('/social/avatars/<int:profile_id>')
    def avatar(profile_id):
        with get_store().connect() as db:
            if not db.execute("SELECT 1 FROM profile_owners WHERE profile_id=? AND owner LIKE 'account:%'",(profile_id,)).fetchone():return jsonify(error='Not found'),404
        from profile_data import get_avatar
        raw=get_avatar(get_store(),profile_id)
        return Response(raw,mimetype='image/jpeg',headers={'Cache-Control':'private, no-store'}) if raw else ('',404)

    @bp.route('/social/friends',methods=['GET','POST'])
    def friends():
        store=get_store();uid=g.account['id']
        if request.method=='GET':
            with store.lock,store.connect() as db:
                rows=[dict(r) for r in db.execute('SELECT * FROM friend_requests WHERE sender=? OR receiver=? ORDER BY created DESC',(uid,uid))]
            return jsonify(requests=[dict(r,player=public_card(r['receiver'] if r['sender']==uid else r['sender']),incoming=r['receiver']==uid) for r in rows])
        data=request.get_json(silent=True) or {};target=data.get('account_id');action=data.get('action')
        if type(target) is not int or target==uid or action not in ('request','accept','remove'):return jsonify(error='Invalid friend request'),400
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM accounts WHERE id=?',(target,)).fetchone():return jsonify(error='Player not found'),404
            if action=='request':
                if not db.execute('SELECT 1 FROM friend_requests WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)',(uid,target,target,uid)).fetchone():
                    db.execute("INSERT INTO friend_requests VALUES(?,?,'pending',?)",(uid,target,time.time()))
            elif action=='accept':
                updated=db.execute("UPDATE friend_requests SET status='accepted' WHERE sender=? AND receiver=? AND status='pending'",(target,uid))
                if not updated.rowcount:return jsonify(error='No incoming request'),409
            else:db.execute('DELETE FROM friend_requests WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)',(uid,target,target,uid))
        return jsonify(ok=True)

    @bp.get('/admin/accounts')
    def all_accounts():
        store=get_store();q=request.args.get('q','').strip()[:254]
        try:page=max(1,int(request.args.get('page','1')))
        except ValueError:return jsonify(error='Invalid page'),400
        with store.lock,store.connect() as db:
            total=db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]
            matched=db.execute('SELECT COUNT(*) FROM accounts WHERE instr(lower(email),lower(?))>0',(q,)).fetchone()[0]
            rows=[dict(r) for r in db.execute('SELECT id,email,created_at FROM accounts WHERE instr(lower(email),lower(?))>0 ORDER BY id DESC LIMIT 50 OFFSET ?',(q,(page-1)*50))]
        for row in rows:
            row['profiles']=owned_profiles(store,'account:'+str(row['id']))
            row['membership']=membership.status(store,'account:'+str(row['id']))
            row['admin']=is_admin(store,row)
        return jsonify(accounts=rows,total=total,matched=matched,page=page,pages=max(1,(matched+49)//50))

    @bp.get('/admin/profiles/<int:pid>')
    def admin_profile(pid):
        from profile_data import overview
        if not get_store().profile(pid):return jsonify(error='Profile not found'),404
        return jsonify(overview(get_store(),pid))

    @bp.post('/admin/accounts/<int:uid>/vip')
    def grant_vip(uid):
        data=request.get_json(silent=True) or {};days=data.get('days',30);op=data.get('operation_id','')
        if type(days) is not int or not 1<=days<=365 or not isinstance(op,str) or len(op)<16 or len(op)>80:return jsonify(error='Use 1–365 days and an operation ID'),400
        store=get_store();owner='account:'+str(uid)
        with store.lock,store.connect() as db:
            membership.schema(db);db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM accounts WHERE id=?',(uid,)).fetchone():return jsonify(error='Account not found'),404
            oldop=db.execute('SELECT * FROM admin_operations WHERE id=?',(op,)).fetchone()
            if oldop:
                if (oldop['actor'],oldop['target'],oldop['days'])!=(g.account['id'],uid,days):return jsonify(error='Operation conflict'),409
            else:
                old=db.execute('SELECT expires FROM vip_memberships WHERE owner=?',(owner,)).fetchone()
                expiry=max(time.time(),old['expires'] if old else 0)+days*86400
                db.execute('INSERT INTO vip_memberships VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET expires=excluded.expires',(owner,expiry))
                db.execute('INSERT INTO admin_operations VALUES(?,?,?,?)',(op,g.account['id'],uid,days))
                db.execute('INSERT INTO admin_audit VALUES(?,?,?,?,?)',(str(uuid.uuid4()),g.account['id'],'grant-vip-'+str(days),owner,time.time()))
        return jsonify(ok=True,membership=membership.status(store,owner))

    @bp.get('/admin/receipts')
    def receipts():
        store=get_store()
        with store.lock,store.connect() as db:
            membership.schema(db)
            rows=[dict(r) for r in db.execute('SELECT id,email,status,created,result FROM vip_receipts ORDER BY created DESC LIMIT 100')]
        return jsonify(receipts=rows)

    @bp.get('/admin/receipts/<rid>/image')
    def receipt_image(rid):
        with get_store().connect() as db:row=db.execute('SELECT image FROM vip_receipts WHERE id=?',(rid,)).fetchone()
        return Response(bytes(row['image']),mimetype='image/jpeg',headers={'Cache-Control':'private, no-store'}) if row else ('',404)

    @bp.post('/admin/receipts/<rid>/approve')
    def approve(rid):
        data=request.get_json(silent=True) or {}
        if data.get('confirmed_bank_transfer') is not True:return jsonify(error='ตรวจยอดเงินจริงในบัญชีก่อน / Confirm actual bank transfer first'),400
        try:membership.approve_manual(get_store(),rid,data.get('transaction'),data.get('amount'),data.get('receiver'))
        except ValueError as e:return jsonify(error=str(e)),400
        with get_store().lock,get_store().connect() as db:db.execute('INSERT INTO admin_audit VALUES(?,?,?,?,?)',(str(uuid.uuid4()),g.account['id'],'approve-receipt',rid,time.time()))
        return jsonify(ok=True)

    app.register_blueprint(bp)
