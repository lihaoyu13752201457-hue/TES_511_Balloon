"""Use the retained P56/SF3 inventory algorithms on AA receipts only."""
from aa_common import *
import math,csv

def prepare(name='delayed_epoch0',buildup_config=None,total_per_family=1000000):
    if (ROOT/'data'/f'{name}_prepared.json').exists():return read(ROOT/'data'/f'{name}_prepared.json')
    prep=read(ROOT/'data/preparation.json');cfg=C.load_config(buildup_config or prep['bundles']['buildup']);jobs=C.load_plan(cfg)
    assert all(C.load_bound_receipt(cfg,j) for j in jobs),'incomplete AA buildup'
    adapter=loadmod('aa_inventory_reference_'+name,G/'56_sg3b_m05_delayed_20260817/prepare_sg3b_m05_delayed.py')
    target=DATA/(name+'_inventory');gen=target/'generated'
    adapter.CANDIDATE='AA';adapter.PROFILE_ID='AA_8H_'+name+'_inventory';adapter.GEOMETRY=SETUP
    adapter.TARGET=target;adapter.GENERATED=gen;adapter.RUN_ROOT=target/'run'
    adapter.INPUTS=(('AA_epoch',cfg['profile_id'],Path(cfg['run_root'])),)
    original_core=adapter.load_reused_primitives
    def core():
        module=original_core()
        material=module['material_category'];inventory=read(AA/'data/component_inventory.json')
        def aa_material(vol):
            if vol in BGO:return 'active_scintillator'
            if inventory.get(vol,{}).get('Material')=='Tungsten':return 'passive_w_or_collimator'
            return material(vol)
        # Patch function globals too: runpy returns a dictionary distinct from
        # individual function globals in some Python versions.
        for v in list(module.values()):
            if callable(v) and hasattr(v,'__globals__'):v.__globals__['material_category']=aa_material
        module['material_category']=aa_material
        return module
    adapter.load_reused_primitives=core
    occupied,audit=occupied_seeds()
    def seeds(_):return {f:new_seed(name+'_mixture_'+f,occupied) for f in FAMILIES}
    adapter.derive_seeds=seeds
    adapter.prepare()
    manifest=read(gen/'activation/manifest.json');assert all(x['family'] in FAMILIES for x in manifest['activation_cells'])
    cfg2=config_for(name,SETUP,'m05_exact_position_delayed');newjobs=[];rows=[];registry=[]
    for cell in manifest['source_cells']:
        if cell['execution_disposition']=='SKIP_ZERO_A15':continue
        family=cell['family'];base=Path(cell['source_path']).read_text();oldrun=re.search(r'^Run (\S+)',base,re.M).group(1)
        remaining=total_per_family;i=0
        while remaining:
            n=min(100000,remaining);remaining-=n;i+=1;jid=f'aa_{name}_{family}_{i:03d}';seed=new_seed(jid,occupied);registry.append({'job_id':jid,'seed':seed})
            job=job_row(cfg2,len(newjobs)+1,jid,family,'delayed',n,seed,350_000_000,{'inventory_manifest':str(gen/'activation/manifest.json'),'positions_path':cell['positions_path'],'activity_Bq':cell['transported_ground_activity_Bq'],'sum_TT_s':cell['sum_TT_s']})
            text=base.replace(oldrun,jid);text=re.sub(r'^Seed .*$',f'Seed {seed}',text,flags=re.M);text=re.sub(r'^\S+\.FileName .*$',f'{jid}.FileName {job["output_prefix"]}',text,flags=re.M);text=re.sub(r'^\S+\.Triggers .*$',f'{jid}.Triggers {n}',text,flags=re.M)
            C.write_once_text(Path(job['source_path']),text);newjobs.append(job);rows.append(source_row(job))
    out={'inventory_manifest':str(gen/'activation/manifest.json'),'zero_families':manifest['zero_source_families'],'source_seeds':registry,'events_per_positive_family':total_per_family}
    if newjobs:out['config']=finish_bundle(name,cfg2,newjobs,rows)
    else:out['config']=None
    out['status']='PASS__AA_OWN_INVENTORY_DELAYED_READY';save(ROOT/'data'/f'{name}_prepared.json',out)
    current=read(ROOT/'data/seed_registry.json');current['seeds'].extend(registry);current['seeds'].extend({'job_id':name+'_mixture_'+c['family'],'seed':c['seed'],'role':'mixture_rng'} for c in manifest['source_cells']);save(ROOT/'data/seed_registry.json',current)
    return out
if __name__=='__main__':print(json.dumps(prepare(),indent=2))
