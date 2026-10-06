"""Reweight actual decaying states and join correlated sub-microsecond decays.

Only the new output package is written. The pinned detector response is retained
for unchanged events; merged pixels receive one Gaussian noise realization.
"""
from common import *
from decay_kernel import NuclearData
from collections import Counter, defaultdict
import time

DD = O / 'data' / 'decay_metadata'

def resolve_excitation(events, future, mapping, starts):
    exc = events['exc'][starts].copy()
    primary = mapping['is_primary'][starts]
    exc[primary] = 0
    unknown = np.flatnonzero(~np.isfinite(exc))
    stats = {'unknown_group_starts': len(unknown), 'future_matches': 0}
    if len(unknown):
        point = mapping['point_id']
        predictions = defaultdict(list)
        for row in future:
            parent = int(row['parent']) - 1
            predictions[(int(point[parent]), int(row['za']))].append(
                (float(events['time'][parent] + row['delay']), float(row['exc']), parent))
        indexed = {}
        for key, vals in predictions.items():
            vals.sort()
            indexed[key] = (np.array([v[0] for v in vals]), vals)
        failures = []
        for k in unknown:
            g = int(starts[k]); key = (int(point[g]), int(events['za'][g]))
            if key not in indexed:
                failures.append((g + 1, key, 'no_future')); continue
            tt, vals = indexed[key]; t = float(events['time'][g])
            lo, hi = np.searchsorted(tt, [t - 5.2e-7, t + 5.2e-7])
            candidates = {round(v[1], 6) for v in vals[lo:hi] if v[2] < g}
            if len(candidates) != 1:
                failures.append((g + 1, key, t, sorted(candidates))); continue
            exc[k] = candidates.pop(); stats['future_matches'] += 1
        if failures:
            raise ValueError(('unresolved_group_start_excitation', failures[:20], len(failures)))
    assert np.all(np.isfinite(exc))
    return exc, stats

