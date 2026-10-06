"""Explicit new-window continuation; no default deadline or automatic launch.
Existing source cards, seeds and PASS receipts are reused without rerunning
accepted work. The user must authorize a new time window before this CLI runs.
"""
import argparse,sys,time
import aa_common as A
ap=argparse.ArgumentParser();ap.add_argument('--deadline-unix',type=float);ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
now=time.time()
if not args.check_only and (args.deadline_unix is None or not now+120<args.deadline_unix<=now+4*3600+5):raise SystemExit('new deadline must be explicit and within the approved four-hour window')
if args.deadline_unix is not None:A.DEADLINE=args.deadline_unix
from aa_common import *
import governor as gov
import campaign as base
from prepare_delayed import prepare as prepare_delayed
import concurrent.futures,contextlib,fcntl,signal,threading,shutil,traceback,subprocess

def preflight():
    prep=read(ROOT/'data/preparation.json');rows={}
    expected=read(ROOT/'data/remaining_jobs_at_deadline.json')
    for name in ['buildup','instant_full','instant_minimal']:
        cfg=C.load_config(prep['bundles'][name]);plan=C.load_plan(cfg);C.validate_generated_bundle(cfg,plan)
        pending=[j for j in plan if not C.load_bound_receipt(cfg,j)]
        assert {j['job_id'] for j in pending}=={j['job_id'] for j in expected if j['profile']==name}
        rows[name]={'skip_existing_PASS':len(plan)-len(pending),'pending_jobs':len(pending),'pending_events':sum(j['events'] for j in pending)}
    frozen_geometry()
    result={'status':'PASS__CONTINUATION_READY_NOT_LAUNCHED','at':utc(),'production_launched':False,'profiles':rows,'phase_order':['finish all remaining BUILDUP','AA inventory while pending prompt runs','AA delayed','proportional full-chain expansion if admissible'],'new_time_authorization_required':True}
    save(ROOT/'data/continuation_preflight.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))

def monitor_aux(proc,component):
    while not R.STOP.is_set():
        code=proc.poll()
        if code is not None:
            if code!=0:gov.notice('FAILURE',component=component,exit_code=code,policy='owned auxiliary failure; inspect its log, preserve running transport receipts')
            return
        time.sleep(5)

def main():
    lock=(ROOT/'campaign.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # Recover resource learning before the monitor replaces the prior snapshot.
    prior_state=read(ROOT/'STATE.json') if (ROOT/'STATE.json').exists() else {}
    gov.initial_host_check();gov.install()
    original_stop=R.STOP.set
    def recorded_stop():
        event('STOP_REQUEST_TRACE',stack=''.join(traceback.format_stack(limit=8)))
        original_stop()
    R.STOP.set=recorded_stop
    def stop_signal(signum,frame):
        event('CONTROLLER_SIGNAL',signum=signum)
        R.request_stop(signum,frame)
    if prior_state.get('active'):
        gov.ADAPTIVE_LIMIT=max(2,min(gov.MAX_WORKERS,prior_state.get('adaptive_limit',4)))
        gov.LAST_PRESSURE=time.monotonic()
        gov.MIN_FREE=min(gov.MIN_FREE,prior_state.get('minimum_observed_free_bytes',gov.MIN_FREE))
        for jid,row in prior_state['active'].items():
            reserved=prior_state.get('reservations',{}).get(jid,{}).get('rss',0)/GiB
            family=row['family'];gov.INITIAL_RSS[family]=max(gov.INITIAL_RSS.get(family,1.),reserved)
    # Keep recent AA measurements across controller restarts, including the
    # prompt family that may have been idle in the final active snapshot.
    calibration=read(ROOT/'data/preparation.json')
    for name in ['instant_full','instant_minimal','delayed_epoch0']:
        cp=calibration['bundles'].get(name,str(ROOT/'bundles'/name/'config.json'))
        if not Path(cp).exists():continue
        cfg=C.load_config(cp);sample={}
        for job in reversed(C.load_plan(cfg)):
            key=(job['mode'],job['family']);bucket=sample.setdefault(key,[])
            if len(bucket)>=20:continue
            rp=R.receipt_path(cfg,job['job_id'])
            if rp.exists():
                row=read(rp)
                if row.get('status')=='PASS' and row.get('peak_process_rss_bytes'):bucket.append(row['peak_process_rss_bytes'])
        for key,values in sample.items():
            if values:gov.PEAKS.setdefault(key,[]).extend(values)
    signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
    threading.Thread(target=gov.monitor,daemon=True).start()
    prep=read(ROOT/'data/preparation.json');paths={k:prep['bundles'][k] for k in ['buildup','instant_full','instant_minimal']}
    previous=read(ROOT/'CAMPAIGN_FINAL.json')
    if not (ROOT/'data/original_eight_hour_final_preserved.json').exists():save(ROOT/'data/original_eight_hour_final_preserved.json',previous)
    if not (ROOT/'data/original_deadline_actions_preserved.json').exists():save(ROOT/'data/original_deadline_actions_preserved.json',read(ROOT/'data/deadline_actions.json'))
    save(ROOT/'data/campaign_launch.json',{'status':'CONTINUATION_LAUNCHED','pid':os.getpid(),'entry_script':'resume_campaign.py','at':utc(),'deadline_unix':DEADLINE,'original_deadline_unix':1789953625,'configs':paths,'hard_reserve_bytes':RESERVE,'scope':'finish pending BUILDUP first; then inventory, remaining prompt and delayed; only then proportional topup','routine_progress_invokes_agent':False})
    children=[]
    for task in ['compact','watch']:
        with (ROOT/f'{task}_continuation.log').open('a',buffering=1) as log:
            proc=subprocess.Popen([sys.executable,str(ROOT/'code/resume_aux.py'),'--deadline-unix',str(DEADLINE),task],stdout=log,stderr=subprocess.STDOUT,cwd=WORKSPACE)
        children.append(proc);threading.Thread(target=monitor_aux,args=(proc,task),daemon=True).start()
    baseline_done=False
    phase={'name':'buildup'}
    from continuation_risk import monitor as risk_monitor
    threading.Thread(target=risk_monitor,args=(phase,),daemon=True).start()
    try:
        with (ROOT/'canonical_controllers.log').open('a',buffering=1) as log,contextlib.redirect_stdout(log):
            # Critical dependency gets all admissible resources first. Completed
            # jobs remain bound to their original immutable PASS receipts.
            gov.run_profile(paths['buildup'])
            phase['name']='inventory'
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                full=pool.submit(gov.run_profile,paths['instant_full'])
                minimal=pool.submit(gov.run_profile,paths['instant_minimal'])
                delayed=prepare_delayed()
                phase['name']='prompt_and_delayed'
                future=pool.submit(gov.run_profile,delayed['config'],4) if delayed['config'] else None
                full.result();minimal.result()
                if future:future.result()
            if delayed['config']:paths['delayed_epoch0']=delayed['config']
            save(ROOT/'data/baseline_transport_complete.json',{'status':'PASS__AA_MATCHED_TRANSPORT_RECEIPTS','at':utc(),'coverage':base.coverage(paths),'delayed':delayed,'original_eight_hour_target_missed':True})
            baseline_done=True
            phase['name']='expansion'
            from proportional_topup import continue_proportionally
            expansion=continue_proportionally(paths)
        final={'status':'CONTINUATION_FINISHED','at':utc(),'baseline_complete':True,'coverage':base.coverage(paths),'expansion':expansion,'deadline_unix':DEADLINE,'original_eight_hour_target_missed':True,'free_bytes':shutil.disk_usage(DISK).free,'minimum_observed_free_bytes':gov.MIN_FREE}
        save(ROOT/'CAMPAIGN_FINAL.json',final);gov.notice('COMPLETE',result=str(ROOT/'CAMPAIGN_FINAL.json'))
    except BaseException as e:
        R.STOP.set();R.terminate_all()
        save(ROOT/'CAMPAIGN_FINAL.json',{'status':'CONTINUATION_EXCEPTION','at':utc(),'error':str(e),'traceback':traceback.format_exc(),'baseline_complete':baseline_done,'coverage':base.coverage(paths),'deadline_unix':DEADLINE,'original_eight_hour_target_missed':True,'free_bytes':shutil.disk_usage(DISK).free,'minimum_observed_free_bytes':gov.MIN_FREE})
        gov.notice('FAILURE',error=str(e));raise
    finally:
        R.STOP.set()
        for proc in children:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
        lock.close()
if __name__=='__main__':preflight() if args.check_only else main()
