from pathlib import Path
import json,csv,collections
import numpy as np
from scipy.spatial import cKDTree
O=Path(__file__).resolve().parents[1];D=O/'data';DISK=Path('/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data')
M={'a':DISK/'AA/aa_reproduce_A_20260921_v1/delayed_epoch0_inventory/generated/activation/manifest.json','b':DISK/'SH3/sh3_optv3_m05_delayed_activation_v1/generated/activation/manifest.json'}
def rebase(p):return Path(str(p).replace('/mnt/data/TES_Balloon_511_data',str(DISK)))
def locator(model,family):
 m=json.loads(M[model].read_text());c=next(c for c in m['source_cells'] if c['family']==family)
 ps={};orders=[]
 for r in csv.DictReader(rebase(c['positions_path']).open()):
  if int(r['sample_index'])%5:continue
  xyz=tuple(float(r[k]) for k in ['x_cm','y_cm','z_cm']);meta=(r['volume'],int(r['ZA']),float(r['excitation_keV']))
  if xyz in ps:assert ps[xyz][:3]==meta
  else:ps[xyz]=(*meta,len(ps),0)
  v=ps[xyz];ps[xyz]=(*v[:4],v[4]+1);orders.append([int(r['sample_index']),v[3]])
 coords=np.array(list(ps));vals=list(ps.values());tree=cKDTree(coords)
 rows=[dict(point_id=v[3],x=x[0],y=x[1],z=x[2],volume=v[0],za=v[1],exc=v[2],source_blocks=v[4]) for x,v in ps.items()]
 (D/f'points_{model}_{family}.json').write_text(json.dumps({'points':rows,'source_block_to_point':orders},separators=(',',':'))+'\n')
 return tree,np.array([v[1] for v in vals]),rows
def run(r,loc):
 stem=r['job_id'];mp=D/'decay_metadata'/(stem+'.npz');dest=D/'decay_metadata'/(stem+'.map.npz');jp=dest.with_suffix('.json')
 if jp.exists():
  old=json.loads(jp.read_text())
  if old.get('map_version')==2:return old
 if not mp.exists():return None
 a=np.load(mp)['events'];tree,zs,_=loc
 xyz=np.column_stack([a[k] for k in ['x','y','z']]);distance,ix=tree.query(xyz,k=2,p=np.inf,workers=2)
 assert np.max(distance[:,0])<.001,(stem,np.max(distance[:,0]))
 assert np.all((distance[:,1]>distance[:,0]+1.102e-5)&(distance[:,1]>2*distance[:,0]))
 point=ix[:,0].astype('u4');primary=(a['za']==zs[point])
 # No beta/EC cycle returns to the original ground state; check the native
 # root-source counter independently instead of assuming this classification.
 assert np.count_nonzero(primary)==r['root_events'],(stem,int(primary.sum()),r['root_events'])
 assert np.all(np.nan_to_num(a['exc'][primary])==0)
 order=np.lexsort((a['time'],point));so=point[order];t=a['time'][order]
 cont=np.r_[False,(so[1:]==so[:-1])&(np.diff(t)<=1e-6+1e-12)]
 coincident_roots=order[cont & primary[order]]
 cont[primary[order]]=False
 starts=np.maximum.accumulate(np.where(cont,0,np.arange(len(a))))
 group=np.empty(len(a),dtype='u4');group[order]=order[starts]
 _,n=np.unique(group,return_counts=True);groups=int(len(n));multi=int(np.sum(n>1))
 # Distinct ordinary source events accidentally close in this MC-only time
 # must not be joined as a radioactive cascade.
 collisions=[]
 for g,nn in zip(*np.unique(group[primary],return_counts=True)):
  if nn>1:collisions.append(int(g))
 res=dict(job_id=stem,model=r['model'],family=r['family'],events=len(a),groups=groups,multiple_event_groups=multi,merged_records=len(a)-groups,primary_source_time_collisions=collisions,coincident_roots_kept_separate=coincident_roots.tolist(),max_match_distance_cm=float(distance[:,0].max()),map_version=2)
 np.savez_compressed(dest,point_id=point,is_primary=primary,group_first_index=group)
 jp.write_text(json.dumps(res,indent=2)+'\n');return res
if __name__=='__main__':
 jobs=json.loads((D/'runtime_jobs.json').read_text());locs={};results=[]
 for r in jobs:
  k=(r['model'],r['family'])
  if k not in locs:locs[k]=locator(*k)
  x=run(r,locs[k])
  if x:results.append(x)
 (D/'source_map_summary.json').write_text(json.dumps(results,indent=2)+'\n')
 print('Mapped',len(results),'records',sum(x['events'] for x in results),'merged',sum(x['merged_records'] for x in results),'collisions',sum(len(x['primary_source_time_collisions']) for x in results))
