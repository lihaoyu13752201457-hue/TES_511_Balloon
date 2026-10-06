"""Locate unsupported daughter source activity in the retained geometry.

This distributes each lineage's source activity over its own sampled source
positions in proportion to source-block multiplicity. It does not transfer a
detector response between locations, materials, or nuclides.
"""
from pathlib import Path
import collections
import csv
import json
import math
import re

O = Path(__file__).resolve().parents[1]
D = O / 'data'
W = O.parents[2]
GEOMETRY = {
    'a': W / 'outputs/00_parent/AA_run_20260921_v1/geometry',
    'b': W / 'outputs/02_sources_response_compton/corrected_optics_signal_20260920/geometry/b',
}


def geometry_materials(directory):
    materials = {}
    copies = {}
    files = sorted(directory.glob('*.geo'))
    for path in files:
        text = path.read_text()
        materials.update(re.findall(r'(?m)^\s*([^\s.]+)\.Material\s+(\S+)\s*$', text))
        copies.update({target: source for source, target in re.findall(
            r'(?m)^\s*([^\s.]+)\.Copy\s+(\S+)\s*$', text)})

    def material(volume, visited=()):
        if volume in materials:
            return materials[volume]
        assert volume not in visited, ('copy cycle', volume)
        assert volume in copies, ('unknown material', volume)
        return material(copies[volume], visited + (volume,))
    return material, list(map(str, files))


screen = json.loads((D / 'zero_sample_energy_screen.json').read_text())
mixtures = {}
geometry_inputs = {}
for model, directory in GEOMETRY.items():
    material, geometry_inputs[model] = geometry_materials(directory)
    for path in sorted(D.glob(f'points_{model}_*.json')):
        family = path.stem.removeprefix(f'points_{model}_')
        by_root = collections.defaultdict(collections.Counter)
        for point in json.loads(path.read_text())['points']:
            by_root[point['za']][point['volume'], material(point['volume'])] += point['source_blocks']
        for root, mixture in by_root.items():
            total = sum(mixture.values())
            mixtures[model, family, root] = [(v, m, n/total) for (v, m), n in mixture.items()]

aggregate = collections.Counter()
for row in screen['rows']:
    model, family, root = row['model'], row['family'], int(row['source_parent_ZA'])
    source_rate = float(row['day15_model_decay_rate_cps'])
    category = 'low_visible_energy_EC' if row['low_energy_screen'] else 'not_energy_excluded'
    for volume, material, fraction in mixtures[model, family, root]:
        aggregate[model, category, row['actual_state'], volume, material] += source_rate * fraction

output = [{'model': k[0], 'screen': k[1], 'actual_state': k[2], 'source_volume': k[3],
           'source_material': k[4], 'day15_source_decay_rate_cps': v}
          for k, v in sorted(aggregate.items())]
with (D / 'missing_daughter_source_materials.csv').open('w') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(output[0]))
    writer.writeheader()
    writer.writerows(output)

summary = {}
for model in ['a', 'b']:
    by_material = collections.defaultdict(collections.Counter)
    selected = [r for r in output if r['model'] == model]
    for row in selected:
        by_material[row['source_material']][row['screen']] += row['day15_source_decay_rate_cps']
    total = sum(r['day15_source_decay_rate_cps'] for r in selected)
    assert math.isclose(total, screen['summary'][model]['zero_sample_source_rate'], rel_tol=1e-12)
    unscreened = [r for r in selected if r['screen'] == 'not_energy_excluded']
    summary[model] = {
        'total_zero_sample_source_rate_cps': total,
        'by_material': dict(sorted(by_material.items(), key=lambda item: -sum(item[1].values()))),
        'largest_unscreened_state_volume_components': sorted(
            unscreened, key=lambda r: -r['day15_source_decay_rate_cps'])[:25],
    }

report = {
    'status': 'SOURCE_POSITION_PRIORITIZATION_ONLY__NO_SELECTION_EFFICIENCY',
    'method': 'Within each model, particle family, and initial ancestor, distribute the '
              'state source rate over the retained source-point multiplicities. Materials '
              'come from the corresponding geometry, with Copy inheritance resolved.',
    'geometry_inputs': geometry_inputs,
    'models': summary,
    'limitations': [
        'These are source decay rates, not 511-keV selected background rates.',
        'BGO-origin activity cannot be assumed completely vetoed without its response.',
        'No response is borrowed from another source position, material, or nuclide.',
        'The separate W176 nuclear-data branch issue is not included in these rates.',
    ],
}
(D / 'missing_daughter_source_materials.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({m: {'by_material': s['by_material']} for m, s in summary.items()}, indent=2))
