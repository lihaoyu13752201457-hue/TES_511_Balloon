# Prompt-511 Collimator Switch Smoke Report

Status: `PASS_PROMPT511_COLLIMATOR_SWITCH_SMOKE`

## Result

| case | events | rate [s^-1] | ratio to current raw |
|---|---:|---:|---:|
| current fullstat raw eplus | 97 | 0.0658845 | 1 |
| collimator-off raw eplus | 40 (10 eff.) | 0.0543564 | 0.825 +/- 0.274 |
| W-liner repack raw eplus | 12 (3 eff.) | 0.0163368 | 0.248 +/- 0.145 |

## Interpretation

Collimator-off is consistent with the current raw eplus rate within counting statistics, while the local W-liner repack gives a clear lower raw eplus rate. Therefore the existing side-entry W sleeve is not the decisive prompt-eplus suppressor.

## Inputs

- Collimator-off run: `outputs/reports/prompt511_collimator_switch_smoke_20260618/runs/instant_eplus_g10m_r4_rawline`
- Collimator-off switch: four `W_Side_Aperture_Sleeve_collimator_*` panels set to `Vacuum`.
- Current baseline: `outputs/reports/prompt511_entry_audit_20260617/prompt511_entry_audit_summary.json`
- W-liner repack reference: `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_direct_summary_eplus_g10m_r4.json`

## Boundaries

- Raw TES line-window only; no veto, no Compton/FoV, no time axis.
- This is not a delayed activation closure.
- Current baseline uses 8 eplus full-stat replicas; collimator-off and W-liner references use 4 eplus replicas each.
- Collimator-off replica note: all replica line-window local-ID signatures are identical; use one-rep event count for counting-error scale.
- W-liner replica note: all replica line-window local-ID signatures are identical; use one-rep event count for counting-error scale.
