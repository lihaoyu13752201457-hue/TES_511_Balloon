"""Quantify finite-shard support independently of detector selections."""
from decay_kernel import *
import time
data=NuclearData();jobs=json.loads((D/'runtime_jobs.json').read_text())
reg=json.loads((D/'lineage_weight_registry.json').read_text());weights=np.load(D/'lineage_weights_81nodes.npy')
counts=collections.Counter();primary=collections.Counter();ratepref={}
for model,family in sorted({(j['model'],j['family']) for j in jobs}):
    pts=json.loads((D/f'points_{model}_{family}.json').read_text())['points']
    zs=np.array([p['za'] for p in pts]);blocks=collections.Counter()
    for p in pts:blocks[p['za']]+=p['source_blocks']
    jj=[j for j in jobs if (j['model'],j['family'])==(model,family)]
    for za,n in blocks.items():ratepref[(model,family,za)]=jj[0]['independent_source_activity_Bq']*n/10000
    for j in jj:
        ev=np.load(D/'decay_metadata'/(j['job_id']+'.npz'))['events']
        mp=np.load(D/'decay_metadata'/(j['job_id']+'.map.npz'))
        keep=mp['group_first_index']==np.arange(len(ev))
        roots=zs[mp['point_id'][keep]];actual=ev['za'][keep]
        pair=roots.astype('i8')*1000000+actual
        for key,n in zip(*np.unique(pair,return_counts=True)):
            counts[(model,family,int(key//1000000),int(key%1000000))]+=int(n)
        for root,n in zip(*np.unique(roots[mp['is_primary'][keep]],return_counts=True)):
            primary[(model,family,int(root))]+=int(n)
    print(model,family,'counted',flush=True)
agg={}
for r in reg:
    key=(r['model'],r['family'],r['source_parent_ZA'],r['actual_ZA'])
    pref=ratepref[key[:3]];tau=data.tau(r['actual_state'])
    survival=1 if r['actual_ZA']==r['source_parent_ZA'] and r['actual_exc_keV']<.001 else (math.exp(-(1e-6-1e-9)/tau) if 0<tau<math.inf else 0)
    expected=r['exposure_per_Bq_s']*pref*survival
    physical=weights[60,r['category_id']]*expected
    if key not in agg:agg[key]=dict(model=key[0],family=key[1],root=key[2],actual=key[3],expected=0.,observed=counts[key],day15_physical_rate=0.)
    agg[key]['expected']+=expected;agg[key]['day15_physical_rate']+=physical
rows=list(agg.values())
rootcols={(q['model'],q['family'],q['source_parent_ZA']):q['category_id'] for q in reg if q['actual_ZA']==q['source_parent_ZA'] and q['actual_exc_keV']<.001}
for r in rows:
    r['z_raw']=(r['observed']-r['expected'])/math.sqrt(r['expected']) if r['expected']>0 else None
    r['weight_ratio_to_root']=r['day15_physical_rate']/r['expected']/weights[60,rootcols[r['model'],r['family'],r['root']]] if r['expected']>0 else None
summary={}
for m in ['a','b']:
    rr=[r for r in rows if r['model']==m]
    summary[m]={'total_day15_activity':sum(r['day15_physical_rate'] for r in rr),
      'daughter_day15_activity':sum(r['day15_physical_rate'] for r in rr if r['root']!=r['actual']),
      'zero_sample_daughter_activity':sum(r['day15_physical_rate'] for r in rr if r['root']!=r['actual'] and r['observed']==0),
      'under10_sample_daughter_activity':sum(r['day15_physical_rate'] for r in rr if r['root']!=r['actual'] and r['observed']<10),
      'zero_sample_top':sorted([r for r in rr if not r['observed']],key=lambda x:-x['day15_physical_rate'])[:30],
      'discrepancy_top':sorted([r for r in rr if r['expected']>30],key=lambda x:-abs(x['z_raw']))[:30]}
(D/'lineage_support_rows.json').write_text(json.dumps(rows,indent=2)+'\n')
(D/'lineage_support_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
