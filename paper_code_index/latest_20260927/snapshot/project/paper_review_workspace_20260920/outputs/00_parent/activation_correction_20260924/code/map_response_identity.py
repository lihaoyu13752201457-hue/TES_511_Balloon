from pathlib import Path
import json,numpy as np
O=Path(__file__).resolve().parents[1];D=O/'data';W=O.parents[2];P=W.parent
AS=Path('/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data/AA/aa_reproduce_A_20260921_v1/derived/merged')
BD=P/'core_md/balloon511_ea_latex_drafts/meeting_revision_20260916/data'
runtime=json.loads((D/'runtime_jobs.json').read_text());known={r['job_id']:r for r in runtime}
reg=json.loads((AS/'category_registry.json').read_text())['categories']
cats={(c['family'],c['source_parent_ZA']):c for c in reg if c['stream']=='delayed'}
curs={k:c['event_start'] for k,c in cats.items()};covered=0
for p in json.loads((AS/'manifest.json').read_text())['input_compacts']:
 p=Path(p)
 if 'aa_delayed_' not in p.name:continue
 meta=json.loads(p.with_suffix('.json').read_text());j=meta['job_id'];assert j in known
 z=np.load(p);eid=z['event_id'];za=z['source_za'];ix=np.empty(len(eid),dtype='i8')
 for q in np.unique(za):
  where=np.flatnonzero(za==q);key=(meta['family'],int(q));st=curs[key];ix[where]=np.arange(st,st+len(where));curs[key]+=len(where)
 np.savez_compressed(D/'decay_metadata'/(j+'.response.npz'),event_id=eid,global_index=ix)
 covered+=len(ix)
assert all(curs[k]==c['event_start']+c['event_count'] for k,c in cats.items())
print('AA response identities',covered,flush=True)
z=np.load(BD/'identity_b.npz');ej=z['event_job'];eid=z['event_id'];identity_jobs=json.loads((BD/'identity_b_jobs.json').read_text());jid={j['job_id']:i for i,j in enumerate(identity_jobs)}
BC=P/'engineering/geometry_optimization_20260815/70_m05_sg3_sh3_prompt_statistics_integration_20260828/outputs/01_integrated_catalog_b'
reg=json.loads((BC/'category_registry.json').read_text())['categories'];cats={(c['family'],c['source_parent_ZA']):c for c in reg if c['stream']=='delayed'};curs={k:c['event_start'] for k,c in cats.items()}
jobs=json.loads((P/'DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json').read_text())['jobs'];covered=0;parity=0;disagreements=[]
for j in sorted(jobs,key=lambda r:r['scan_index']):
 if j['stream']!='delayed':continue
 assert j['job_id'] in known
 ar=np.load(j['catalog_path']);ids=ar['event_id'];za=ar['source_za'];where=np.empty(len(ids),dtype='i8')
 for q in np.unique(za):
  ix=np.flatnonzero(za==q);key=(j['family'],int(q));st=curs[key];where[ix]=np.arange(st,st+len(ix));curs[key]+=len(ix)
 pinned=ej[where]>=0
 bad=np.flatnonzero(pinned & ((ej[where]!=jid[j['job_id']])|(eid[where]!=ids)))
 for k in bad:disagreements.append(dict(global_index=int(where[k]),true_job=j['job_id'],true_event_id=int(ids[k]),old_job=identity_jobs[int(ej[where[k]])]['job_id'],old_event_id=int(eid[where[k]])))
 parity+=int(pinned.sum())
 np.savez_compressed(D/'decay_metadata'/(j['job_id']+'.response.npz'),event_id=ids,global_index=where)
 covered+=len(where)
assert all(curs[k]==c['event_start']+c['event_count'] for k,c in cats.items())
print('B response identities',covered,flush=True)
print('B previously pinned identity matches',parity,flush=True)
(D/'old_identity_b_disagreements.json').write_text(json.dumps(disagreements,indent=2)+'\n')
print('B old signature-based identity disagreements',len(disagreements),flush=True)
