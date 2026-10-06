"""Disjoint merge: existing supported response plus independent targeted pools."""
from common import *
from targeted_environment import T
from collections import Counter,defaultdict
FINAL=T/'final';FINAL.mkdir(exist_ok=True)
if not (FINAL/'code').exists():(FINAL/'code').symlink_to(O/'code',target_is_directory=True)
(FINAL/'validation').mkdir(exist_ok=True)
physical=read(T/'physical_registry.json');prates=np.load(T/'physical_rates_81nodes.npy');lookup={(r['model'],r['family'],r['root_za'],r['state']):r for r in physical}
support={(r['model'],r['family'],int(r['source_parent_ZA']),r['actual_state']):float(r['expected_one_us_groups']) for r in rows(O/'data/state_support_rows.csv')}
plans=[]
for p in sorted(T.glob('batch*/plan.json')):
    assert (p.parent/'compact_summary.json').exists(),p
    plans.extend(read(p))
ntotal=Counter()
for r in plans:ntotal[r['model'],r['stratum'],r['family']]+=r['events']

def run(model):
    d=FINAL/'data'/model;dest=d/'response';dest.mkdir(parents=True,exist_ok=True)
    for name in ['signal_catalog.npz','signal_summary.json']:
        if not (d/name).exists():(d/name).symlink_to(O/'data'/model/name)
    a,oldreg,oldfac=background(model);reg=[dict(c) for c in oldreg];fac=oldfac.copy()
    replacements=[]
    for i,c in enumerate(reg):
        if c['stream']!='delayed' or 'actual_state' not in c:continue
        key=(model,c['family'],c['source_parent_ZA'],c['actual_state']);p=lookup.get(key)
        if p is None or p['policy']=='targeted':
            fac[:,i]=0.;replacements.append(dict(category=i,key=key,reason='targeted replacement' if p else 'absent physical category'))
        else:
            den=support[key];assert den>0
            fac[:,i]=prates[:,p['category_id']]/den
            c['physical_registry_id']=p['category_id']
    nc=len(reg);fac=np.column_stack([fac,prates])
    for c in physical:
        reg.append(dict(category_id=len(reg),stream='delayed',component='other',family=c['family'],actual_state=c['state'],source_parent_ZA=c['root_za'],physical_registry_id=c['category_id'],response_origin='targeted',event_count=0,sum_event_base_weight_cps=0.,**{'model':c['model']}))
    fields=['bgo_keV','measured_total_keV','hit_start','hit_count','event_category','event_component','event_base_weight_cps','broad_flags','hit_code','hit_energy_keV']
    pieces={k:[np.asarray(a[k])] for k in fields};final=[np.load(O/'data'/model/'background_broad_continuous.npy')];nh=len(a['hit_code']);nb=len(a['hit_count']);selected=[];pool_rows=[]
    for r in plans:
        if r['model']!=model:continue
        jd=Path(r['directory']);report=read(jd/'compact.json');assert report.get('decoder')=='native_HTsim_v1' and report['status']=='PASS'
        z=dict(np.load(jd/'compact.npz'));N=ntotal[model,r['stratum'],r['family']];scale=r['events']/N
        # Multiple batches of the same pool share a fixed proposal law; divide
        # by the combined N, never add two full independently-normalized rates.
        pieces['bgo_keV'].append(z['bgo_keV']);pieces['measured_total_keV'].append(z['measured_total_keV']);pieces['hit_start'].append(z['hit_start']+nh);pieces['hit_count'].append(z['hit_count']);pieces['hit_code'].append(z['hit_code']);pieces['hit_energy_keV'].append(z['hit_energy_keV'])
        cat=z['event_category']+nc;pieces['event_category'].append(cat)
        # Keep all generated histories in the normalization denominator, but
        # only actual TES/BGO deposits can trigger the coincidence timeline.
        detector_positive=(z['hit_count']>0)|(z['bgo_keV']>0)
        pieces['event_base_weight_cps'].append(z['event_base_weight_cps']*scale*detector_positive);pieces['event_component'].append(np.zeros(r['events'],dtype='u1'))
        broad=(z['measured_total_keV']>=480)&(z['measured_total_keV']<550);active=z['bgo_keV']<50
        pieces['broad_flags'].append(broad.astype('u1')+4*(broad&active).astype('u1')+16*z['final'].astype('u1'));final.append(z['final'])
        for s in read(jd/'selected.json'):
            c=physical[s['category']];pt=read(O/'data'/f"points_{model}_{r['family']}.json")['points'][s['point_id']]
            selected.append(dict(catalog_index=nb+s['event_id']-1,job_id=r['job'],batch=jd.parent.name,family=r['family'],event_id=s['event_id'],source_parent_ZA=c['root_za'],actual_state=c['state'],actual_ZA=c['za'],source_volume=pt['volume'],source_x_cm=pt['x'],source_y_cm=pt['y'],source_z_cm=pt['z'],category_id=nc+c['category_id'],day15_weight_cps=s['day15_weight_cps']*scale,measured_total_keV=s['measured_total_keV']))
        pool_rows.append({**report,'combined_pool_N':N,'normalization_scale':scale})
        nh+=len(z['hit_code']);nb+=r['events']
    arrays={k:np.concatenate(v) for k,v in pieces.items()}
    count=np.bincount(arrays['event_category'][arrays['event_base_weight_cps']>0],minlength=len(reg));sw=np.bincount(arrays['event_category'],weights=arrays['event_base_weight_cps'],minlength=len(reg))
    for i,c in enumerate(reg):c.update(event_count=int(count[i]),sum_event_base_weight_cps=float(sw[i]))
    for key,arr in arrays.items():np.save(dest/(key+'.npy'),arr)
    np.save(d/'background_broad_continuous.npy',np.concatenate(final));np.save(dest/'category_factors.npy',fac)
    save(dest/'category_registry.json',{'categories':reg});save(dest/'manifest.json',{'arrays':fields,'model':model,'response':'Existing supported categories reweighted by corrected inventory. Targeted categories disjoint; multiple batches normalized jointly within their identical source pool.'})
    old=[]
    for r in rows(O/'data'/model/'selected_delayed_origins.csv'):
        c=int(r['category_id']);rate=fac[60,c]
        if rate<=0:continue
        old.append({**r,'day15_weight_cps':float(rate)})
    save(d/'selected_origins_all.json',old+selected);save(d/'targeted_pool_summary.json',pool_rows);save(d/'replaced_categories.json',replacements)
    print(model,'combined',nb,'events',len(old),'retained selections +',len(selected),'new independent selections',flush=True)
for model in sys.argv[1:] or ['a','b']:run(model)
