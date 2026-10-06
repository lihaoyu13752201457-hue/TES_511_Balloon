"""Normalize completed AA epochs and assemble mmap replay inputs on the 2 TB disk."""
from aa_common import *
import csv,math,collections,shutil
import numpy as np
Q=Path('/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823')
FLUX=loadmod('aa_flux_closure',Q/'code/build_fluxclosed_catalog.py')
P58=loadmod('aa_inventory_evolution',G/'58_sg3b_m05_common_time_response_20260817/code/analyze_sg3b_common_time.py')
OUT=DATA/'derived/merged'
EVENT_DT={'plastic_keV':'f4','bgo_keV':'f4','measured_total_keV':'f4','broad_flags':'u1','w2_flags':'u1','hit_start':'i8','hit_count':'u2','event_category':'i4','event_component':'u1','event_base_weight_cps':'f8','continuum_importance_weight':'f8','source_bin80':'u1'}
HIT_DT={'hit_code':'i4','hit_layer':'u1','hit_energy_keV':'f4','hit_x_cm':'f4','hit_y_cm':'f4','hit_z_cm':'f4'}

def csvrows(p):return list(csv.DictReader(Path(p).open()))
def inventory_epochs():
    base=read(ROOT/'data/baseline_transport_complete.json');epochs=[{'epoch':0,'configs':{k:v for k,v in read(ROOT/'data/campaign_launch.json')['configs'].items()},'delayed':base['delayed']}]
    ledger=ROOT/'data/proportional_epochs.json'
    if ledger.exists():epochs.extend(x for x in read(ledger)['epochs'] if x['status']=='PASS__TRANSPORT_COMPLETE')
    return epochs

