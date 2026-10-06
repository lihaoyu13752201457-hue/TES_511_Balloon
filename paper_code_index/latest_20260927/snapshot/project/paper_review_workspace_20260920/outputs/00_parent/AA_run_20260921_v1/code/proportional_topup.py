"""Fresh proportional AA epochs, admitted only after the matched baseline.

Each delayed epoch retains its own production TT and activity. Independent
inventory estimates may only be combined with TT weights, never raw pooling.
"""
from aa_common import *
from prepare_aa import CAPS
from prepare_delayed import prepare as prepare_delayed
import governor as gov
import csv, math, shutil, concurrent.futures


def prepare_epoch(index,fraction):
    name=f'epoch{index}';saved=ROOT/'data'/f'{name}_prepared.json'
    if saved.exists():return read(saved)
    refs=list(csv.DictReader((ASSESS/'JOB_TARGETS.csv').open()))
    ev=read(ASSESS/'data/receipt_storage_evidence.json')['rows']
    seeds,_=occupied_seeds();registry=[];configs={};totals={}
    for mode,minimal,select in [
        ('buildup',False,lambda r:r['mode']=='buildup'),
        ('instant_full',False,lambda r:r['mode']=='instant' and r['recording']=='full_all'),
        ('instant_minimal',True,lambda r:r['recording']=='minimal_init_only')]:
        profile=name+'_'+mode;cfg=config_for(profile,MINIMAL_SETUP if minimal else SETUP);jobs=[];sources=[]
        for ref in filter(select,refs):
            fam=ref['family'];n_total=max(1,math.ceil(int(ref['events'])*fraction));left=n_total;ordinal=0
            old=next(x for x in ev if x['batch']==ref['reference_batch'] and x['job_id']==ref['reference_job'])
            bpe=(old['artifact_bytes'] or old['sim_bytes'])/int(ref['events'])
            while left:
                n=min(left,CAPS[fam]);left-=n;ordinal+=1
                jid=f"aa{index}_{mode}_{ref['target_id']}_{ordinal:03d}_{fam}";seed=new_seed(jid,seeds)
                j=job_row(cfg,len(jobs)+1,jid,fam,ref['mode'],n,seed,2*bpe*n+10_000_000,{**ref,'AA_epoch':index,'requested_fraction':fraction,'epoch_logical_target':n_total})
                C.write_once_text(Path(j['source_path']),source_text(fam,ref['mode'],jid,seed,n,Path(j['output_prefix']),Path(cfg['geometry_setup']),minimal))
                jobs.append(j);sources.append(source_row(j));registry.append({'job_id':jid,'seed':seed})
        queues={f:[j for j in jobs if j['family']==f] for f in FAMILIES};ordered=[]
        while any(queues.values()):
            for f in FAMILIES:
                if queues[f]:ordered.append(queues[f].pop(0))
        for i,j in enumerate(ordered):j['ordinal']=i+1
        configs[mode]=finish_bundle(profile,cfg,ordered,sources)
        totals[mode]={f:sum(j['events'] for j in jobs if j['family']==f) for f in FAMILIES}
    current=read(ROOT/'data/seed_registry.json');current['seeds'].extend(registry);save(ROOT/'data/seed_registry.json',current)
    result={'epoch':index,'fraction':fraction,'configs':configs,'totals':totals,'delayed_events_per_positive_family':math.ceil(1_000_000*fraction),'combination_policy':'prompt: sum counts / sum own TT within identical source proposal; delayed: retain own inventory response, combine physical rate estimates with per-family buildup TT weights'}
    save(saved,result);return result


def observed_cost(configs):
    size=0;cpu=0
    for path in configs.values():
        cfg=C.load_config(path)
        for job in C.load_plan(cfg):
            receipt=C.load_bound_receipt(cfg,job)
            if receipt:
                size+=receipt.get('artifact_bytes',sum(receipt.get(k,0) for k in ['sim_bytes','log_bytes','isotope_dat_bytes']))
                cpu+=receipt.get('wall_s',0)
    return size,cpu


def continue_proportionally(baseline):
    ledger_path=ROOT/'data/proportional_epochs.json'
    ledger=read(ledger_path) if ledger_path.exists() else {'epochs':[],'baseline_configs':baseline,'deadline_unix':DEADLINE,'reserve_bytes':RESERVE}
    decision=ROOT/'data/continuation_priority.json'
    if decision.exists() and read(decision).get('defer_optional_expansion'):
        ledger.update(stop_reason='deadline risk: preserve remaining time for matched baseline analysis',at=utc(),priority_decision=str(decision))
        save(ledger_path,ledger)
        from finalize_analysis import finalize
        ledger['analysis']=finalize();save(ledger_path,ledger);return ledger
    base_bytes,base_cpu=observed_cost(baseline)
    elapsed=max(60,time.time()-START)
    while not R.STOP.is_set():
        free=shutil.disk_usage(DISK).free;remaining=DEADLINE-time.time()
        # Keep time for closure/postprocessing and an inflight filesystem margin.
        budget_bytes=max(0,free-RESERVE-8*GiB)
        candidates=[.10,.05,.02,.01,.005,.001]
        fraction=next((x for x in candidates if 1.5*base_bytes*x+GiB<budget_bytes and 1.5*elapsed*x+300<remaining-900),None)
        if fraction is None:
            ledger.update(stop_reason='whole proportional increment cannot fit disk/time margin',free_bytes=free,remaining_seconds=remaining,baseline_bytes=base_bytes,at=utc())
            save(ledger_path,ledger)
            from finalize_analysis import finalize
            ledger['analysis']=finalize();save(ledger_path,ledger);return ledger
        index=len(ledger['epochs'])+1;epoch=prepare_epoch(index,fraction)
        row={**epoch,'status':'RUNNING','started_at':utc(),'free_before_bytes':free};ledger['epochs'].append(row);save(ledger_path,ledger)
        event('PROPORTIONAL_EPOCH_START',epoch=index,fraction=fraction)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            buildup=pool.submit(gov.run_profile,epoch['configs']['buildup'])
            full=pool.submit(gov.run_profile,epoch['configs']['instant_full'])
            minimal=pool.submit(gov.run_profile,epoch['configs']['instant_minimal'])
            buildup.result()
            delayed=prepare_delayed(name=f'delayed_epoch{index}',buildup_config=epoch['configs']['buildup'],total_per_family=epoch['delayed_events_per_positive_family'])
            future=pool.submit(gov.run_profile,delayed['config']) if delayed['config'] else None
            full.result();minimal.result()
            if future:future.result()
        row.update(status='PASS__TRANSPORT_COMPLETE',delayed=delayed,completed_at=utc(),free_after_bytes=shutil.disk_usage(DISK).free)
        save(ledger_path,ledger);event('PROPORTIONAL_EPOCH_COMPLETE',epoch=index,fraction=fraction)
    ledger.update(stop_reason='controller_stop',at=utc());save(ledger_path,ledger);return ledger
