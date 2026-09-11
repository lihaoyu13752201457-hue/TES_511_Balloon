# Old new_geo_re delayed-chain audit

Date: 2026-06-23

Auditor role: old `new_geo_re` delayed-chain auditor.

Scope: old delayed processing from buildup RPIP through ground-state correction, source construction/compression, Cosima delayed transport, Step05 selected delayed cps, and Step09 W2 table. This report is read-only except for this assigned audit file and the paired JSON report.

Old project root inspected: `/home/ubuntu/codex_tes_511_sim/new_geo_re`

## Executive status

Overall status: **WARN**

I do not find evidence for an internal old-chain processing bug that directly inflates the delayed rate by O(10-100). I do find audit gaps and mismatches that a supervisor must compare before using the old delayed value as a physics benchmark:

- **PASS**: old source activity is traceable to RP/RPIP yields, TT exposure, half-life buildup, and a fixed-source NUBASE ground-state correction.
- **WARN**: the non-gamma divide-by-8 exists in old source-building code, but the old chain lacks the current-style per-family TT/division audit artifact.
- **PASS**: the half-life ground-state correction was audited against NUBASE units, including prefix-year units; W-180 ground-state blocks were effectively removed.
- **WARN**: old source sampling compresses true RPIP positions into z-bin/radial-profile beams, not exact-position M sampling. That can bias spatial acceptance, especially thin passive structures, without changing total activity.
- **PASS/WARN**: delayed cps is computed as selected weighted events divided by Cosima observation time from the log. There is a small TE/activity mismatch of about 1.1%, not O(10-100).

## Explicit answers

### 1. How old fixed/source activity was computed

Status: **PASS**

The old buildup normalization used the aligned gamma exposure and eight non-gamma replicas. The normalization record states `gamma_events = 10000000`, `non_gamma_replicas = 8`, `gamma_norm_factor = 541.3815137522625`, `non_gamma_combined_norm_factor = 67.67268921903281`, and `gamma_prompt_time_s_with_farfield_area = 541.3815137522625`.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_equiv2602_aligned/normalization.json:5` = `gamma_events: 10000000`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_equiv2602_aligned/normalization.json:7` = `non_gamma_replicas: 8`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_equiv2602_aligned/normalization.json:9` = `gamma_norm_factor: 541.3815137522625`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_equiv2602_aligned/normalization.json:10` = `non_gamma_combined_norm_factor: 67.67268921903281`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_equiv2602_aligned/normalization.json:13` = `gamma_prompt_time_s_with_farfield_area: 541.3815137522625`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/run_equiv2602_pipeline_NEW_GEO.py:359-363` computes `gamma_factor`, `non_gamma_factor = gamma_factor / non_gamma_replicas`, farfield area, and prompt time.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/run_equiv2602_pipeline_NEW_GEO.py:421-438` writes the normalization constants.

The old raw delayed source builder reads isotope production from `.dat` files, divides non-gamma RP yields by `--non-gamma-div`, reads RPIP production points with the same file weight, computes activity as:

`R = N_prod / TT_s`

`A_end = R * (1 - exp(-lambda * Texp))`

then assigns source flux across compressed z/r source blocks.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:140-181` parses `.dat` RP records; line 176 adds `val / div`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:203-231` parses RPIP points; line 205 sets `wfile = 1.0 if gamma else 1/non_gamma_div`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:336-346` computes production rate and decay activity.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:976-986` chooses `TT = tt_by_tag.get(tag, 1.0)`, computes activity, and accumulates total yield/activity.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:992-1021` distributes activity over z bins and writes per-block flux.

The old fixed source then rescales or removes ground-state source blocks using NUBASE ground-state half-lives. The fixed source summary reports:

- raw source total activity: `624.5591421396799 Bq`
- fixed source total activity: `624.2710918319826 Bq`
- source blocks in: `6008`
- source blocks removed: `40`

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json:7` = `old_total_activity_Bq: 624.5591421396799`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json:8` = `new_total_activity_Bq: 624.2710918319826`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json:9` = `source_blocks_in: 6008`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json:10` = `source_blocks_removed: 40`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source:12-14` sets `Run DecayRun`, output filename, and `DecayRun.Triggers 1000000`.

### 2. Whether any per-family TT division exists or is missing

Status: **WARN**

Implementation-level non-gamma division exists, but an auditable per-family TT/division guard is missing in the old chain.

What exists:

- Non-gamma RP yields are divided by `non_gamma_div`.
- Non-gamma RPIP point weights are set to `1/non_gamma_div`.
- The ground-state fixer independently applies the same `val / div` rule when recomputing fixed ground-state activities.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:150` sets `div = 1.0 if tag == "gamma" else non_gamma_div`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:176` adds `val / div`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:205` sets RPIP `wfile = 1.0 if tag == "gamma" else 1.0 / float(non_gamma_div)`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:182` sets `div = 1.0 if tag == "gamma" else float(non_gamma_div)`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:204` adds `value / div`.

