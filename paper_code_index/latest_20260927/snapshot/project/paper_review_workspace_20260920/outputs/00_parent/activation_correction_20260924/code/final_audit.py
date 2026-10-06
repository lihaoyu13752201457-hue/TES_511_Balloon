"""Bounded audit of final artifacts; never run transport or edit a manuscript."""
from pathlib import Path
import hashlib,json,csv,math,collections
import numpy as np
O=Path(__file__).resolve().parents[1];T=O/'targeted_response';F=T/'final'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def csvout(p,rr):
    with p.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
plans=sum([read(T/b/'plan.json') for b in ['batch01','batch02']],[])
assert sum(r['events'] for r in plans)+2000==2000000
assert len({r['seed'] for r in plans})==len(plans)==60
for r in plans:
    d=Path(r['directory']);c=read(d/'compact.json');receipt=read(d/'receipt.json')
    assert c['status']=='PASS' and c['decoder']=='native_HTsim_v1'
    assert c['events']==r['events'] and c['seed_verified'] and c['one_init_per_event'] and c['no_daughter_queue']
    assert sha(Path(r['source']))==r['source_sha256']
    assert sha(Path(r['geometry']))==r['geometry_setup_sha256']
ref=read(O/'validation/manuscript_reference.json');assert sha(Path(ref['path']))==ref['sha256']
source_base=Path('/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data')
manifests={'a':source_base/'AA/aa_reproduce_A_20260921_v1/delayed_epoch0_inventory/generated/activation/manifest.json','b':source_base/'SH3/sh3_optv3_m05_delayed_activation_v1/generated/activation/manifest.json'}
held=[];unknown=[]
for m,path in manifests.items():
    for c in read(path)['source_cells']:
        held.extend(dict(model=m,family=c['family'],manifest=str(path),**s) for s in c.get('holdout_states',[]) if (s['day15_activity_Bq'] or 0)>0)
        unknown.extend(dict(model=m,family=c['family'],manifest=str(path),**s) for s in c.get('holdout_states',[]) if s['day15_activity_Bq'] is None)
save(F/'data/positive_source_holdouts.json',held)
save(F/'data/unknown_source_holdouts.json',unknown)
jobs=read(O/'data/runtime_jobs.json');tables=[];closure={}
for m in ['a','b']:
    d=F/'data'/m/'response';reg=read(d/'category_registry.json')['categories'];fac=np.load(d/'category_factors.npy')
    a={k:np.load(d/(k+'.npy'),mmap_mode='r') for k in ['event_category','event_base_weight_cps','hit_count','bgo_keV','measured_total_keV']}
    cat=a['event_category'];base=a['event_base_weight_cps'];weight=base*fac[60,cat]
    pos=(a['hit_count']>0)|(a['bgo_keV']>0)
    assert not np.any((weight>0)&~pos)
    streams=np.array([c['stream'] for c in reg]);fam=np.array([c['family'] for c in reg])
    oldd=O/'data'/m/'response';oldcat=np.load(oldd/'event_category.npy',mmap_mode='r');oldreg=read(oldd/'category_registry.json')['categories']
    prompt=np.array([c['stream']=='prompt' for c in oldreg])[oldcat];n=len(oldcat)
    for k in ['event_category','event_base_weight_cps','bgo_keV','measured_total_keV']:
        old=np.load(oldd/(k+'.npy'),mmap_mode='r');assert np.array_equal(a[k][:n][prompt],old[prompt])
    oldfac=np.load(oldd/'category_factors.npy');pc=np.flatnonzero(np.array([c['stream']=='prompt' for c in oldreg]));assert np.array_equal(fac[:,pc],oldfac[:,pc])
    origins=read(F/'data'/m/'selected_origins_all.json');stats=read(F/'data'/m/'direct_statistics.json')['compton_trajectory_veto']
    assert len(origins)==stats['delayed']['n']
    assert math.isclose(sum(float(r['day15_weight_cps']) for r in origins),stats['delayed']['rate'],rel_tol=1e-12)
    assert math.isclose(sum(stats[k]['rate'] for k in ['gamma','non_gamma','delayed']),stats['total']['rate'],rel_tol=1e-12)
    for family in ['gamma','n','eminus','eplus','p','alpha','muminus','muplus']:
        ix=(streams[cat]=='delayed')&(fam[cat]==family)&(weight>0)
        tables.append(dict(model=m,family=family,original_raw_decay_records=sum(j['events'] for j in jobs if (j['model'],j['family'])==(m,family)),targeted_independent_histories=sum(j['events'] for j in plans if (j['model'],j['family'])==(m,family)),positive_response_groups=int(ix.sum()),day15_detector_positive_rate_cps=float(weight[ix].sum()),single_delayed_equivalent_exposure=None))
    meta=read(F/'data'/m/'metadata.json')['anchors']['60']
    assert math.isclose(sum(r['day15_detector_positive_rate_cps'] for r in tables if r['model']==m),meta['delayed_rate'],rel_tol=1e-12)
    closure[m]=dict(selected_delayed_groups=len(origins),origin_rate_closure=True,prompt_responses_and_81node_weights_unchanged=True,zero_deposit_arrival_rate=0,detector_positive_rate_day15_cps=meta['total_background_rate'],heldout_direct_source_activity_Bq=sum(r['day15_activity_Bq'] for r in held if r['model']==m))
csvout(F/'data/table3_delayed_replacement.csv',tables);save(F/'data/table3_delayed_replacement.json',tables)
save(F/'validation/final_input_and_response_audit.json',dict(status='PASS',production_histories=1998000,validation_histories=2000,total_authorized_histories=2000000,independent_production_jobs=60,manuscript_unchanged=True,manuscript_sha256=ref['sha256'],response_closure=closure,scope='These checks do not establish completeness of nuclear data or source-bank holdouts.'))
print(json.dumps(closure,indent=2))
