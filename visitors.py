"""Device-bound guests can train before registration; accounts retain private ownership."""
import re
import secrets
import accounts
from sessions import owned_profiles,add_profile,install_ownership

COOKIE='fitness_guest_v14'
def valid(token):
    return isinstance(token,str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{43}',token))
def owner(token):
    return 'guest:'+accounts.digest(token) if valid(token) else None
def ensure_profile(store,identity):
    profiles=owned_profiles(store,identity)
    if profiles:return profiles[0]
    with store.lock:
        profiles=owned_profiles(store,identity)
        if profiles:return profiles[0]
        return add_profile(store,identity,('Guest ' if identity.startswith('guest:') else 'Player ')+secrets.token_hex(4))
def adopt(store,token,account):
    previous=owner(token)
    if not previous:return
    install_ownership(store)
    with store.lock,store.connect() as db:
        db.execute('UPDATE profile_owners SET owner=? WHERE owner=?',(account['owner'],previous))
