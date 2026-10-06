"""Independent invariants for the existing-sample response correction."""
from common import *

result = {}
jobs = read(O / 'data/runtime_jobs.json')
for model in ['a', 'b']:
    old, old_reg, _ = base_background(model)
    directory = O / 'data' / model / 'response'
    new = {k: np.load(directory/(k+'.npy'), mmap_mode='r') for k in
           ['measured_total_keV', 'bgo_keV', 'event_base_weight_cps', 'event_category']}
    old_stream = np.array([r['stream'] == 'delayed' for r in old_reg])[old['event_category']]
    prompt = ~old_stream
    for key in new:
        assert np.array_equal(np.asarray(old[key])[prompt], new[key][prompt]), (model, key, 'prompt changed')
    max_energy_difference = max_bgo_difference = 0.
    checked = 0
    for job in [j for j in jobs if j['model'] == model]:
        jid = job['job_id']
        identity = np.load(O/'data/decay_metadata'/(jid+'.response.npz'))
        mapping = np.load(O/'data/decay_metadata'/(jid+'.map.npz'))
        indices = identity['global_index']
        groups = mapping['group_first_index'][identity['event_id'].astype('i8')-1]
        starts, first, inverse, count = np.unique(groups, return_index=True, return_inverse=True, return_counts=True)
        representatives = indices[first]
        bgo = np.bincount(inverse, weights=old['bgo_keV'][indices], minlength=len(starts))
        error = np.max(np.abs(bgo - new['bgo_keV'][representatives]))
        max_bgo_difference = max(max_bgo_difference, float(error))
        assert np.allclose(bgo, new['bgo_keV'][representatives], rtol=2e-7, atol=1e-5)
        hit = old['hit_count'][indices] > 0
        positive = np.bincount(inverse, weights=hit, minlength=len(starts))
        energy = np.bincount(inverse, weights=old['measured_total_keV'][indices]*hit, minlength=len(starts))
        test = (count > 1) & (positive == 1)
        delta = np.abs(energy[test] - new['measured_total_keV'][representatives[test]])
        if len(delta):
            max_energy_difference = max(max_energy_difference, float(delta.max()))
            assert np.allclose(energy[test], new['measured_total_keV'][representatives[test]], rtol=2e-7, atol=2e-4), (model, jid, delta.max())
        checked += int(test.sum())
        assert np.all(new['event_base_weight_cps'][representatives] == 1)
        assert np.sum(new['event_base_weight_cps'][indices]) == len(starts)
    result[model] = {'prompt_arrays_unchanged': True, 'single_TES_multiple_record_groups_checked': checked,
                     'maximum_single_TES_energy_difference_keV': max_energy_difference,
                     'maximum_BGO_sum_float_rounding_difference_keV': max_bgo_difference,
                     'each_group_has_one_nonzero_weight_representative': True}
save(O/'validation/response_invariants.json', result)
print(json.dumps(result, indent=2))