What is missing:

- I found no old current-style machine-readable guard equivalent to `normalization_audit_groundstate_fix.json` proving, for every family, raw RP totals, scaled RP totals, TT, replica division, and post-fix activity.
- The old parser stores `tt_by_tag[tag] = tt_val`, so TT for repeated non-gamma replica tags is overwritten rather than summed as an explicit per-family exposure table. This is probably numerically equivalent only if all replica TT values are equal and RP counts are averaged by the divide-by-8 rule. It is not an auditable guard.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:179` sets `tt_by_tag[tag] = tt_val`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:206` sets `tt_by_tag[tag] = tt_val`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json:27` records source blocks removed, but this audit does not include per-family raw/scaled RP totals and TT division proof.

Bias implication:

- If the non-gamma divide-by-8 were absent, non-gamma-derived delayed activity could be inflated by up to about 8x. In the inspected old files, the divide is present.
- The missing guard is therefore a reproducibility/audit weakness, not direct evidence of the old W2 delayed rate being inflated by O(10-100).

### 3. What half-life correction source/method was used

Status: **PASS**

The old fixed source uses a local NUBASE 2020 file to recompute ground-state (`exc == 0`) source activities. It parses ground-state NUBASE rows, supports prefix-year units, computes day-15 activity with an exponential buildup formula, and rescales or removes matching source blocks.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/workflow.md:10` names `inputs/nubase/nubase_2020.txt` as the NUBASE authority.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:2-8` describes the post-processor that recomputes `exc=0` activities using local NUBASE ground-state records.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:55-73` defines half-life unit conversion, including `ky`, `My`, `Gy`, `Ty`, `Py`, `Ey`, `Zy`, and `Yy`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:139-174` parses NUBASE ground-state records.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:210-218` computes ground-state activity as `(nprod/tt_s) * (-expm1(-lambda * t_flight_days * 86400))`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:327-341` recomputes only `exc == 0` activities using NUBASE.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:345-357` computes scale factors and removes near-zero flux blocks.

The half-life unit audit reports PASS with exact NUBASE archive identity and zero conversion mismatches. It explicitly validates W-180 removal.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json:2-3` = `status: PASS`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json:5-10` records the corrections CSV, fixed source, NUBASE archive hash, and line count.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json:13-21` records `corrections_rows: 1568`, prefix-year rows, and unit counts.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json:43-46` reports max conversion errors of zero and no line mismatches.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json:47-54` reports W-180 old total `0.284519501 Bq`, new total `5.093794371872413e-21 Bq`, W-180 removed, and no forbidden particle types in the fixed source.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json:15-28` shows a W-180 `Passive_W_Outer_Liner` row scaled from `0.127479 Bq` to `2.282484e-21 Bq` using NUBASE line 4013 and raw half-life `1.59 Ey`.

### 4. How old source sampling/compression works

Status: **WARN**

The old chain starts from true RPIP isotope production positions, but it does not preserve exact positions in the production delayed source. It compresses points into axisymmetric z-bin plus radial-profile source beams. Source entries then use `RadialProfileBeam` with per-bin flux.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:4-20` documents use of true isotope production positions from `CC IP RP <VN> x y z ZA exc_keV t` and total yields from `.dat`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:269-330` builds z bins and radial profiles.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:296-305` normalizes z-bin weights.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:307-323` creates normalized radial profiles.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:745-756` writes `ParticleType`, `Beam RadialProfileBeam`, and `.Flux` source fields.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source:16` begins fixed source blocks after the run header.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source:5986-5988` has an example fixed CsI/I-128 source block using `RadialProfileBeam` and flux `9.27997922e+00`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source:6526-6528` has an example W-187 source block using `RadialProfileBeam` and flux `8.03639015e-01`.

