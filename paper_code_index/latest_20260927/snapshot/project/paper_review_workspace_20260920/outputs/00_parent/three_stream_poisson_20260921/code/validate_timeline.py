from pathlib import Path
import numpy as np,json,subprocess,struct,math
O=Path(__file__).resolve().parents[1];d=O/'validation'/'synthetic';d.mkdir(exist_ok=True)
dtype=np.dtype([('plastic','<f4'),('bgo','<f4'),('hits','<u2'),('flags','u1'),('stream','u1')]);a=np.zeros(4,dtype=dtype)
a['stream']=[0,1,1,2];a['hits']=[1,1,0,1];a['flags']=7;a.tofile(d/'records.bin');np.array([8.,2.,0.,1.]).tofile(d/'weights_000.bin')
subprocess.run([str(O/'code/timeline_direct'),str(d),'000','100000','92831415','3',str(d/'run'),'.01'],check=True)
j=json.loads((d/'run.json').read_text());nids=0;gids=set();maxsize=0
with (d/'run.groups').open('rb') as f:
 while h:=f.read(12):
  serial,n=struct.unpack('<QI',h);assert serial not in gids;gids.add(serial);maxsize=max(maxsize,n);prev=None
  for _ in range(n):
   ix,t=struct.unpack('<Id',f.read(12));assert ix!=2
   if prev is not None:assert 0<=t-prev<=.0100000001
   prev=t;nids+=ix==3
assert nids==j['arrivals'][2]
zs=[(x-r*1e5)/math.sqrt(r*1e5) for x,r in zip(j['arrivals'],[8,2,1])];assert max(map(abs,zs))<6
expected_fraction=1-math.exp(-11*.01);observed=j['multi_groups']/j['groups'];assert abs(expected_fraction-observed)<.003
assert maxsize>=4
out={'status':'PASS','arrival_rate_zscores':zs,'multi_group_fraction':observed,'exact_expected_multi_group_fraction':expected_fraction,'signal_arrivals_conserved':nids,'zero_weight_record_never_sampled':True,'all_written_adjacent_gaps_within_tau':True,'maximum_group_size':maxsize,'method':'All events are unconditional exponentially spaced draws with physical-rate marks; no conditional signal draw.'}
(O/'validation/timeline_test.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
