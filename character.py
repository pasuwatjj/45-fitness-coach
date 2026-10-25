"""Saved adult game characters and capped workout-based growth, not body measurements."""
import json,re
from exercises import CATALOG
DEFAULT={'gender':'male','hair':'short','hair_color':'#292536','skin_color':'#c78f68','shorts_color':'#252d40'}
HAIRS=('short','swept','curly','bob','ponytail','bald')

def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS game_characters(
      owner TEXT PRIMARY KEY,appearance TEXT NOT NULL,updated TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS profile_dimensions(
      profile_id INTEGER PRIMARY KEY REFERENCES profiles(id),height_cm REAL NOT NULL,weight_kg REAL NOT NULL,
      updated TEXT DEFAULT CURRENT_TIMESTAMP);''')

def dimensions(store,profile):
    with store.lock,store.connect() as db:
        schema(db)
        row=db.execute('SELECT height_cm,weight_kg FROM profile_dimensions WHERE profile_id=?',(profile,)).fetchone()
        if row:return dict(row)
        row=db.execute('SELECT inputs FROM health_records WHERE profile_id=? ORDER BY measured_on DESC,created_at DESC LIMIT 1',(profile,)).fetchone()
        if row:
            v=json.loads(row['inputs']);return dict(height_cm=v['height_cm'],weight_kg=v['weight_kg'])
    return dict(height_cm=None,weight_kg=None)

def validate_dimensions(data):
    from health import number
    return dict(height_cm=number(data,'height_cm','ส่วนสูง / height',50,250),weight_kg=number(data,'weight_kg','น้ำหนัก / weight',5,350))

def sync_dimensions(store,profile,data):
    values=validate_dimensions(data)
    with store.lock,store.connect() as db:
        schema(db)
        db.execute('INSERT INTO profile_dimensions(profile_id,height_cm,weight_kg) VALUES(?,?,?) ON CONFLICT(profile_id) DO UPDATE SET height_cm=excluded.height_cm,weight_kg=excluded.weight_kg,updated=CURRENT_TIMESTAMP',(profile,values['height_cm'],values['weight_kg']))

EXP_PER_REP={'beginner':10,'pro':100,'expert':1000}
GROUPS=('arms','chest','back','legs','shoulders')

def progression(total):
    """LV1 starts at 0; successive level costs are 10, 100, 1000, ... ."""
    total=max(0,int(total));remaining=total;level=1;cost=10
    while remaining>=cost:
        remaining-=cost;level+=1;cost*=10
    return dict(level=level,total_exp=total,exp=remaining,next_exp=cost,
                remaining_exp=cost-remaining,progress=remaining/cost)

def growth(store,profile):
    # Derive from unique, server-saved sets; no additive migration or second ledger.
    # Old sets without a recorded difficulty retain the beginner rate.
    reps=dict.fromkeys(GROUPS,0);exp=dict.fromkeys(GROUPS,0)
    sides={'left':0,'right':0};side_exp={'left':0,'right':0}
    from training_economy import schema as training_schema
    with store.lock,store.connect() as db:
        training_schema(db)
        for r in db.execute("""SELECT w.exercise,w.reps,w.left_reps,w.right_reps,
            COALESCE(t.difficulty,'beginner') difficulty FROM workout_sets w
            LEFT JOIN training_sets t ON t.set_id=w.id AND t.profile_id=w.profile_id
            WHERE w.profile_id=?""",(profile,)):
            group=CATALOG.get(r['exercise'],{}).get('group')
            rate=EXP_PER_REP[r['difficulty']]
            if group in reps:
                reps[group]+=max(0,r['reps']);exp[group]+=max(0,r['reps'])*rate
            if group=='arms':
                for side in sides:
                    accepted=max(0,min(r['reps'],r[side+'_reps']))
                    sides[side]+=accepted;side_exp[side]+=accepted*rate
    parts={k:progression(v) for k,v in exp.items()}
    arm_parts={k:progression(v) for k,v in side_exp.items()}
    # Monotone, bounded game geometry: LV1 is thin; every higher LV is larger.
    visual=lambda p:round(1-1/p['level'],6)
    return dict(reps=reps,parts=parts,arm_reps=sides,arm_parts=arm_parts,
                levels={k:visual(p) for k,p in parts.items()},
                arm_levels={k:visual(p) for k,p in arm_parts.items()},exp_per_rep=EXP_PER_REP)

def overview(store,profile,private=False):
    with store.lock,store.connect() as db:
        schema(db)
        row=db.execute('SELECT owner FROM profile_owners WHERE profile_id=?',(profile,)).fetchone()
        if not row:raise ValueError('Character not found / ไม่พบตัวละคร')
        saved=db.execute('SELECT appearance FROM game_characters WHERE owner=?',(row['owner'],)).fetchone()
        appearance=json.loads(saved['appearance']) if saved else dict(DEFAULT)
    dims=dimensions(store,profile)
    height=dims.get('height_cm') or 170
    weight=dims.get('weight_kg') or 65
    visual=dict(height_scale=round(max(.92,min(1.08,height/170)),3),waist_scale=round(max(.94,min(1.10,1+(weight-65)*.002)),3))
    result=dict(profile=store.profile(profile),appearance=appearance,growth=growth(store,profile),visual=visual)
    if private:result['dimensions']=dims
    return result

def save(store,owner,profile,data):
    if not isinstance(data,dict):raise ValueError('Invalid character')
    appearance=data.get('appearance')
    if not isinstance(appearance,dict) or set(appearance)!=set(DEFAULT):raise ValueError('Complete character options / เลือกตัวละครให้ครบ')
    if appearance['gender'] not in ('male','female') or appearance['hair'] not in HAIRS:raise ValueError('Invalid character style')
    for key in ('hair_color','skin_color','shorts_color'):
        if not isinstance(appearance[key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',appearance[key]):raise ValueError('Invalid color')
    dims=validate_dimensions(data['dimensions']) if data.get('dimensions') is not None else None
    with store.lock,store.connect() as db:
        schema(db);db.execute('BEGIN IMMEDIATE')
        if not owner.startswith('account:') or not db.execute('SELECT 1 FROM profile_owners WHERE profile_id=? AND owner=?',(profile,owner)).fetchone():raise PermissionError('Sign in with the owning account / เข้าสู่บัญชีเจ้าของ')
        db.execute('INSERT INTO game_characters(owner,appearance) VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET appearance=excluded.appearance,updated=CURRENT_TIMESTAMP',(owner,json.dumps(appearance)))
        if dims:db.execute('INSERT INTO profile_dimensions(profile_id,height_cm,weight_kg) VALUES(?,?,?) ON CONFLICT(profile_id) DO UPDATE SET height_cm=excluded.height_cm,weight_kg=excluded.weight_kg,updated=CURRENT_TIMESTAMP',(profile,dims['height_cm'],dims['weight_kg']))
    return overview(store,profile,True)
