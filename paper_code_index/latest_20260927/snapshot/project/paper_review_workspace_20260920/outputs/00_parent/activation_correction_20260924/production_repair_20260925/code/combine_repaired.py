"""Subtract affected legacy points; add independent restored-parent response."""
from pathlib import Path
import sys,json,collections,shutil
import numpy as np
P=Path(__file__).resolve().parents[1];O=P.parent;T=O/'targeted_response';OLD=T/'final';FINAL=P/'final'
read=lambda p:json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def link(p,t):
    if not p.exists():p.symlink_to(t)

def main():
    assert read(P/'data/repair_ledger_summary.json')['files_processed']==246
    assert (P/'responses/compact_summary.json').exists()
    FINAL.mkdir(exist_ok=True);(FINAL/'code').mkdir(exist_ok=True);(FINAL/'validation').mkdir(exist_ok=True)
    # Import the pinned scientific constants/geometry; route every output to
    # this dated repair package, never to either earlier result package.
    common=f'''import importlib.util,sys
from pathlib import Path
_source=Path({str(O/'code/common.py')!r})
sys.path.append(str(_source.parent))
_spec=importlib.util.spec_from_file_location('prior_correction_common',_source)
_m=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_m)
for _k,_v in vars(_m).items():
    if not _k.startswith('_'):globals()[_k]=_v
O=Path({str(FINAL)!r})
def background(model):
    d=O/'data'/model/'response';m=read(d/'manifest.json')
    return {{k:np.load(d/(k+'.npy'),mmap_mode='r') for k in m['arrays']}},read(d/'category_registry.json')['categories'],np.load(d/'category_factors.npy')
'''
    (FINAL/'code/common.py').write_text(common)
    for name in ['analyze.py','prepare_timelines.py','run_corrected_timelines.py','integrate_corrected.py']:
        shutil.copyfile(O/'code'/name,FINAL/'code'/name)
    for name in ['timeline_deferred','continuous_disk.py']:link(FINAL/'code'/name,O/'code'/name)
    regnew=read(P/'data/restored_registry.json');rates=np.load(P/'data/restored_rates_81nodes.npy');plans=read(P/'responses/plan.json')
    rem=read(P/'data/remove_RP.json');pointmap={};matches=[]
    for r in rem:
        key=r['model'],r['family'];pt=O/'data'/f'points_{key[0]}_{key[1]}.json'
        if key not in pointmap:pointmap[key]=read(pt)['points'] if pt.exists() else []
        pp=[p for p in pointmap[key] if p['za']==r['za'] and abs(p['exc']-r['exc'])<.101 and p['volume']==r['volume'] and np.linalg.norm(np.array([p[k] for k in ['x','y','z']])-r['xyz'])<5e-5]
        assert len(pp)<=1,(r,pp)
        matches.append(dict(**r,legacy_point_ids=[p['point_id'] for p in pp],legacy_source_blocks=sum(p['source_blocks'] for p in pp)))
    save(P/'data/removed_point_mapping.json',matches)
    jobs=read(O/'data/runtime_jobs.json');oldplans=[]
    for p in sorted(T.glob('batch*/plan.json')):oldplans.extend(read(p))
    for model in ['a','b']:
        old=OLD/'data'/model;dest=FINAL/'data'/model;resp=dest/'response';resp.mkdir(parents=True,exist_ok=True)
        for name in ['signal_catalog.npz','signal_summary.json']:link(dest/name,old/name)
        man=read(old/'response/manifest.json');arr={k:np.load(old/'response'/(k+'.npy'),mmap_mode='r') for k in man['arrays']};base=np.array(arr['event_base_weight_cps']);removed_ids=[]
        bad={f:set(p for r in matches if r['model']==model and r['family']==f for p in r['legacy_point_ids']) for f in {r['family'] for r in matches if r['model']==model}}
        for j in jobs:
            if j['model']!=model or not bad.get(j['family']):continue
            identity=np.load(O/'data/decay_metadata'/(j['job_id']+'.response.npz'));mapping=np.load(O/'data/decay_metadata'/(j['job_id']+'.map.npz'))
            ix=identity['global_index'];pid=mapping['point_id'][identity['event_id'].astype('i8')-1];removed_ids.extend(ix[np.isin(pid,list(bad[j['family']]))].tolist())
        offset=len(np.load(O/'data'/model/'response/event_base_weight_cps.npy',mmap_mode='r'))
        for r in oldplans:
            if r['model']!=model:continue
            if bad.get(r['family']):
                pid=np.load(Path(r['directory'])/'draws.npz')['point_id'];removed_ids.extend((offset+np.flatnonzero(np.isin(pid,list(bad[r['family']])))).tolist())
            offset+=r['events']
        assert offset==len(base)
        removed_ids=np.array(sorted(set(removed_ids)),dtype='i8');base[removed_ids]=0
        reg=read(old/'response/category_registry.json')['categories'];fac=np.load(old/'response/category_factors.npy');nc=len(reg);fac=np.column_stack([fac,rates]);selected=[r for r in read(old/'selected_origins_all.json') if int(r['catalog_index']) not in set(removed_ids)]
        for c in regnew:reg.append(dict(category_id=len(reg),stream='delayed',component='other',family=c['family'],actual_state=c['state'],source_parent_ZA=c['root_za'],restored_registry_id=c['category_id'],response_origin='restored_parent',model=c['model']))
        pieces={k:[base if k=='event_base_weight_cps' else np.asarray(v)] for k,v in arr.items()};final=[np.load(old/'background_broad_continuous.npy')];nh=len(arr['hit_code']);nb=len(base)
        for r in plans:
            if r['model']!=model:continue
            jd=Path(r['directory']);report=read(jd/'compact.json');assert report['status']=='PASS' and report['all_primary_material_locations_verified']
            z=dict(np.load(jd/'compact.npz'));positive=(z['hit_count']>0)|(z['bgo_keV']>0)
            for k in ['bgo_keV','measured_total_keV','hit_count','hit_code','hit_energy_keV']:pieces[k].append(z[k])
            pieces['hit_start'].append(z['hit_start']+nh);pieces['event_category'].append(z['event_category']+nc)
            pieces['event_base_weight_cps'].append(z['event_base_weight_cps']*positive);pieces['event_component'].append(np.zeros(r['events'],dtype='u1'))
            broad=(z['measured_total_keV']>=480)&(z['measured_total_keV']<550);active=z['bgo_keV']<50
            pieces['broad_flags'].append(broad.astype('u1')+4*(broad&active).astype('u1')+16*z['final'].astype('u1'));final.append(z['final'])
            for s in read(jd/'selected.json'):
                c=regnew[s['category']];selected.append(dict(catalog_index=nb+s['event_id']-1,job_id=r['job'],family=r['family'],event_id=s['event_id'],source_parent_ZA=c['root_za'],actual_state=c['state'],actual_ZA=c['za'],source_volume=c['volume'],source_x_cm=c['x'],source_y_cm=c['y'],source_z_cm=c['z'],category_id=nc+c['category_id'],day15_weight_cps=s['day15_weight_cps'],measured_total_keV=s['measured_total_keV']))
            nb+=r['events'];nh+=len(z['hit_code'])
        arrays={k:np.concatenate(v) for k,v in pieces.items()};count=np.bincount(arrays['event_category'][arrays['event_base_weight_cps']>0],minlength=len(reg));sw=np.bincount(arrays['event_category'],weights=arrays['event_base_weight_cps'],minlength=len(reg))
        for i,c in enumerate(reg):c.update(event_count=int(count[i]),sum_event_base_weight_cps=float(sw[i]))
        for k,v in arrays.items():np.save(resp/(k+'.npy'),v)
        np.save(resp/'category_factors.npy',fac);np.save(dest/'background_broad_continuous.npy',np.concatenate(final));np.save(dest/'removed_old_catalog_indices.npy',removed_ids)
        save(resp/'category_registry.json',{'categories':reg});save(resp/'manifest.json',dict(model=model,arrays=list(arrays),source=str(OLD),repair='Exact affected old points removed; restored stopped parents added with per-family production exposure and chain evolution.'))
        save(dest/'selected_origins_all.json',selected);print(model,'combined',nb,'removed old records',len(removed_ids),flush=True)
if __name__=='__main__':main()
