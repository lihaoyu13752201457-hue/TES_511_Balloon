from targeted_environment import *
import concurrent.futures,time,sys
batch=sys.argv[1] if len(sys.argv)>1 else 'batch01'
assert json.loads((T/'smoke_verified/validation.json').read_text())['status']=='PASS'
plan=json.loads((T/batch/'plan.json').read_text())
registered=[]
for f in T.glob('batch*/plan.json'):registered.extend(json.loads(f.read_text()))
assert sum(r['events'] for r in registered)+2000<=2000000
assert len({r['seed'] for r in registered})==len(registered)

def run(r):
    directory=Path(r['directory']);receipt=directory/'receipt.json'
    if receipt.exists():
        saved=json.loads(receipt.read_text());assert saved['status']=='TRANSPORT_COMPLETE';return saved
    assert not (directory/'started.json').exists(),('Do not silently restart a registered seed',r['job'])
    assert sha(r['source'])==r['source_sha256']
    started=time.time();(directory/'started.json').write_text(json.dumps(dict(started=started,job=r['job'],seed=r['seed'],events=r['events']))+'\n')
    with (directory/'run.log').open('w') as log:
        p=subprocess.run([str(T/'cosima'),'-s',str(r['seed']),'-z',r['source']],cwd=directory,env=environment(),stdout=log,stderr=subprocess.STDOUT)
    files=list(directory.glob('response*.sim.gz'));assert p.returncode==0 and len(files)==1,(r['job'],p.returncode,files)
    result={**r,'status':'TRANSPORT_COMPLETE','sim':str(files[0]),'sim_bytes':files[0].stat().st_size,'seconds':time.time()-started}
    receipt.write_text(json.dumps(result,indent=2)+'\n');print(r['job'],r['events'],'transport complete',round(result['seconds'],1),'s',flush=True)
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    futures=[ex.submit(run,r) for r in sorted(plan,key=lambda x:-x['events'])]
    result=[f.result() for f in concurrent.futures.as_completed(futures)]
(T/batch/'transport_complete.json').write_text(json.dumps(result,indent=2)+'\n')
print('ALL TRANSPORT COMPLETE',sum(r['events'] for r in result),flush=True)
