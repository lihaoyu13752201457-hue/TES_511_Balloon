from pathlib import Path
import numpy as np,json,subprocess,math,struct
O=Path(__file__).resolve().parents[1];d=O/'validation/deferred_synthetic';d.mkdir(exist_ok=True)
dt=np.dtype([('plastic','<f4'),('bgo','<f4'),('hits','<u2'),('flags','u1'),('stream','u1')]);a=np.zeros(4,dtype=dt);a['hits']=[0,1,0,1];a['flags']=[0,7,0,7];a['bgo']=[50,0,0,0];a['stream']=[0,1,1,2];a.tofile(d/'records.bin');np.array([8.,2.,0.,1.]).tofile(d/'weights_000.bin')
subprocess.run([str(O/'code/timeline_deferred'),str(d),'000','100000','82346721','3',str(d/'run'),'.01'],check=True)
j=json.loads((d/'run.json').read_text());zs=[(x-r*1e5)/math.sqrt(r*1e5) for x,r in zip(j['arrivals'],[8,2,1])];assert max(map(abs,zs))<6
nsignal=0;vetoed_signal=0
with (d/'run.groups').open('rb') as f:
 while h:=f.read(12):
  serial,n=struct.unpack('<QI',h);ids=[];times=[]
  for _ in range(n):
   ix,t=struct.unpack('<Id',f.read(12));assert ix!=2;ids.append(ix);times.append(t)
  assert all(0<=times[k+1]-times[k]<=.010000001 for k in range(n-1))
  ns=ids.count(3);nsignal+=ns;vetoed_signal+=ns*(0 in ids)
assert nsignal==j['arrivals'][2]
# Exact analytic BGO-only survival of a specified signal arrival, including
# arbitrarily long transitive groups and any number of other signal arrivals.
p=math.exp(-.11);survive=(p/(1-(1-p)*3/11))**2;actual=1-vetoed_signal/nsignal;z=(actual-survive)/math.sqrt(survive*(1-survive)/nsignal);assert abs(z)<6
out={'status':'PASS','arrival_zscores':zs,'signal_arrivals_conserved':nsignal,'event_signal_survival':actual,'exact_analytic_BGO_survival':survive,'survival_zscore_approx':z,'all_generated_arrival_streams_counted':True,'signal_deposits_not_replaced_by_neighbour_occupancy':True}
(O/'validation/deferred_sampler_test.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
