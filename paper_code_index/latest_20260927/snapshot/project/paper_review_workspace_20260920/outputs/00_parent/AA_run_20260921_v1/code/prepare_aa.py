from aa_common import *
import csv, math

CAPS={'gamma':50000,'n':10000,'eminus':20000,'eplus':2000,'p':2000,'alpha':400,'muminus':3000,'muplus':3000}

def prepare():
    if (ROOT/'data/preparation.json').exists():return read(ROOT/'data/preparation.json')
    geo=minimal_geometry();save(ROOT/'data/minimal_geometry.json',geo)
    seeds,seed_audit=occupied_seeds();registry=[]
    ev=read(ASSESS/'data/receipt_storage_evidence.json')
    for r in ev['rows']:seeds.add(r['seed'])
    bundles={};stats={};target_rows=list(csv.DictReader((ASSESS/'JOB_TARGETS.csv').open()))
    for name,minimal,select in [
        ('buildup',False,lambda r:r['mode']=='buildup'),
        ('instant_full',False,lambda r:r['mode']=='instant' and r['recording']=='full_all'),
        ('instant_minimal',True,lambda r:r['recording']=='minimal_init_only')]:
        cfg=config_for(name,MINIMAL_SETUP if minimal else SETUP);jobs=[];sources=[]
        selected=[r for r in target_rows if select(r)]
        # Preserve exact accepted logical targets and sub-shard solely for memory.
        for ref in selected:
            fam=ref['family'];left=int(ref['events']);chunk=0
            estimate_ref=next(x for x in ev['rows'] if x['batch']==ref['reference_batch'] and x['job_id']==ref['reference_job'])
            bpe=(estimate_ref['artifact_bytes'] or estimate_ref['sim_bytes'])/int(ref['events'])
            while left:
                n=min(left,CAPS[fam]);left-=n;chunk+=1
                jid=f"aa0_{name}_{ref['target_id']}_{chunk:03d}_{fam}"
                seed=new_seed(jid,seeds);registry.append({'job_id':jid,'seed':seed})
                j=job_row(cfg,len(jobs)+1,jid,fam,ref['mode'],n,seed,2*bpe*n+10_000_000,ref)
                C.write_once_text(Path(j['source_path']),source_text(fam,ref['mode'],jid,seed,n,Path(j['output_prefix']),Path(cfg['geometry_setup']),minimal))
                jobs.append(j);sources.append(source_row(j))
        # Interleave families to avoid starving slow/rare families at the deadline.
        queues={f:[j for j in jobs if j['family']==f] for f in FAMILIES};ordered=[]
        while any(queues.values()):
            for f in FAMILIES:
                if queues[f]:ordered.append(queues[f].pop(0))
        for i,j in enumerate(ordered):j['ordinal']=i+1
        bundles[name]=finish_bundle(name,cfg,ordered,sources)
        stats[name]={'jobs':len(jobs),'events':sum(j['events'] for j in jobs),'by_family':{f:sum(j['events'] for j in jobs if j['family']==f) for f in FAMILIES}}
    # Complete physical signal, from outside every AA layer. The focal coordinates
    # and TES placement are unchanged from the corrected A input mapping.
    cfg=config_for('signal',SETUP,'focused_eventlist');jid='aa0_signal_37175';seed=new_seed(jid,seeds);registry.append({'job_id':jid,'seed':seed})
    j=job_row(cfg,1,jid,'focused511','signal',37175,seed,256*2**20)
    base=(SIGNAL/'configs/signal_a.source').read_text();old=re.search(r'^Run (\S+)',base,re.M).group(1)
    t=base.replace(old,jid);t=re.sub(r'^Geometry .*$',f'Geometry {SETUP}',t,flags=re.M);t=re.sub(r'^Seed .*$',f'Seed {seed}',t,flags=re.M);t=re.sub(r'^\S+\.FileName .*$',f'{jid}.FileName {j["output_prefix"]}',t,flags=re.M)
    C.write_once_text(Path(j['source_path']),t);bundles['signal']=finish_bundle('signal',cfg,[j],[source_row(j)])
    # Intentional same-seed diagnostic pair, never pooled into production counts.
    pair_seed=new_seed('aa0_representation_alpha100',seeds)
    for name,setup,record in [('pilot_full',SETUP,'all'),('pilot_minimal_all',MINIMAL_SETUP,'all'),('pilot_minimal_init',MINIMAL_SETUP,'init-only')]:
        cfg=config_for(name,setup);jid='aa0_'+name+'_alpha100'
        j=job_row(cfg,1,jid,'alpha','instant',100,pair_seed,256*2**20)
        t=source_text('alpha','instant',jid,pair_seed,100,Path(j['output_prefix']),setup,record=='init-only')
        C.write_once_text(Path(j['source_path']),t);bundles[name]=finish_bundle(name,cfg,[j],[source_row(j)])
        registry.append({'job_id':jid,'seed':pair_seed,'diagnostic_pair_only':True,'production_credit':False})
    freeze=frozen_geometry()
    save(ROOT/'data/seed_registry.json',{'status':'PASS__REGISTERED_FRESH_AA_SEEDS','seeds':registry,'occupied_prior_count':len(seeds)-len(registry)+2,'deliberate_pair_seed':pair_seed,'prior_registry_audit':seed_audit})
    result={'status':'PASS__AA_PREPARED_NOT_LAUNCHED','created_at':utc(),'start_unix':START,'deadline_unix':DEADLINE,'reserve_bytes':RESERVE,'global_max_workers':12,'adaptive_workers':True,'bundles':bundles,'statistics':stats,'geometry_hashes':freeze,'minimal_geometry':geo,'compton_sha256':sha(SIGNAL/'code/pixel_geometry_compton.py'),'response':{'fwhm_keV':.5,'pixel_threshold_keV':.3,'bgo_threshold_keV':50,'narrow_window_keV':[510.5,511.5],'plastic_volumes':[],'bgo_volumes':BGO,'reference_disk_local_cm':[-13.1,0,-5.2],'reference_disk_radius_cm':1.898,'physical_aperture_radius_cm':2.7,'launch_plane_local_x_cm':-60.,'reference_policy':'retain A optical reference mapping; actual mechanical aperture and entire envelope transported'},'script_only_resource_monitoring':True,'observer_notifications':'exceptions/deadline/completion only','production_topup_policy':'only after matching every baseline stratum; proportional full-chain 10-percent increments with fresh inventory epochs'}
    assert sum(stats[k]['events'] for k in ['instant_full','instant_minimal'])==23005699
    assert stats['buildup']['events']==3045028
    save(ROOT/'data/preparation.json',result)
    return result
if __name__=='__main__':
    r=prepare();print(json.dumps({k:r[k] for k in ['status','statistics','reserve_bytes','deadline_unix']},indent=2))
