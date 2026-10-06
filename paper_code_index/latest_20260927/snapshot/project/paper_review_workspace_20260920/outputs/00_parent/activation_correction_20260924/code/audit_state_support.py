"""State-resolved sampling support, including all zero-deposit decays."""
from common import *
from decay_kernel import NuclearData
from correct_response import resolve_excitation
from collections import Counter

data=NuclearData();jobs=read(O/'data/runtime_jobs.json');counts=Counter();pref={};details=[];unresolved=[]
for model,family in sorted({(j['model'],j['family']) for j in jobs}):
    pts=read(O/'data'/f'points_{model}_{family}.json')['points'];zs=np.array([p['za'] for p in pts])
    blocks=Counter()
    for p in pts:blocks[p['za']]+=p['source_blocks']
    js=[j for j in jobs if (j['model'],j['family'])==(model,family)]
    for za,n in blocks.items():pref[model,family,za]=js[0]['independent_source_activity_Bq']*n/10000
    for job in js:
        jid=job['job_id'];d=O/'data/decay_metadata';md=dict(np.load(d/(jid+'.npz')))
        ev=md['events'];mp=dict(np.load(d/(jid+'.map.npz')))
        starts=np.flatnonzero(mp['group_first_index']==np.arange(len(ev)))
        ex,stat=resolve_excitation(ev,md['future'],mp,starts)
        roots=zs[mp['point_id'][starts]];za=ev['za'][starts]
        # The original CC label records excitation to 0.001 keV.
        key=np.rec.fromarrays([roots,za,np.rint(ex*1000).astype('i8')],names='root,za,exc')
        for row,n in zip(*np.unique(key,return_counts=True)):
            try:name=data.name(int(row['za']),int(row['exc'])/1000)
            except (KeyError,ValueError):
                unresolved.append({'job':jid,'root':int(row['root']),'za':int(row['za']),'exc_keV':int(row['exc'])/1000,'count':int(n)})
                continue
            counts[model,family,int(row['root']),name]+=int(n)
        details.append({'job':jid,'groups':len(starts),**stat})
    print(model,family,'state counts complete',flush=True)
reg=read(O/'data/lineage_weight_registry.json');w=np.load(O/'data/lineage_weights_81nodes.npy');rows=[]
for r in reg:
    key=(r['model'],r['family'],r['source_parent_ZA'],r['actual_state'])
    tau=data.tau(r['actual_state']);root=data.name(r['source_parent_ZA'])
    s=1 if r['actual_state']==root else (math.exp(-(1e-6-1e-9)/tau) if 0<tau<math.inf else 0)
    expected=pref[key[:3]]*r['exposure_per_Bq_s']*s
    if expected<1e-100:continue
    rate=expected*w[60,r['category_id']]
    rows.append({**r,'expected_one_us_groups':expected,'observed_one_us_groups':counts[key],
       'day15_model_decay_rate_cps':rate,'z_count':(counts[key]-expected)/math.sqrt(expected),
       'is_daughter':r['actual_state']!=root})
summary={}
for m in ['a','b']:
    rr=[r for r in rows if r['model']==m]
    summary[m]={'model_day15_decay_rate_cps':sum(r['day15_model_decay_rate_cps'] for r in rr),
        'zero_sample_daughter_model_rate_cps':sum(r['day15_model_decay_rate_cps'] for r in rr if r['is_daughter'] and not r['observed_one_us_groups']),
        'under10_sample_daughter_model_rate_cps':sum(r['day15_model_decay_rate_cps'] for r in rr if r['is_daughter'] and r['observed_one_us_groups']<10),
        'zero_sample_top':sorted([r for r in rr if r['is_daughter'] and not r['observed_one_us_groups']],key=lambda r:-r['day15_model_decay_rate_cps'])[:30],
        'discrepancy_top':sorted([r for r in rr if r['expected_one_us_groups']>30],key=lambda r:-abs(r['z_count']))[:30]}
save(O/'data/state_support_summary.json',{'models':summary,'unresolved_states':unresolved,'jobs':details})
write(O/'data/state_support_rows.csv',rows)
save(O/'data/observed_state_counts.json',[{'model':k[0],'family':k[1],'root':k[2],'state':k[3],'count':v} for k,v in counts.items()])
print('DONE unknown',unresolved,flush=True)
