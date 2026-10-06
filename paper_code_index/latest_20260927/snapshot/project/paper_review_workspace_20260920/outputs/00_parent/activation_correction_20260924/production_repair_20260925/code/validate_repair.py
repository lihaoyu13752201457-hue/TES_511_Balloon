from pathlib import Path
import json,numpy as np,hashlib,math,collections,gzip
P=Path(__file__).resolve().parents[1];O=P.parent;F=P/'final';OLD=O/'targeted_response/final'
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ledger=read(P/'data/repair_ledger.json');rem=read(P/'data/remove_RP.json');held=read(O/'closure_followup/data/heldout_ancestry.json');holdouts=[]
for r in held:
    matches=[s for s in rem if s['model']==r['model'] and s['family']==r['family'] and s['event_id']==r['event_id'] and s['za']==r['za'] and abs(s['exc']-r['exc_keV'])<.02 and np.linalg.norm(np.array(s['xyz'])-[r['x'],r['y'],r['z']])<5e-5]
    assert len(matches)==1,(r,matches);parent=ledger[matches[0]['ledger_id']]['parent'];assert parent==r['earliest_long_parent'];holdouts.append(dict(holdout_index=r['holdout_index'],ledger_id=matches[0]['ledger_id'],restored_parent=parent))
assert len(holdouts)==11
report=read(P/'data/repair_ledger_summary.json');assert report['files_processed']==246 and report['unresolved_groups']==report['uncertain_descendant_joins']==0
modelcheck={}
for model in ['a','b']:
    old=OLD/'data'/model;new=F/'data'/model;manifest=read(old/'response/manifest.json');checks={}
    for k in manifest['arrays']:
        a=np.load(old/'response'/(k+'.npy'),mmap_mode='r');b=np.load(new/'response'/(k+'.npy'),mmap_mode='r');assert np.array_equal(a,b[:len(a)]),(model,k);checks[k]=len(a)
    a=np.load(old/'response/category_factors.npy');b=np.load(new/'response/category_factors.npy');assert np.array_equal(a,b[:,:a.shape[1]])
    before=read(old/'direct_statistics.json')['compton_trajectory_veto'];after=read(new/'direct_statistics.json')['compton_trajectory_veto'];target=read(P/'data/response_uncertainty.json')['models'][model]['added_day15_selected_cps']
    for name in ['gamma','non_gamma']:assert before[name]==after[name]
    assert abs(after['delayed']['rate']-before['delayed']['rate']-target)<1e-12
    assert sha(old/'signal_catalog.npz')==sha(new/'signal_catalog.npz')
    modelcheck[model]={'legacy_response_arrays_unchanged':checks,'legacy_81node_factors_unchanged':True,'signal_catalog_unchanged':True,'prompt_statistics_unchanged':True,'direct_rate_increment_closed_cps':target}
plans=read(P/'responses/plan.json');seeds=[r['seed'] for r in plans];assert len(seeds)==len(set(seeds))==12
for r in plans:
    d=Path(r['directory']);v=read(d/'compact.json');assert v['status']=='PASS' and v['seed_verified'] and v['one_init_per_event'] and v['no_daughter_queue'] and v['events']==r['events'];assert sha(r['source'])==r['source_sha256'] and sha(d/'events.dat')==r['eventlist_sha256']
assert sum(r['events'] for r in plans)==160000
mp=O.parent/'final_manuscript_20260924_authors_antarctic/paper_clean.tex';assert sha(mp)=='dc856b91bd357c0f3ecc5f674a0238cc0b30784d3dcc0ad5b655a02b5f23989d'
orig=Path('/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCSteppingAction.cc');assert sha(orig)==read(O/'targeted_response/build_manifest.json')['original_sha256']
out={'status':'PASS','production_files':246,'retained_primary_histories':15367941,'restored_parents':len(ledger),'removed_stored_descendants':len(rem),'eleven_previous_holdouts_closed':holdouts,'models':modelcheck,'valid_new_response_histories':160000,'excluded_default_seed_duplicate_histories':40000,'geometry_check_histories':523,'new_atmospheric_production_histories':0,'valid_response_seeds_unique':True,'original_installation_source_unchanged':True,'manuscript_unchanged_sha256':sha(mp),'prompt_mode_audit':read(P/'data/prompt_mode_validation.json')['status']}
(P/'data/final_validation.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS: production ledger, holdouts, response weighting, seed isolation, original-data/manuscript boundaries',flush=True)
