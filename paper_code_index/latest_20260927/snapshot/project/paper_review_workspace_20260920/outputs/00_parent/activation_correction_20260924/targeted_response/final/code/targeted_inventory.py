"""Corrected physical inventory and a disjoint existing/new response partition."""
from decay_kernel import *
from targeted_environment import T
import copy

def corrected_data():
    old=NuclearData();new=NuclearData('geant4_targeted_states_tmp');d=copy.deepcopy(old)
    # The Er158 branch previously terminated; its Ho158 levels were never
    # reached through it. Retain all unrelated old channels exactly.
    replace={n for n,s in new.states.items() if s['za']==67158 or n=='Er158'}
    for n in replace:
        d.states[n]=new.states[n];d.adj[n]=new.adj[n].copy();d.valid[n]=new.valid[n]
    # Known W176 EC feeds short-lived levels ending in Ta176 ground. This is
    # an inventory connection, NOT a fabricated transport decay scheme.
    d.adj['W176']=collections.Counter({'Ta176':1.});d.valid['W176']=1.
    d.bykey={(s['za'],round(s['exc'],3)):n for n,s in d.states.items() if s['exc']==0 or round(s['exc'],3)!=0}
    return d

def main():
    d=corrected_data();jobs=json.loads((D/'runtime_jobs.json').read_text())
    observed={(r['model'],r['family'],r['root'],r['state']):r['count'] for r in json.loads((D/'observed_state_counts.json').read_text())}
    oldreg=json.loads((D/'lineage_weight_registry.json').read_text());oldidx={(r['model'],r['family'],r['source_parent_ZA'],r['actual_state']):r for r in oldreg}
    P=O.parents[2].parent
    scales=list(csv.DictReader((P/'engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv').open()))
    times=np.array([float(r['day_mid'])*86400 for r in scales]);cache={};rows=[];rates=[];wlimitations=[]
    for model,family in sorted({(j['model'],j['family']) for j in jobs}):
        pts=json.loads((D/f'points_{model}_{family}.json').read_text())['points'];blocks=collections.Counter()
        for p in pts:blocks[p['za']]+=p['source_blocks']
        a=next(j['independent_source_activity_Bq'] for j in jobs if (j['model'],j['family'])==(model,family))
        ss=np.array([float(r[f'scale_{family}_to_parma_reference']) for r in scales])
        for za,nb in sorted(blocks.items()):
            root=d.name(za);key=(family,root)
            if key not in cache:
                k=LineageKernel(d,root);cache[key]=(k,k.mission(times,ss,1e-6))
            k,curve=cache[key];sat=-math.expm1(-15*86400/d.tau(root,True));pref=a*nb/10000/sat
            for state,rate in zip(k.names,curve.T*pref):
                rate=np.maximum(rate,0.)
                if max(rate)<1e-20:continue
                key=(model,family,za,state);nobs=observed.get(key,0)
                if state=='W176':
                    wlimitations.append(dict(model=model,family=family,root=root,day15_source_rate_cps=float(rate[60]),reason='Unnormalized EC feeding scheme; direct W176 radiation not fabricated. Downstream Ta176 restored via evaluated prompt low levels.'));continue
                # Replace Ho158 response because its accompanying level scheme
                # is updated, and Ho156 because its old selected estimate was
                # dominated by one record. Everything else with support stays.
                replaced=(d.states[state]['za']==67158 or state=='Ho156')
                policy='targeted' if nobs==0 or replaced else 'existing'
                r=dict(category_id=len(rows),model=model,family=family,root_za=za,root=root,state=state,za=d.states[state]['za'],exc_keV=d.states[state]['exc'],observed_old_groups=nobs,policy=policy,reason=('rare_Ho156' if state=='Ho156' else 'Er158_Ho158_update' if d.states[state]['za'] in (67158,68158) else 'missing_support' if nobs==0 else 'retained_response'),old_lineage_id=oldidx[key]['category_id'] if key in oldidx else None,day15_source_cps=float(rate[60]))
                rows.append(r);rates.append(rate)
        print(model,family,len(rows),flush=True)
    np.save(T/'physical_rates_81nodes.npy',np.array(rates).T)
    (T/'physical_registry.json').write_text(json.dumps(rows,indent=2)+'\n')
    (T/'W176_limitations.json').write_text(json.dumps(wlimitations,indent=2)+'\n')
    print('inventory complete',len(rows),flush=True)
if __name__=='__main__':main()
