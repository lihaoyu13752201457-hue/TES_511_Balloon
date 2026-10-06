"""Cross-check native hit centres against named CC deposits in existing data."""
from targeted_environment import *
import gzip,collections,re
jobs=json.loads((O/'data/runtime_jobs.json').read_text());maps={};audits={}
active={'a':{'BGO_S3C_FullWrap_SideShell_WindowCut_40mm','BGO_S3D_O8_FullWrap_BottomCap_30mm','AA_BGO_TopCap_12Ports_10mm'},'b':{'SH3_BGO40_SideShield','SH3_BGO40_FrontOpticalAnnulus','SH3_BGO40_RearColdPortAnnulus'}}
for model in ['a','b']:
    job=next(j for j in jobs if j['model']==model and j['family']=='p');seen=collections.defaultdict(collections.Counter);sums=collections.Counter();hits=[];events=0
    def flush():
        for name,e in sums.items():
            if name not in active[model] or e<=1e-4:continue
            candidates=[xyz for xyz,v in hits if abs(v-e)<max(1e-4,e*2e-6)]
            if len(candidates)==1:seen[name][candidates[0]]+=1
    with gzip.open(job['sim_path'],'rt') as f:
        for l in f:
            if l.startswith('ID '):
                flush();events+=1;sums=collections.Counter();hits=[]
                if events>2000:break
            elif l.startswith('CC HIT '):
                w=l.split();sums[w[2]]+=float(w[3].split('=')[1])
            elif l.startswith('HTsim 4;'):
                w=l.split(';');hits.append((tuple(float(x) for x in w[1:4]),float(w[4])))
    assert set(seen)==active[model],(model,seen)
    assert all(len(c)==1 and sum(c.values())>=5 for c in seen.values()),seen
    maps[model]={name:list(next(iter(c))) for name,c in seen.items()}
    audits[model]=dict(source=job['sim_path'],prefix_events=2000,named_to_native_matches={k:sum(v.values()) for k,v in seen.items()})
(T/'ht_mapping.json').write_text(json.dumps(dict(centres=maps,audit=audits),indent=2)+'\n')
print(json.dumps(maps,indent=2))
