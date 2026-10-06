"""Conservative screening of zero-sample, pure-EC-to-stable components.

This is not a selection-efficiency calculation. It only identifies low visible
energy decays whose missing samples should not be counted as missing 511 keV
events merely from source activity.
"""
from decay_kernel import *
data=NuclearData();rows=list(csv.DictReader((D/'state_support_rows.csv').open()))
binding={int(r['Z']):float(r['K_binding_keV']) for r in csv.DictReader((D/'atomic_binding_energies.csv').open())}
channels=collections.defaultdict(list)
for r in csv.DictReader((D/'geant4_native_ground_channels.tsv').open(),delimiter='\t'):
    if int(r['daughter_za'])>2004:channels[r['parent']].append(r)
out=[];summary={m:{'zero_sample_source_rate':0.,'low_visible_energy_source_rate':0.,'remaining_source_rate':0.} for m in ['a','b']}
for r in rows:
    if r['is_daughter']!='True' or int(r['observed_one_us_groups']):continue
    rate=float(r['day15_model_decay_rate_cps']);m=r['model'];n=r['actual_state'];chs=channels[n]
    summary[m]['zero_sample_source_rate']+=rate
    low=False;cap=None;reason='Needs decay-energy or response assessment'
    if chs and all(x['mode']=='electron capture' for x in chs):
        stable=all(data.nubase.get(int(x['daughter_za']),(0,))[0]==math.inf for x in chs)
        if stable:
            # Daughter excitation bounds its entire electromagnetic cascade;
            # K binding bounds the initial EC atomic cascade. A 10-keV recoil
            # allowance is deliberately generous for these heavy EC nuclides.
            cap=max(float(x['daughter_exc_keV'])+binding[int(x['daughter_za'])//1000]+10 for x in chs)
            low=cap<480
            reason='Pure EC to stable isotope; daughter excitation + K-shell binding + 10 keV recoil allowance'
    if low:summary[m]['low_visible_energy_source_rate']+=rate
    else:summary[m]['remaining_source_rate']+=rate
    out.append({**r,'visible_energy_ceiling_keV':cap,'low_energy_screen':low,'screen_reason':reason})
(D/'zero_sample_energy_screen.json').write_text(json.dumps({'summary':summary,'rows':out,
 'limitation':'Only a conservative pure-EC subset is screened. Source activity is not selected background. Energy smearing and accidental overlaps are not response efficiencies; no rate is removed from the original simulation by this screening.'},indent=2)+'\n')
print(json.dumps(summary,indent=2))
