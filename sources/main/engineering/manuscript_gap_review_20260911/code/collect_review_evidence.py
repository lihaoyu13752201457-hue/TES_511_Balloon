#!/usr/bin/env python3
"""Read retained summaries and small receipts; never open or hash SIM payloads."""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path('/home/ubuntu/TES_511_Balloon')
OUT = Path(__file__).resolve().parents[1]
P70 = ROOT / 'engineering/geometry_optimization_20260815/70_m05_sg3_sh3_prompt_statistics_integration_20260828/outputs'
EXT = Path('/media/ubuntu/903261CE3261BA3C')

def read(p):
    return json.loads(Path(p).read_text())

def external(p):
    return Path(str(p).replace('/mnt/data/', str(EXT) + '/', 1))

def add_job(z, j, receipt):
    z['jobs'] += 1
    z['primaries'] += j['events']
    z['sim_bytes'] += j['sim_bytes']
    if receipt.exists():
        r = read(receipt)
        assert r['status'] == 'PASS', receipt
        z['pass_receipts_read'] += 1
        z['cpu_seconds'] += r.get('log', {}).get('beam_on_cpu_s', 0)
        z['sum_job_wall_seconds'] += r.get('wall_s', 0)

def finish(z):
    z = dict(z)
    z['sim_GiB'] = z['sim_bytes'] / 2**30
    z['bytes_per_primary'] = z['sim_bytes'] / z['primaries']
    z['cpu_hours_per_million'] = z.get('cpu_seconds', 0) / 3600 / z['primaries'] * 1e6
    return z

gamma = defaultdict(float)
for j in read(ROOT / 'DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820/summary.json')['jobs']:
    if j['family'] == 'gamma' and j['stream'] == 'prompt':
        receipt = external(j['sim_path']).parents[4] / 'receipts' / (j['job_id'] + '.json')
        add_job(gamma, j, receipt)
gamma = finish(gamma)

families = defaultdict(lambda: defaultdict(float))
for j in read(P70 / 'sh3/jobs.json')['jobs']:
    add_job(families[j['family']], j, Path(j['receipt_path']))
families = {f: finish(z) for f, z in families.items()}

neutron_root = ROOT / 'engineering/geometry_optimization_20260815/72_sh3_si_substrate_sd_neutron_canary_20260903'
neutron = defaultdict(float)
for p in (neutron_root / 'production_10m/run/receipts').glob('*.json'):
    r = read(p)
    add_job(neutron, r, p)
neutron = finish(neutron)

folds = {}
for g in ['a', 'b']:
    folder = P70 / f'03_section4_timeline_{g}_authority_v2'
    summary = read(folder / 'summary.json')
    rows = list(csv.DictReader((folder / 'mission_timeline_81nodes.csv').open()))
    assert len(rows) == 81
    kernels = []
    for r in rows:
        transmission = float(r['T_atm_511_slant45']) ** (math.sin(math.pi / 4) / math.sin(math.radians(27)))
        kernels.append(float(r['conditional_signal_Aeff_cm2']) * float(r['conditional_signal_accidental_survival']) * transmission)
    kernel = sum((kernels[i] + kernels[i-1]) / 2 * (float(rows[i]['day_mid']) - float(rows[i-1]['day_mid'])) * 86400 for i in range(1, len(rows)))
    b = float(rows[-1]['cumulative_background_counts'])
    folds[g.upper()] = {
        'method': 'Independent 27-degree refold of retained 45-degree transmission at every node; same attenuation coefficient, backgrounds, eta and area',
        'signal_counts_at_2p4e_minus4': kernel * 2.4e-4,
        'background_counts': b,
        'F3_gaussian': 3 * math.sqrt(b) / kernel,
        'day15_signal_cps_at_2p4e_minus4': kernels[60] * 2.4e-4,
        'effective_transmission_times_accidental_survival': kernel / (float(rows[0]['conditional_signal_Aeff_cm2']) * 20 * 86400),
        'existing_five_anchor_elapsed_seconds': summary['elapsed_s'],
        'disabled_components': summary['analysis_scenario']['disabled_components'],
    }

manifest_paths = [
    Path('/home/ubuntu/paper/balloon511_ea_draft_en_sg3_sh3_revision_20260821.tex'),
    Path('/home/ubuntu/paper_new/balloon511_ea_manuscript_en_20260831.tex'),
    Path('/home/ubuntu/paper_new/balloon511_ea_manuscript_en_20260831.pdf'),
    P70 / '01_integrated_catalog_b/audit.json',
    P70 / '03_section4_timeline_b_authority_v2/summary.json',
    neutron_root / 'production_10m/analysis_10m/si_deposition_summary_10m.json',
    Path('/home/ubuntu/neutron_fen/FINAL_EVALUATION.md'),
    Path('/home/ubuntu/neutron_fen/outputs/tes_two_node_fenics/TES_TWO_NODE_EVALUATION.md'),
    ROOT / 'engineering/ea_peer_review_m08_laue_validation_20260715/README.md',
]
inputs = []
for p in manifest_paths:
    inputs.append({'path': str(p), 'size_bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})

g_extra = gamma['primaries'] * (25 / 11.84 - 1)
ep_extra = 2119548 * (25 / 3 - 1)
storage = os.statvfs(ROOT)
evidence = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Read-only review of existing physics products. Only this new review directory is written. No transport or production replay launched.',
    'units': {'GiB': '2**30 bytes', 'CPU_hour': '3600 core-seconds', 'person_day': '8 hours of researcher/engineering effort'},
    'machine': {'logical_cpus': os.cpu_count(), 'local_available_bytes': storage.f_bavail * storage.f_frsize, 'external_mount': str(EXT), 'external_mount_read_only_at_review': True},
    'measured_SH3_gamma': gamma,
    'measured_SH3_prompt_supplement_by_family': families,
    'measured_SH3_Si_neutron_99_production_jobs': neutron,
    'refold_27deg': folds,
    'illustrative_topups_not_authorized_or_executed': {
        'gamma_to_effective_25': {'extra_primaries': g_extra, 'raw_GiB': g_extra * gamma['bytes_per_primary'] / 2**30, 'CPU_hours': g_extra / 1e6 * gamma['cpu_hours_per_million'], 'assumption': 'unchanged selected yield, importance-weight distribution and output mode; random yield is not guaranteed'},
        'positron_to_25': {'extra_primaries': ep_extra, 'raw_GiB': ep_extra * families['eplus']['bytes_per_primary'] / 2**30, 'CPU_hours': ep_extra / 1e6 * families['eplus']['cpu_hours_per_million'], 'assumption': 'unchanged selected yield and output mode; current paper total 2119548 primaries and 3 survivors'},
    },
    'illustrative_single_pixel_gaussian_window_acceptance': {str(width): math.erf(.420 / (math.sqrt(2) * math.hypot(.420, width) / 2.354820045)) for width in [0, 1.3, 5.4]},
    'input_manifest': inputs,
}
(OUT / 'evidence.json').write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({k: evidence[k] for k in ['machine', 'refold_27deg', 'illustrative_topups_not_authorized_or_executed']}, indent=2))
