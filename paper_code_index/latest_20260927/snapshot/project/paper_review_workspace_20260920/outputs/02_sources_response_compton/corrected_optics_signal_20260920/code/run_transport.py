"""Run one bounded signal job; preserve receipts and reject reused outputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
O=Path(__file__).resolve().parents[1]
model=sys.argv[1]
cfg=json.loads((O/'inputs_manifest.json').read_text());assert model in cfg['models'];m=cfg['models'][model]
assert not Path(m['sim']).exists(),'Never overwrite a prior transport'
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['ROOT_HIST']='0'
mega=Path('/home/ubuntu/MEGAlib_Install/megalib-main');g4=mega/'external/geant4_v10.02.p03';data=g4/'share/Geant4-10.2.3/data'
env['MEGALIB']=str(mega);env['LD_LIBRARY_PATH']=':'.join(map(str,[mega/'lib',mega/'external/root_v6.36.6/lib',g4/'lib']))+':'+env.get('LD_LIBRARY_PATH','')
for key,d in {'G4NEUTRONHPDATA':'G4NDL4.5','G4LEDATA':'G4EMLOW6.48','G4LEVELGAMMADATA':'PhotonEvaporation3.2','G4RADIOACTIVEDATA':'RadioactiveDecay4.3.2','G4NEUTRONXSDATA':'G4NEUTRONXS1.4','G4PIIDATA':'G4PII1.3','G4REALSURFACEDATA':'RealSurface1.0','G4SAIDXSDATA':'G4SAIDDATA1.1','G4ABLADATA':'G4ABLA3.0','G4ENSDFSTATEDATA':'G4ENSDFSTATE1.2.3'}.items():
    env[key]=str(data/d);assert (data/d).is_dir()
cmd=[str(mega/'bin/cosima'),'-s',str(m['seed']),m['source_card']]
receipt={'model':model,'command':cmd,'cwd':str(O/'runs'/model),'seed':m['seed'],'started_epoch':time.time(),'status':'RUNNING'}
p=O/'runs'/model/'receipt.json';p.write_text(json.dumps(receipt,indent=2)+'\n')
with Path(m['log']).open('w') as f:r=subprocess.run(cmd,cwd=O/'runs'/model,env=env,stdout=f,stderr=subprocess.STDOUT)
receipt.update(returncode=r.returncode,elapsed_seconds=time.time()-receipt['started_epoch'],status='TRANSPORT_EXITED' if r.returncode==0 else 'FAILED')
p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2));assert r.returncode==0
