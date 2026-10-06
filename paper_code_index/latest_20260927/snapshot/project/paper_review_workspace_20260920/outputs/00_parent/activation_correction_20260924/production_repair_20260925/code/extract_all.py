from pathlib import Path
import json,hashlib,subprocess,concurrent.futures,time
P=Path(__file__).resolve().parents[1];O=P.parent;H=O/'closure_followup';fix=lambda p:Path(p.replace('/mnt/data','/media/ubuntu/903261CE3261BA3C'))
mf={r['model']:r['manifest'] for r in json.loads((H/'data/holdouts.json').read_text())};plan=[]
for model,mp in mf.items():
 m=json.loads(Path(mp).read_text())
 for i,r in enumerate(m['input_receipts']):
  dat=fix(r['dat_path']);assert hashlib.sha256(dat.read_bytes()).hexdigest()==r['dat_sha256'];f=fix(r['sim_path']);assert f.stat().st_size==r['sim_bytes'];receipt=json.loads(fix(r['receipt_path']).read_text());src=fix(receipt['source_path']);st=src.read_text();assert 'DecayMode ActivationBuildUp' in st and 'DetectorTimeConstant 1e-9' in st
  d=P/'data'/model/f'{i:03d}_{r["job_id"]}';d.mkdir(parents=True,exist_ok=True)
  plan.append({**r,'model':model,'sim_path':str(f),'dat_path':str(dat),'receipt_path':str(fix(r['receipt_path'])),'source_path':str(src),'directory':str(d),'manifest':mp})
(P/'data/production_plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('closed list',len(plan),'compressed bytes',sum(r['sim_bytes'] for r in plan),flush=True)
def run(r):
 d=Path(r['directory']);rep=d/'extraction.json'
 if rep.exists():return json.loads(rep.read_text())
 start=time.monotonic();p=subprocess.run([str(P/'code/extract_production'),r['sim_path'],str(d/'thin.sim.gz')],capture_output=True,text=True);assert p.returncode==0,p.stderr;nev,nout,nrp=map(int,p.stdout.split());assert nev==r['events'],(r['job_id'],nev,r['events']);assert nrp==r['sum_RP'],(r['job_id'],nrp,r['sum_RP'])
 res={**r,'read_events':nev,'retained_events':nout,'RP_records':nrp,'thin_bytes':(d/'thin.sim.gz').stat().st_size,'elapsed_s':time.monotonic()-start,'status':'EXTRACTED_COUNTS_CLOSED'};rep.write_text(json.dumps(res,indent=2)+'\n');print(r['model'],r['job_id'],nev,nout,nrp,round(res['elapsed_s'],1),flush=True);return res
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,plan))
(P/'data/extraction_manifest.json').write_text(json.dumps(results,indent=2)+'\n');print('COMPLETE',len(results),flush=True)
