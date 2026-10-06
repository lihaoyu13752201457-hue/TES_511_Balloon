"""Inventory of confirmed EC nuclides terminated by the installed old library.

Terminal bookkeeping sinks expose the activity of Er158 and W176 without
inventing their daughter-level populations or a detector response. Other
branches retain the installed data. This does not alter response weights.
"""
from decay_kernel import *

data = NuclearData()
targets = ['Er158', 'W176']
for name in targets:
    sink = name + '_bookkeeping_sink'
    data.states[sink] = {**data.states[name], 'stable': 1, 'channels': 0, 'tau': -1}
    data.adj[name] = collections.Counter({sink: 1.})
reverse = collections.defaultdict(set)
for parent, children in data.adj.items():
    for child in children:
        reverse[child].add(parent)
ancestors = set(targets)
todo = list(targets)
while todo:
    for parent in reverse[todo.pop()]:
        if parent not in ancestors:
            ancestors.add(parent)
            todo.append(parent)

P = O.parents[2].parent
scales = list(csv.DictReader((P / 'engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv').open()))
times = np.array([float(r['day_mid'])*86400 for r in scales])
jobs = json.loads((D / 'runtime_jobs.json').read_text())
output = []
for model, family in sorted({(j['model'], j['family']) for j in jobs}):
    points = json.loads((D / f'points_{model}_{family}.json').read_text())['points']
    blocks = collections.Counter()
    for point in points:
        blocks[point['za']] += point['source_blocks']
    activity = next(j['independent_source_activity_Bq'] for j in jobs if (j['model'], j['family']) == (model, family))
    for za, multiplicity in blocks.items():
        root = data.name(za)
        if root not in ancestors:
            continue
        kernel = LineageKernel(data, root)
        scale = np.array([float(r[f'scale_{family}_to_parma_reference']) for r in scales])
        curve = kernel.mission(times, scale, 1e-6)
        prefactor = activity * multiplicity / 10000 / -math.expm1(-15*86400/data.tau(root, True))
        for name in targets:
            if name in kernel.idx:
                output.append({'model': model, 'family': family, 'root': root, 'target': name,
                               'source_blocks': multiplicity,
                               'day15_decay_rate_cps': float(curve[60, kernel.idx[name]]*prefactor)})

summary = {m: {name: sum(r['day15_decay_rate_cps'] for r in output if r['model'] == m and r['target'] == name)
               for name in targets} for m in ['a', 'b']}
result = {'status': 'SOURCE_INVENTORY_ONLY__NO_EMISSION_OR_DETECTOR_RESPONSE',
          'method': 'Expose confirmed terminating EC states as decaying states ending in artificial nonradiating bookkeeping sinks. No physical daughter-level mixture is asserted.',
          'targets': targets, 'summary': summary, 'rows': output,
          'limitations': ['Rates are source activities, not missing selected background.',
                          'Other branches retain the old installed model.',
                          'Downstream missing daughter activity is not included in these target rates.']}
(D / 'blocked_EC_activity_assessment.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(summary, indent=2))