def merge():
    if (OUT/'manifest.json').exists():return read(OUT/'manifest.json')
    assert not OUT.exists(),'partial merge exists; preserve for explicit recovery'
    epochs=inventory_epochs();plans=[];inventories={};totaltt=collections.defaultdict(float);delayed_n=collections.defaultdict(int);buildtt=collections.defaultdict(float)
    for epoch in epochs:
        ei=epoch['epoch'];inv=read(epoch['delayed']['inventory_manifest']);inventories[ei]=inv
        for cell in inv['activation_cells']:buildtt[(ei,cell['family'])]=cell['sum_TT_s']
        configs={k:v for k,v in epoch['configs'].items() if k.startswith('instant')}
        if epoch['delayed']['config']:configs['delayed']=epoch['delayed']['config']
        for path in configs.values():
            cfg=C.load_config(path)
            for job in C.load_plan(cfg):
                r=C.load_bound_receipt(cfg,job);assert r,job['job_id']
                mp=DATA/'derived/catalogs'/cfg['profile_id']/f"job_{job['ordinal']:03d}_{job['job_id']}.json"
                meta=read(mp);assert meta['AA_audit']['status']=='PASS'
                if job['mode']=='instant':totaltt[job['family']]+=r['isotope_dat']['TT_s']
                else:delayed_n[(ei,job['family'])]+=job['events']
                plans.append((ei,job,meta))
    assert all(totaltt[f]>0 for f in FAMILIES)
    catcounts=collections.Counter();nhits=0
    for ei,j,m in plans:
        if time.time()>DEADLINE-30:raise RuntimeError('deadline: merge interrupted; staging files retained')
        with np.load(m['catalog_path'],allow_pickle=False) as a:
            nhits+=len(a['hit_code'])
            if j['mode']=='instant':catcounts[('prompt',j['family'],-1,-1)]+=len(a['event_id'])
            else:
                za,n=np.unique(a['source_za'],return_counts=True)
                for z,c in zip(za,n):catcounts[('delayed',j['family'],ei,int(z))]+=int(c)
    catcounts={k:v for k,v in sorted(catcounts.items()) if v>0};nevents=sum(catcounts.values())
    required=nevents*sum(np.dtype(t).itemsize for t in EVENT_DT.values())+nhits*sum(np.dtype(t).itemsize for t in HIT_DT.values())
    assert shutil.disk_usage(DISK).free-required>RESERVE+GiB
    OUT.mkdir(parents=True)
    arrays={k:np.lib.format.open_memmap(OUT/(k+'.npy'),mode='w+',dtype=t,shape=(nevents,)) for k,t in EVENT_DT.items()}
    arrays.update({k:np.lib.format.open_memmap(OUT/(k+'.npy'),mode='w+',dtype=t,shape=(nhits,)) for k,t in HIT_DT.items()})
    starts={};offset=0
    for k,n in catcounts.items():starts[k]=offset;offset+=n
    cursor=starts.copy();catid={k:i for i,k in enumerate(catcounts)};hitoffset=0;flux=FLUX.SourceClosure();boundary_count=0
    for ei,j,m in plans:
        if time.time()>DEADLINE-30:raise RuntimeError('deadline: merge interrupted; staging files retained')
        with np.load(m['catalog_path'],allow_pickle=False) as z:a={k:z[k] for k in z.files}
        count=len(a['hit_code'])
        for k in HIT_DT:arrays[k][hitoffset:hitoffset+count]=a[k]
        keys=[('prompt',j['family'],-1,-1)] if j['mode']=='instant' else [('delayed',j['family'],ei,int(za)) for za in np.unique(a['source_za'])]
        for key in keys:
            idx=np.arange(len(a['event_id'])) if key[0]=='prompt' else np.flatnonzero(a['source_za']==key[3]);n=len(idx)
            if not n:continue
            sl=slice(cursor[key],cursor[key]+n);cursor[key]+=n
            for field in ['plastic_keV','bgo_keV','measured_total_keV','broad_flags','w2_flags','hit_count']:arrays[field][sl]=a[field][idx]
            arrays['hit_start'][sl]=a['hit_start'][idx]+hitoffset;arrays['event_category'][sl]=catid[key]
            gamma=key[0]=='prompt' and j['family']=='gamma';arrays['event_component'][sl]=int(gamma);arrays['source_bin80'][sl]=255
            importance=np.ones(n)
            if gamma:
                direction=a['primary_dir_z'][idx];bins=FLUX.source_bin20_from_dir_z(direction)
                importance=flux.importance(bins,a['primary_energy_keV'][idx]);boundary_count+=int(FLUX.boundary_candidates(direction)[0].sum())
            if key[0]=='prompt':base=1/totaltt[j['family']]
            else:
                cell=next(x for x in inventories[ei]['source_cells'] if x['family']==j['family'])
                denom=sum(buildtt[(e['epoch'],j['family'])] for e in epochs)
                base=cell['transported_ground_activity_Bq']/delayed_n[(ei,j['family'])]*buildtt[(ei,j['family'])]/denom
            arrays['continuum_importance_weight'][sl]=importance;arrays['event_base_weight_cps'][sl]=base*importance
        hitoffset+=count
    assert hitoffset==nhits and all(cursor[k]==starts[k]+n for k,n in catcounts.items())
    p58cfg=read(G/'58_sg3b_m05_common_time_response_20260817/analysis_inputs.json');scales=csvrows(PROJECT/p58cfg['mission']['family_scales'])
    components=csvrows(Q/'outputs/00_source_closure/trajectory_component_scales_81nodes.csv')
    invs={ei:P58.inventory_authority(inv) for ei,inv in inventories.items()};curves={ei:P58.activity_curves(inv,scales) for ei,inv in invs.items()}
    factors=np.ones((81,len(catcounts)));cats=[]
    for key,n in catcounts.items():
        stream,fam,ei,za=key;i=catid[key];sl=slice(starts[key],starts[key]+n);q=arrays['event_base_weight_cps'][sl]
        if stream=='prompt':
            factors[:,i]=[float(row['gamma_continuum_scale_to_reference']) for row in components] if fam=='gamma' else [float(row[f'scale_{fam}_to_parma_reference']) for row in scales]
        else:factors[:,i]=np.asarray(curves[ei][(fam,za)])/invs[ei][(fam,za)]['day15_activity_Bq']
        cats.append({'category_id':i,'stream':stream,'family':fam,'inventory_epoch':ei,'source_parent_ZA':za,'component':'gamma_continuum' if stream=='prompt' and fam=='gamma' else 'other','event_start':starts[key],'event_count':n,'sum_event_base_weight_cps':float(np.sum(q,dtype=np.float64)),'sum_event_base_weight2_cps2':float(np.sum(q*q,dtype=np.float64))})
    for a in arrays.values():a.flush()
    np.save(OUT/'category_factors.npy',factors)
    save(OUT/'category_registry.json',{'categories':cats})
    result={'status':'PASS__AA_NORMALIZED_REPLAY_INPUTS','at':utc(),'epochs':[e['epoch'] for e in epochs],'events':nevents,'raw_hits':nhits,'input_jobs':len(plans),'prompt_TT_s':dict(totaltt),'files':list(arrays),'gamma_dir_boundary_candidates':boundary_count,'gamma_policy':'retained source_bin20_from_dir_z deterministic printed-boundary rule; one Jcont/Jtotal factor only; no additive mono511','delayed_policy':'each epoch keeps own activity and response; combine per-family physical-rate estimators with buildup-TT weights','sources':{'flux_adapter':str(Q/'code/build_fluxclosed_catalog.py'),'scales':str(PROJECT/p58cfg['mission']['family_scales']),'activity_adapter':str(G/'58_sg3b_m05_common_time_response_20260817/code/analyze_sg3b_common_time.py')},'input_compacts':[m['catalog_path'] for _,_,m in plans]}
    save(OUT/'manifest.json',result);save(ROOT/'data/merge.json',result);return result
if __name__=='__main__':print(json.dumps(merge(),ensure_ascii=False,indent=2))
