"""Read-only final audit of new AA receipts and completed derived products."""
from aa_common import *
import csv,math,collections,datetime,shutil
import numpy as np

def rows(path):return list(csv.DictReader(Path(path).open()))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=3e-10,abs_tol=1e-10),(a,b)

def main():
    deadline=1789977484.7260895
    prep=read(ROOT/'data/preparation.json');delayed=read(ROOT/'data/delayed_epoch0_prepared.json')
    profiles={k:prep['bundles'][k] for k in ['buildup','instant_full','instant_minimal','signal']}
    profiles['delayed_epoch0']=delayed['config']
    summary={};accepted=[];seen_seeds=set();prompt_tt=collections.defaultdict(float);build_tt=collections.defaultdict(float)
    compact_paths=set();artifact_bytes=0;compact_events=0;latest=None
    compton=sha(SIGNAL/'code/pixel_geometry_compton.py')
    for name,path in profiles.items():
        cfg=C.load_config(path);plan=C.load_plan(cfg);C.validate_generated_bundle(cfg,plan)
        totals=collections.Counter()
        for job in plan:
            receipt=C.load_bound_receipt(cfg,job);assert receipt,(name,job['job_id'])
            assert receipt['seed'] not in seen_seeds;seen_seeds.add(receipt['seed'])
            ended=datetime.datetime.fromisoformat(receipt['ended_at']);assert ended.timestamp()<deadline
            latest=max(latest,ended) if latest else ended
            totals[job['family']]+=job['events'];artifact_bytes+=receipt['artifact_bytes']
            assert Path(receipt['sim_path']).stat().st_size==receipt['sim_bytes']
            source=Path(job['source_path']).read_text();assert FORBIDDEN not in source
            if job['mode'] in ['instant','buildup']:
                assert TOKEN in source
                tt=receipt['isotope_dat']['TT_s'];assert tt>0
                (prompt_tt if job['mode']=='instant' else build_tt)[job['family']]+=tt
            if job['mode'] in ['instant','delayed']:
                p=DATA/'derived/catalogs'/cfg['profile_id']/f"job_{job['ordinal']:03d}_{job['job_id']}.json"
                meta=read(p);audit=meta['AA_audit'];assert audit['status']=='PASS'
                assert audit['TS']==job['events'] and audit['source_sha256']==receipt['source_sha256']
                assert audit['corrected_compton_sha256']==compton and audit['truth_positions_used_in_reconstruction'] is False
                assert audit['fwhm_keV']==.5 and audit['narrow_window_keV']==[510.5,511.5]
                assert all(audit[k] is True for k in ['gzip_crc_complete','terminal_EN','one_INIT_per_event','ordered_primary_ID'])
                assert Path(meta['catalog_path']).is_file();compact_paths.add(meta['catalog_path']);compact_events+=audit['TS']
            accepted.append({'profile':name,'job_id':job['job_id'],'events':job['events'],'seed':job['seed'],'source_sha256':receipt['source_sha256'],'sim_path':receipt['sim_path'],'ended_at':receipt['ended_at']})
        summary[name]={'jobs':len(plan),'events':sum(totals.values()),'by_family':dict(totals)}
        print(json.dumps({'audited':name,**summary[name]}),flush=True)
    assert summary['instant_full']['events']+summary['instant_minimal']['events']==23005699
    assert summary['buildup']['events']==3045028 and summary['signal']['events']==37175
    assert summary['delayed_epoch0']['events']==7000000
    inv=read(delayed['inventory_manifest']);assert inv['candidate']=='AA' and inv['geometry']==str(SETUP)
    assert inv['zero_source_families']==['muplus']
    for row in inv['activation_cells']:close(row['sum_TT_s'],build_tt[row['family']])
    mu=next(r for r in inv['activation_cells'] if r['family']=='muplus');assert mu['sum_RP']==mu['transported_ground_activity_Bq']==0
    merge=read(DATA/'derived/merged/manifest.json');assert merge['status']=='PASS__AA_NORMALIZED_REPLAY_INPUTS'
    assert set(merge['input_compacts'])==compact_paths and merge['input_jobs']==1170
    for family,tt in prompt_tt.items():close(tt,merge['prompt_TT_s'][family])
    for field in merge['files']:
        a=np.load(DATA/'derived/merged'/(field+'.npy'),mmap_mode='r',allow_pickle=False)
        n=merge['raw_hits'] if field in ['hit_code','hit_layer','hit_energy_keV','hit_x_cm','hit_y_cm','hit_z_cm'] else merge['events']
        assert a.ndim==1 and len(a)==n,(field,a.shape,n)
        if a.dtype.kind=='f':assert np.isfinite(a).all(),field
    mission=rows(DATA/'derived/timeline/mission_81nodes.csv');assert len(mission)==81
    assert [float(x['day_mid']) for x in mission]==[i/4 for i in range(81)]
    integral=0.;kernel=0.
    for i,row in enumerate(mission):
        if i:
            prior=mission[i-1];dt=21600
            integral+=.5*(float(row['mature_background_W2_final_cps'])+float(prior['mature_background_W2_final_cps']))*dt
            kernel+=.5*(float(row['conditional_signal_kernel_cm2'])+float(prior['conditional_signal_kernel_cm2']))*dt
        close(integral,row['cumulative_background_counts']);close(kernel,row['cumulative_signal_counts_per_unit_flux'])
        close(float(row['cumulative_other_background_counts'])+float(row['cumulative_gamma_continuum_background_counts']),integral)
        assert float(row['cumulative_atm511_background_counts'])==0
        if i:close(3*math.sqrt(integral)/kernel,row['Fmin_3sigma_gaussian_ph_cm2_s'])
    result=read(DATA/'derived/timeline/summary.json');assert result['status']=='PASS__AA_PIXEL_COMPTON_POISSON_MISSION'
    assert result['day15_schema']['closure_status']=='PASS__DAY15_PRODUCTS_ADDITIVE_CUTFLOW_CLOSED'
    assert result['fingerprint']['corrected_compton']==compton
    assert datetime.datetime.fromisoformat(result['at']).timestamp()<deadline
    anchor_fingerprints=set()
    for node in [0,20,40,60,80]:
        receipt=read(DATA/f'derived/timeline/receipts/anchor_{node:03d}.json')
        assert receipt['status']=='PASS__FLUXCLOSED_ANCHOR_COMPLETE' and receipt['candidate']=='AA'
        anchor_fingerprints.add(receipt['input_fingerprint_sha256'])
    assert len(anchor_fingerprints)==1
    assert read(ROOT/'data/continuation_process_end_audit.json')['live_owned_transport_or_controller']==[]
    free=shutil.disk_usage(DISK).free;assert free>RESERVE
    metrics=[]
    for path in profiles.values():
        mf=Path(C.load_config(path)['run_root'])/'resource_metrics.jsonl'
        if mf.exists():metrics.extend(json.loads(line)['free_disk_bytes'] for line in mf.read_text().splitlines())
    minimum=min(metrics+[free,read(ROOT/'STATE.json')['minimum_observed_free_bytes']]);assert minimum>RESERVE
    cut=rows(DATA/'derived/timeline/direct_cutflow_day15.csv');narrow=[x for x in cut if x['window_id']=='w2_510p58_511p42']
    cutflow={stage:{'selected_raw':sum(int(x['selected_raw']) for x in narrow if x['stage']==stage),'rate_cps':math.fsum(float(x['sumw_cps']) for x in narrow if x['stage']==stage)} for stage in ['pre_veto','combined_active_veto','compton_trajectory_veto']}
    report={'at':utc(),'status':'PASS__AA_BASELINE_AND_ANALYSIS_INDEPENDENTLY_AUDITED','baseline_complete':True,'analysis_complete':True,'profiles':summary,'validated_receipts':len(accepted),'response_compacts':len(compact_paths),'response_primaries_or_decays':compact_events,'accepted_artifact_bytes':artifact_bytes,'last_transport_receipt_at':latest.isoformat(),'analysis_complete_at':result['at'],'continuation_deadline_unix':deadline,'all_transport_and_analysis_before_authorized_deadline':True,'original_eight_hour_target_missed':True,'original_goal_followup_authorization':'补充吧; continue','optional_expansion_performed':False,'zero_delayed_family':mu,'geometry_hashes':frozen_geometry(),'corrected_compton_sha256':compton,'free_bytes':free,'minimum_recorded_free_bytes':minimum,'reserve_bytes':RESERVE,'controller_exit':read(ROOT/'data/detached_continuation_exit.json'),'controller_exit_interpretation':'deadline watchdog killed controller during post-analysis bookkeeping; actual transport and analysis artifacts independently passed before deadline','prompt_TT_s':dict(prompt_tt),'day15_narrow_direct_cutflow':cutflow,'mission_days':{str(n//4):mission[n] for n in [40,60,80]},'day20_uncertainty':result['uncertainty'],'limitations':['This continues the originally missed eight-hour run under an authorized four-hour extension.','Zero muplus delayed source describes the finite AA inventory, not a proof of zero physical activation.','Signal accidental-coincidence factor is the inherited background-only contamination proxy, not joint signal/background transport.','Reported uncertainty includes finite background templates and fixed-optics conditional signal retention; it is not all instrument, atmospheric, or source-model systematics.'],'legacy_field_mapping':{'w2_510p58_511p42':'actual AA window is [510.5, 511.5) keV','T_atm_511_slant45':'actual source elevation is 27 degrees','plastic_positron_veto':'pass-through stage: AA has no plastic scintillator','aeff_cm2':'internal optical area times signal retention; not a new selected-effective-area paper quantity'}}
    save(ROOT/'data/accepted_jobs_after_continuation.json',accepted)
    save(ROOT/'CONTINUATION_FINAL_AUDIT.json',report)
    print(json.dumps({k:report[k] for k in ['status','validated_receipts','response_compacts','free_bytes','minimum_recorded_free_bytes','last_transport_receipt_at','analysis_complete_at']},indent=2),flush=True)

if __name__=='__main__':main()
