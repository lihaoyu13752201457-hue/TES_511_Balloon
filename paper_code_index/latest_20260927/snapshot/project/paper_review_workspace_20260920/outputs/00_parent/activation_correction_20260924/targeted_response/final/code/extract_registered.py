from pathlib import Path
import json,subprocess,concurrent.futures,time
import numpy as np
O=Path(__file__).resolve().parents[1];D=O/'data/decay_metadata';D.mkdir(exist_ok=True)
rows=json.loads((O/'data/runtime_jobs.json').read_text())
dt=np.dtype([('id','<u4'),('za','<u4'),('time','<f8'),('x','<f8'),('y','<f8'),('z','<f8'),('exc','<f8'),('primza','<i4'),('flags','<u4')])
ft=np.dtype([('parent','<u4'),('za','<u4'),('exc','<f8'),('delay','<f8')])
def run(r):
 j=r['job_id'];meta=D/(j+'.json');out=D/(j+'.npz')
 if meta.exists() and out.exists():return json.loads(meta.read_text())
 st=time.time();ep=D/(j+'.events.bin');fp=D/(j+'.future.bin')
 z=subprocess.run([str(O/'code/extract_decay_metadata'),r['sim_path'],str(ep),str(fp)],text=True,capture_output=True,check=True)
 m=json.loads(z.stdout);a=np.fromfile(ep,dtype=dt);b=np.fromfile(fp,dtype=ft)
 assert len(a)==r['events']==m['events'];assert np.array_equal(a['id'],np.arange(1,len(a)+1))
 assert np.all(np.diff(a['time'])>=0)
 known=(a['flags']&4)!=0;assert np.all(a['za'][known]==a['primza'][known])
 np.savez_compressed(out,events=a,future=b)
 m.update(job_id=j,model=r['model'],family=r['family'],sim_path=r['sim_path'],sim_bytes=r['sim_bytes'],seconds=time.time()-st,last_time_s=float(a['time'][-1]),metadata_bytes=out.stat().st_size)
 meta.write_text(json.dumps(m,indent=2)+'\n');ep.unlink();fp.unlink()
 return m
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  fs={ex.submit(run,r):r for r in rows}
  for i,f in enumerate(concurrent.futures.as_completed(fs),1):
   m=f.result();print(i,len(rows),m['job_id'],round(m['seconds'],1),m['unknown_excitation'],flush=True)
