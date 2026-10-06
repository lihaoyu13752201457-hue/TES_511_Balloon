from pathlib import Path
import json,subprocess,sys,concurrent.futures,time
O=Path(__file__).resolve().parents[1]
model=sys.argv[1];nodes=[60,0,20,40,80]
def run(node):
 d=O/'data'/model;m=json.loads((d/'compact_metadata.json').read_text());out=d/f'anchor_{node:03d}'
 assert not out.with_suffix('.json').exists() and not out.with_suffix('.groups').exists()
 generator='timeline_direct' if model=='b' or node in [0,20,60] else 'timeline_deferred'
 cmd=[str(O/'code'/generator),str(d),f'{node:03d}','200000',str(2609210000+(0 if model=='a' else 1000)+node),str(m['background_records']),str(out),'1e-6','4']
 print('START',model,node,flush=True);subprocess.run(cmd,check=True);return node
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:
 for result in p.map(run,nodes):print('FINISHED',model,result,flush=True)
