"""Compare the pinned paper to corrected existing samples, without editing TeX."""
from common import *
from collections import defaultdict
import re

LABELS = {'a': 'Under-stage', 'b': 'Lateral-chimney'}
OLD_VALUES = read(ORIGINAL / 'data/paper_values_500.json')


def material_resolver(model):
    materials, copies = {}, {}
    for path in geometry(model).parent.glob('*.geo'):
        content = path.read_text()
        materials.update(re.findall(r'(?m)^\s*([^\s.]+)\.Material\s+(\S+)\s*$', content))
        copies.update({target: source for source, target in re.findall(
            r'(?m)^\s*([^\s.]+)\.Copy\s+(\S+)\s*$', content)})
    def resolve(volume):
        visited = set()
        while volume not in materials:
            assert volume not in visited and volume in copies, volume
            visited.add(volume)
            volume = copies[volume]
        return materials[volume]
    return resolve


def component_classifier(model):
    path = P / 'tmp/m05_issue9_fixed27_20260831/build_activation_origin_donuts_model_b.py'
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if
             isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id.endswith('_VOLUMES') for t in n.targets)
             or isinstance(n, ast.FunctionDef) and n.name == 'classify_component']
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    def classify(volume, material):
        if model == 'b':
            if volume.startswith('TES_Pixel_'): return 'tes_pixel_ta'
            if volume.startswith('SH3_OptV2_W_Frame_'): return 'w_focal_plane_frame'
            return namespace['classify_component'](volume)
        if volume == 'ColdPlate_MXC_100mK_SD_anchor': return 'mxc_50mk_cu_plate'
        if volume.startswith('Cu_SubstrateSupport_'): return 'tes_substrate_cu_panels'
        if volume == 'SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm': return 'tes_cu_heat_sink'
        if material == 'Bi': return 'nearfield_bi_liner'
        if material == 'Aluminium': return 'al_cryostat_shields'
        if material == 'W': return 'other_detector_bay'
        if material == 'BGO': return 'bpe_bgo_shielding'
        return 'other_dr_cold_hardware'
    return classify


def aggregate(origins, field):
    grouped = defaultdict(list)
    for row in origins:
        grouped[str(row[field])].append(float(row['day15_weight_cps']))
    total = math.fsum(w for weights in grouped.values() for w in weights)
    return {k: {'n': len(v), 'rate': math.fsum(v), 'sigma': math.sqrt(math.fsum(x*x for x in v)),
                'share': math.fsum(v)/total} for k, v in grouped.items()}


def main():
    comparison, decomp, paper_values = [], {}, {}
    def item(model, quantity, before, after, status='CORRECTED_EXISTING_SAMPLE_ONLY'):
        if os.environ.get('ACTIVATION_TARGETED_FINAL')=='1':status='TARGETED_RESPONSE_CORRECTED__STATED_NUCLEAR_AND_FINITE_STATISTICAL_LIMITATIONS'
        comparison.append({'model': model, 'quantity': quantity, 'before': before, 'after': after,
                           'relative_change': after/before-1 if before else None, 'status': status})

    for model in ['a', 'b']:
        old = OLD_VALUES[model]
        new = read(O / 'data' / model / 'direct_statistics.json')
        paper_values[model] = new
        for stage in ['pre_veto', 'combined_active_veto', 'compton_trajectory_veto']:
            for component in ['total', 'delayed', 'gamma', 'non_gamma']:
                for quantity in ['n', 'rate', 'sigma', 'neff']:
                    item(model, f'{stage}/{component}/{quantity}', old[stage][component][quantity], new[stage][component][quantity])
        resolve, classify = material_resolver(model), component_classifier(model)
        origins = rows(O / 'data' / model / 'selected_delayed_origins.csv')
        for row in origins:
            volume = row['source_volume']
            row['source_material'] = resolve(volume)
            row['component_key'] = classify(volume, row['source_material'])
            row['region'] = 'DR/MXC and cold plates' if volume.startswith('ColdPlate_') or volume == 'DR_MixingChamber_Cu' else (
                'TES-near structures' if any(k in volume for k in ['TES_', 'SubstrateSupport', 'SH3_Layer', 'SH3_OptV2_W_Frame', 'BottomColdPlate', 'ColdFinger', '50mK', 'Bi_MXC_TES']) else 'Other structures')
        fields = {'components': 'component_key', 'materials': 'source_material', 'families': 'family',
                  'regions': 'region', 'volumes': 'source_volume', 'nuclides': 'source_parent_ZA',
                  'actual_decaying_nuclides': 'actual_ZA', 'actual_decaying_states': 'actual_state'}
        decomp[model] = {name: aggregate(origins, field) for name, field in fields.items()}
        total = new['compton_trajectory_veto']['delayed']['rate']
        for name, values in decomp[model].items():
            assert math.isclose(sum(v['rate'] for v in values.values()), total, rel_tol=1e-12)
            if name in old['origin_statistics']:
                before = old['origin_statistics'][name]
                for key in sorted(set(before) | set(values)):
                    for quantity in ['rate', 'share']:
                        item(model, f'origin_{name}/{key}/{quantity}', before.get(key, {}).get(quantity, 0), values.get(key, {}).get(quantity, 0))
        paper_values[model]['origin_statistics'] = decomp[model]
        write(O/'data'/model/'selected_delayed_origins_enriched.csv', origins)

    old_mission = read(ORIGINAL / 'data/RESULTS.json')
    new_mission = read(O / 'data/RESULTS.json')
    if all(m in new_mission['models'] for m in ['a', 'b']):
        for model in ['a', 'b']:
            old, new = old_mission['models'][model], new_mission['models'][model]
            for quantity in ['Ns', 'Nb', 'Z', 'F3', 'F5', 'F3_MC_SE_approx', 'T3_days', 'T5_days']:
                item(model, f'mission_20day/{quantity}', old['mission_20day'][quantity], new['mission_20day'][quantity])
            for quantity in ['signal_final_rate_cps', 'direct_background_BGO_cps', 'timeline_background_BGO_cps', 'eta_bgo']:
                item(model, f'day15/{quantity}', old['day15'][quantity], new['day15'][quantity])
        for quantity in ['Nb_lateral_over_under', 'Ns_lateral_over_under', 'F3_under_over_lateral']:
            item('ratio', quantity, old_mission['ratios'][quantity], new_mission['ratios'][quantity])

    save(O / 'data/paper_values_corrected_current_sample.json', paper_values)
    save(O / 'data/NUMERIC_COMPARISON_TWO_MODELS.json', comparison)
    write(O / 'data/NUMERIC_COMPARISON_TWO_MODELS.csv', comparison)
    for model in ['a', 'b']:
        print(model, 'final', paper_values[model]['compton_trajectory_veto'])
        print(model, 'Cu share', decomp[model]['materials']['Copper']['share'])
        print(model, 'actual isotope rates', sorted(decomp[model]['actual_decaying_nuclides'].items(), key=lambda kv:-kv[1]['rate'])[:5])


if __name__ == '__main__':
    main()
