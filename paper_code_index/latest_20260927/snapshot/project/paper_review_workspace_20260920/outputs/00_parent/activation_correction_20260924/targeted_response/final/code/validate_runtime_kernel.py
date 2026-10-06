from decay_kernel import *
import sys,time
data=NuclearData();jobs=json.loads((D/'runtime_jobs.json').read_text());cache={}
selected=sys.argv[1:] or ['aa_delayed_epoch0_p_001','optv3_delayed_p_shard0001']
reports=[]
for jobid in selected:
 r=next(r for r in jobs if r['job_id']==jobid);point=json.loads((D/f"points_{r['model']}_{r['family']}.json").read_text())['points'];za=np.array([x['za'] for x in point]);blocks=collections.Counter()
 for x in point:blocks[x['za']]+=x['source_blocks']
 a=np.load(D/'decay_metadata'/(jobid+'.npz'))['events'];mapping=np.load(D/'decay_metadata'/(jobid+'.map.npz'));rootza=za[mapping['point_id']]
 actual=collections.Counter(zip(rootza,a['za']));pred=collections.Counter();rr=[];unsupported=[]
 T=float(a['time'][-1]);rootrate=r['independent_source_activity_Bq']/10000
 for z,nblock in blocks.items():
  name=data.name(z)
  if name not in cache:cache[name]=LineageKernel(data,name)
  k=cache[name];c=k.finite_counts(T);p=rootrate*nblock*c
  for n,v in zip(k.names,p):pred[z,data.states[n]['za']]+=float(v)
  obs=sum(v for (root,child),v in actual.items() if root==z);expected=float(p.sum());rootexp=rootrate*nblock*T
  rr.append(dict(root_za=int(z),source_blocks=nblock,observed=obs,expected=expected,expected_roots=rootexp,excess=obs-expected,unresolved=k.unresolved))
  for (root,child),nn in actual.items():
   if root==z and (root,child) not in pred:unsupported.append([int(root),int(child),nn])
 total=sum(pred.values());rep=dict(job_id=jobid,observed=len(a),expected=total,relative_difference=(len(a)-total)/total,observed_queued=r['queued_events'],expected_queued=total-rootrate*10000*T,unsupported_observed_pairs=unsupported,roots=rr)
 reports.append(rep);print(jobid,'observed',len(a),'expected',total,'queued',r['queued_events'],rep['expected_queued'],'missing',unsupported,flush=True)
 print('largest residual',sorted(rr,key=lambda x:abs(x['excess']),reverse=True)[:6],flush=True)
(D/'kernel_runtime_validation.json').write_text(json.dumps(reports,indent=2)+'\n')
