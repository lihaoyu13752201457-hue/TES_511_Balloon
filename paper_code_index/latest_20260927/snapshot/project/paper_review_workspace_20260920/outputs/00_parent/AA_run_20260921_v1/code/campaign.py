"""Eight-hour AA campaign, using the canonical executor and AA governor."""
from aa_common import *
import concurrent.futures, contextlib, fcntl, shutil, signal, subprocess, threading, traceback
import governor as gov
from prepare_delayed import prepare as prepare_delayed

THREAD_ID='01a0bfa6-2760-7803-908d-6106613f317c'

def notify_agent(kind,message):
    payload={'kind':kind,'at':utc(),'message':message,'state':str(ROOT/'STATE.json'),'deadline_unix':DEADLINE}
    save(ROOT/'LAST_EVENT.json',payload)
    prompt=(f'AA八小时模拟脚本发来{kind}事件，不是定时轮询。{message}。'
            f'先读{ROOT}/CAMPAIGN_FINAL.json（若存在）、LAST_EVENT.json和events.jsonl末尾；'
            '只核对本任务PID/新AA数据，保留PASS receipt及150GB安全空间。'
            '修正康普顿已固定，禁止复用旧质心重建。'
            f'原硬截止时间为Unix {DEADLINE}，重试不能延长它。'
            '若未到截止且异常可修复，修复后按同一冻结输入和原截止时间恢复；'
            '若已到截止，停止新输运，核验结果并如实报告达到A统计量的比例和未完成项；'
            '不要创建定时轮询，不要将目标缩减为仅启动成功，也不要无证据宣告目标完成。')
    with (ROOT/'codex_notification.jsonl').open('a') as log:
        p=subprocess.Popen(['/home/ubuntu/.local/bin/codex','exec','resume','--json','-m','gpt-6-astra','-c','model_reasoning_effort="max"',THREAD_ID,prompt],cwd=WORKSPACE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    save(ROOT/'data/notification_dispatch.json',{**payload,'notifier_pid':p.pid,'mode':'event-triggered same-thread resume','documentation':'https://developers.openai.com/zh-Hans/docs/non-interactive-mode'})

def coverage(configs):
    result={}
    for name,path in configs.items():
        cfg=C.load_config(path);jobs=C.load_plan(cfg);done=[];sums={f:0 for f in FAMILIES}
        for j in jobs:
            r=C.load_bound_receipt(cfg,j)
            if r:done.append(j);sums[j['family']]=sums.get(j['family'],0)+j['events']
        result[name]={'completed_jobs':len(done),'planned_jobs':len(jobs),'events':sum(j['events'] for j in done),'target':sum(j['events'] for j in jobs),'by_family':sums}
    return result

def run_epoch(configs):
    # All profile runners share R.ACTIVE, the governor's admission tickets and
    # memory/disk budget. No profile can independently claim 12 processes.
    errors=[];delayed=None
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        buildup=pool.submit(gov.run_profile,configs['buildup'])
        instant=pool.submit(gov.run_profile,configs['instant_full'])
        minimal=pool.submit(gov.run_profile,configs['instant_minimal'])
        try:
            buildup.result()
            event('INVENTORY_BEGIN',buildup=configs['buildup'])
            delayed=prepare_delayed()
            event('INVENTORY_READY',**delayed)
            if delayed['config']:d_future=pool.submit(gov.run_profile,delayed['config'])
            else:d_future=None
            instant.result();minimal.result()
            if d_future:d_future.result()
        except BaseException:
            R.STOP.set();R.terminate_all();raise
    return delayed

def main():
    lock=(ROOT/'campaign.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prep=read(ROOT/'data/preparation.json')
    assert read(ROOT/'data/bridge_validation.json')['status'].startswith('PASS')
    assert read(ROOT/'data/bridge_validation.json')['BGO_50_80_observed']
    assert read(ROOT/'data/signal_gate.json')['status'].startswith('PASS')
    assert sha(SIGNAL/'code/pixel_geometry_compton.py')==prep['compton_sha256']
    gov.initial_host_check();gov.install()
    allgeom={str(f):sha(f) for f in (ROOT/'geometry').iterdir() if f.suffix in ('.geo','.det','.setup')}
    save(ROOT/'data/AA_production_freeze.json',{'at':utc(),'original_AA':frozen_geometry(),'minimal_bundle':allgeom,'source_preparation_sha256':sha(ROOT/'data/preparation.json'),'response':'500eV, physical pixel Compton, no plastic, AA top BGO included','deadline_unix':DEADLINE,'reserve_bytes':RESERVE})
    signal.signal(signal.SIGINT,R.request_stop);signal.signal(signal.SIGTERM,R.request_stop)
    threading.Thread(target=gov.monitor,daemon=True).start()
    paths={k:prep['bundles'][k] for k in ['buildup','instant_full','instant_minimal']}
    save(ROOT/'data/campaign_launch.json',{'status':'LAUNCHED','pid':os.getpid(),'at':utc(),'deadline_unix':DEADLINE,'scope':'A-matched baseline first, then proportional full-chain increments','configs':paths,'hard_reserve_bytes':RESERVE,'global_concurrency_ceiling':gov.MAX_WORKERS,'adaptive_concurrency':True,'routine_progress_invokes_agent':False})
    try:
        with (ROOT/'canonical_controllers.log').open('a',buffering=1) as log,contextlib.redirect_stdout(log):
            delayed=run_epoch(paths)
            if delayed['config']:paths['delayed_epoch0']=delayed['config']
            save(ROOT/'data/baseline_transport_complete.json',{'status':'PASS__AA_MATCHED_TRANSPORT_RECEIPTS','at':utc(),'coverage':coverage(paths),'delayed':delayed})
            # The proportional continuation is a separate adapter, imported only
            # after the complete matched baseline; it can never preempt it.
            from proportional_topup import continue_proportionally
            expansion=continue_proportionally(paths)
        final={'status':'CAMPAIGN_STOPPED','at':utc(),'coverage':coverage(paths),'expansion':expansion,'minimum_observed_free_bytes':gov.MIN_FREE,'free_bytes':shutil.disk_usage(DISK).free,'deadline_unix':DEADLINE,'baseline_complete':True}
        save(ROOT/'CAMPAIGN_FINAL.json',final);gov.notice('COMPLETE',result=str(ROOT/'CAMPAIGN_FINAL.json'));notify_agent('COMPLETE','匹配A的主链输运已完成，补统计阶段已结束；请核验最终账本与响应分析。')
    except BaseException as exc:
        R.STOP.set();R.terminate_all()
        final={'status':'STOPPED_AT_DEADLINE' if time.time()>=DEADLINE-120 else 'EXCEPTION','at':utc(),'error':str(exc),'traceback':traceback.format_exc(),'coverage':coverage(paths),'minimum_observed_free_bytes':gov.MIN_FREE,'free_bytes':shutil.disk_usage(DISK).free,'deadline_unix':DEADLINE,'baseline_complete':False}
        save(ROOT/'CAMPAIGN_FINAL.json',final);gov.notice('FAILURE',error=str(exc),result=str(ROOT/'CAMPAIGN_FINAL.json'));notify_agent(final['status'],str(exc));raise
    finally:
        R.STOP.set();lock.close()
if __name__=='__main__':main()
