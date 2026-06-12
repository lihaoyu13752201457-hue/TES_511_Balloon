# Codex A-Series Execution Report 2026-06-11

Scope: A1 -> A3 -> A4 -> A2 -> A5 current-data fixes from
`CODEX_FIX_PLAN_A_SERIES_20260611.md`. No git commit/push was made. No cosima,
Geant4, Step06 PARMA rerun, or `../new_geo_re_2` write was performed.

## Guardrails

- Archived before overwrite:
  - `outputs/reports/route_b_diffuse_supplement_20260602_pre_a_series_20260611/`
  - `outputs/reports/day15_complete_report_pre_a_series_20260611/` (`work/` excluded)
  - `stepwise_maintenance/step08_significance/outputs_pre_a_series_20260611/`
  - `outputs/reports/experiment_report_20260601_pre_a_series_20260611/`
- Final validator: `python3 code/tools/validate_new_geo_re.py` -> `Status: **PASS**`, 20 checks.

## A1 Route B Disk Sigma Fix

Changed:

- `code/tools/build_route_b_diffuse_supplement_20260602.py`
- `outputs/reports/route_b_diffuse_supplement_20260602/`
- `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`

Commands:

```bash
rsync -a --exclude work/ outputs/reports/route_b_diffuse_supplement_20260602/ outputs/reports/route_b_diffuse_supplement_20260602_pre_a_series_20260611/
python3 code/tools/build_route_b_diffuse_supplement_20260602.py
python3 code/tools/validate_new_geo_re.py
```

Acceptance:

| disk metric | before | after |
| --- | ---: | ---: |
| sigma_l_deg | 25.479654008640573 | 60.0 |
| sigma_b_deg | 4.4589394515121 | 10.5 |
| fwhm_l_deg | 60.0 | 141.28920270185696 |
| fwhm_b_deg | 10.5 | 24.725610472824968 |
| fov_flux_top_atm_ph_cm2_s | 1.0666068424588441e-07 | 1.923485502742013e-08 |
| W2_Z20d_no_spatial | 0.0029334148127012874 | 0.000529002875394297 |

Bulge rows were unchanged relative to the archive. Disk sky-model fields
matched `../new_geo_re_2/.../route_b_diffuse_metrics.csv` with zero relative
delta for sigma, FWHM, central intensity, FoV fraction, and FoV flux. The Route
B conclusion remains a null/foreground comparison.

## A3 Ledger Fix, Step05 Rerun, Step08 Refresh

Changed:

- `config/science_511_onaxis_source/metadata/science_rate_ledger.csv`
- `code/tools/make_complete_day15_report_ADR.py`
- `outputs/reports/day15_complete_report/`
- `stepwise_maintenance/step08_significance/outputs/`

Commands:

```bash
python3 - <<'PY'
# regenerated science_rate_ledger.csv from current A_eff and preserved T_atm
PY
rsync -a --exclude work/ outputs/reports/day15_complete_report/ outputs/reports/day15_complete_report_pre_a_series_20260611/
python3 code/tools/make_complete_day15_report_ADR.py --workers 6 > /tmp/step05_rerun_a3_20260611.log 2>&1
rsync -a --exclude work/ stepwise_maintenance/step08_significance/outputs/ stepwise_maintenance/step08_significance/outputs_pre_a_series_20260611/
python3 stepwise_maintenance/step08_significance/code/build_step08_significance.py
python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py
python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py
python3 code/tools/validate_new_geo_re.py
```

Acceptance:

| metric | before | after | scale |
| --- | ---: | ---: | ---: |
| science injection rate at 1e-4 | 0.00376098671661694 | 0.00113068164381614 | 0.300634309294557 |
| Step05 science final cps | 0.00239928386599985 | 0.000721307047856697 | 0.300634309294664 |
| Step05 prompt final cps | 0.0535666609652108 | 0.0535666609652108 | 1.0 |
| Step05 delayed final cps | 2.31224086683797 | 2.31224086683797 | 1.0 |
| 10 ks 3-sigma broad flux | 0.0019232215903007 | 0.00639721259630307 | 3.32630032262837 |

Step08 headline deltas vs archive were zero for:

- W1 `A_reference_final_Z_20d=0.7669158563686436`
- W2 `line_pm_3sigma_Z20d_time_dependent=2.735425315169172`
- W2 `line_pm_3sigma_flux_3sigma_20d_time_dependent_ph_cm2_s=1.096721589642255e-04`
- `spot_r90_Z20d_time_dependent=4.507789163321426`
- `spot_r90_T3_day_time_dependent=8.1793477059377`
- `spot_r90_flux_3sigma_20d_time_dependent_ph_cm2_s=6.655147104949208e-05`

Deviation recorded: the plan text said "5 data rows"; the actual ledger has 4
data rows plus header, and that row count was preserved. Also, the existing
Step05 `event_catalog.pkl` stored per-event science `rate_hz`; the first Step05
rerun updated only `normalization.science_injection_rate_s^-1`, not science
expectation rates. I added `refresh_science_event_rates()` to refresh cached
science weights from the current ledger without rebuilding or reparsing the SIM
cache, then reran Step05 successfully.

