import sys,json,collections,math,csv
from pathlib import Path
import numpy as np
C=Path(__file__).resolve().parents[1];O=C.parent;sys.path.insert(0,str(O/'code'))
from targeted_inventory import corrected_data
from decay_kernel import LineageKernel
D=O/'data';T=O/'targeted_response';F=C/'final'
data=corrected_data();jobs=json.loads((D/'runtime_jobs.json').read_text());wold=json.loads((T/'W176_limitations.json').read_text());scales=list(csv.DictReader(Path('/home/ubuntu/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv').open()));times=np.array([float(r['day_mid'])*86400 for r in scales]);out={};cache={}
for model in ('a','b'):
 curve=np.zeros(81)
 for family in sorted({r['family'] for r in wold if r['model']==model}):
  pts=json.loads((D/f'points_{model}_{family}.json').read_text())['points'];blocks=collections.Counter()
  for p in pts:blocks[p['za']]+=p['source_blocks']
  act=next(j['independent_source_activity_Bq'] for j in jobs if (j['model'],j['family'])==(model,family));ss=np.array([float(r[f'scale_{family}_to_parma_reference']) for r in scales])
  for wr in [r for r in wold if (r['model'],r['family'])==(model,family)]:
   root=wr['root'];key=(family,root)
   if key not in cache:
    k=LineageKernel(data,root);cache[key]=k.mission(times,ss,1e-6)[:,k.idx['W176']]
   pref=act*blocks[data.states[root]['za']]/10000/-math.expm1(-15*86400/data.tau(root,True));v=cache[key]*pref
   assert abs(v[60]-wr['day15_source_rate_cps'])<1e-10;curve+=v
 np.save(C/'data'/f'W176_source_rate_{model}.npy',curve)
 p=F/'data'/model/'response';a={k:np.load(p/(k+'.npy'),mmap_mode='r') for k in ('event_category','event_base_weight_cps','bgo_keV','hit_count','measured_total_keV')};factors=np.load(p/'category_factors.npy');cat=a['event_category'];b=a['event_base_weight_cps'];e=a['measured_total_keV'];veto_free=a['bgo_keV']<50;n=len(factors[0]);total={}
 masks={'all_positive':b>0,'bgo_free':(b>0)&veto_free,'bgo_free_TES':(b>0)&veto_free&(a['hit_count']>0),'bgo_free_200_520':(b>0)&veto_free&(e>=200)&(e<=520),'bgo_free_0_520':(b>0)&veto_free&(e<=520),'bgo_free_510_512':(b>0)&veto_free&(e>=510)&(e<=512)}
 for name,mask in masks.items():
  q=np.bincount(cat[mask],weights=b[mask],minlength=n);r=factors@q
  total[name]={'day15_cps':float(r[60]),'max_cps':float(r.max())};np.save(C/'data'/f'Wbound_{model}_{name}_rate.npy',r)
 out[model]={'W176_day15_cps':float(curve[60]),'W176_max_cps':float(curve.max()),'existing_rate_summary':total};print(model,out[model],flush=True)
(C/'data/W176_preliminary_rates.json').write_text(json.dumps(out,indent=2)+'\n')
