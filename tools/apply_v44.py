"""Apply this cumulative update to an existing V42/V43 checkout, with hash guards."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--check',action='store_true');args=p.parse_args();target=args.project.resolve()
    if target==ROOT:raise SystemExit('Select your EXISTING project, not the extracted update folder.')
    manifest=json.loads((ROOT/'MANIFEST_V44.json').read_text())
    missing=[name for name in manifest['required_base_files'] if not (target/name).is_file()]
    if missing:raise SystemExit('Incomplete base project; missing: '+', '.join(missing))
    conflicts=[]
    for name,info in manifest['application_files'].items():
        source=ROOT/name;dest=target/name
        if digest(source)!=info['sha256']:raise SystemExit('Package integrity mismatch: '+name)
        if dest.exists() and digest(dest) not in info['accepted_previous_sha256']+[info['sha256']]:conflicts.append(name)
    if conflicts:raise SystemExit('Local edits or different version detected. No files changed. Merge these manually: '+', '.join(conflicts))
    if args.check:print('Compatible base found. No files changed.');return
    backup=target.parent/(target.name+'-before-v44-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir()
    for name,info in manifest['application_files'].items():
        dest=target/name
        if dest.exists():
            copy=backup/name;copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,copy)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    print('V44 update applied. Source backup: '+str(backup))
    print('Restart the Python server, then hard-refresh the browser. Runtime database was not copied or replaced.')
if __name__=='__main__':main()