def run(model):
    out = O / 'data' / model; dest = out / 'response'
    dest.mkdir(parents=True, exist_ok=True)
    ar, reg0, fac0 = base_background(model)
    a = dict(ar)
    changed = ['bgo_keV', 'measured_total_keV', 'hit_start', 'hit_count', 'event_base_weight_cps', 'broad_flags']
    for key in changed:
        a[key] = np.array(ar[key], copy=True)
    a['event_category'] = ar['event_category'].astype('u4')
    changed.append('event_category')
    pinned_final = np.load(ORIGINAL / 'data' / model / 'background_broad_continuous.npy')
    final = pinned_final.copy()
    modelreg = [r for r in read(O / 'data/lineage_weight_registry.json') if r['model'] == model]
    allweights = np.load(O / 'data/lineage_weights_81nodes.npy')
    fac = np.column_stack([fac0, allweights[:, [r['category_id'] for r in modelreg]]])
    reg = [dict(c) for c in reg0]
    for i, c in enumerate(reg):
        if c['stream'] == 'delayed':
            fac[:, i] = 0
    lookup = {}
    for r in modelreg:
        i = len(reg)
        lookup[(r['family'], r['source_parent_ZA'], r['actual_state'])] = i
        reg.append({**r, 'category_id': i, 'stream': 'delayed', 'component': 'other',
                    'weight_policy': 'physical lineage rate divided by finite native exposure',
                    'lineage_registry_id': r['category_id']})
    data = NuclearData(); pixel = recon(model)
    jobs = [j for j in read(O / 'data/runtime_jobs.json') if j['model'] == model]
    bj = {j['job_id']: j for j in read(D / 'identity_b_jobs.json')} if model == 'b' else {}
    if model == 'a':
        plan=read(AA/'bundles/delayed_epoch0/generated/job_plan.json')
        bj={j['job_id']:{**j,'batch_id':plan['profile_id']} for j in plan['jobs']}
    nh = len(ar['hit_code']); extra = {k: [] for k in ar if k.startswith('hit_') and k not in ['hit_start','hit_count']}
    audits = []; merged_details = []; unsupported = []; all_origin_rows = []
    removed = 0; merged_tes = 0
    for job in jobs:
        jid = job['job_id']; meta = dict(np.load(DD / (jid + '.npz')))
        ev = meta['events']; mapping = dict(np.load(DD / (jid + '.map.npz')))
        identity = dict(np.load(DD / (jid + '.response.npz')))
        ids = identity['event_id'].astype('i8') - 1; ix = identity['global_index']
        assert np.all(np.diff(ids) > 0), jid
        groups = mapping['group_first_index'][ids]
        starts, first, inverse, counts = np.unique(groups, return_index=True, return_inverse=True, return_counts=True)
        representatives = ix[first]
        pts = read(O / 'data' / f"points_{model}_{job['family']}.json")['points']
        pids = mapping['point_id'][starts]
        rootza = np.array([p['za'] for p in pts])[pids]
        ex, excitation_stats = resolve_excitation(ev, meta['future'], mapping, starts)
        states = {}
        cat = np.empty(len(starts), dtype='u4')
        for k, (root, za, exc) in enumerate(zip(rootza, ev['za'][starts], ex)):
            key = (int(root), int(za), round(float(exc), 3))
            if key not in states:
                try:
                    name = data.name(za, exc)
                    states[key] = lookup[(job['family'], int(root), name)]
                except (KeyError, ValueError):
                    unsupported.append({'job': jid, 'event_id': int(starts[k])+1,
                                        'root': int(root), 'actual_za': int(za), 'exc': float(exc),
                                        'representative': int(representatives[k])})
                    states[key] = 0
            cat[k] = states[key]
        if unsupported:
            save(dest / 'unsupported_states.json', unsupported)
            raise ValueError(('unsupported actual states', unsupported[:10]))
        a['event_base_weight_cps'][ix] = 0
        a['event_base_weight_cps'][representatives] = 1
        a['event_category'][representatives] = cat
        # All response-positive members are included, including veto-only records.
        a['bgo_keV'][representatives] = np.bincount(inverse, weights=ar['bgo_keV'][ix], minlength=len(starts))
        multiple = np.flatnonzero(counts > 1)
        order = np.argsort(inverse, kind='stable'); offsets = np.r_[0,np.cumsum(counts)]
        seedmeta = bj[jid]
        for k in multiple:
            positions = order[offsets[k]:offsets[k+1]]; members = ix[positions]
            representative = int(representatives[k]); hc = ar['hit_count'][members]
            if not np.any(hc):
                continue
            merged_tes += 1
            deposits = {}; firsthit = {}; noise = {}
            for pos, i in zip(positions, members):
                st = int(ar['hit_start'][i]); end = st + int(ar['hit_count'][i])
                for h in range(st, end):
                    code = int(ar['hit_code'][h]); uid = f'TP_L{code//100000}_{code%100000:05d}'
                    deposits[code] = deposits.get(code, 0.) + float(ar['hit_energy_keV'][h])
                    if code not in noise:
                        eid = int(ids[pos]) + 1
                        if model == 'b':
                            noise[code] = SIGMA * normal('sh3_optv3', 'delayed', job['family'], seedmeta['batch_id'], int(seedmeta['seed']), jid, eid, uid)
                        else:
                            noise[code] = SIGMA * a_normal('sg3b', 'delayed', job['family'], seedmeta['batch_id'], int(seedmeta['seed']), jid, eid, uid)
                        firsthit[code] = h
            hits = []
            for code, e in sorted(deposits.items()):
                h = firsthit[code]
                for key in extra:
                    extra[key].append(e if key == 'hit_energy_keV' else ar[key][h])
                ee = e + noise[code]
                if ee >= .3:
                    hits.append(PixelMeasurement(f'TP_L{code//100000}_{code%100000:05d}', ee))
            total = math.fsum(h.energy_keV for h in hits)
            a['hit_start'][representative] = nh
            a['hit_count'][representative] = len(deposits); nh += len(deposits)
            a['measured_total_keV'][representative] = total
            broad = 480 <= total < 550; active = float(a['bgo_keV'][representative]) < 50
            keep = bool(pixel.classify(hits)[0]) if broad and active else False
            final[representative] = broad and active and keep
            a['broad_flags'][representative] = int(broad) | (4*int(broad and active)) | (16*int(final[representative]))
            oldsel = ((ar['measured_total_keV'][members]>=510.5) & (ar['measured_total_keV'][members]<511.5) & pinned_final[members])
            newsel = final[representative] and 510.5 <= total < 511.5
            if np.any(oldsel) or newsel:
                merged_details.append({'job':jid,'event_ids':(ids[positions]+1).tolist(), 'group_start_event_id':int(starts[k])+1,
                    'catalog_indices':members.tolist(), 'old_selected_ids':(ids[positions][oldsel]+1).tolist(),
                    'new_selected':bool(newsel),'new_energy_keV':total,'new_bgo_keV':float(a['bgo_keV'][representative]),
                    'actual_state':reg[int(cat[k])]['actual_state']})
        # A previously selected singleton can be vetoed by a zero-TES daughter.
        final[representatives] &= a['bgo_keV'][representatives] < 50
        positive = representatives[(a['measured_total_keV'][representatives]>=510.5) & (a['measured_total_keV'][representatives]<511.5) & final[representatives]]
        byrep = {int(i):k for k,i in enumerate(representatives)}
        for i in positive:
            k=byrep[int(i)]; p=pts[int(pids[k])]; c=int(cat[k]); memberpos=order[offsets[k]:offsets[k+1]]
            all_origin_rows.append({'catalog_index':int(i),'job_id':jid,'family':job['family'],
                'event_id':int(starts[k])+1,'response_event_ids':','.join(map(str,ids[memberpos]+1)),
                'source_parent_ZA':int(rootza[k]),'actual_state':reg[c]['actual_state'],
                'actual_ZA':int(ev['za'][starts[k]]),'source_volume':p['volume'],
                'source_x_cm':p['x'],'source_y_cm':p['y'],'source_z_cm':p['z'],
                'category_id':c,'day15_weight_cps':float(fac[60,c]),
                'measured_total_keV':float(a['measured_total_keV'][i])})
        np.savez_compressed(dest/(jid+'.groups.npz'), group_start_event_id=starts+1, representative_index=representatives,
                            category=cat, detector_positive_members=counts, actual_exc_keV=ex)
        audit={'job':jid,'response_records':len(ix),'response_positive_clusters':len(starts),
               'multiple_positive_clusters':len(multiple),**excitation_stats}
        audits.append(audit); removed+=len(ix)-len(starts)
        print(jid, audit, 'selected', len(positive), flush=True)
    count = np.bincount(a['event_category'][a['event_base_weight_cps']>0],minlength=len(reg))
    sw = np.bincount(a['event_category'],weights=a['event_base_weight_cps'],minlength=len(reg))
    sw2 = np.bincount(a['event_category'],weights=a['event_base_weight_cps']**2,minlength=len(reg))
    for i,c in enumerate(reg):
        c['event_count']=int(count[i]);c['sum_event_base_weight_cps']=float(sw[i]);c['sum_event_base_weight2_cps2']=float(sw2[i])
    for key in changed:
        np.save(dest/(key+'.npy'), a[key])
    for key, vals in extra.items():
        np.save(dest/(key+'.npy'), np.r_[ar[key],np.array(vals,dtype=ar[key].dtype)])
    np.save(out/'background_broad_continuous.npy',final)
    np.save(dest/'category_factors.npy',fac)
    save(dest/'category_registry.json',{'categories':reg})
    save(dest/'merge_audit.json',{'jobs':audits,'removed_positive_records':removed,'merged_TES_clusters':merged_tes,
                               'selected_cluster_changes':merged_details})
    write(out/'selected_delayed_origins.csv',all_origin_rows)
    save(dest/'manifest.json',{'model':model,'arrays':changed+list(extra),'source':str(ORIGINAL),
        'response_policy':'Preserve unchanged pinned response; sum correlated deposits by actual pixel and add one original first-hit Gaussian per pixel.',
        'narrow_selected_delayed_records':len(all_origin_rows),'narrow_selected_delayed_day15_rate':sum(r['day15_weight_cps'] for r in all_origin_rows)})
    print('COMPLETE',model,'selected',len(all_origin_rows),'rate',sum(r['day15_weight_cps'] for r in all_origin_rows),flush=True)

if __name__=='__main__':
    run(sys.argv[1])
