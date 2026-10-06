"""Audit retained AA selected events without needing the off-line energy catalogue."""
from common import *
from decay_kernel import NuclearData
data=NuclearData();reg=read(O/'data/lineage_weight_registry.json')
lookup={(r['model'],r['family'],r['source_parent_ZA'],r['actual_state']):r['category_id'] for r in reg}
w=np.load(O/'data/lineage_weights_81nodes.npy')
selected=rows(ORIGINAL/'data/delayed_origins_a_500.csv');cache={};out=[];changes=[];indices=[]
for r in selected:
    jid=r['job_id'];eid=int(r['event_id'])-1
    if jid not in cache:
        dd=O/'data/decay_metadata';ev=np.load(dd/(jid+'.npz'))['events'];mp=dict(np.load(dd/(jid+'.map.npz')))
        counts=np.bincount(mp['group_first_index'],minlength=len(ev));cache[jid]=(ev,mp,counts)
    ev,mp,counts=cache[jid];first=int(mp['group_first_index'][eid]);n=int(counts[first])
    if first!=eid or n!=1:changes.append({'job':jid,'event_id':eid+1,'first_id':first+1,'members':n})
    assert mp['is_primary'][eid] and int(ev['za'][eid])==int(r['source_parent_ZA'])
    name=data.name(int(ev['za'][eid]),float(np.nan_to_num(ev['exc'][eid])))
    c=lookup['a',r['family'],int(r['source_parent_ZA']),name];indices.append(c)
    out.append({**r,'old_day15_weight_cps':float(r['day15_weight_cps']),
        'day15_weight_cps':float(w[60,c]),'actual_state':name,'lineage_registry_id':c,
        'short_group_records':n})
assert not changes,changes
rates=w[:,indices].sum(axis=1);variance=(w[:,indices]**2).sum(axis=1)
rr={'status':'PARTIAL_AA__EXISTING_404_SELECTIONS_ONLY','existing_selected_records':len(out),
    'all_existing_selected_records_are_single_primary_decay_groups':True,
    'old_delayed_rate_cps':sum(float(r['old_day15_weight_cps']) for r in out),
    'corrected_existing_selected_contribution_cps':float(rates[60]),
    'weighted_sigma_cps':float(np.sqrt(variance[60])),
    'effective_count':float(rates[60]**2/variance[60]),
    'not_yet_checked':'Previously unselected AA records may enter the window after correlated-decay merging; this requires the external energy catalogue.'}
save(O/'data/aa_existing_selection_audit.json',rr)
write(O/'data/aa_existing_selected_reweighted.csv',out)
np.savez_compressed(O/'data/aa_existing_selection_81nodes.npz',rates=rates,variance=variance)
print(json.dumps(rr,indent=2))
