"""Administrator operations. All mutations and their audit share one transaction."""
import json, time, uuid
from flask import request, jsonify, g
import training_economy as economy
MAX_BALANCE=9007199254740991

def schema(db):
    economy.schema(db)
    db.executescript('''CREATE TABLE IF NOT EXISTS account_bans(account_id INTEGER PRIMARY KEY,banned INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS management_audit(id TEXT PRIMARY KEY,actor INTEGER NOT NULL,actor_email TEXT NOT NULL,target INTEGER NOT NULL,target_email TEXT NOT NULL,profile INTEGER,profile_name TEXT,action TEXT NOT NULL,currency TEXT,amount INTEGER,before_value INTEGER,after_value INTEGER,reason TEXT NOT NULL,created REAL NOT NULL,signature TEXT NOT NULL);''')

def admin(db,actor):
    if not db.execute("SELECT 1 FROM accounts a JOIN account_roles r ON r.account_id=a.id WHERE a.id=? AND r.role='admin' AND NOT EXISTS(SELECT 1 FROM account_bans b WHERE b.account_id=a.id AND b.banned=1)",(actor,)).fetchone():raise PermissionError('Administrators only / เฉพาะแอดมิน')

def mutate(store,actor,target,data,action):
    if type(target) is not int or not 1<=target<=MAX_BALANCE:raise ValueError('Invalid account / บัญชีไม่ถูกต้อง')
    if not isinstance(data,dict):raise ValueError('Invalid request / คำขอไม่ถูกต้อง')
    key=data.get('request_id');reason=data.get('reason')
    if not isinstance(key,str) or len(key)!=36:raise ValueError('Invalid request ID / รหัสคำขอไม่ถูกต้อง')
    try:key=str(uuid.UUID(key))
    except ValueError:raise ValueError('Invalid request ID / รหัสคำขอไม่ถูกต้อง')
    if not isinstance(reason,str) or not reason.strip() or len(reason)>500:raise ValueError('Reason required (1–500 characters) / ระบุเหตุผล 1–500 ตัวอักษร')
    payload=dict(action=action,target=target,reason=reason.strip());pid=None;currency=None;amount=None
    if action=='coins':
        pid=data.get('target_profile_id');currency=data.get('currency');amount=data.get('amount')
        if type(pid) is not int or not 1<=pid<=MAX_BALANCE:raise ValueError('Invalid profile / โปรไฟล์ไม่ถูกต้อง')
        if not isinstance(currency,str) or currency not in economy.CURRENCIES:raise ValueError('Invalid currency / ชนิดเหรียญไม่ถูกต้อง')
        if type(amount) is not int or not 1<=abs(amount)<=1000000:raise ValueError('Amount must be ±1–1,000,000 / จำนวนต้องเป็น ±1–1,000,000')
        payload.update(profile=pid,currency=currency,amount=amount)
    else:
        if type(data.get('banned')) is not bool:raise ValueError('Invalid ban state / สถานะระงับไม่ถูกต้อง')
        payload['banned']=data['banned']
    signature=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE');admin(db,actor)
        account=db.execute('SELECT email FROM accounts WHERE id=?',(target,)).fetchone()
        if not account:raise ValueError('Account not found / ไม่พบบัญชี')
        old=db.execute('SELECT * FROM management_audit WHERE id=?',(key,)).fetchone()
        if old:
            if old['actor']!=actor or old['signature']!=signature:raise FileExistsError('Request conflict / รหัสคำขอซ้ำกับข้อมูลอื่น')
            return dict(audit=dict(old),replayed=True)
        profile=None
        if action=='coins':
            profile=db.execute("SELECT p.name FROM profiles p JOIN profile_owners o ON o.profile_id=p.id WHERE p.id=? AND o.owner=?",(pid,'account:'+str(target))).fetchone()
            if not profile:raise ValueError('Profile does not belong to account / โปรไฟล์ไม่ใช่ของบัญชีนี้')
            before=economy.balance(db,pid)[currency];after=before+amount
            if not 0<=after<=MAX_BALANCE:raise ValueError('Insufficient coins or balance limit / เหรียญไม่พอหรือเกินขีดจำกัด')
            db.execute('INSERT INTO training_ledger VALUES(?,?,?,?,?,?)',('admin:'+key,pid,currency,amount,'admin_adjustment',time.time()))
        else:
            banned=payload['banned']
            if banned and target==actor:raise ValueError('Cannot ban yourself / ระงับตนเองไม่ได้')
            if banned and db.execute("SELECT 1 FROM account_roles WHERE account_id=? AND role='admin'",(target,)).fetchone():
                if db.execute("SELECT COUNT(*) FROM account_roles r JOIN accounts a ON a.id=r.account_id WHERE r.role='admin' AND NOT EXISTS(SELECT 1 FROM account_bans b WHERE b.account_id=a.id AND b.banned=1)").fetchone()[0]<=1:raise ValueError('Cannot ban last administrator / ระงับแอดมินคนสุดท้ายไม่ได้')
            row=db.execute('SELECT banned FROM account_bans WHERE account_id=?',(target,)).fetchone();before=row[0] if row else 0;after=int(banned)
            db.execute('INSERT INTO account_bans VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET banned=excluded.banned',(target,after))
        actor_email=db.execute('SELECT email FROM accounts WHERE id=?',(actor,)).fetchone()[0]
        db.execute('INSERT INTO management_audit VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,actor,actor_email,target,account['email'],pid,profile['name'] if profile else None,action,currency,amount,before,after,payload['reason'],time.time(),signature))
        result=dict(db.execute('SELECT * FROM management_audit WHERE id=?',(key,)).fetchone())
    return dict(audit=result,replayed=False)

def register(bp,get_store):
    @bp.post('/admin/accounts/<int:uid>/coins')
    @bp.post('/admin/accounts/<int:uid>/ban')
    def management_change(uid):
        try:return jsonify(mutate(get_store(),g.account['id'],uid,request.get_json(),request.path.rsplit('/',1)[1]))
        except PermissionError as e:return jsonify(error=str(e)),403
        except FileExistsError as e:return jsonify(error=str(e)),409
        except ValueError as e:return jsonify(error=str(e)),400
    @bp.get('/admin/accounts/<int:uid>/wallets')
    def wallets(uid):
        if not 1<=uid<=MAX_BALANCE:return jsonify(error='Invalid account / บัญชีไม่ถูกต้อง'),400
        with get_store().lock,get_store().connect() as db:
            schema(db);admin(db,g.account['id'])
            rows=[dict(id=r['id'],name=r['name'],wallet=economy.balance(db,r['id'])) for r in db.execute('SELECT p.id,p.name FROM profiles p JOIN profile_owners o ON o.profile_id=p.id WHERE o.owner=?',('account:'+str(uid),))]
            ban=db.execute('SELECT banned FROM account_bans WHERE account_id=?',(uid,)).fetchone()
        return jsonify(profiles=rows,banned=bool(ban and ban[0]))
    @bp.get('/admin/management-history')
    def history():
        try:page=int(request.args.get('page','1'));assert 1<=page<=1000000
        except (ValueError,AssertionError):return jsonify(error='Invalid page'),400
        with get_store().lock,get_store().connect() as db:
            schema(db);admin(db,g.account['id'])
            rows=[dict(r) for r in db.execute('SELECT * FROM management_audit ORDER BY created DESC,id DESC LIMIT 50 OFFSET ?',((page-1)*50,))]
        return jsonify(history=rows,page=page)
    @bp.get('/admin/exchange-history')
    def exchanges():
        try:page=int(request.args.get('page','1'));assert 1<=page<=1000000
        except (ValueError,AssertionError):return jsonify(error='Invalid page'),400
        with get_store().lock,get_store().connect() as db:
            schema(db);admin(db,g.account['id'])
            rows=[dict(r) for r in db.execute("""SELECT o.id,o.owner,o.profile_id,p.name,a.email,l.currency,-l.amount AS spent,u.amount AS received,l.created FROM training_operations o JOIN training_ledger l ON l.id=o.id||':'||l.currency AND l.kind='exchange' AND l.amount<0 JOIN training_ledger u ON u.id=o.id||':universal' AND u.kind='exchange' JOIN profiles p ON p.id=o.profile_id LEFT JOIN accounts a ON o.owner='account:'||a.id ORDER BY l.created DESC,o.id DESC LIMIT 50 OFFSET ?""",((page-1)*50,))]
        return jsonify(history=rows,page=page)
