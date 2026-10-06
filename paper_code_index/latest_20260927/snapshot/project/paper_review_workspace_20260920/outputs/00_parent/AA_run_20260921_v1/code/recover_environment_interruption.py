"""Archive only unaccepted AA artifacts after proving their owners are gone."""
from aa_common import *
import fcntl

def main():
    lock=(ROOT/'campaign.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    own=str(ROOT/'code'); data=str(DATA)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except OSError:continue
        if (own in cmd or data in cmd) and ('cosima ' in cmd or 'resume_campaign.py' in cmd or 'resume_aux.py' in cmd):
            raise RuntimeError('owned process still alive: '+proc.name+' '+cmd)
    prep=read(ROOT/'data/preparation.json');report={'at':utc(),'status':'PASS__INTERRUPTED_UNACCEPTED_ARTIFACTS_PRESERVED','accepted':{},'archived':[]}
    for name in ['buildup','instant_full','instant_minimal']:
        cfg=C.load_config(prep['bundles'][name]);jobs=C.load_plan(cfg);accepted=0
        for j in jobs:
            if C.load_bound_receipt(cfg,j):accepted+=1;continue
            active=Path(cfg['run_root'])/'jobs'/j['job_id']/'active'
            if not active.exists():continue
            with (active/(j['job_id']+'.log')).open() as f:header=json.loads(f.readline())
            assert header['job_id']==j['job_id'] and header['source_sha256']==sha(j['source_path'])
            ordinal=header['attempt'];dest=active.parent/'failed'/f'attempt{ordinal:02d}'
            assert not dest.exists()
            dest.parent.mkdir(exist_ok=True);active.rename(dest)
            record={'status':'FAIL','job_id':j['job_id'],'attempt':ordinal,'errors':['environment interruption: owning processes absent; exit status and terminal validation unavailable'],'watchdog_reason':'environment_interruption','at':utc(),'accepted_as_physics':False,'preserved_at':str(dest)}
            C.write_once_json(dest/'validation.json',record);report['archived'].append(record)
        report['accepted'][name]=accepted
    partial=DATA/'delayed_epoch0_inventory'
    if partial.exists() and not (ROOT/'data/delayed_epoch0_prepared.json').exists():
        assert not (partial/'generated/activation/manifest.json').exists(),'inventory complete: recover manifest explicitly'
        dest=DATA/'delayed_epoch0_inventory_interrupted_20260921_0432'
        assert not dest.exists();partial.rename(dest);report['inventory_partial_preserved_at']=str(dest)
    for meta in (DATA/'derived/catalogs').glob('*/*.json'):
        payload=read(meta)
        if payload.get('AA_audit',{}).get('status')=='PASS':continue
        dest=meta.parent/'interrupted_20260921_0432';dest.mkdir(exist_ok=True)
        candidates=[meta,Path(payload['catalog_path'])]
        for path in candidates:
            assert path.parent==meta.parent and not (dest/path.name).exists()
            if path.exists():path.rename(dest/path.name)
        report['archived'].append({'incomplete_compact':str(meta),'preserved_at':str(dest)})
    save(ROOT/'data/environment_recovery_20260921.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
