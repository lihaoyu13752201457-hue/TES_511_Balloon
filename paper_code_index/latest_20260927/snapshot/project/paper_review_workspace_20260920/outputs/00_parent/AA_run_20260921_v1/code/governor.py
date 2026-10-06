"""Resource/admission policy injected into the unchanged canonical executor.

The executor owns subprocesses, retry attempts, file locks and receipts.
This adapter owns AA-wide budgets and a single hard wall deadline.
"""
from aa_common import *
import contextlib, inspect, shutil, threading, signal, concurrent.futures

LOCK=threading.RLock()
TICKETS={};RESULTS={};PEAKS={};CURRENT={};NOTICES=[]
MAX_WORKERS=12
ADAPTIVE_LIMIT=12
PRESSURE_SINCE=None
LAST_PRESSURE=0.
MIN_FREE=shutil.disk_usage(DISK).free
ORIG_ATTEMPT=R.run_attempt
ORIG_GUARD=R.local_resource_guard_reason
ORIG_CANARY=R.run_canary
ORIG_PUBLISH=R.publish_state
CHECK_GEOMETRY_AT_START=True
INITIAL_RSS={'gamma':.70,'n':1.1,'eminus':.70,'eplus':1.15,'p':1.1,'alpha':1.55,'muminus':.75,'muplus':.75,'focused511':.6,'parma511':.6}

def notice(kind,**kw):
    row=event(kind,**kw);save(ROOT/'LAST_EVENT.json',row)
    # Only exceptional events or terminal states reach the agent's event stream.
    if kind in ('FAILURE','DEADLINE','DEADLINE_RISK','STALLED','RESERVE_REACHED','PILOT_COMPLETE','COMPLETE'):
        sys.__stdout__.write(json.dumps(row,ensure_ascii=False)+'\n');sys.__stdout__.flush()

def predicted_rss(job):
    values=PEAKS.get((job['mode'],job['family']),[])
    baseline=INITIAL_RSS.get(job['family'],1.)*GiB
    if values:
        values=sorted(values);baseline=max(.35*GiB,values[min(len(values)-1,int(.9*len(values)))]*1.15)
    return max(baseline,job.get('retry_rss_bytes',0))

def admission(cfg,job,inflight_count=0):
    with LOCK:
        if job['job_id'] in TICKETS:return True,{'reserved':True}
        now=time.time();mem=C.meminfo();free=shutil.disk_usage(DISK).free
        active=R.active_snapshot();rss_need=predicted_rss(job)
        warming=sum(max(0,t['rss']-active.get(k,{}).get('rss_bytes',0)) for k,t in TICKETS.items())
        pending_disk=sum(max(0,t['bytes']-active.get(k,{}).get('artifact_bytes',0)) for k,t in TICKETS.items())
        values=RESULTS.get((job['mode'],job['family']),[])
        est=job['estimated_bytes']
        if values:est=max(est,max(x['artifact_bytes']/x['events'] for x in values)*job['events']*1.25+10_000_000)
        reasons=[]
        if now>DEADLINE-120:reasons.append('deadline_no_new_job')
        if len(TICKETS)>=ADAPTIVE_LIMIT:reasons.append('global_worker_ceiling')
        if mem['MemAvailable']<768*2**20+warming+rss_need:reasons.append('predicted_memory')
        if free<RESERVE+8*GiB+pending_disk+est:reasons.append('predicted_disk')
        if mem['SwapFree']<2*GiB:reasons.append('swap_free')
        if R.memory_full_psi_avg10()>5.:reasons.append('memory_PSI')
        # Avoid a late large shard that cannot close before the wall deadline.
        if values:
            speed=sum(x['events'] for x in values)/sum(max(.1,x.get('wall_s',.1)) for x in values)
            if now+job['events']/speed*1.4+30>DEADLINE-30:reasons.append('predicted_deadline')
        if not reasons:TICKETS[job['job_id']]={'rss':rss_need,'bytes':est,'profile':cfg['profile_id']}
        return not reasons,{'reasons':reasons,'free_bytes':free,'mem_available_bytes':mem['MemAvailable'],'reserved_growth_bytes':warming,'predicted_job_rss_bytes':rss_need,'projected_remaining_output_bytes':pending_disk+est,'global_workers':len(TICKETS)}

