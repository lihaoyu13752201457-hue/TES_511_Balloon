# XHGIH-REVIEW Final Audit

Status: `PASS_WITH_LIMITATIONS`

Date: 2026-07-07

2026-07-08 atmospheric-511 supersession: the original review validated the
2026-07-07 lower-hemisphere unit-transfer replay. Current downstream
geometry-optimization conclusions must instead use
`engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/`
with the EXPACS-like 4pi sidecar replay. The older atmospheric rows below are
retained only as review provenance where explicitly marked.

Review scope:

- Execution branch: `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/`
- Review precheck: `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_review/REVIEW_PRECHECK.md`
- Run branch: `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/`

This review did not modify the original `511_Mass`, `Mass_model_511`, fix5 authority geometry, or EXEC artifacts.

## Verdict Table

| Area | Status | Verdict |
| --- | --- | --- |
| Main current-geometry veto denominators | `PASS` | `veto_efficiency_summary.csv/json/md` uses raw -> active -> side/FoV with the correct denominators. |
| Atmospheric 511 caveat | `PASS_WITH_WEAK_TABLE_SCOPE` | Main atmospheric cutflow is from the P2 3M replay, while atmospheric ingress is final-candidate-only. This caveat is present, but one region table can still be misread. |
| Ingress evidence completeness | `WEAK` | Source bin, entry proxy, first volume, material, energy, active veto energy, and Compton class are present. Prompt e+/n first-hit position columns are blank; proxy coordinates exist in JSON but not the CSV stage table. |
| Barrel geometry allowlist/denylist | `PASS` | Geometry keeps TES/TES pixels, CsI, `InstrumentFrame`/world, and `NF2_OuterSupport_*`; denylisted internal cryostat/DR/current-GeoOpt volumes are absent. |
| CsI/TES/support preservation | `PASS` | Compared source vs generated geometry lines for CsI, TES, TP placements, and NF2 supports; no missing or changed geometric/material/mother/placement lines found. |
| Detector map cleanup | `PASS` | `.det` contains TES and CsI detector volumes only; no stale detector entries for removed passive internals were found. |
| Source/SIM geometry provenance | `PASS` | Loadcheck and smoke source cards and SIM headers point to the new barrel geometry. |
| Loadcheck run | `PASS_LOAD_ONLY` | 1-event loadcheck completed and wrote SIM/log. It is not physics performance evidence. |
| Atmospheric 511 replay integration | `PASS_SUPERSEDED_BY_20260708_SIDECAR` | The 2026-07-07 lower-hemisphere replay was internally consistent, but current conclusions use the 2026-07-08 4pi sidecar replay: W2 raw/active/final `114/114/107`, active veto rejection `0%`, side Compton/FoV rejection `7/114 = 6.14%`, final nominal rate `0.0207913135058 cps`. |
| Smoke e+ transport and analysis | `PASS_SMOKE_ONLY` | 200k e+ smoke completed and `barrel_eplus_smoke_summary.*` reports W2 and broad raw/active/final all `0/0/0`. This is smoke-only, not full-stat/20-day performance. |
| 2M e+ extension | `PASS_POSITRON_ONLY_LIMIT` | 2M e+ extension completed and `barrel_eplus_2M_summary.*` reports W2 and broad raw/active/final all `0/0/0`, with zero-count 95% upper rate `0.00351839721692 cps`. |
| e+ suppression/performance claim | `PASS_WITH_LIMITATIONS` | 2M e+ extension shows zero TES-window candidates and gives a 95% upper rate for the e+ component. It still cannot be promoted to all-particle or 20-day performance. |
| Overclaim audit | `PASS` | The replay/smoke/2M outputs keep scope boundaries clear. `EXEC_SUMMARY.md` has been rechecked and no longer retains the old missing-ingress or unrun-smoke statements. |

## Evidence Checked

### Current Ingress / Veto

Files checked:

- `ingress_summary.csv`
- `ingress_summary.json`
- `ingress_summary.md`
- `ingress_aggregate_summary.csv`
- `veto_efficiency_summary.csv`
- `veto_efficiency_summary.json`
- `veto_efficiency_summary.md`
- `veto_efficiency_by_source_window_stage.csv`
- `veto_efficiency_by_ingress_region.csv`
- `side_compton_class_counts.csv`
- `build_ingress_veto_audit.py`
- `build_ingress_veto_audit_fast.py`

Main W2 veto rows reproduce the expected current geo-opt authority values:

| family | raw | active pass | final pass | raw rate | active rate | final rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `eplus` | 62 | 40 | 35 | 0.0421003740822 cps | 0.0271615316659 cps | 0.0237663402077 cps |
| `n` | 60 | 13 | 13 | 0.0407117775780 cps | 0.0088208851419 cps | 0.0088208851419 cps |
| `atm511` | 114 | 114 | 107 | 0.0221514928940 cps | 0.0221514928940 cps | 0.0207913135058 cps |

Denominator formulas were checked and match:

- active rejection: `1 - active_veto_pass / raw`
- Compton/FoV rejection: `1 - side_compton_fov_pass / active_veto_pass`
- total rejection: `1 - side_compton_fov_pass / raw`

Atmospheric 511 handling after the 2026-07-08 sidecar replacement is:

- `veto_efficiency_summary.*` uses the 4pi sidecar cutflow: raw `114`, active `114`, final `107`.
- `ingress_summary.*` states that atmospheric ingress rows are only the `107` final W2 candidates.
- `build_ingress_veto_audit_fast.py` explicitly sets atmospheric event rows to `stage_raw=False`, `stage_active_veto_pass=False`, `stage_side_compton_fov_pass=True` and gets the cutflow from the sidecar summary.

Weak point:

- `veto_efficiency_by_ingress_region.csv` includes atmospheric rows with `raw_events=0`, `active_veto_pass_events=0`, and nonzero final events by region. The efficiency cells are blank, so it is not numerically wrong, but the file name implies per-region veto efficiency. This must be labeled as final-candidate-only, split into a separate atmospheric final-ingress table, or recomputed with true raw/active region metadata.

Second weak point:

- For prompt `eplus` and `n`, `first_recorded_volume` and `first_recorded_material` are populated, but `first_recorded_x_cm/y_cm/z_cm` are blank in `ingress_summary.csv`. `ingress_summary.json` has `entry_local_x_cm/y_cm/z_cm` proxy coordinates for most prompt rows, but those fields are not exported to the CSV stage table. Either export the proxy coordinates or explicitly state that first-hit coordinates are unavailable for prompt e+/n.

### Atmospheric 511 Replay Integration

2026-07-08 replacement for current conclusions:

- Summary:
  `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json`
- Source:
  `runs/geometry_optimization_20260704/p2_atm511_sidecar_s1_nominal_geo_opt_s1_bpe_w5_20260708/Atm511SidecarS1Nominal3M_GeoOptS1BpeW5.source`
- SIM:
  `runs/geometry_optimization_20260704/p2_atm511_sidecar_s1_nominal_geo_opt_s1_bpe_w5_20260708/Atm511SidecarS1Nominal3M_GeoOptS1BpeW5.inc1.id1.sim.gz`
- Source model: EXPACS-like semi-empirical 4pi atmospheric 511-keV sidecar,
  20 equal-mu bins, Step06 day-15 environment.
- W2 cutflow: raw `114`, active `114`, final `107`.
- Active veto rejection: `0%`.
- Side Compton/FoV rejection: `7/114 = 6.14%`.
- Final nominal atmospheric-511 rate: `0.0207913135058 cps`.
- Sidecar-included W2 background: `0.0561719296626 cps`.
- Sidecar-included `F3(20d)`: `4.62986036016e-05 ph cm^-2 s^-1`.
- Final atmospheric entry proxy: side_wall `74`, top `24`, bottom `7`,
  side_window `2`.

The older evidence block below describes the superseded 2026-07-07
lower-hemisphere replay and must not be used for current atmospheric-511
geometry-optimization conclusions.