The old audit output reports 5968 fixed listed sources and confirms `ActivationDelayedDecay` plus `RadialProfileBeam`.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json:2` = `fixed_listed_sources: 5968`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json:5` = `fixed_total_activity_Bq: 624.2710918416279`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json:30-34` reports fixed source profile files, `ActivationDelayedDecay`, and RPIP radial-profile beam usage.

Known caveat:

- Exact-position smoke-test notes in the old project say the production source compresses true RPIP points into axisymmetric z/r grids, and that this is weak for thin-wall structures. This is a credible detector-response bias mechanism, but not by itself proof of an O(10-100) rate inflation.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/README.md:5-10` states that the production source compresses true RPIP points into an axisymmetric z-bin plus radial-profile grid.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/README.md:12-19` identifies coarse radial grids as weak for thin-wall structures.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/README.md:25-31` describes the exact-position alternative: draw M decays weighted by `Activity_Bq/n_points` and set source flux to `A_total/M`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/README.md:63-78` explains that exact-point sampling eliminates radial smearing for passive thin shells.

### 5. How old delayed selected cps is computed from selected events and TE/activity

Status: **PASS**

Step05 uses the Cosima delayed transport observation time as the delayed exposure time. It parses delayed SIM events, assigns each delayed catalog event a rate of `1 / delayed_time_s`, and sums selected event rates through the broad 480-550 keV and final selection stages. If the log observation time is unavailable, the code falls back to `source_triggers / source_activity`.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/make_complete_day15_report_ADR.py:111-131` defines `delayed_time_s()`: parse `Observation time:` from the Cosima log, else use `source_triggers/source_activity`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/make_complete_day15_report_ADR.py:159-166` makes delayed event rate `1.0 / delayed_time_s()`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/make_complete_day15_report_ADR.py:240-287` parses SIM `SE` and `ID` event records and active-shield hits.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/make_complete_day15_report_ADR.py:490-533` computes direct expectation rates through raw, BGO, and final stages.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/make_complete_day15_report_ADR.py:903-914` writes prompt time, delayed time, observation time, coincidence window, and BGO threshold into the summary.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/make_complete_day15_report_ADR.py:1172-1226` uses the delayed observation time by default and then computes direct expectation and timeline summaries.

The Cosima transport log reports 1,000,000 generated particles and observation time `1584.61 s`.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delayed_transport_equiv2602_aligned/cosima_delayed_transport_1m.log:4126878` = `Total number of generated particles: 1000000`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delayed_transport_equiv2602_aligned/cosima_delayed_transport_1m.log:4132852` = `Observation time: 1584.61 sec`

The Step05 report records delayed time `1584.61 s`, delayed catalog events `444640`, and delayed catalog rate `280.59901174421475 cps`, which is `444640 / 1584.61`. It reports broad 480-550 keV delayed final rate `2.31224086683797 cps`.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json:7-10` records `prompt_time_s: 541.3815137522625`, `delayed_time_s: 1584.61`, and `obs_time_s: 1584.61`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json:24-43` records delayed catalog `events: 444640`, `rate_hz: 280.59901174421475`, and `tes_events: 121458`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json:118-133` records direct-expectation final rates: total `2.366528834846823 cps`, prompt `0.05356666096521081 cps`, delayed `2.31224086683797 cps`.

Step09 W2 then applies detector-coupled energy-window probabilities and veto classes to the background event catalog. The W2 both-veto delayed value in the old output is `0.15211317269106375 cps`.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py:117-119` computes Gaussian window probability.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py:122-154` defines W2 as 511 keV +/- 0.420 keV.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py:364-412` loops over catalog events and adds `rate_hz * prob`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py:415-446` combines prompt and delayed rates by window and veto class.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv:9` row `W2_511_pm_420eV,both` gives `rate_cps 0.18434717748640367`, `prompt_cps 0.03223400479533992`, `delayed_cps 0.15211317269106375`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty_by_stream.csv:4` row `W2,delayed` gives `B_cps 0.1521131726910638`, `delta_B_cps 0.009671642969996412`, `N_eff 247.36208744053428`, and weighted event count `344`.

TE/activity caveat:

- Fixed source total activity `624.27109184 Bq` and 1,000,000 triggers imply `1000000 / 624.27109184 = 1601.87 s`, whereas the Cosima log reports `1584.61 s`. Step05 uses the log time, so the rate difference is about 1.1%, not O(10-100). This should be compared in the current chain.

### 6. Suspected bug or mismatch that could inflate delayed by O(10-100)

Status: **NO_BUG**

I do not find a proven old-chain processing bug that inflates delayed by O(10-100).

