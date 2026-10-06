"""Non-overwriting physical production ledger, independent per family."""
from pathlib import Path
import json,csv,collections,math,sys
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parent/'code'))
from decay_kernel import NuclearData
def main():
    plan=json.loads((P/'data/production_plan.json').read_text());ledger=json.loads((P/'data/repair_ledger.json').read_text());removed=json.loads((P/'data/remove_RP.json').read_text());loc={r['ledger_id']:r for r in json.loads((P/'data/location_validation.json').read_text())['locations']}
    old=collections.Counter();TT=collections.Counter();events=collections.Counter()
    for j in plan:
        key=j['model'],j['family'];TT[key]+=j['TT_s'];events[key]+=j['events'];volume=None;total=0
        for line in Path(j['dat_path']).read_text().splitlines():
            w=line.split()
            if not w:continue
            if w[0]=='VN':volume=w[1]
            elif w[0]=='RP':
                n=float(w[3]);assert n==round(n);old[(*key,volume,int(w[1]),round(float(w[2]),2))]+=int(n);total+=int(n)
        assert total==j['sum_RP']
    minus=collections.Counter();plus=collections.Counter()
    for r in removed:minus[r['model'],r['family'],r['volume'],r['za'],round(r['exc'],2)]+=1
    for r in ledger:plus[r['model'],r['family'],loc[r['ledger_id']]['volume'],r['za'],round(r['exc_keV'],2)]+=1
    rows=[]
    for k in sorted(set(old)|set(minus)|set(plus)):
        n=old[k]-minus[k]+plus[k];assert n>=0,(k,old[k],minus[k]);m,f,v,z,e=k
        rows.append(dict(model=m,family=f,volume=v,za=z,exc_keV=e,original_count=old[k],removed_descendants=minus[k],restored_parents=plus[k],corrected_count=n,production_TT_s=TT[m,f],production_rate_cps=n/TT[m,f]))
    with (P/'data/corrected_production_inventory.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    stats=[]
    for m,f in sorted(TT):
        rr=[r for r in rows if (r['model'],r['family'])==(m,f)]
        stats.append(dict(model=m,family=f,primaries=events[m,f],TT_s=TT[m,f],original_RP=sum(r['original_count'] for r in rr),removed_RP=sum(r['removed_descendants'] for r in rr),restored_parents=sum(r['restored_parents'] for r in rr),corrected_RP=sum(r['corrected_count'] for r in rr),added_root_production_cps=sum(r['restored_parents'] for r in rr)/TT[m,f]))
    # A genuinely <=1 ns decay of any millisecond-scale parent is possible;
    # saved old records reset the time. Bound this ambiguity instead of claiming
    # exact recovery of an unsaved random lifetime.
    data=NuclearData();affected={(r['model'],r['family'],r['za'],round(r['exc_keV'],2)):r['native_tau_s'] for r in ledger};ambiguity=collections.Counter();expected=collections.Counter()
    for r in rows:
        key=r['model'],r['family'],r['za'],r['exc_keV']
        if key in affected:
            prob=-math.expm1(-1e-9/affected[key]);ambiguity[r['model']]+=r['production_rate_cps']*prob;expected[r['model']]+=r['corrected_count']*prob
    out={'status':'COUNTS_AND_EXPOSURE_CLOSED','files':len(plan),'primaries':sum(events.values()),'compressed_input_bytes':sum(j['sim_bytes'] for j in plan),'restored_parents':len(ledger),'removed_descendants':len(removed),'families':stats,'possible_genuine_sub_ns_expected_production_cps':dict(ambiguity),'possible_genuine_sub_ns_expected_records':dict(expected),'sub_ns_note':'Expected number using the exponential lifetime law across all produced records of affected states, not conditional on being retained. Original decay times were reset and cannot be recovered exactly.','position_precision_cm':1e-5,'original_data_modified':False,'new_atmospheric_primaries':0}
    (P/'data/production_inventory_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