Files checked:

- `engineering/geometry_optimization_20260704/06_atm511_replay_20260707/build_geo_opt_atm511_replay.py`
- `engineering/geometry_optimization_20260704/06_atm511_replay_20260707/p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json`
- `runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1/Atm511LowerUnit3M_GeoOptS1BpeW5.inc1.id1.sim.gz`
- `runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1/cosima_Atm511LowerUnit3M_GeoOptS1BpeW5.log`

Replay status:

- `PASS_GEO_OPT_S1_BPE_W5_P2_ATM511_TRANSFER_REPLAY`
- generated events: `3000000`
- observation time: `265.314 s`
- SIM geometry header: `/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- source normalization: lower-hemisphere mono-511 total flux `1.0 ph cm^-2 s^-1`
- active veto rule: CsI/BGO/legacy active names plus `GeoOpt_S1_PlasticFullWrap*`, threshold `50 keV`

Cutflow:

| window | raw | active pass | final pass | active veto rejection | side Compton/FoV rejection vs active | final transfer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `w2_510p58_511p42` | 108 | 108 | 95 | 0.000% | 12.037% | 0.35806629126242867 cps/(ph cm^-2 s^-1) |
| `broad_480_550` | 135 | 135 | 117 | 0.000% | 13.333% | 0.44098690608109636 cps/(ph cm^-2 s^-1) |

Harris scenario:

- atmospheric 511 added W2 background: `0.008343517492480608 cps`
- Harris-included W2 background: `0.043724133649250325 cps`
- Harris-included `F3(20d)`: `4.084781471084379e-05 ph cm^-2 s^-1`

Denominator review:

- Active veto rejection is correctly `1 - active/raw`; for W2 this is `1 - 108/108 = 0`.
- Side Compton/FoV rejection is correctly `1 - final/active`; for W2 this is `1 - 95/108 = 13/108 = 12.037%`.
- This replay does not show active anticoincidence rejection of atmospheric 511 candidates. The rejection observed here is only the side Compton/FoV stage.

Verdict: `PASS`. No blocking issue found in the replay path, denominator, or Harris scenario calculation.

### Geometry

Files checked:

- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup`
- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo`
- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.det`
- `geometry/Materials_Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo`
- `barrel_hypothesis_geometry_manifest.json`

Manifest status:

- `PASS_BUILD_HYPOTHESIS_GEOMETRY_NOT_TRANSPORT_VALIDATED`

Barrel:

- material: `W`
- inner radius: `30.0 cm`
- outer radius: `33.0 cm`
- side z range: `-25.0..10.0 cm`
- cap thickness: `3.0 cm`
- thin Al side window: `0.5 mm` total thickness
- W mass: about `797.26 kg`
- active status: passive only; not counted as active veto

Allowlist/denylist checks:

- Kept: TES/TES pixels, CsI, `InstrumentFrame`, `WorldVolume`, `NF2_OuterSupport_*`
- Added: `Hyp_W_Barrel_SideShell_WindowCut`, `Hyp_W_Barrel_BottomCap`, `Hyp_W_Barrel_TopCap`, `Hyp_Al_SideWindow_Thin`
- Removed: current `GeoOpt_S1_PlasticFullWrap_*`, `GeoOpt_BPE5_*`, `GeoOpt_W_BottomBaffle_*`, cryostat/window/shell, DR/coldplate, Cu support/coldfinger stacks.
- Text denylist search over `.geo`, `.det`, `.geo.setup` found no forbidden internal-structure tokens.

Preservation check:

- CsI: source and generated geometry have identical relevant material/shape/position/mother lines.
- TES/TES-pixel/TP placements: identical relevant lines.
- NF2 outer supports: identical relevant lines.
- Detector map: 28 detector volumes kept; all are TES or CsI. No extra detector volumes found.

Geometry review status: `PASS`.

Engineering caveat:

- The W barrel is extremely massive for a balloon payload hypothesis (`~797 kg`). This is not a geometry-file failure, but it must be treated as a physics/engineering stress test, not a directly deployable design.

