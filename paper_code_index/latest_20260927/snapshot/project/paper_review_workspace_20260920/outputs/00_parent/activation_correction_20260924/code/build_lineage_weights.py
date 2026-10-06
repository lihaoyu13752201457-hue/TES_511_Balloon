from decay_kernel import *
import time
P=O.parents[2].parent
data=NuclearData();jobs=json.loads((D/'runtime_jobs.json').read_text());kernels={};curves={};rows=[];weights=[];audit=[]
scales=list(csv.DictReader((P/'engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv').open()))
times=np.array([float(x['day_mid'])*86400 for x in scales]);assert len(times)==81
for model,family in sorted({(j['model'],j['family']) for j in jobs}):
 js=[j for j in jobs if (j['model'],j['family'])==(model,family)];Ts=[]
 for j in js:Ts.append(json.loads((D/'decay_metadata'/(j['job_id']+'.json')).read_text())['last_time_s'])
 points=json.loads((D/f'points_{model}_{family}.json').read_text())['points'];roots=sorted({x['za'] for x in points});blocks=collections.Counter()
 for x in points:blocks[x['za']]+=x['source_blocks']
 expected_total=0.;expected_cluster=0.;unresolved=[]
 for rootza in roots:
  root=data.name(rootza)
  if root not in kernels:kernels[root]=LineageKernel(data,root)
  k=kernels[root];key=(family,root)
  if key not in curves:
   ss=np.array([float(x[f'scale_{family}_to_parma_reference']) for x in scales]);curves[key]=k.mission(times,ss,coincidence_s=1e-9)
  curve=curves[key];sat=-math.expm1(-15*86400/data.tau(root,True));assert sat>0,(root,data.tau(root,True))
  exposure=sum((k.finite_counts(T,1e-9) for T in Ts),np.zeros(len(k.names)))
  expected_total+=float(exposure.sum())*js[0]['independent_source_activity_Bq']*blocks[rootza]/10000
  cluster_exposure=sum((k.finite_counts(T,1e-6) for T in Ts),np.zeros(len(k.names)))
  expected_cluster+=float(cluster_exposure.sum())*js[0]['independent_source_activity_Bq']*blocks[rootza]/10000
  for n,den,cur in zip(k.names,exposure,curve.T):
   if den<=1e-100:continue
   w=np.maximum(cur,0)/sat/den
   assert np.all(np.isfinite(w)),(root,n)
   state=data.states[n]
   rows.append(dict(category_id=len(rows),model=model,family=family,source_parent_ZA=rootza,actual_state=n,actual_ZA=state['za'],actual_exc_keV=state['exc'],exposure_per_Bq_s=float(den),original_root_saturation=sat))
   weights.append(w)
  if k.unresolved:unresolved.append(dict(root=root,blocks=blocks[rootza],states=k.unresolved))
 audit.append(dict(model=model,family=family,expected_events=expected_total,observed_events=sum(j['events'] for j in js),expected_one_us_clusters=expected_cluster,observed_one_us_clusters=sum(json.loads((D/'decay_metadata'/(j['job_id']+'.map.json')).read_text())['groups'] for j in js),unresolved=unresolved))
 print(model,family,'categories',len(rows),'expected/raw',expected_total,sum(j['events'] for j in js),'unresolved_roots',len(unresolved),flush=True)
np.save(D/'lineage_weights_81nodes.npy',np.array(weights).T)
(D/'lineage_weight_registry.json').write_text(json.dumps(rows,indent=2)+'\n')
(D/'kernel_family_validation.json').write_text(json.dumps(audit,indent=2)+'\n')
