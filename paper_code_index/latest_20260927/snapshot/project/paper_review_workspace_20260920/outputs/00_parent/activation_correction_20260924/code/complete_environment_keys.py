from targeted_environment import *
import collections
manifest=Path('/media/ubuntu/903261CE3261BA3C/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_activation_v1/generated/activation/manifest.json');m=json.loads(manifest.read_text())
keys={('p','SH3_OptV2_W_Frame_PosY',74170),('gamma','TES_Pixel_L2',73180),('n','TES_Pixel_L1',74170)};sources=[]
fix=lambda p:Path(p.replace('/mnt/data','/media/ubuntu/903261CE3261BA3C'))
for r in m['input_receipts']:
    if r['family'] not in {k[0] for k in keys}:continue
    volume=None
    for line in fix(r['dat_path']).read_text().splitlines():
        w=line.split()
        if not w:continue
        if w[0]=='VN':volume=w[1]
        if w[0]=='RP' and (r['family'],volume,int(w[1])) in keys and float(w[2])==0:
            assert float(w[3])==1
            sources.append(dict(family=r['family'],source_volume=volume,source_parent_ZA=int(w[1]),sim=str(fix(r['sim_path'])),sim_bytes=r['sim_bytes'],dat=str(fix(r['dat_path'])),dat_sha256=sha(fix(r['dat_path']))))
assert len(sources)==3
print('exact files',len(sources),'compressed bytes',sum(r['sim_bytes'] for r in sources),flush=True)
(T/'environment_source_join_plan.json').write_text(json.dumps(sources,indent=2)+'\n')
binary=O/'code/extract_targeted_primary'
subprocess.run(['g++','-O3',str(binary.with_suffix('.cpp')),'-lz','-o',str(binary)],check=True)
for r in sources:
    result=subprocess.check_output([str(binary),r['sim'],r['source_volume'],str(r['source_parent_ZA'])],text=True).split();r.update(event_id=int(result[0]),primary_energy_keV_total=float(result[1]));print(r['family'],r['event_id'],r['primary_energy_keV_total'],flush=True)
(T/'environment_new_keys.json').write_text(json.dumps(sources,indent=2)+'\n')