def attempt(cfg,job,ordinal,env):
    try:
        result=ORIG_ATTEMPT(cfg,job,ordinal,env)
        with LOCK:
            if result.get('peak_process_rss_bytes'):PEAKS.setdefault((job['mode'],job['family']),[]).append(result['peak_process_rss_bytes'])
            if result['status']=='PASS':RESULTS.setdefault((job['mode'],job['family']),[]).append(result)
            else:
                job['retry_rss_bytes']=max(job.get('retry_rss_bytes',0),result.get('peak_process_rss_bytes',0)*1.25)
                event('ATTEMPT_RETRY',job=job['job_id'],reason=result.get('watchdog_reason'),errors=result.get('errors'))
        return result
    finally:
        with LOCK:TICKETS.pop(job['job_id'],None)

def guard(cfg,root,jid):
    global MIN_FREE, PRESSURE_SINCE, LAST_PRESSURE, ADAPTIVE_LIMIT
    free=shutil.disk_usage(DISK).free
    with LOCK:MIN_FREE=min(MIN_FREE,free)
    if time.time()>=DEADLINE-15:
        R.STOP.set();return 'AA_EIGHT_HOUR_DEADLINE'
    if free<RESERVE+GiB:
        R.STOP.set();return 'AA_150GB_HARD_RESERVE'
    # PSI is a trailing average: killing several workers while it decays wastes
    # complete shards. Stop admission immediately, but require sustained PSI
    # before selecting one victim. Hard memory/swap floors remain immediate.
    now=time.monotonic();psi=R.memory_full_psi_avg10()
    with LOCK:
        if psi>15.:
            if PRESSURE_SINCE is None:PRESSURE_SINCE=now
        else:PRESSURE_SINCE=None
        sustained=PRESSURE_SINCE is not None and now-PRESSURE_SINCE>30 and now-LAST_PRESSURE>45
        local=dict(cfg,runtime_memory_full_psi_avg10_max=15. if sustained else float('inf'))
        reason=ORIG_GUARD(local,root,jid)
        if reason:
            ADAPTIVE_LIMIT=max(2,min(ADAPTIVE_LIMIT-1,len(TICKETS)-1));LAST_PRESSURE=now
            event('RESOURCE_BACKOFF',workers=ADAPTIVE_LIMIT,reason=reason)
        elif psi<2 and now-LAST_PRESSURE>300 and ADAPTIVE_LIMIT<MAX_WORKERS:
            ADAPTIVE_LIMIT+=1;LAST_PRESSURE=now
            event('RESOURCE_RECOVERY',workers=ADAPTIVE_LIMIT)
        return reason

def canary(cfg,job,environment):
    if R.load_receipt(cfg,job) is not None:return
    while not R.STOP.is_set():
        allowed,_=admission(cfg,job,0)
        if allowed:
            ordinal=R.next_attempt(cfg,job['job_id'])
            if ordinal is None:raise RuntimeError('production canary exhausted all attempts')
            result=R.run_attempt(cfg,job,ordinal,environment)
            if result['status']=='PASS':return
        if time.time()>DEADLINE-120:raise RuntimeError('AA deadline admission closed before canary')
        time.sleep(2)
    raise RuntimeError('AA governor stopped')

def publish(cfg,**kw):
    # Canonical state publication also hashes/loads all completed cards. Throttle
    # ordinary progress locally; terminal states are always written immediately.
    key=cfg['profile_id'];now=time.monotonic();old=CURRENT.get(key,0)
    if kw['status'] in ('RUNNING',) and now-old<20:return
    CURRENT[key]=now;ORIG_PUBLISH(cfg,**kw)

