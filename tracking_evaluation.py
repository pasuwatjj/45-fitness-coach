"""Human-reference evaluation. Never presented as validated production accuracy."""
import json, math, time, uuid
from flask import request,jsonify,g

def evaluate(data):
    if not isinstance(data,dict):raise ValueError('Expected object')
    name=data.get('name','');exercise=data.get('exercise','');reference=data.get('reference','')
    if not all(isinstance(s,str) and 1<=len(s.strip())<=300 for s in (name,exercise,reference)):raise ValueError('Enter test name, exercise and reference method / ระบุชื่อการทดสอบ ท่า และวิธีวัดอ้างอิง')
    reps=data.get('reps',[]);angles=data.get('angles',[])
    if not isinstance(reps,list) or not isinstance(angles,list) or len(reps)>500 or len(angles)>500 or not(reps or angles):raise ValueError('Enter 1–500 rows / ใส่ข้อมูล 1–500 แถว')
    counts=dict(wrong=0,correct=0,caught=0,missed=0,false_alarm=0,accepted_correct=0,unknown=0,wrong_unknown=0)
    for r in reps:
        if not isinstance(r,dict) or r.get('truth') not in ('wrong','correct') or r.get('result') not in ('rejected','accepted','unverified'):raise ValueError('Invalid repetition label / ป้ายกำกับรอบไม่ถูกต้อง')
        truth,result=r['truth'],r['result'];counts[truth]+=1
        if result=='unverified':counts['unknown']+=1;counts['wrong_unknown']+=truth=='wrong'
        elif truth=='wrong':counts['caught' if result=='rejected' else 'missed']+=1
        else:counts['false_alarm' if result=='rejected' else 'accepted_correct']+=1
    errors=[]
    for a in angles:
        if not isinstance(a,dict) or not isinstance(a.get('sample'),str) or not a['sample'].strip() or len(a['sample'])>120:raise ValueError('Label the same frame and joint / ระบุเฟรมและข้อต่อที่ตรงกัน')
        values=[a.get(k) for k in ('reference','measured')]
        if not all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=180 for v in values):raise ValueError('Angles must be 0–180 degrees / มุมต้องอยู่ระหว่าง 0–180 องศา')
        errors.append(values[1]-values[0])
    n=len(reps);known=n-counts['unknown'];pct=lambda a,b:round(a/b*100,2) if b else None
    return dict(**counts,total=n,coverage=pct(known,n),wrong_detection=pct(counts['caught'],counts['wrong']),false_positive_rate=pct(counts['false_alarm'],counts['correct']),accuracy=pct(counts['caught']+counts['accepted_correct'],n) if counts['wrong'] and counts['correct'] else None,angle_samples=len(errors),signed_errors=[round(e,3) for e in errors],bias=round(sum(errors)/len(errors),3) if errors else None,mae=round(sum(abs(e) for e in errors)/len(errors),3) if errors else None,rmse=round(math.sqrt(sum(e*e for e in errors)/len(errors)),3) if errors else None,max_error=round(max(map(abs,errors)),3) if errors else None)

def schema(db):db.execute('CREATE TABLE IF NOT EXISTS tracking_evaluations(id TEXT PRIMARY KEY,actor INTEGER,created REAL,payload TEXT,result TEXT)')
def register(bp,get_store):
    @bp.route('/admin/tracking-evaluations',methods=['GET','POST'])
    def evaluations():
        store=get_store()
        if request.method=='POST':
            data=request.get_json(silent=True)
            try:result=evaluate(data)
            except ValueError as e:return jsonify(error=str(e)),400
            record=dict(id=str(uuid.uuid4()),actor=g.account['id'],created=time.time(),payload=data,result=result)
            with store.lock,store.connect() as db:
                schema(db);db.execute('INSERT INTO tracking_evaluations VALUES(?,?,?,?,?)',(record['id'],record['actor'],record['created'],json.dumps(data),json.dumps(result)))
            return jsonify(record)
        with store.lock,store.connect() as db:
            schema(db);rows=[dict(r) for r in db.execute('SELECT * FROM tracking_evaluations ORDER BY created DESC LIMIT 50')]
        for r in rows:r['payload']=json.loads(r['payload']);r['result']=json.loads(r['result'])
        return jsonify(records=rows)
