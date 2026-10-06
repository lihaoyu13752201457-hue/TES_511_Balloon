"""Finish AA-derived products when accepted transport has closed."""
from aa_common import *
import traceback

def finalize():
    try:
        from merge_aa import inventory_epochs,merge
        epochs=inventory_epochs();needed=[]
        for epoch in epochs:
            configs=[v for k,v in epoch['configs'].items() if k.startswith('instant')]
            if epoch['delayed']['config']:configs.append(epoch['delayed']['config'])
            for path in configs:
                cfg=C.load_config(path)
                for job in C.load_plan(cfg):needed.append(DATA/'derived/catalogs'/cfg['profile_id']/f"job_{job['ordinal']:03d}_{job['job_id']}.json")
        while time.time()<DEADLINE-120:
            state=read(ROOT/'data/compact_service.json')
            if state['status']=='EXCEPTION':raise RuntimeError('AA compact service exception: '+state['error'])
            missing=[p for p in needed if not p.exists() or read(p).get('AA_audit',{}).get('status')!='PASS']
            if not missing:break
            if state['status']=='STOPPED':raise RuntimeError(f'compact service stopped with {len(missing)} jobs not closed')
            time.sleep(15)
        else:raise RuntimeError('deadline margin reached before compact closure')
        if C.meminfo()['MemAvailable']<2*GiB:raise RuntimeError('insufficient memory for final merge/replay within remaining window')
        result=merge()
        from replay_aa import main as replay
        replay()
        out={'status':'PASS__AA_ANALYSIS_COMPLETE','at':utc(),'merged':str(DATA/'derived/merged/manifest.json'),'timeline':str(DATA/'derived/timeline/summary.json')}
    except BaseException as e:
        out={'status':'ANALYSIS_INCOMPLETE','at':utc(),'error':str(e),'traceback':traceback.format_exc(),'baseline_transport_not_invalidated':True}
        event('ANALYSIS_EXCEPTION',**out)
    save(ROOT/'data/final_analysis.json',out);return out
