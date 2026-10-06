"""Restore only uniquely identified stopped parents; preserve per-family exposure."""
from pathlib import Path
import sys,json,re,gzip,subprocess,collections,csv,math
import numpy as np
P=Path(__file__).resolve().parents[1]; O=P.parent
sys.path.insert(0,str(O/'code'))
from targeted_environment import environment,sha
from targeted_inventory import corrected_data,LineageKernel

def env():
    e=environment();e['LD_LIBRARY_PATH']=str(P/'runtime/lib')+':'+e['LD_LIBRARY_PATH'];return e

def main():
    audit=json.loads((P/'data/repair_ledger_summary.json').read_text())
    assert audit['files_processed']==audit['production_files']==246
    assert not audit['unresolved_groups'] and not audit['uncertain_descendant_joins']
    ledger=json.loads((P/'data/repair_ledger.json').read_text());jobs=json.loads((O/'data/runtime_jobs.json').read_text())
    locations=[];plans=[]
    for k,model in enumerate(['a','b']):
        records=[r for r in ledger if r['model']==model];d=P/'location_check'/model;d.mkdir(parents=True,exist_ok=True)
        geom=re.search(r'(?m)^Geometry\s+(.*)$',Path(next(j for j in jobs if j['model']==model)['source_path']).read_text()).group(1)
        seed=1690270101+k;elist=d/'events.dat';source=d/'run.source'
        elist.write_text('\n'.join(f'{i} 0 {r["za"]} {r["exc_keV"]:.12g} {i+1} {r["x"]:.12g} {r["y"]:.12g} {r["z"]:.12g} 0 0 1 0 0 0 0.000001' for i,r in enumerate(records))+'\n')
        source.write_text(f'''Version 1
Geometry {geom}
Seed {seed}
PhysicsListHD qgsp-bic-hp
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationBuildUp
DetectorTimeConstant 1e-9
StoreSimulationInfo all
StoreIsotopes true
Run check
check.FileName {d}/check
check.Triggers {len(records)}
check.Source explicit
explicit.EventList {elist}
''')
        receipt=d/'receipt.json'
        if not receipt.exists():
            assert not (d/'started.json').exists(),'Do not silently repeat an unfinished seed'
            (d/'started.json').write_text(json.dumps({'seed':seed,'events':len(records)}))
            with (d/'run.log').open('w') as log:
                run=subprocess.run([str(P/'runtime/cosima'),'-s',str(seed),'-z',str(source)],cwd=d,env=env(),stdout=log,stderr=subprocess.STDOUT)
            assert run.returncode==0
            sims=list(d.glob('check*.sim.gz'));assert len(sims)==1
            receipt.write_text(json.dumps({'sim':str(sims[0]),'seed':seed,'source_sha256':sha(source),'events':len(records)},indent=2))
        rcp=json.loads(receipt.read_text());eid=None;loc={};rp=collections.Counter();ts=None
        with gzip.open(rcp['sim'],'rt') as f:
            for line in f:
                if line.startswith('ID '):eid=int(line.split()[1])-1
                elif line.startswith('CC INITIAL_LOCATION '):
                    w=line.split();loc[eid]=dict(volume=w[2].removesuffix('_pv'),**dict(x.split('=',1) for x in w[3:]))
                elif line.startswith('CC IP RP '):
                    w=line.split();r=records[eid];assert int(w[7])==r['za'] and abs(float(w[8])-r['exc_keV'])<.11
                    assert np.linalg.norm(np.array(list(map(float,w[4:7])))-[r['x'],r['y'],r['z']])<1e-4
                    rp[eid]+=1
                elif line.startswith('TS '):ts=int(line.split()[1])
        assert len(loc)==len(records)==ts and all(rp[i]==1 for i in range(len(records)))
        for i,r in enumerate(records):
            assert loc[i]['ion']==r['parent'],(r,loc[i])
            assert loc[i]['material'].lower() not in ('vacuum','air'),(r,loc[i])
            locations.append(dict(ledger_id=r['ledger_id'],model=model,**loc[i]))
        plans.append(dict(model=model,geometry=geom,events=len(records),seed=rcp['seed'],requested_source_seed=seed,receipt=str(receipt)))
        print('location PASS',model,len(records),flush=True)
    (P/'data/location_validation.json').write_text(json.dumps({'status':'PASS','plans':plans,'locations':locations},indent=2)+'\n')
    d=corrected_data();scalep=O.parents[2].parent/'engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv'
    scales=list(csv.DictReader(scalep.open()));times=np.array([float(r['day_mid'])*86400 for r in scales]);curves={};reg=[];rates=[];lim=[]
    loc={r['ledger_id']:r for r in locations}
    for r in ledger:
        key=(r['family'],r['parent'])
        if key not in curves:
            k=LineageKernel(d,r['parent']);s=np.array([float(row[f'scale_{r["family"]}_to_parma_reference']) for row in scales]);curves[key]=(k,k.mission(times,s,1e-6))
            if k.unresolved:lim.append({'family':r['family'],'root':r['parent'],'channels':k.unresolved})
        k,curve=curves[key]
        for state,rate in zip(k.names,curve.T*r['production_rate_cps']):
            rate=np.maximum(rate,0.)
            if rate.max()<1e-20:continue
            reg.append(dict(category_id=len(reg),ledger_id=r['ledger_id'],model=r['model'],family=r['family'],root=r['parent'],root_za=r['za'],state=state,za=d.states[state]['za'],exc_keV=d.states[state]['exc'],x=r['x'],y=r['y'],z=r['z'],volume=loc[r['ledger_id']]['volume'],material=loc[r['ledger_id']]['material'],day15_source_cps=float(rate[60]),root_production_cps=r['production_rate_cps']))
            rates.append(rate)
    np.save(P/'data/restored_rates_81nodes.npy',np.array(rates).T)
    (P/'data/restored_registry.json').write_text(json.dumps(reg,indent=2)+'\n')
    terminal=[];unresolved=[]
    channels=list(csv.DictReader((O/'data/geant4_native_ground_channels.tsv').open(),delimiter='\t'))
    for item in lim:
        rest=[]
        for state,value in item['channels']:
            cc=[c for c in channels if c['parent']==state]
            if cc and d.valid[state]>=.99999 and all(int(c['daughter_za'])<=2004 for c in cc):terminal.append(dict(family=item['family'],root=item['root'],state=state,channels=cc))
            else:rest.append((state,value))
        if rest:unresolved.append(dict(item,channels=rest))
    (P/'data/kernel_limitations.json').write_text(json.dumps({'unresolved_residual_inventory_channels':unresolved,'terminal_light_fragment_channels':terminal,'explanation':'Two-alpha terminal channels have no further radioactive residual inventory. Emitted light fragments belong to transport, not a new independently normalized radioactive daughter source.'},indent=2)+'\n')
    print('prepared',len(reg),'state/point categories',flush=True)
if __name__=='__main__':main()