## A4 Headline Statistical Uncertainties

Changed:

- `stepwise_maintenance/step08_significance/code/build_headline_statistical_uncertainty.py`
- `stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty.csv`
- `stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty_by_stream.csv`
- `stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty.md`
- `stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty_summary.json`
- `stepwise_maintenance/step08_significance/outputs/which_number_is_headline.md` (one pointer line)

Commands:

```bash
python3 stepwise_maintenance/step08_significance/code/build_headline_statistical_uncertainty.py
python3 code/tools/validate_new_geo_re.py
```

Event catalog schema:

- Top-level type: `dict`.
- Event arrays: `stream`, `tag`, `source_file`, `local_id`, `rate_hz`,
  `tes_total_keV`, `bgo_total_keV`, `pix_start`, `pix_count`.
- Pixel arrays: `pix_uid`, `pix_layer`, `pix_e`, `pix_x`, `pix_y`, `pix_z`.
- Stream rates: prompt `757.334 Hz`, delayed `280.599 Hz`, science
  `9.349154e-04 Hz`.

Acceptance:

| selection | B cps | delta B cps | N_eff | Z20d td | delta Z | T3 td day | delta T3 day |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| W1_design_passband | 0.7830469008295945 | 0.02197399388364376 | 1269.8649945570144 | 1.3327565730763073 | 0.018700019599169556 | 101.3376523336149 | 2.8437542504829594 |
| W2_511_pm_420eV | 0.1843471774864037 | 0.010339289845014003 | 317.90075890749154 | 2.735425315169172 | 0.07670948795787443 | 24.055964903748688 | 1.3492020709657329 |
| spot_r90 | 0.055100483553150656 | 0.005959715558883723 | 85.47906346834459 | 4.507789163321426 | 0.24378317103968491 | 8.1793477059377 | 1.2512413832522595 |

Cross-checks:

- Reconstructed W1/W2/spot background rates matched authority files with max
  relative delta `1.4178244284588007e-15`.
- W2 `N_eff` is `O(300)` and spot_r90 `N_eff` is `O(90)`, as expected.

## A2 Experiment Report Refresh

Changed:

- `code/tools/build_experiment_report_20260601.py`
- `outputs/reports/experiment_report_20260601/experiment_report.md`
- `ROUTE_A_FULLCHAIN_EXECUTION_LOG_20260601.md`

Commands:

```bash
rsync -a --exclude work/ outputs/reports/experiment_report_20260601/ outputs/reports/experiment_report_20260601_pre_a_series_20260611/
python3 code/tools/build_experiment_report_20260601.py
python3 code/tools/validate_new_geo_re.py
```

Acceptance:

- W2 now quotes time-dependent headline `Z20d=2.73543`, with `2.75023` only as
  a labeled constant-rate variant.
- `spot_r90` now quotes time-dependent `Z20d=4.50779`, `T3=8.17935 day`, and
  20-day 3-sigma flux `6.655147e-05`; constant-rate values appear only as
  labeled variants.
- W1 A-reference is labeled as time-dependent `Z20d=0.766916`, `T3=306.039 day`.
- A4 uncertainties are included: W2 `B=0.184347 +/- 0.0103393 cps`,
  `Z20d=2.73543 +/- 0.0767095`; spot_r90
  `B=0.0551005 +/- 0.00595972 cps`, `Z20d=4.50779 +/- 0.243783`.

## A5 CsI Activation Anchor

Changed:

- `stepwise_maintenance/step03_delay_source/code/build_csi_activation_anchor_20260611.py`
- `stepwise_maintenance/step03_delay_source/outputs/csi_activation_anchor_20260611.csv`
- `stepwise_maintenance/step03_delay_source/outputs/csi_activation_anchor_20260611.md`
- `stepwise_maintenance/step03_delay_source/outputs/csi_activation_anchor_20260611.json`

Commands:

```bash
python3 stepwise_maintenance/step03_delay_source/code/build_csi_activation_anchor_20260611.py
python3 code/tools/validate_new_geo_re.py
```

Acceptance:

| metric | value |
| --- | ---: |
| Chain I-128 activity | 533.2757337939476 Bq |
| CsI active-shield mass | 65.15479778075493 kg |
| Chain specific activity | 8.184750040793828 Bq/kg |
| Analytic two-group activity | 6.322563602492813 Bq/kg |
| Chain / analytic ratio | 1.2945302816039377 |

The ratio is within the planned factor-of-3-to-5 order-of-magnitude band.
Literature reference slots are left as TODOs; no unverified web citations were
invented.

## Final Documentation Sync

Changed:

- `Project_Memory.md`: A1/A3/A4/A2/A5 state, Pending Fix #7 DONE notes,
  misquote guardrails, authority map, and publication-readiness annotations.
- `Project_List.md`: ledger migration warning now says the mainline CSV was
  fixed on 2026-06-11 and should be regenerated only when optics authority or
  geometry changes.

Final validator command:

```bash
python3 code/tools/validate_new_geo_re.py
```

Result: `Status: **PASS**`.
