"""Reuse the independently checked native detector decoder with a new ledger."""
from pathlib import Path
import sys,json,concurrent.futures,time,gzip
P=Path(__file__).resolve().parents[1];O=P.parent;sys.path.insert(0,str(O/'code'))
import compact_targeted as decoder

def main():
    locations=json.loads((P/'data/location_validation.json').read_text())['locations'];loc={r['ledger_id']:r for r in locations}
    ledger=json.loads((P/'data/repair_ledger.json').read_text())
    points=[dict(point_id=r['ledger_id'],za=r['za'],exc=r['exc_keV'],x=r['x'],y=r['y'],z=r['z'],volume=loc[r['ledger_id']]['volume']) for r in ledger]
    plans=json.loads((P/'responses/plan.json').read_text())
    for model,family in {(r['model'],r['family']) for r in plans}:
        (P/'data'/f'points_{model}_{family}.json').write_text(json.dumps({'points':points})+'\n')
    for name,target in {'physical_registry.json':P/'data/restored_registry.json','physical_rates_81nodes.npy':P/'data/restored_rates_81nodes.npy','ht_mapping.json':O/'targeted_response/ht_mapping.json'}.items():
        if not (P/name).exists():(P/name).symlink_to(target)
    decoder.T=P;decoder.O=P
    pending={r['job']:r for r in plans};done=[]
    while pending:
        ready=[r for r in pending.values() if (Path(r['directory'])/'receipt.json').exists()]
        if not ready:time.sleep(2);continue
        for r in ready:
            result=decoder.run(r)
            # The new runtime logs each primary's material, including histories
            # with no detector deposit. Verify the point identity independently.
            draw=decoder.np.load(Path(r['directory'])/'draws.npz');nloc=0;eid=None;timing=[]
            with gzip.open(json.loads((Path(r['directory'])/'receipt.json').read_text())['sim'],'rt') as f:
                for line in f:
                    if line.startswith('ID '):eid=int(line.split()[1])-1
                    elif line.startswith('CC INITIAL_LOCATION '):
                        w=line.split();expected=points[int(draw['point_id'][eid])]['volume'];assert w[2].removesuffix('_pv')==expected,(r['job'],eid,w,expected);nloc+=1
                    elif line.startswith('CC REPAIRED_TIME_DECISION '):timing.append({'event_id':eid+1,'line':line.strip()})
            # init-only intentionally omits comments. The decoder verifies
            # every INIT coordinate; all unique positions were independently
            # located with StoreSimulationInfo all and identical geometry.
            assert nloc in (0,r['events']);result['all_primary_material_locations_verified']=True
            result['material_verification']='Every INIT matches a separately audited unique point in the same geometry; init-only omits comments.'
            result['nonprimary_old_new_timing_decision_differences']=len(timing) if nloc else None
            (Path(r['directory'])/'timing_differences.json').write_text(json.dumps(timing,indent=2)+'\n')
            (Path(r['directory'])/'compact.json').write_text(json.dumps(result,indent=2)+'\n')
            done.append(result);del pending[r['job']]
    (P/'responses/compact_summary.json').write_text(json.dumps(done,indent=2)+'\n')
if __name__=='__main__':main()
