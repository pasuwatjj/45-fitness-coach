"""Descriptive progress statistics. No clinical scores or inferred muscle growth."""
import json
from collections import defaultdict
from statistics import mean
import angles,cardio


def report(store,pid):
    with store.lock,store.connect() as db:
        angles.schema(db)
        records=[dict(r) for r in db.execute('SELECT * FROM set_angles WHERE profile_id=? ORDER BY created_at DESC,id DESC LIMIT 1000',(pid,))]
    rows=[];groups=defaultdict(list)
    for s in reversed(records):
        for r in json.loads(s['data']):
            m=r.get('metrics',{}).get('elbow')
            if not m:continue
            low,high=r.get('low'),r.get('high')
            row=dict(set_id=s['id'],day=s['day'],created_at=s['created_at'],exercise=s['exercise'],side=r['side'],source=r['source'],samples=m['samples'],mean=m['mean'],minimum=m['minimum'],maximum=m['maximum'],whole_sd=m['sd'],attempts=r.get('completed_attempts',0),low=low['mean'] if low else None,high=high['mean'] if high else None,endpoint_sd=round((low['sd']+high['sd'])/2,2) if low and high else None,rom=round(high['mean']-low['mean'],1) if low and high else None)
            row['eligible']=row['attempts']>=3 and row['samples']>=10 and row['endpoint_sd'] is not None
            row['advice']='more_samples' if not row['eligible'] else 'repeat_range' if row['endpoint_sd']>12 else 'steady'
            rows.append(row);groups[(row['exercise'],row['side'],row['source'])].append(row)
    summaries=[];days=[]
    for key,rr in groups.items():
        valid=[r for r in rr if r['eligible']];trend='insufficient';delta=None
        # Non-overlapping first and latest three comparable sets. Equal set weights.
        if len(valid)>=6:
            delta=round(mean(r['endpoint_sd'] for r in valid[-3:])-mean(r['endpoint_sd'] for r in valid[:3]),2)
            trend='more_consistent' if delta<=-2 else 'less_consistent' if delta>=2 else 'similar'
        summaries.append(dict(exercise=key[0],side=key[1],source=key[2],sets=len(rr),eligible_sets=len(valid),trend=trend,sd_change=delta,baseline_ids=[r['set_id'] for r in valid[:3]],recent_ids=[r['set_id'] for r in valid[-3:]]))
        dated=defaultdict(list)
        for r in rr:dated[r['day']].append(r)
        for day,dr in sorted(dated.items()):
            good=[r for r in dr if r['eligible']]
            days.append(dict(day=day,exercise=key[0],side=key[1],source=key[2],sets=len(dr),eligible_sets=len(good),mean=round(mean(r['mean'] for r in dr),1),endpoint_sd=round(mean(r['endpoint_sd'] for r in good),2) if good else None,rom=round(mean(r['rom'] for r in good),1) if good else None))
    cr=cardio.history(store,pid)
    for r in cr:r['reps_per_minute']=round(r['reps']*60/r['duration'],1)
    return dict(sets=rows,days=days,comparisons=summaries,cardio=cr,limits=dict(angle_sets=1000,cardio_rounds=500),method='v20-descriptive-1')
