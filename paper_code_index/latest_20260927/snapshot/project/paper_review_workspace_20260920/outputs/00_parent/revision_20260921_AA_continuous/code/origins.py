from common import *
import gzip,re,concurrent.futures
from collections import defaultdict
jobs=defaultdict(list)
for r in rows(O/'data/a/origin_tasks.csv'):jobs[r['sim_path']].append(r)
def extract(item):
 path,rs=item;cache=O/'data/a/origin_cache'/f"{rs[0]['job_id']}.json"
 if cache.exists():return read(cache)
 want={int(r['event_id']):r for r in rs};out=[];current=None;seed=None
 with gzip.open(path,'rb') as f:
  for line in f:
   if line.startswith(b'Seed '):seed=int(line.split()[1])
   if line.startswith(b'ID '):current=int(line.split()[1])
   if current in want and line.startswith(b'IA INIT'):
    r=want.pop(current).copy();assert seed==int(r['seed']);v=line.decode().strip().split(';');x,y,z=map(float,v[4:7]);r.update(xprime_cm=(x-z)/math.sqrt(2),yprime_cm=y,zprime_cm=(x+z)/math.sqrt(2),init_line=line.decode().strip());out.append(r)
    if not want:break
 assert not want,(path,want)
 save(cache,out);print('ORIGINS',rs[0]['job_id'],len(out),flush=True);return out
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:orig=[r for rs in pool.map(extract,jobs.items()) for r in rs]
write(O/'data/delayed_origins_a_500.csv',sorted(orig,key=lambda r:int(r['catalog_index'])))
old=O.parent/'no_plastic_followup_20260921/data/delayed_origins_b_500.csv'
assert old.exists();write(O/'data/delayed_origins_b_500.csv',rows(old))
V={m:{} for m in 'ab'}
for model in ['a','b']:
 V[model].update(read(O/f'data/{model}/direct_statistics.json'))
 origins=rows(O/f'data/delayed_origins_{model}_500.csv')
 file=P/('tmp/m05_issue9_fixed27_20260831/build_activation_origin_donuts'+('' if model=='a' else '_model_b')+'.py');tree=ast.parse(file.read_text());nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id.endswith('_VOLUMES') for t in n.targets) or isinstance(n,ast.FunctionDef) and n.name=='classify_component'];ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),ns);classify=ns['classify_component']
 for r in origins:
  if model=='a':
   v=r['source_volume'];mat=r['source_material']
   if v=='ColdPlate_MXC_100mK_SD_anchor':component='mxc_50mk_cu_plate'
   elif v.startswith('Cu_SubstrateSupport_'):component='tes_substrate_cu_panels'
   elif v=='SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm':component='tes_cu_heat_sink'
   elif mat=='Bi':component='nearfield_bi_liner'
   elif mat=='Aluminium':component='al_cryostat_shields'
   elif mat=='W':component='other_detector_bay'
   elif mat=='BGO':component='bpe_bgo_shielding'
   else:component='other_dr_cold_hardware'
   r['component_key']=component
  else:r['component_key']='tes_pixel_ta' if r['source_volume'].startswith('TES_Pixel_') else classify(r['source_volume'])
  r['region']='DR/MXC and cold plates' if r['source_volume'].startswith('ColdPlate_') or r['source_volume']=='DR_MixingChamber_Cu' else ('TES-near structures' if any(k in r['source_volume'] for k in ['TES_','SubstrateSupport','SH3_Layer','SH3_OptV2_W_Frame','BottomColdPlate','ColdFinger','50mK','Bi_MXC_TES']) else 'Other structures')

 agg={};total=V[model]['compton_trajectory_veto']['delayed']['rate']
 for name,field in [('components','component_key'),('families','family'),('materials','source_material'),('nuclides','source_parent_ZA'),('regions','region'),('volumes','source_volume')]:
  agg[name]={}
  for key in sorted({str(r[field]) for r in origins}):
   w=np.array([float(r['day15_weight_cps']) for r in origins if str(r[field])==key]);rate=float(w.sum());var=float((w*w).sum());agg[name][key]={'n':len(w),'rate':rate,'variance':var,'sigma':math.sqrt(var),'share':rate/total}
  assert math.isclose(sum(x['rate'] for x in agg[name].values()),total,rel_tol=1e-12)
  V[model]['origin_'+name]={k:x['rate'] for k,x in agg[name].items()}
 V[model]['origin_statistics']=agg
save(O/'data/paper_values_500.json',V)
print('ORIGINS COMPLETE',len(orig),flush=True)