### Source / SIM Provenance

Source cards checked:

- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_loadcheck.source`
- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_smoke.source`

Both source cards use:

```text
Geometry engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup
```

SIM headers checked:

- `Background_eplus_barrelW_loadcheck.inc1.id1.sim.gz`
- `Background_eplus_barrelW_smoke.inc1.id1.sim.gz`

Both SIM headers contain:

```text
Geometry /home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup
```

Run status:

- Loadcheck: completed, `1` generated particle, observation time `0.000497218 s`.
- Smoke: completed, `200000` generated particles, observation time `85.1781 s`.

Run caveat:

- Both logs warn: `You have not defined any trigger criteria!!`
- This is acceptable for geometry load and transport smoke, because SIM files were written. It is not by itself a detector performance validation.

### Barrel W e+ Smoke Analysis Integration

Files checked:

- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_smoke.source`
- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_smoke.inc1.id1.sim.gz`
- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/cosima_Background_eplus_barrelW_smoke.log`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/analyze_barrel_eplus_smoke.py`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/barrel_eplus_smoke_summary.json`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/barrel_eplus_smoke_summary.md`

Smoke status:

- analysis status: `PASS_BARREL_EPLUS_SMOKE_ANALYZED`
- scope: `200k e+ smoke only; not full-stat, not 20-day performance`
- generated events: `200000`
- observation time: `85.1781 s`
- SIM geometry header: `/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup`
- active veto rule: CsI-only at `50 keV`; passive W/Al barrel deposits are not active veto

Smoke cutflow:

| window | raw | active pass | final pass | raw cps | final cps |
| --- | ---: | ---: | ---: | ---: | ---: |
| `w2_510p58_511p42` | 0 | 0 | 0 | 0 | 0 |
| `broad_480_550` | 0 | 0 | 0 | 0 | 0 |

Denominator review:

- The analyzer uses CsI-only active veto and does not count passive W/Al as veto, which matches the hypothesis geometry rule.
- Because raw candidates are zero in both windows, active-veto, Compton/FoV, and total rejection fractions are intentionally blank rather than reported as 100%. This is the correct denominator treatment.
- The zero-candidate result is a smoke result. It should be interpreted as "no TES-window e+ candidates observed in 200k events", not as a full-stat upper bound or 20-day performance number.

Overclaim review:

- `barrel_eplus_smoke_summary.md/json` explicitly says smoke-only and not full-stat/20-day performance.
- This removes the earlier blocker that no e+ response/selection summary existed.
- It does not prove final suppression at the required production statistics. A full-stat or upper-limit analysis is still needed before promoting the barrel hypothesis.

Verdict: `PASS_SMOKE_ONLY`.

### 2M e+ Extension Incremental Review

Files checked:

- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_2M.source`
- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_2M.inc1.id1.sim.gz`
- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/cosima_Background_eplus_barrelW_2M.log`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/analyze_barrel_eplus_smoke.py`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/barrel_eplus_2M_summary.json`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/barrel_eplus_2M_summary.csv`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/barrel_eplus_2M_summary.md`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/barrel_eplus_2M_events.csv`

Source card review:

- run name: `Background_eplus_barrelW_2M`
- events: `2000000`
- seed in source card: `260708`
- geometry line: `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup`
- source family: only the 20 `Atm_eplus_binXX` sources, all with `ParticleType 2`
- declared scope: `2M_EPLUS_ONLY`; not all-particle and not 20-day closure

Transport provenance:

- SIM exists: `Background_eplus_barrelW_2M.inc1.id1.sim.gz`
- log exists: `cosima_Background_eplus_barrelW_2M.log`
- log summary reports `2000000` generated particles
- log observation time: `851.448 s`
- SIM header geometry: `/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707/geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup`
- normal log end observed; only the recurring Cosima trigger-warning class was present

Analyzer review:

