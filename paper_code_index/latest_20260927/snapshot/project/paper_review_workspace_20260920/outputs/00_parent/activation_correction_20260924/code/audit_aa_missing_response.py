"""Use local pinned veto/hit marks to identify the exact AA data still needed.

No new event is declared selected without its pixel energy deposits. This
computes a rigorous existing-sample upper bound by allowing every eligible
multi-TES cluster to pass the final energy/direction selections.
"""
from common import *
from correct_response import resolve_excitation
from decay_kernel import NuclearData
from collections import Counter

data=NuclearData();reg=read(O/'data/lineage_weight_registry.json')
lookup={(r['family'],r['source_parent_ZA'],r['actual_state']):r['category_id'] for r in reg if r['model']=='a'}
weights=np.load(O/'data/lineage_weights_81nodes.npy')
marks=np.memmap(ORIGINAL/'data/a/records.bin',dtype=DT,mode='r')
jobs=[j for j in read(O/'data/runtime_jobs.json') if j['model']=='a'];rows_out=[];audit=[];bound=np.zeros(81)
all_rates=np.zeros(81);all_bgo_veto_rates=np.zeros(81);source_shape=Counter()
for job in jobs:
    jid=job['job_id'];d=O/'data/decay_metadata'
    md=dict(np.load(d/(jid+'.npz')));ev=md['events'];mp=dict(np.load(d/(jid+'.map.npz')))
    ident=np.load(d/(jid+'.response.npz'));ei=ident['event_id'].astype('i8')-1;gi=ident['global_index']
    starts,first,inv,counts=np.unique(mp['group_first_index'][ei],return_index=True,return_inverse=True,return_counts=True)
    bgo=np.bincount(inv,weights=marks['bgo'][gi],minlength=len(starts))
    tes_records=np.bincount(inv,weights=(marks['hits'][gi]>0),minlength=len(starts)).astype('i8')
    pts=read(O/'data'/f"points_a_{job['family']}.json")['points'];pids=mp['point_id'][starts]
    roots=np.array([p['za'] for p in pts])[pids]
    ex,stat=resolve_excitation(ev,md['future'],mp,starts)
    key=np.rec.fromarrays([roots,ev['za'][starts],np.rint(ex*1000).astype('i8')],names='root,za,exc')
    unique,which,n=np.unique(key,return_inverse=True,return_counts=True);cats=[]
    for r in unique:
        name=data.name(int(r['za']),int(r['exc'])/1000)
        cats.append(lookup[job['family'],int(r['root']),name])
    cat=np.array(cats,dtype='i4')[which]
    sums=np.bincount(cat,minlength=weights.shape[1]);all_rates+=weights@sums
    veto=bgo>=50;vs=np.bincount(cat[veto],minlength=weights.shape[1]);all_bgo_veto_rates+=weights@vs
    eligible=np.flatnonzero((tes_records>=2)&~veto)
    bound+=weights[:,cat[eligible]].sum(axis=1)
    order=np.argsort(inv,kind='stable');off=np.r_[0,np.cumsum(counts)]
    for k in eligible:
        members=order[off[k]:off[k+1]];p=pts[int(pids[k])];c=int(cat[k])
        row={'job_id':jid,'family':job['family'],'group_start_event_id':int(starts[k])+1,
            'response_event_ids':','.join(map(str,ei[members]+1)),
            'catalog_indices':','.join(map(str,gi[members])),
            'source_parent_ZA':int(roots[k]),'actual_state':reg[c]['actual_state'],
            'source_volume':p['volume'],'bgo_sum_keV':float(bgo[k]),
            'TES_positive_member_records':int(tes_records[k]),'detector_positive_member_records':int(counts[k]),
            'day15_weight_cps':float(weights[60,c]),'lineage_registry_id':c,
            'old_member_window_flags':','.join(str(int(marks['flags'][i]&1)) for i in gi[members]),
            'old_member_selected_flags':','.join(str(int(bool(marks['flags'][i]&2))) for i in gi[members])}
        rows_out.append(row);source_shape[row['actual_state']]+=1
    audit.append({'job':jid,'response_clusters':len(starts),'multi_TES_clusters':int(np.sum(tes_records>=2)),
                  'eligible_multi_TES_clusters':len(eligible),**stat})
    print(jid,'eligible',len(eligible),flush=True)
known=read(O/'data/aa_existing_selection_audit.json')['corrected_existing_selected_contribution_cps']
out={'status':'EXISTING_SAMPLE_BOUND__NOT_FINAL_AA_SELECTION','eligible_new_selection_clusters':len(rows_out),
     'day15_existing_selected_contribution_cps':known,'day15_maximum_additional_selected_cps':float(bound[60]),
     'day15_existing_sample_delayed_rate_interval_cps':[known,known+float(bound[60])],
     'day15_detector_positive_delayed_cluster_rate_cps':float(all_rates[60]),
     'day15_BGO_vetoing_delayed_cluster_rate_cps':float(all_bgo_veto_rates[60]),
     'possible_new_selection_states':dict(source_shape),'jobs':audit,
     'limitation':'Upper bound only; no unknown cluster has been assigned a fabricated energy or Compton decision. It does not cover unsampled chains or nuclear-data corrections.'}
save(O/'data/aa_missing_response_audit.json',out)
write(O/'data/aa_required_pixel_groups.csv',rows_out)
np.savez_compressed(O/'data/aa_local_bounds_81nodes.npz',additional_selected_upper_bound=bound,
                   detector_positive_delayed_rate=all_rates,bgo_vetoing_delayed_rate=all_bgo_veto_rates)
print(json.dumps({k:v for k,v in out.items() if k!='jobs'},indent=2))
