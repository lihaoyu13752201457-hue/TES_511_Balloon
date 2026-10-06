"""Inventory-only assessment of the identified W176 EC branch mismatch.

No detector response is invented or transferred between nuclides or positions.
"""
from decay_kernel import *
data=NuclearData();original=NuclearData();reverse=collections.defaultdict(set)
for n,children in data.adj.items():
    for d in children:reverse[d].add(n)
ancestors={'W176'};todo=['W176']
while todo:
    for n in reverse[todo.pop()]:
        if n not in ancestors:ancestors.add(n);todo.append(n)
data.adj['W176']=collections.Counter({'Ta176':1.})
# The counterfactual changes only the physical W176 branch. Native proposal
# weights and existing response files remain untouched.
P=O.parents[2].parent
scales=list(csv.DictReader((P/'engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv').open()))
times=np.array([float(r['day_mid'])*86400 for r in scales]);jobs=json.loads((D/'runtime_jobs.json').read_text());out=[]
for model,family in sorted({(j['model'],j['family']) for j in jobs}):
    pts=json.loads((D/f'points_{model}_{family}.json').read_text())['points'];blocks=collections.Counter()
    for p in pts:blocks[p['za']]+=p['source_blocks']
    activity=next(j['independent_source_activity_Bq'] for j in jobs if(j['model'],j['family'])==(model,family))
    for za,n in blocks.items():
        root=data.name(za)
        if root not in ancestors:continue
        k=LineageKernel(data,root);sat=-math.expm1(-15*86400/data.tau(root,True))
        scale=np.array([float(r[f'scale_{family}_to_parma_reference']) for r in scales])
        curve=k.mission(times,scale,1e-6)
        ko=LineageKernel(original,root)
        old_ta=float(ko.mission(times,scale,1e-6)[60,ko.idx['Ta176']]) if 'Ta176' in ko.idx else 0.
        pref=activity*n/10000/sat
        out.append({'model':model,'family':family,'root':root,'source_blocks':n,
           'W176_day15_decay_rate_cps':float(curve[60,k.idx['W176']]*pref),
           'Ta176_day15_decay_rate_from_this_chain_cps':float(curve[60,k.idx['Ta176']]*pref),
           'Ta176_day15_added_rate_cps':float((curve[60,k.idx['Ta176']]-old_ta)*pref)})
summary={m:{'W176_day15_cps':sum(r['W176_day15_decay_rate_cps'] for r in out if r['model']==m),
            'Ta176_day15_cps':sum(r['Ta176_day15_added_rate_cps'] for r in out if r['model']==m)} for m in ['a','b']}
(D/'W176_branch_inventory_assessment.json').write_text(json.dumps({'status':'INVENTORY_ONLY_NO_SELECTED_BACKGROUND_PREDICTION','assumption':'W176 -> Ta176 EC=100% from NUBASE2020; other branches retain the installed model','summary':summary,'rows':out},indent=2)+'\n')
print(json.dumps(summary,indent=2))
