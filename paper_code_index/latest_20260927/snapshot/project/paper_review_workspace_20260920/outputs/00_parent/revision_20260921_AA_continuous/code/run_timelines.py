from common import *
import subprocess,time,concurrent.futures

def run(model,node):
 d=O/'data'/model;meta=read(d/'compact_metadata.json');base=d/f'anchor_{node:03d}'
 if not base.with_suffix('.json').exists():
  print('START',model,node,flush=True)
  with base.with_suffix('.log').open('w') as log:
   subprocess.run([str(O/'code/timeline_deferred'),str(d),f'{node:03d}','200000',str(2609220000+(1000 if model=='b' else 0)+node),str(meta['background_records']),str(base),str(TAU),'4'],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('TIMELINE DONE',model,node,flush=True)
 with base.with_name(base.name+'_analyze.log').open('w') as log:
  subprocess.run([sys.executable,str(O/'code/analyze.py'),model,str(node)],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('ANALYZED',model,node,flush=True)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  fs=[pool.submit(run,m,n) for m in ['a','b'] for n in [0,20,40,60,80]]
  for f in concurrent.futures.as_completed(fs):f.result()
