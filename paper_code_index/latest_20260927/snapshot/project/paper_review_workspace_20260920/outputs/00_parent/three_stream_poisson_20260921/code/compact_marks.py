"""Exact mark compression: saturating deposits with no TES hits.
Every arrival is still generated. A >=50-keV BGO hit always vetoes its group;
its exact energy and plastic deposit cannot affect either selection outcome.
"""
from pathlib import Path
import json,numpy as np
O=Path(__file__).resolve().parents[1];dt=np.dtype([('plastic','<f4'),('bgo','<f4'),('hits','<u2'),('flags','u1'),('stream','u1')])
for model in ['a','b']:
 d=O/'data'/model;m=json.loads((d/'metadata.json').read_text());a=np.memmap(d/'records.bin',mode='r',dtype=dt);nb=m['background_records'];masks=[]
 for stream in [0,1]:
  masks.extend([(a['hits']==0)&(a['stream']==stream)&(a['bgo']>=50),(a['hits']==0)&(a['stream']==stream)&(a['bgo']==0)&(a['plastic']>=50)])
 remove=np.logical_or.reduce(masks);retained=np.flatnonzero(~remove);hot=np.zeros(4,dtype=dt)
 hot['bgo'][[0,2]]=50;hot['plastic'][[1,3]]=50;hot['stream']=[0,0,1,1]
 compact=np.r_[hot,a[retained]];mapping=np.r_[-np.arange(1,5,dtype='i8'),retained].astype('i8');mapping.tofile(d/'compact_to_original.bin');compact.tofile(d/'compact_records.bin')
 cm={**m,'original_background_records':nb,'background_records':len(compact)-m['signal_records'],'hot_marks':4,'exact_compression':'No-TES BGO>=50 -> BGO50; no-TES BGO0+plastic>=50 -> plastic50. Separate prompt/delayed marks. All arrivals and subthreshold deposits retained.'}
 for node in [0,20,40,60,80]:
  w=np.memmap(d/f'weights_{node:03d}.bin',mode='r',dtype='f8');nw=np.r_[[w[mask].sum() for mask in masks],w[retained]]
  assert np.isclose(nw.sum(),w.sum(),rtol=1e-14)
  for stream in [0,1,2]:assert np.isclose(nw[compact['stream']==stream].sum(),w[a['stream']==stream].sum(),rtol=1e-14)
  nw.tofile(d/f'compact_weights_{node:03d}.bin')
 (d/'compact_metadata.json').write_text(json.dumps(cm,indent=2)+'\n')
 partial=d/'aborted_uncompressed';partial.mkdir(exist_ok=True)
 for p in d.glob('anchor_*.groups'):p.rename(partial/p.name)
 (partial/'README.txt').write_text('Interrupted incomplete full-mark timelines; excluded from all results. Restart uses mathematically equivalent mark compression, unchanged arrivals and rates.\n')
 print(model,len(a),'->',len(compact),'marks; exact stream-rate checks PASS',flush=True)
