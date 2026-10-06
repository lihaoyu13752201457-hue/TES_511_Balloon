"""Authorized A internal-injection control. Never pool with physical A/B."""
from pathlib import Path
import copy,hashlib,json,math
import numpy as np
O=Path(__file__).resolve().parents[1];F=O.parent
cfg=json.loads((O/'inputs_manifest.json').read_text());m=copy.deepcopy(cfg['models']['a']);name='a_internal_diagnostic';seed=1952092003;n=cfg['n_input']
assert name not in cfg['models'],'diagnostic already registered'
(O/'runs'/name).mkdir()
identity=np.load(O/'data/optical_identity.npz');pos=identity['optical_position_mm'];direction=identity['optical_direction'];c=math.sqrt(.5);rot=np.array([[c,0,c],[0,1,0],[-c,0,c]])
worldpos=np.column_stack([np.full(n,-13.1),pos[:,0]*.1,pos[:,1]*.1-5.2])@rot.T
worlddir=direction[:,[2,0,1]]@rot.T
eventlist=O/'eventlists'/f'{name}_37175.dat'
with eventlist.open('w') as f:
    for i,(p,d) in enumerate(zip(worldpos,worlddir)):
        f.write(' '.join([str(i),'0','1','0',f'{i*1e-9:.12e}',*[f'{v:.15g}' for v in p],*[f'{v:.15g}' for v in d],'0','0','0','511'])+'\n')
run='INTERNAL_DIAGNOSTIC_A_37175';prefix=O/'runs'/name/run;card=O/'configs'/f'{name}.source'
card.write_text(f'''# INTERNAL INJECTION DIAGNOSTIC ONLY; front materials are bypassed.
Version 1
Geometry {m['geometry_setup']}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {seed}

Run {run}
{run}.FileName {prefix}
{run}.Triggers {n}
{run}.Source {run}_PhaseSpace
{run}_PhaseSpace.EventList {eventlist}
''')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m.update(seed=seed,source_card=str(card),source_card_sha256=sha(card),eventlist=str(eventlist),eventlist_sha256=sha(eventlist),sim=str(prefix)+'.inc1.id1.sim.gz',log=str(O/'runs'/name/'cosima.log'),launch_plane_local_x_cm=-13.1,production_physics_eligible=False,purpose='Old internal injection plane on the same new optical sample; diagnostic only, independent seed; never pooled with physical A.')
cfg['models'][name]=m;(O/'inputs_manifest.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
p=O/'seed_ledger.json';ledger=json.loads(p.read_text());ledger['jobs'].append({k:m[k] for k in ['seed','source_card','geometry_setup','eventlist','production_physics_eligible']});ledger['status']='PHYSICAL_A_B_VALIDATED_INTERNAL_CONTROL_REGISTERED';p.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
for p in [O/'NUMERIC_SYNC_HANDOFF.json',F/'NUMERIC_SYNC_HANDOFF.json']:
    d=json.loads(p.read_text());d['status']='SIGNAL_COUNTS_READY_A_SOURCE_CLOSURE_IN_PROGRESS';d['internal_control_authorized']=True;d['internal_control_physics_eligible']=False;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('Registered separate internal diagnostic',seed)
