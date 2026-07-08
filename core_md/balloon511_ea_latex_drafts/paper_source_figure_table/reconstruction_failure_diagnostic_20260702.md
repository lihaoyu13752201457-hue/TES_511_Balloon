# Reconstruction-Failure Diagnostic Sidecar 20260702

Status: `PASS_EA_RECONSTRUCTION_FAILURE_DIAGNOSTIC`

This sidecar replays the existing Step05 event catalog and does not rerun transport.

## Manuscript Values

| diagnostic | signal retention | background retention | S/sqrt(B) fraction |
|---|---:|---:|---:|
| single-site-only | 59.4% | 68.2% | 0.720 |
| drop reject_kept only | 100.0% | 100.0% | 1.000 |

The manuscript sentence should describe the quoted 59.4%, 68.2%, and 0.720 values as a single-site-only diagnostic, not as merely dropping the unreconstructed/reject_kept class.

## Inputs

- Step05 script: `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py`
- Step05 summary: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json`
- Event catalog: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/work/event_catalog.pkl`

## Consistency

- Matches Step05 summary: `True`
- Recomputed baseline signal: `0.7989191805127599 cps`
- Recomputed baseline background: `0.03921622651863149 cps`