- `analyze_barrel_eplus_smoke.py` now accepts `--run-name`, `--tag`, and `--scope`.
- The requested command scope is preserved in JSON/MD: `2M e+ only barrel-hypothesis test; not all-particle or 20-day closure`.
- Active veto convention remains CsI-only at `50 keV`; passive W/Al barrel deposits are not active veto.
- Zero-count 95% upper-rate columns are added for raw, active, and final stages.
- The upper rate uses `2.995732273553991 / observation_time_s`; for `851.448 s` this is `0.0035183972169222206 cps`.

2M cutflow:

| window | raw | active pass | final pass | raw cps | final cps | zero-count 95% upper rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `w2_510p58_511p42` | 0 | 0 | 0 | 0 | 0 | 0.0035183972169222206 cps |
| `broad_480_550` | 0 | 0 | 0 | 0 | 0 | 0.0035183972169222206 cps |

Denominator review:

- Since raw candidates are zero, active-veto, Compton/FoV, and total rejection fractions are intentionally blank. This is correct; they must not be reported as 100% rejection.
- The zero-count upper-rate columns provide a statistical upper bound for the e+ only barrel-hypothesis test.
- Compared with the current geo-opt W2 e+ final rate `0.0237663402077 cps`, the 2M zero-count 95% upper rate is about `14.8%` of that e+ component. This comparison is e+ only and must not be treated as all-background closure.

Overclaim review:

- `barrel_eplus_2M_summary.md/json` state that the result is `2M e+ only` and not all-particle or 20-day closure.
- `EXEC_SUMMARY.md` records the same limitation and does not claim all-particle performance closure from the 2M extension.
- No blocking overclaim was found in the 2M extension.

Verdict: `PASS_POSITRON_ONLY_LIMIT`.

## Remaining Limitations And Non-Blocking Fixes

1. `EXEC_SUMMARY.md` status.
   - Rechecked after parent update: no stale missing-ingress/veto or unrun-smoke statements remain.
   - The 2M section is consistent with the current artifacts and preserves the positron-only, non-closure boundary.

2. Fix or relabel atmospheric rows in `veto_efficiency_by_ingress_region.csv`.
   - Current atmospheric region rows are final-candidate-only but appear in a file named as veto efficiency by region.
   - Acceptable fixes:
     - move atmospheric rows to a separate final-ingress table;
     - add an explicit `scope=final_candidate_only` column and keep efficiency fields blank;
     - or compute true atmospheric raw/active/final region cutflow from the full P2 SIM.

3. Fix prompt e+/n first-position reporting.
   - `first_recorded_x_cm/y_cm/z_cm` are blank for prompt e+/n.
   - Either export `entry_local_x_cm/y_cm/z_cm` into `ingress_summary.csv`, or add a clear caveat that prompt first-hit coordinates are unavailable and only the IA INIT envelope-intersection proxy is spatially populated.

4. Do not promote to all-particle or 20-day closure from e+ only.
   - The 2M zero-count upper limit is useful e+ component evidence.
   - A promoted detector-background claim still needs all-particle closure, delayed handling, atmospheric 511 handling, and normalization through the mission/significance chain.
   - Passive W/Al energy must remain excluded from active veto; retained active veto is CsI only.

5. Keep loadcheck/smoke claim boundaries explicit.
   - Loadcheck proves geometry/source loading only.
   - Smoke plus `barrel_eplus_smoke_summary.*` proves 200k e+ transport and smoke-level response analysis only.
   - The 2M extension gives a stronger e+ only zero-count upper limit.
   - Neither result proves all-particle background closure or 20-day mission performance by itself.

## Final Decision

`PASS_WITH_LIMITATIONS`

No blocking issue was found in the integration results reviewed here. The atmospheric 511 replay is internally consistent and preserves the correct veto denominators. The barrel W e+ smoke and 2M extension analyses are also internally consistent and correctly report zero W2 and broad TES-window candidates with CsI-only active veto.

The result remains limited: atmospheric ingress by region is final-candidate-only, prompt e+/n first-hit coordinates are incomplete in the CSV, and the barrel e+ results are positron-only rather than all-particle or 20-day performance proof.
