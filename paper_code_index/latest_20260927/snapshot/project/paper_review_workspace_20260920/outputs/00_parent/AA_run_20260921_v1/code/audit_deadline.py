from aa_common import *
import collections,datetime as dt,shutil

def main():
    audit=read(ROOT/'data/deadline_receipt_audit.json');start=dt.datetime.fromtimestamp(START,dt.timezone.utc);end=dt.datetime.fromtimestamp(DEADLINE,dt.timezone.utc)
    points=[];metrics=[];complete=[];missing=[];families=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
    for name,p in audit['profiles'].items():
        cfg=C.load_config(read(ROOT/'data/preparation.json')['bundles'][name]);mf=Path(cfg['run_root'])/'resource_metrics.jsonl'
        if mf.exists():metrics.extend(json.loads(line) for line in mf.read_text().splitlines())
        for fam,(done,target) in p['by_family'].items():
            mode='buildup' if name=='buildup' else 'instant';families[fam][mode][0]+=done;families[fam][mode][1]+=target
        missing.extend({'profile':name,**j} for j in p['missing'])
        for rp in sorted((Path(cfg['run_root'])/'receipts').glob('*.json')):
            r=read(rp);t0=dt.datetime.fromisoformat(r['started_at']);t1=dt.datetime.fromisoformat(r['ended_at']);points.extend([(t0,1),(t1,-1)])
            complete.append({'profile':name,'job_id':r['job_id'],'events':r['events'],'family':r['family'],'receipt_path':str(rp),'source_sha256':r['source_sha256'],'sim_path':r['sim_path'],'sim_bytes':r['sim_bytes'],'ended_at':r['ended_at']})
    active=0;peak=0;last=start;duration=collections.defaultdict(float)
    for t,d in sorted(points):
        duration[active]+=max(0,(min(t,end)-max(last,start)).total_seconds());active+=d;peak=max(peak,active);last=t
    if last<end:duration[active]+=(end-last).total_seconds()
    vals={'at':utc(),'status':'INCOMPLETE__HARD_DEADLINE_REACHED','baseline_complete':False,'delayed_started':False,'topup_started':False,'deadline_unix':DEADLINE,'process_exit':{'campaign_pid_135992':'absent','controller_exit_code':137,'compact_exit_code':0,'AA_cosima_processes_observed':0},'completed_jobs':len(complete),'missing_pre_delayed_jobs':len(missing),'counts':{mode:{'done':sum(v.get(mode,[0,0])[0] for v in families.values()),'target':sum(v.get(mode,[0,0])[1] for v in families.values())} for mode in ['instant','buildup']},'by_family':dict(families),'signal_events_complete':37175,'delayed_target':8000000,'delayed_done':0,'compact_pass_jobs':read(ROOT/'data/compact_service.json')['completed_jobs'],'free_bytes':shutil.disk_usage(DISK).free,'minimum_recorded_free_bytes':min([x['free_disk_bytes'] for x in metrics]+[read(ROOT/'STATE.json')['minimum_observed_free_bytes']]),'reserve_bytes':RESERVE,'accepted_job_peak_concurrency':peak,'accepted_job_worker_seconds':sum(k*v for k,v in duration.items()),'accepted_job_concurrency_duration_seconds':dict(duration),'raw_scope':'completed canonical receipt/header/log/DAT validation; completed prompt also full gzip/ID/INIT/response audits; buildup RPIP inventory not yet assembled','constraints_not_met':['complete A-matched baseline within eight hours','delayed transport','proportional expansion','actual full-chain mission analysis'],'geometry_hashes':frozen_geometry(),'compton_sha256':sha(SIGNAL/'code/pixel_geometry_compton.py')}
    for v in vals['counts'].values():v['fraction']=v['done']/v['target']
    save(ROOT/'FINAL_AUDIT.json',vals);save(ROOT/'data/accepted_jobs_at_deadline.json',complete);save(ROOT/'data/remaining_jobs_at_deadline.json',missing)
    historical=ROOT/'data/first_attempt_failure_preserved.json'
    if not historical.exists():save(historical,read(ROOT/'CAMPAIGN_FINAL.json'))
    save(ROOT/'CAMPAIGN_FINAL.json',{**vals,'authoritative_audit':str(ROOT/'FINAL_AUDIT.json'),'earlier_failure_snapshot':str(historical)})
    save(ROOT/'STATE.json',{'status':'STOPPED_AT_DEADLINE','at':utc(),'live_AA_transport_processes':0,'final_audit':str(ROOT/'FINAL_AUDIT.json'),'minimum_observed_free_bytes':vals['minimum_recorded_free_bytes']})
    print(json.dumps({k:vals[k] for k in ['status','completed_jobs','missing_pre_delayed_jobs','counts','free_bytes','minimum_recorded_free_bytes','accepted_job_peak_concurrency','accepted_job_worker_seconds']},indent=2))
if __name__=='__main__':main()
