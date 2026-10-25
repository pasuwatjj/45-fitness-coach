"""Private browser sessions and profile ownership. Tokens never enter URLs."""
import secrets
import threading
import time


class SessionRegistry:
    def __init__(self, factory, limit=128):
        self.factory, self.limit = factory, limit
        self.lock = threading.RLock()
        self.items = {}

    def create(self, owner):
        with self.lock:
            self.sweep()
            if len(self.items) >= self.limit:
                raise ValueError('มีผู้เปิดเว็บจำนวนมาก ลองใหม่อีกสักครู่')
            token = secrets.token_urlsafe(32)
            self.items[token] = dict(owner=owner, coach=self.factory(), seen=time.monotonic())
            return token

    def get(self, token):
        with self.lock:
            item = self.items.get(token)
            if item:
                item['seen'] = time.monotonic()
            return item

    def sweep(self):
        with self.lock:
            now = time.monotonic()
            for token, item in list(self.items.items()):
                coach = item['coach']
                with coach.condition:
                    if coach.state['running'] and now-coach.last_frame_at > 20:
                        coach.stop()
                        coach.state['message'] = 'กล้องขาดการเชื่อมต่อเกิน 20 วินาที บันทึกเซตแล้ว กดเปิดใหม่ได้'
                    if not coach.state['running'] and now-coach.last_frame_at > 120 and hasattr(coach,'release_detector'):
                        coach.release_detector()
                    if now-item['seen'] > 1800 and not (coach.state.get('summary') or {}).get('save_error'):
                        coach.stop()
                        if hasattr(coach,'release_detector'):coach.release_detector()
                        del self.items[token]

    def stop_all(self):
        with self.lock:
            for item in self.items.values():
                item['coach'].stop()
                if hasattr(item['coach'],'release_detector'):item['coach'].release_detector()


def install_ownership(store):
    with store.lock, store.connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS profile_owners (
            profile_id INTEGER PRIMARY KEY REFERENCES profiles(id), owner TEXT NOT NULL)''')


def owned_profiles(store, owner):
    install_ownership(store)
    with store.lock, store.connect() as db:
        return [dict(r) for r in db.execute('''SELECT p.id,p.name FROM profiles p
            JOIN profile_owners o ON o.profile_id=p.id WHERE o.owner=? ORDER BY p.id''',(owner,))]


def owns(store, owner, profile_id):
    install_ownership(store)
    with store.lock, store.connect() as db:
        return bool(db.execute('SELECT 1 FROM profile_owners WHERE owner=? AND profile_id=?',
                               (owner,profile_id)).fetchone())


def add_profile(store, owner, name):
    install_ownership(store)
    if not isinstance(name,str):
        raise ValueError('กรุณาใส่ชื่อผู้เล่น')
    name=' '.join(name.split())
    if not name or len(name)>30 or not name.isprintable():
        raise ValueError('ชื่อผู้เล่นต้องยาว 1–30 ตัวอักษร')
    with store.lock, store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        existing=db.execute('SELECT p.id,p.name FROM profiles p JOIN profile_owners o ON o.profile_id=p.id WHERE o.owner=? ORDER BY p.id LIMIT 1',(owner,)).fetchone()
        if existing:
            raise ValueError('บัญชีนี้มีโปรไฟล์แล้ว เปลี่ยนชื่อได้ในโปรไฟล์ของฉัน / This account already has a profile. Rename it in My profile.')
        old=db.execute('SELECT id,name FROM profiles WHERE name=? COLLATE NOCASE',(name,)).fetchone()
        if old:
            row=db.execute('SELECT owner FROM profile_owners WHERE profile_id=?',(old['id'],)).fetchone()
            if row and row['owner']==owner:
                return dict(old)
            raise ValueError('ชื่อนี้มีผู้ใช้แล้ว กรุณาตั้งชื่ออื่น')
        cursor=db.execute('INSERT INTO profiles(name) VALUES(?)',(name,))
        db.execute('INSERT INTO profile_owners(profile_id,owner) VALUES(?,?)',(cursor.lastrowid,owner))
        return dict(id=cursor.lastrowid,name=name)


def migrate_legacy(store, owner):
    """Only the first LOCAL browser may adopt pre-v7 profiles; never public visitors."""
    install_ownership(store)
    with store.lock, store.connect() as db:
        db.execute('''INSERT INTO profile_owners(profile_id,owner)
            SELECT p.id,? FROM profiles p LEFT JOIN profile_owners o ON o.profile_id=p.id
            WHERE o.profile_id IS NULL''',(owner,))


def rename_profile(store, owner, profile_id, name):
    install_ownership(store)
    if not isinstance(name,str):raise ValueError('Enter a player name')
    name=' '.join(name.split())
    if not name or len(name)>30 or not name.isprintable():raise ValueError('Player name must contain 1–30 printable characters')
    with store.lock,store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        first=db.execute('SELECT profile_id FROM profile_owners WHERE owner=? ORDER BY profile_id LIMIT 1',(owner,)).fetchone()
        if not first or first['profile_id']!=profile_id:raise ValueError('Only your primary profile can be renamed. Legacy history is preserved.')
        if db.execute('SELECT 1 FROM profiles WHERE name=? COLLATE NOCASE AND id<>?',(name,profile_id)).fetchone():raise ValueError('This player name is already taken')
        db.execute('UPDATE profiles SET name=? WHERE id=?',(name,profile_id))
        return dict(id=profile_id,name=name)
