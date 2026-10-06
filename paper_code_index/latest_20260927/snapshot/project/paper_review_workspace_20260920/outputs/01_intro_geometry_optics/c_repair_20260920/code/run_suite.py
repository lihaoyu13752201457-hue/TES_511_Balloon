"""Bounded, immutable run ledger for corrected optics and matched comparisons."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,subprocess,json,os,hashlib,time,resource
H=Path(__file__).resolve().parents[1];WR=Path('/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh')
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def spec(name,model='dh',physics='combined',geometry='single',thickness=10.218801,offset=0,step=1,point=True,n=50000,seed=92028200):return dict(name=name,model=model,physics=physics,geometry=geometry,thickness=thickness,offset=offset,step=step,point=point,n=n,seed=seed)
def run(s):
 out=H/'runs'/s['name'];assert not out.exists(),f'Will not overwrite {out}'
 cmd=[str(WR),str(H/'build/laue511'),'--out',str(out),'--data',str(H/'inputs/corrected_physics.dat'),'--legacy-curve',str(H/'inputs/xop_511_raw.csv')]
 for k in ['model','physics','geometry','thickness','offset','step','n','seed']:cmd+=['--'+k,str(s[k])]
 if s['point']:cmd+=['--point']
 if s['geometry']=='legacy25':cmd+=['--allow-invalid-legacy']
 meta={**s,'command':cmd,'executable_sha256':sha(H/'build/laue511'),'reference_sha256':sha(H/'inputs/corrected_physics.dat'),'production_replacement':False,'geometry_validation_eligible':s['geometry']!='legacy25','started':time.time()}
 env=os.environ.copy();env['TMPDIR']=str(H/'tmp');env['PYTHONDONTWRITEBYTECODE']='1'
 with (H/'logs'/f'{s["name"]}.log').open('w') as log:p=subprocess.run(cmd,cwd=H,stdout=log,stderr=log,env=env,timeout=180)
 meta.update(returncode=p.returncode,elapsed_seconds=time.time()-meta['started'])
 if out.exists():(out/'run_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 assert p.returncode==0,f'{s["name"]}: return {p.returncode}'
 su=json.loads((out/'summary.json').read_text());assert su['n_primaries']==s['n'];return meta

def makeplan():
 specs=[]
 for physics in ['laue_only','loss']:
  for t in [1,5,10.218801,20]:specs.append(spec(f'{physics}_t{str(t).replace(".","p")}_off0',physics=physics,thickness=t))
 for off in [-60,-30,-18,18,30,60]:specs.append(spec(f'laue_only_off{str(off).replace("-","m")}',physics='laue_only',offset=off))
 for off in [18,30,60]:specs.append(spec(f'loss_off{off}',physics='loss',offset=off))
 for off in [0,18,60]:specs.append(spec(f'combined_off{off}',offset=off))
 specs.append(spec('em_only',physics='em_only'))
 for step in [0,.2,5]:specs.append(spec(f'step{str(step).replace(".","p")}',step=step))
 for model in ['legacy','input_only','dh']:
  for i in range(3):specs.append(spec(f'foot_{model}_s{i}',model=model,point=False))
 for geometry,model in [('ring25cut','dh'),('ring22','dh'),('legacy25','legacy')]:
  for i in range(3):specs.append(spec(f'{geometry}_s{i}',geometry=geometry,model=model,point=False))
 for i,s in enumerate(specs):s['seed']=92029000+i
 for s in specs:
  if s['name'].startswith('step') or s['name']=='combined_off0':s['seed']=92029100
 return specs
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('section',choices=['smoke','suite']);a=ap.parse_args()
 if a.section=='smoke':
  for s in [spec('smoke_dh',physics='laue_only',n=3000,seed=92028101),spec('smoke_loss',physics='loss',n=3000,seed=92028102),spec('smoke_combined',n=3000,seed=92028103),spec('smoke_cut',geometry='ring25cut',point=False,n=3000,seed=92028104)]:
   r=run(s);print(r['name'],r['elapsed_seconds'],flush=True)
 else:
  plan=makeplan();(H/'inputs/run_plan.json').write_text(json.dumps(plan,indent=2)+'\n');results=[];errors=[]
  with ThreadPoolExecutor(max_workers=2) as pool:
   fut={pool.submit(run,s):s for s in plan}
   for f in as_completed(fut):
    try:r=f.result();results.append(r);print('DONE',r['name'],round(r['elapsed_seconds'],2),flush=True)
    except Exception as ex:errors.append(str(ex));print('FAIL',str(ex),flush=True)
  ledger={'status':'PASS' if not errors else 'INCOMPLETE','valid_runs':results,'failures':errors,'n_valid_primaries':sum(r['n'] for r in results),'scope':'no cross-model/geometry pooling; same step seed only a paired diagnostic'}
  (H/'reports/run_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n');assert not errors,errors