Rejected O(10-100 mechanisms:

- **No evidence of missing half-life prefix-year parsing**: half-life audit status is PASS; W-180 ground-state rows are removed/scaled to near zero.
- **No evidence of multiplying delayed events by source activity twice**: Step05 assigns delayed event rates as `1 / TE` and Step09 sums `rate_hz * Gaussian_window_probability`.
- **No evidence that the non-gamma divide-by-8 is absent**: old source-building and ground-state-fix code both divide non-gamma RP yields by `non_gamma_div`.

Remaining WARN mechanisms:

- **Missing per-family TT/division audit**: this is an audit gap. A missing non-gamma divide would be an up-to-8x class bug, but the inspected old implementation contains the divide.
- **Radial-profile compression**: this can alter detector acceptance because old production delayed sources smear exact RPIP positions into radial profiles. It is a credible source of mismatch against current exact-position delayed chains, especially for passive thin shells. It is not proven here to be O(10-100).
- **Stale old-memory values**: old `MEMORY.md` contains stale delayed activity/time values (`110.0882 Bq` and `9003.74 s`) that conflict with old authority outputs (`624.271 Bq` and `1584.61 s`). Using those stale values would mislead rate comparisons by about 5.7x, but the old Step05/Step09 authority outputs do not use them.
- **Exact W2 benchmark mismatch**: the current fix5 benchmark JSON restates old delayed W2 as `0.151456825339 cps`, while the old Step09 output inspected here is `0.15211317269106375 cps`. The difference is about `0.000656 cps`, or 0.43%, and is only about 0.07 sigma using the old delayed W2 uncertainty `0.00967164297 cps`.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/half_life_unit_audit/half_life_unit_audit_summary.json:2-3` half-life audit PASS.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/code/tools/make_complete_day15_report_ADR.py:159-166` delayed event rate is `1.0 / delayed_time_s()`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py:364-412` W2 event contribution is rate times Gaussian probability.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:150-176` non-gamma RP divide exists.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/build_fixed_delay_source.py:182-204` ground-state fix non-gamma RP divide exists.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/MEMORY.md:120-124` contains stale old delayed activity/time values; compare to `/home/ubuntu/codex_tes_511_sim/new_geo_re/workflow.md:21-29` and fixed-source/log evidence above.
- `/home/ubuntu/TES_511_Balloon/core_md/fix5_benchmarks.json:85-91` restates old `new_geo_re` delayed total as `0.151456825339 cps`, while `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv:9` gives `0.15211317269106375 cps`.

### 7. Current-chain quantities the supervisor must compare

Status: **WARN**

The supervisor should not compare only final delayed cps. The following quantities must be compared old-vs-current/fix5 before assigning the old/current delayed discrepancy to geometry or physics:

1. Source and activity normalization
   - raw source activity, fixed source activity, fixed source block count, removed block count
   - per-family raw RP total, scaled RP total, TT, non-gamma division, and post-fix activity
   - no-RPIP or unknown-remap rows and total missing activity
   - dominant inventory by nuclide and volume, especially CsI/I-128 and W/passive-shield families

2. Half-life correction
   - NUBASE file hash/line count and ground-state line references
   - prefix-year unit conversion audit
   - W-180/W-183 removal or scaling rows
   - old vs new ground-state correction totals by family

3. Source sampling
   - old radial-profile z/r source block counts and binning versus current exact-position M sampling
   - total flux conservation after compression/sampling
   - matched inventory point count and missing point/activity fraction
   - thin-shell W/collimator spatial placement and activity after sampling

4. Delayed transport exposure
   - source `Triggers`, Cosima generated particle count, Cosima observation time, SIM `SE`/`ID` count
   - `TE` from log versus `Triggers / sum(source flux)`
   - SIM/source geometry header path

5. Selection and W2 rate construction
   - broad 480-550 keV delayed final cps
   - W2 delayed cps, W2 prompt cps, total cps, uncertainty, `N_eff`, weighted event count, and `sum_w2`
   - exact W2 definition: Gaussian detector-coupled probability versus hard truth-energy window
   - veto class: raw, scintillator, Compton, and both

6. Benchmark identity
   - reconcile `fix5_benchmarks.json` old delayed value `0.151456825339 cps` with old Step09 inspected value `0.15211317269106375 cps`
   - compare with uncertainty, not only nominal values

## Key old numerical anchors

Status: **PASS**

- Old fixed delayed source activity: `624.2710918319826 Bq`
- Old delayed transport triggers: `1000000`
- Old delayed transport observation time: `1584.61 s`
- Step05 broad delayed final selected rate: `2.31224086683797 cps`
- Step09 W2 both-veto delayed rate in inspected old output: `0.15211317269106375 cps`
- Step09 W2 both-veto prompt rate in inspected old output: `0.03223400479533992 cps`
- Step09 W2 both-veto total rate in inspected old output: `0.18434717748640367 cps`
- Old W2 delayed statistical uncertainty: `0.009671642969996412 cps`

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json:8`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delayed_transport_equiv2602_aligned/cosima_delayed_transport_1m.log:4126878`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delayed_transport_equiv2602_aligned/cosima_delayed_transport_1m.log:4132852`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json:118-133`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv:9`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty_by_stream.csv:4`

## Final verdict

Status: **WARN**

The challenged prior conclusion should be narrowed:

- **NO_BUG**: I do not see a demonstrated old delayed-chain processing bug that inflates W2 delayed by O(10-100).
- **WARN**: old delayed processing is not as auditable as the current fix5 contract requires because it lacks a per-family TT/division guard and uses compressed radial-profile source sampling.
- **WARN**: the old W2 delayed number in current benchmark prose/JSON is not exactly the inspected old Step09 output, but the mismatch is statistically negligible relative to old W2 delayed uncertainty.
- **ACTION**: the current-chain supervisor must compare normalization, half-life correction, exact-position sampling, TE, and W2 selection quantities side-by-side before interpreting old/new delayed discrepancies.
