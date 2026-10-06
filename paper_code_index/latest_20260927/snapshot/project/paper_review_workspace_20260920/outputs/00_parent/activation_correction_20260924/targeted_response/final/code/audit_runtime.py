"""Read only registered delayed receipts and the last 1 MB of each native log."""
from pathlib import Path
import json,re,csv,hashlib
from collections import defaultdict
O=Path(__file__).resolve().parents[1]
W=O.parents[2]
P=W.parent
DISK=Path('/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data')
def rebase(p):
    return Path(str(p).replace('/mnt/data/TES_Balloon_511_data',str(DISK)))
manifests={
 'a':DISK/'AA/aa_reproduce_A_20260921_v1/delayed_epoch0_inventory/generated/activation/manifest.json',
 'b':DISK/'SH3/sh3_optv3_m05_delayed_activation_v1/generated/activation/manifest.json'}
sources={k:json.loads(p.read_text()) for k,p in manifests.items()}
source_cells={k:{c['family']:c for c in v['source_cells']} for k,v in sources.items()}
jobs_a=json.loads((W/'outputs/00_parent/AA_run_20260921_v1/bundles/delayed_epoch0/generated/job_plan.json').read_text())['jobs']
jobs_b=[j for j in json.loads((P/'DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json').read_text())['jobs'] if j['stream']=='delayed']
receipts={'a':DISK/'AA/aa_reproduce_A_20260921_v1/delayed_epoch0/receipts', 'b':DISK/'SH3/sh3_optv3_m05_delayed_8m_v1/run/receipts'}
rows=[]; counters={}
for m,jobs in [('a',jobs_a),('b',jobs_b)]:
 for j in jobs:
    rpath=receipts[m]/(j['job_id']+'.json');r=json.loads(rpath.read_text())
    assert r['status']=='PASS' and r['events']==j['events']
    lp=rebase(r['log_path'])
    with lp.open('rb') as f:
        f.seek(max(0,lp.stat().st_size-1000000));txt=f.read().decode(errors='replace')
    tail=txt[txt.rfind('Summary for run'):]
    cs={k:int(n) for k,n in re.findall(r'^\s*Source (\S+):\s+(\d+)\s*$',tail,re.M)}
    assert len(cs)-(1 if 'DelayedDecaysList' in cs else 0)==10000,(j['job_id'],len(cs))
    assert sum(cs.values())==j['events']
    nchild=cs.pop('DelayedDecaysList',0);nroot=sum(cs.values())
    activity=source_cells[m][j['family']]['transported_ground_activity_Bq']
    tt=r['log']['observation_time_s']
    sp=rebase(r['source_path']);raw=sp.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['source_sha256']
    text=raw.decode();assert 'ActivationDelayedDecay' in text
    assert text.count('Beam PointSource')==10000
    rows.append(dict(model=m,family=j['family'],job_id=j['job_id'],events=j['events'],root_events=nroot,queued_events=nchild,observation_time_s=tt,independent_source_activity_Bq=activity,nominal_N_over_A_s=j['events']/activity,all_over_root=j['events']/nroot,root_rate_over_input=nroot/(tt*activity),sim_bytes=r['sim_bytes'],sim_path=str(rebase(r['sim_path'])),source_path=str(sp),source_sha256=r['source_sha256'],receipt_path=str(rpath),log_path=str(lp)))
    counters[j['job_id']]=cs
(O/'data/runtime_jobs.json').write_text(json.dumps(rows,indent=2)+'\n')
(O/'data/native_point_source_counts.json').write_text(json.dumps(counters,separators=(',',':'))+'\n')
with (O/'data/runtime_jobs.csv').open('w') as f:
 wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
agg=[]
for m in ['a','b']:
 for fam in sorted({r['family'] for r in rows if r['model']==m}):
    rs=[r for r in rows if r['model']==m and r['family']==fam]
    d={k:sum(r[k] for r in rs) for k in ['events','root_events','queued_events','observation_time_s','sim_bytes']}
    d.update(model=m,family=fam,jobs=len(rs),activity_Bq=rs[0]['independent_source_activity_Bq'])
    d['queued_fraction']=d['queued_events']/d['events'];d['normalization_factor_root']=d['events']/d['root_events'];d['normalization_factor_time']=d['events']/(d['activity_Bq']*d['observation_time_s'])
    agg.append(d)
(O/'data/runtime_families.json').write_text(json.dumps(agg,indent=2)+'\n')
for d in agg:print(d['model'],d['family'],d['root_events'],d['queued_events'],round(d['normalization_factor_root'],5),round(d['normalization_factor_time'],5))
print('JOBS',len(rows),'RAW_GB',sum(r['sim_bytes'] for r in rows)/1e9)