def install():
    R.admission=admission;R.run_attempt=attempt;R.local_resource_guard_reason=guard;R.run_canary=canary;R.publish_state=publish
    # A blocked family waits while another profile finishes; keep all canonical
    # job launching, retry, receipt, and process management code unchanged.
    source=inspect.getsource(R.run_queue)
    old='raise RuntimeError(f"all pending jobs blocked by resource admission: {blocked[:4]}")'
    assert source.count(old)==1
    source=source.replace(old,'time.sleep(float(config["poll_seconds"]))')
    exec(compile(source,str(EXEC/'run.py')+'::AA_admission_wait','exec'),R.__dict__)
    save(ROOT/'data/executor_reuse.json',{'canonical_run_path':str(EXEC/'run.py'),'canonical_sha256':sha(EXEC/'run.py'),'modified_original_files':False,'policy_hooks':['admission','run_attempt resource calibration wrapper','local_resource_guard_reason deadline/reserve','canary wait','publish_state throttling'],'queue_single_change':'blocked jobs wait for resources instead of failing the entire campaign','adapter_sha256':sha(__file__)})

def run_profile(path,workers=MAX_WORKERS):
    cfg=C.load_config(path);plan=C.load_plan(cfg);C.validate_generated_bundle(cfg,plan)
    event('PROFILE_START',profile=cfg['profile_id'],jobs=len(plan))
    result=R.run(workers,path)
    event('PROFILE_COMPLETE',profile=cfg['profile_id'],jobs=len(plan))
    return result

def monitor():
    while not R.STOP.is_set():
        with LOCK:
            rows=R.active_snapshot()
            save(ROOT/'STATE.json',{'status':'RUNNING','pid':os.getpid(),'at':utc(),'deadline_unix':DEADLINE,'remaining_seconds':max(0,DEADLINE-time.time()),'global_worker_ceiling':MAX_WORKERS,'adaptive_limit':ADAPTIVE_LIMIT,'active_workers':len(rows),'active':rows,'reservations':TICKETS,'minimum_observed_free_bytes':MIN_FREE,'free_bytes':shutil.disk_usage(DISK).free,'memory':C.meminfo(),'successful_attempts_this_process':sum(map(len,RESULTS.values())),'ordinary_monitoring':'local script only; no agent polling'})
        if time.time()>=DEADLINE-15:
            notice('DEADLINE',reason='eight_hour_window_ended');R.STOP.set();R.terminate_all();return
        time.sleep(5)

def initial_host_check():
    import subprocess
    m=subprocess.run(['findmnt','-rn',str(DISK),'-o','SOURCE,TARGET,FSTYPE,OPTIONS'],capture_output=True,text=True,check=True).stdout.strip().split()
    assert m[0]=='/dev/sdb2' and m[1]==str(DISK) and 'rw' in m[3].split(','),m
    assert Path('/dev/disk/by-uuid/903261CE3261BA3C').resolve()==Path('/dev/sdb2')
    DATA.mkdir(parents=True,exist_ok=True)
    probe=DATA/'.write_probe'
    with probe.open('xb') as f:f.write(b'AA run write probe\n');f.flush();os.fsync(f.fileno())
    assert probe.read_bytes()==b'AA run write probe\n';probe.unlink()
    assert shutil.disk_usage(DISK).free>RESERVE+20*GiB
    frozen_geometry()
    save(ROOT/'data/launch_host.json',{'mount':m,'checked_at':utc(),'disk_free_bytes':shutil.disk_usage(DISK).free,'memory':C.meminfo(),'deadline_unix':DEADLINE,'reserve_bytes':RESERVE,'write_probe':'PASS'})

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');args=ap.parse_args()
    prep=read(ROOT/'data/preparation.json');initial_host_check();install()
    signal.signal(signal.SIGTERM,R.request_stop);signal.signal(signal.SIGINT,R.request_stop)
    threading.Thread(target=monitor,daemon=True).start()
    try:
        with (ROOT/'canonical_controllers.log').open('a',buffering=1) as f,contextlib.redirect_stdout(f):
            for name in ['signal','pilot_full','pilot_minimal_all','pilot_minimal_init']:run_profile(prep['bundles'][name],1)
        notice('PILOT_COMPLETE',message='AA signal and full/minimal paired pilots completed; validate representation before baseline launch')
    except BaseException as exc:
        R.STOP.set();R.terminate_all();notice('FAILURE',error=str(exc));raise
    finally:
        R.STOP.set()
if __name__=='__main__':main()
