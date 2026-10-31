"""Private inbox and durable account-level weekly workout reminders.
Only additive tables. Due messages materialize on inbox access; no push service required.
"""
import json,re,time
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from flask import Blueprint,g,request,jsonify
import collaboration_features


def clock():return time.time()

def schema(store):
    collaboration_features.schema(store)
    with store.lock,store.connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS workout_reminders(account_id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL,timezone TEXT NOT NULL,days TEXT NOT NULL,effective_at REAL NOT NULL,checked_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS inbox_system_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,account_id INTEGER NOT NULL,local_day TEXT NOT NULL,scheduled REAL NOT NULL,timezone TEXT NOT NULL,body TEXT NOT NULL,UNIQUE(account_id,local_day));
        CREATE INDEX IF NOT EXISTS inbox_system_owner ON inbox_system_messages(account_id,id);
        CREATE TABLE IF NOT EXISTS inbox_read_cursors(account_id INTEGER NOT NULL,thread TEXT NOT NULL,last_id INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(account_id,thread));
        ''')

def defaults():return dict(enabled=False,timezone='Asia/Bangkok',days=[dict(day=i,enabled=True,time='18:00') for i in range(7)])

def validate(data):
    if not isinstance(data,dict) or type(data.get('enabled')) is not bool:raise ValueError('Invalid reminder settings')
    zone=data.get('timezone')
    if not isinstance(zone,str) or len(zone)>80:raise ValueError('Invalid time zone')
    try:ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError):raise ValueError('Unknown time zone')
    days=data.get('days')
    if not isinstance(days,list) or len(days)!=7:raise ValueError('Choose all seven days')
    result=[]
    for index,row in enumerate(days):
        if not isinstance(row,dict) or type(row.get('day')) is not int or row['day']!=index or type(row.get('enabled')) is not bool or not isinstance(row.get('time'),str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',row['time']):raise ValueError('Invalid day or time')
        result.append(dict(day=index,enabled=row['enabled'],time=row['time']))
    return dict(enabled=data['enabled'],timezone=zone,days=result)

def preference(db,uid):
    row=db.execute('SELECT * FROM workout_reminders WHERE account_id=?',(uid,)).fetchone()
    return dict(enabled=bool(row['enabled']),timezone=row['timezone'],days=json.loads(row['days'])) if row else defaults()

def materialize(db,uid,now):
    row=db.execute('SELECT * FROM workout_reminders WHERE account_id=?',(uid,)).fetchone()
    if not row or not row['enabled']:return
    tz=ZoneInfo(row['timezone']);start=max(row['effective_at'],row['checked_at']);days=json.loads(row['days'])
    day=datetime.fromtimestamp(start,tz).date();last=datetime.fromtimestamp(now,tz).date()
    while day<=last:
        setting=days[day.weekday()]
        if setting['enabled']:
            hour,minute=map(int,setting['time'].split(':'));local=datetime(day.year,day.month,day.day,hour,minute,tzinfo=tz,fold=0);due=local.timestamp()
            # A nonexistent DST time is delivered at the normalized next valid local time.
            if start<due<=now:
                db.execute('INSERT OR IGNORE INTO inbox_system_messages(account_id,local_day,scheduled,timezone,body) VALUES(?,?,?,?,?)',(uid,day.isoformat(),due,row['timezone'],'ถึงเวลาฝึกของเราแล้ว 💪 เตรียมดัมเบลและเริ่มตามตารางวันนี้ได้เลย / Time to train! Get your dumbbells ready and open today’s plan.'))
        day+=timedelta(days=1)
    db.execute('UPDATE workout_reminders SET checked_at=MAX(checked_at,?) WHERE account_id=?',(now,uid))

def friends(db,uid):
    return [r[0] for r in db.execute("SELECT CASE WHEN sender=? THEN receiver ELSE sender END FROM friend_requests WHERE status='accepted' AND (sender=? OR receiver=?)",(uid,uid,uid))]

def register(app,get_store):
    bp=Blueprint('inbox_features',__name__)
    @bp.before_request
    def guard():
        if not getattr(g,'account',None):return jsonify(error='กรุณาเข้าสู่ระบบ / Please sign in'),401
        schema(get_store())
    @bp.after_request
    def private(response):response.headers['Cache-Control']='private, no-store';return response
    @bp.route('/social/inbox/reminders',methods=['GET','POST'])
    def reminders():
        store=get_store();uid=g.account['id'];now=clock()
        if request.method=='POST':
            try:settings=validate(request.get_json(silent=True))
            except ValueError as e:return jsonify(error=str(e)),400
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE');materialize(db,uid,now)
            if request.method=='POST':
                db.execute('INSERT INTO workout_reminders VALUES(?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET enabled=excluded.enabled,timezone=excluded.timezone,days=excluded.days,effective_at=excluded.effective_at,checked_at=excluded.checked_at',(uid,int(settings['enabled']),settings['timezone'],json.dumps(settings['days']),now,now))
            return jsonify(preference(db,uid))
    @bp.get('/social/inbox')
    def inbox():
        store=get_store();uid=g.account['id']
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE');materialize(db,uid,clock())
            markers={r['thread']:r['last_id'] for r in db.execute('SELECT thread,last_id FROM inbox_read_cursors WHERE account_id=?',(uid,))}
            messages=[dict(r) for r in db.execute('SELECT id,scheduled,timezone,body FROM inbox_system_messages WHERE account_id=? ORDER BY id DESC LIMIT 100',(uid,))]
            system_unread=db.execute('SELECT COUNT(*) FROM inbox_system_messages WHERE account_id=? AND id>?',(uid,markers.get('system',0))).fetchone()[0]
            for m in messages:m['unread']=m['id']>markers.get('system',0)
            threads=[]
            for friend in friends(db,uid):
                row=db.execute("SELECT p.name FROM profiles p JOIN profile_owners o ON o.profile_id=p.id WHERE o.owner=? ORDER BY p.id LIMIT 1",('account:'+str(friend),)).fetchone()
                last=db.execute('SELECT id,body,created FROM friend_messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1',(uid,friend,friend,uid)).fetchone()
                unread=db.execute('SELECT COUNT(*) FROM friend_messages WHERE sender=? AND receiver=? AND id>?',(friend,uid,markers.get('friend:'+str(friend),0))).fetchone()[0]
                threads.append(dict(account_id=friend,name=row['name'] if row else 'Player '+str(friend),last=dict(last) if last else None,unread=unread))
            threads.sort(key=lambda t:t['last']['created'] if t['last'] else 0,reverse=True)
            return jsonify(messages=messages,system_unread=system_unread,friends=threads,unread=system_unread+sum(t['unread'] for t in threads),settings=preference(db,uid))
    @bp.post('/social/inbox/read')
    def read():
        data=request.get_json(silent=True);uid=g.account['id'];store=get_store()
        if not isinstance(data,dict) or type(data.get('through')) is not int or data['through']<1:return jsonify(error='Invalid read cursor'),400
        with store.lock,store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if data.get('source')=='system':
                thread='system';found=db.execute('SELECT 1 FROM inbox_system_messages WHERE account_id=? AND id=?',(uid,data['through'])).fetchone()
            elif data.get('source')=='friend' and type(data.get('account_id')) is int and data['account_id'] in friends(db,uid):
                thread='friend:'+str(data['account_id']);found=db.execute('SELECT 1 FROM friend_messages WHERE sender=? AND receiver=? AND id=?',(data['account_id'],uid,data['through'])).fetchone()
            else:return jsonify(error='Thread not found'),404
            if not found:return jsonify(error='Message not found'),404
            db.execute('INSERT INTO inbox_read_cursors VALUES(?,?,?) ON CONFLICT(account_id,thread) DO UPDATE SET last_id=MAX(last_id,excluded.last_id)',(uid,thread,data['through']))
        return jsonify(ok=True)
    app.register_blueprint(bp)
