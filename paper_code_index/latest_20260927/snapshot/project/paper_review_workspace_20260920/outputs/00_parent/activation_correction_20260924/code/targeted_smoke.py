from targeted_environment import *
import json, re
S=T/'smoke_verified';S.mkdir(exist_ok=True)
points=json.loads((O/'data/points_a_p.json').read_text())['points']
p=next(p for p in points if p['za']==29062 and 'Cu' in p['volume'])
jobs=json.loads((O/'data/runtime_jobs.json').read_text())
geometry=re.search(r'(?m)^Geometry\s+(.*)$',Path(jobs[0]['source_path']).read_text()).group(1)
variants=[('Zn62',30062,0),('Cu62',29062,0),('Er158',68158,0),('Ho158m',67158,67.2),('Ge73m',32073,13.284)]
elist=S/'events.dat';rows=[]
for name,za,exc in variants:
 for k in range(200):
  i=len(rows);rows.append(f'{i} 0 {za} {exc} {i+1} {p["x"]} {p["y"]} {p["z"]} 0 0 1 0 0 0 0.000001')
elist.write_text('\n'.join(rows)+'\n')
source=S/'smoke.source';source.write_text(f'''Version 1
Geometry {geometry}
Seed 629240701
PhysicsListHD qgsp-bic-hp
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationDelayedDecay
DetectorTimeConstant 1e-6
StoreSimulationInfo all
StoreIsotopes true
Run smoke
smoke.FileName {S}/smoke
smoke.Triggers {len(rows)}
smoke.Source explicit
explicit.EventList {elist}
''')
with (S/'run.log').open('w') as f:
 p=subprocess.run([str(T/'cosima'),'-z',str(source)],cwd=S,env=environment(),stdout=f,stderr=subprocess.STDOUT)
print('smoke returncode',p.returncode,flush=True)
assert p.returncode==0
