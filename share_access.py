"""Keep a local share access key across server restarts; no camera/session changes."""
import secrets

def load_key(store):
    with store.lock,store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS app_secrets(name TEXT PRIMARY KEY,value TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO app_secrets VALUES(?,?)',('share_access',secrets.token_urlsafe(32)))
        return db.execute('SELECT value FROM app_secrets WHERE name=?',('share_access',)).fetchone()[0]
