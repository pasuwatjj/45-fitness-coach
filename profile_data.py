"""Private profile dashboard and normalized avatars; callers enforce ownership."""
import io
import json
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from planner import today_thailand

def avatar_table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS profile_avatars (
        profile_id INTEGER PRIMARY KEY REFERENCES profiles(id),
        image BLOB NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

def get_avatar(store, profile_id):
    with store.lock, store.connect() as db:
        avatar_table(db)
        row=db.execute('SELECT image FROM profile_avatars WHERE profile_id=?',(profile_id,)).fetchone()
        return bytes(row['image']) if row else None

def save_avatar(store, profile_id, raw):
    if not raw or len(raw)>3*1024*1024:
        raise ValueError('Use a JPG, PNG or WebP image under 3 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ('JPEG','PNG','WEBP') or source.width*source.height>16_000_000:
                    raise ValueError('Use JPG, PNG or WebP, up to 16 megapixels.')
                source.load()
                normalized=ImageOps.exif_transpose(source).convert('RGB')
                normalized=ImageOps.fit(normalized,(384,384),method=Image.Resampling.LANCZOS)
                output=io.BytesIO();normalized.save(output,format='JPEG',quality=88)
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
        raise ValueError('Cannot read this image. Try JPG, PNG or WebP.') from exc
    with store.lock,store.connect() as db:
        avatar_table(db)
        db.execute('''INSERT INTO profile_avatars(profile_id,image) VALUES(?,?)
            ON CONFLICT(profile_id) DO UPDATE SET image=excluded.image,updated_at=CURRENT_TIMESTAMP''',
            (profile_id,output.getvalue()))

def overview(store, profile_id):
    with store.lock,store.connect() as db:
        avatar_table(db)
        from rewards import schema
        schema(db)
        totals=dict(db.execute('''SELECT COUNT(*) AS sets,COALESCE(SUM(reps),0) AS reps,
            COALESCE(SUM(flagged),0) AS flagged FROM workout_sets WHERE profile_id=?''',(profile_id,)).fetchone())
        rows=[dict(r) for r in db.execute('''SELECT id,exercise,arm_mode,reps,flagged,observations,created_at
            FROM workout_sets WHERE profile_id=? ORDER BY created_at DESC,id DESC LIMIT 60''',(profile_id,))]
        has_avatar=db.execute('SELECT 1 FROM profile_avatars WHERE profile_id=?',(profile_id,)).fetchone() is not None
    from exercises import CATALOG
    groups={key:dict(group=key,reps=0,sets=0) for key in ('arms','chest','back','legs','shoulders')}
    with store.lock,store.connect() as db:
        for row in db.execute('SELECT exercise,SUM(reps) reps,COUNT(*) sets FROM workout_sets WHERE profile_id=? GROUP BY exercise',(profile_id,)):
            group=CATALOG.get(row['exercise'],{}).get('group')
            if group in groups:
                groups[group]['reps']+=row['reps'];groups[group]['sets']+=row['sets']
    with store.lock,store.connect() as db:
        quality={r['id']:dict(r) for r in db.execute('SELECT * FROM quality_sets WHERE profile_id=? ORDER BY created_at DESC,id DESC LIMIT 60',(profile_id,))}
    for row in rows:
        q=quality.pop(row['id'],None)
        row['rejected']=q['rejected'] if q else 0
        row['unverified']=q['unverified'] if q else 0
        row['strict']=q is not None
        row['accepted']=q['accepted'] if q else row['reps']
    for q in quality.values():
        if not q['reps']:rows.append(dict(q,flagged=0,observations='{}',strict=True))
    rows.sort(key=lambda r:(r['created_at'],r['id']),reverse=True);rows=rows[:60]
    for row in rows:
        row['observations']=json.loads(row['observations'])
        row['created_at']=row['created_at'].replace(' ','T')+'Z'
    plan=store.plan_month(profile_id,today_thailand().strftime('%Y-%m'))
    from rewards import overview as reward_overview
    badges=reward_overview(store,profile_id)
    from character import dimensions
    return dict(dimensions=dimensions(store,profile_id),muscle_groups=list(groups.values()),rewards=badges,profile=store.profile(profile_id),has_avatar=has_avatar,totals=totals,
                sets=rows,history_limit=60,health=store.health_history(profile_id),streak=plan['streak'])
