"""Local deadline-risk alarms; no routine model updates or raw-data scans."""
from aa_common import *
import governor as gov
import statistics

def monitor(phase):
    pending=read(ROOT/'data/remaining_jobs_at_deadline.json')
    # A recovered controller must credit receipts completed by its predecessor.
    prep=read(ROOT/'data/preparation.json');already=set()
    for name in ['buildup','instant_full','instant_minimal']:
        cfg=C.load_config(prep['bundles'][name]);wanted={j['job_id'] for j in pending if j['profile']==name}
        for job in C.load_plan(cfg):
            if job['job_id'] in wanted and C.load_bound_receipt(cfg,job):already.add(job['job_id'])
    estimates=read(ROOT/'data/remaining_transport_estimate.json')['missing_pre_delayed']
    seconds_per_event={(r['profile'],r['family']):r['estimated_serial_wall_s']/r['missing_events'] for r in estimates}
    old=read(ASSESS/'data/receipt_storage_evidence.json')['rows'];delayed_seconds=sum(r['wall_s'] for r in old if 'delayed' in r['job_id'] or 'delayed' in r['batch'])
    started=time.monotonic();last=started;active_seconds=0.;idle_since=None;warned=set()
    while not R.STOP.is_set():
        now=time.monotonic();n=len(R.active_snapshot());active_seconds+=n*(now-last);last=now
        if phase['name'] in ('analysis','expansion','finished'):return
        with gov.LOCK:done=[dict(r) for rs in gov.RESULTS.values() for r in rs]
        ids=already|{r['job_id'] for r in done};left=[j for j in pending if j['job_id'] not in ids]
        remaining_pre=sum(j['events']*seconds_per_event[(j['profile'],j['family'])] for j in left)
        delayed_done=sum(r['events'] for r in done if r['mode']=='delayed')
        remaining_delayed=max(0,1-delayed_done/8_000_000)*delayed_seconds*1.5
        parallel=max(1,active_seconds/max(1,now-started));expected=(remaining_pre+remaining_delayed)/parallel+900
        remaining=DEADLINE-time.time()
        if now-started>900 and expected>remaining and 'risk' not in warned:
            warned.add('risk');gov.notice('DEADLINE_RISK',phase=phase['name'],estimated_remaining_s=expected,available_s=remaining,basis='remaining own-shard costs plus 1.5x historical delayed cost; observed concurrency; estimate, not a completion promise')
        if n==0 and phase['name']!='inventory' and left:
            if idle_since is None:idle_since=now
            if now-idle_since>120 and 'idle' not in warned:
                warned.add('idle');gov.notice('STALLED',phase=phase['name'],pending_jobs=len(left),idle_seconds=now-idle_since)
        else:idle_since=None
        time.sleep(5)
