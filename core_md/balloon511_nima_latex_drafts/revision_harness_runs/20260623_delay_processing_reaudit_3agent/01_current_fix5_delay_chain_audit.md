# Current Fix5 Delayed-Chain Audit

Date: 2026-06-23

Scope: current `/home/ubuntu/TES_511_Balloon` fix5 delayed chain only, from
fix5 buildup RPIP through ground-state/NUBASE correction, per-family division,
exact-position M sampling, Cosima delayed transport, Step05 selected delayed
cps, and PI-02 convergence. No code, geometry, source card, authority output, or
old `new_geo_re` artifact was modified.

Overall status: **NO_BUG** for an O(10-100) current-fix5 delayed-rate suppressor.
I found two non-blocking warnings: a small TE-vs-source-flux normalization
wrinkle at the 0.5-0.7% level, and a stale rerun path in the W-origin audit
script. Neither can explain the old/current delayed gap.

## Answer Matrix

### 1. fixed_total_activity_Bq

Status: **PASS**

`fixed_total_activity_Bq` is the ground-state-corrected source activity from
`runs/step02_delay_fix_fix5_fullstat_v2/source_fix_summary.json`, specifically
`new_total_activity_Bq = 85.44920253876245 Bq`. The fixed-source builder computes
ground-state activity per `(VN, ZA)` from scaled RP production and mean per-family
TT, rescales/removes source blocks, then writes `new_total_activity_Bq` as the
sum of surviving source fluxes. The exact-position builder then copies that
value into the exact-position manifest and divides it evenly over `M=50000`
PointSource blocks.

Evidence:

- `code/tools/build_fixed_delay_source.py:365-373`: `activity_after_exposure(nprod, tt_s, half_life_s, t_flight_days)` computes `(nprod / tt_s) * (1 - exp(-lambda*Tflight))`.
- `code/tools/build_fixed_delay_source.py:508-513`: ground-state activities are accumulated from `nprod`, per-family `tt_by_tag`, NUBASE half-life, and flight duration.
- `code/tools/build_fixed_delay_source.py:613-615`: `new_total_activity_Bq` is `sum(v for n, v in new_flux_by_name.items() if n not in remove_names)`.
- `runs/step02_delay_fix_fix5_fullstat_v2/source_fix_summary.json#/new_total_activity_Bq = 85.44920253876245`; `#/old_total_activity_Bq = 87.48329383240524`; `#/source_blocks_removed = 29`.
- `code/tools/build_fix5_1of10_exactpos_delayed_source.py:431-433`: exact-position source loads `fixed["new_total_activity_Bq"]` and sets `flux_per_source = total_activity / n_decays`.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json#/fixed_total_activity_Bq = 85.44920253876245`; `#/flux_per_pointsource_Bq = 0.001708984050775249`.

### 2. Per-family division

Status: **PASS**

The current fix5 full-stat delayed normalization divides RP/RPIP production by
the per-family buildup file count: non-gamma families have `files=8,
division=8`; gamma has `files=12, division=12` in auto mode. The audit rows
close exactly: `rp_scaled_total == rp_raw_total / division` for every family.
This directly guards the historical multi-rep over-normalization mode; the
current chain does not show that bug.

Evidence:

- `code/tools/build_fixed_delay_source.py:85-90`: gamma `auto` resolves to file count; non-gamma uses the configured division.
- `code/tools/build_fixed_delay_source.py:339-343`: each RP value is scaled as `raw_val / div`, and both raw/scaled totals are audited.
- `code/tools/build_fixed_delay_source.py:135-140`: division must match file count unless mismatch is explicitly allowed.
- `runs/step02_delay_fix_fix5_fullstat_v2/normalization_audit_groundstate_fix.json#/status = "PASS"`; `#/problems = []`.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_normalization_rows.csv`, rows 2-9: alpha `145/8=18.125`, eplus `4/8=0.5`, gamma `0/12=0`, muminus `4422/8=552.75`, n `251062/8=31382.75`, all `status=PASS`.

Warning: muminus and muplus TT spreads are 3.52% and 2.60% in
`normalization_audit_groundstate_fix.json#/rows/4/warnings` and
`#/rows/5/warnings`; the code uses mean TT after averaging yields. This is a
small percent-level assumption, not an O(10-100) rate suppressor.

### 3. Half-life source and material changes

Status: **PASS**

The half-life source is the archived local NUBASE2020 file
`inputs/nubase/nubase_2020.txt`, using ground-state records only. The audit
checks the fixed-width NUBASE line fields against the CSV-reported half-lives and
reports zero mismatches and zero unit self-test error.

Materially changed nuclides are long-lived ground states that the old source had
over-active before the ground-state correction, mainly Nb-94, Al-26, Ni-59, and
W-180. Dominant short-lived contributors such as I-128, Al-28, Cu-64, W-187,
W-185, and W-181 are essentially unchanged by the correction.

Evidence:

- `code/tools/build_fixed_delay_source.py:265-300`: NUBASE parser skips non-ground states and reads half-life fields from fixed columns.
- `code/tools/audit_fix5_groundstate_half_life_units.py:100-121`: audit loads `inputs/nubase/nubase_2020.txt`, re-parses NUBASE lines, and requires CSV value/unit agreement plus tiny relative error.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json#/inputs/nubase_archive = "inputs/nubase/nubase_2020.txt"`.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json#/checks/nubase_line_mismatches = 0`; `#/checks/unit_self_test_max_rel_error = 0.0`; `#/checks/raw_unit_counts` includes `Ey`, `My`, `ky`, `y`, `d`, `h`, `m`, `s`, `ms`.
- `runs/step02_delay_fix_fix5_fullstat_v2/groundstate_activity_corrections.csv`, row 40: Nb-94 in `Nb_MagShield_Inner_Cylinder_2mm`, `0.323099364628 -> 4.5085005708458237e-07 Bq`, scale `1.3953913453332472e-06`, NUBASE line 1563, `20.4 ky`.
- Same CSV, row 46: Al-26 in side-port vacuum jacket, `0.229375551592 -> 9.106562176217918e-09 Bq`, scale `3.970153799309939e-08`, NUBASE line 252, `717 ky`.
- Same CSV, row 88: Ni-59 in MuMetal, `0.05633851987 -> 1.979916309545751e-08 Bq`, scale `3.514320777532614e-07`, NUBASE line 818, `81 ky`.
- Same CSV, row 174: W-180 in `Passive_W_Bottom_Plate_detector_bay`, `0.01425438375 -> 2.5519832357038237e-22 Bq`, action `removed_negligible_or_stable`, NUBASE line 4013, `1.59 Ey`.
- Same CSV, rows 23, 90, and 225: W-187, W-185, W-181 remain scale ~1.0 with half-lives `23.809 h`, `75.1 d`, and `120.956 d`.

### 4. Exact-position M=50000 sampling

Status: **PASS**

The current exact-position source uses `M=50000` equal-flux PointSource blocks
drawn from the weighted RPIP table. It preserves total source activity in the
manifest exactly and in the written source text to relative error
`4.53631512934923e-10`. It loses only unsampled rare nuclide support at
`0.0001463401094264377` of total activity, far below the 1% audit threshold.

Evidence:

- `code/tools/build_fix5_1of10_exactpos_delayed_source.py:238-266`: RPIP points are parsed from `CC IP RP` lines and assigned `wfile = 1/division`.
- `code/tools/build_fix5_1of10_exactpos_delayed_source.py:401-425`: sampling weight per point is `activity(VN,ZA) * wfile / sum_wfile(VN,ZA)`.
- `code/tools/build_fix5_1of10_exactpos_delayed_source.py:431-438`: total activity is divided by `n_decays`; source text flux rounding is explicitly audited.
- `code/tools/build_fix5_1of10_exactpos_delayed_source.py:491-500`: sample audit compares drawn support and flux conservation.
- `runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source:2`: source card uses the fix5 `.geo.setup`.
- Same source card, line 14: `DecayRun.Triggers 1000000`.
- Same source card counted values: `PointSource=50000`, `.Flux=50000`, `.ParticleType=50000`.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json#/n_pointsource_blocks = 50000`; `#/rpip_lines_seen = 257309`; `#/eligible_rpip_rows = 251681`.
- Same JSON `#/sampling_audit/parsed_pointsource_blocks = 50000`; `#/sampling_audit/manifest_flux_relative_delta = 0.0`; `#/sampling_audit/source_text_flux_relative_delta = 4.53631512934923e-10`; `#/sampling_audit/matched_back_to_exact_table_fraction = 1.0`; `#/sampling_audit/ambiguous_coordinate_key_fraction = 0.0`; `#/sampling_audit/missed_nuclides_total_activity_fraction = 0.0001463401094264377`.

### 5. Delayed selected cps from selected events and TE/activity

Status: **PASS**

The Step05 selected delayed cps is computed from transported selected events and
the SIM `TE_s`, not directly from the source-card `fixed_total_activity_Bq`.
For the full-stat production sample, delayed W2 selected events are 30 and
`TE_s = 11649.564832 s`, giving `30 / 11649.564832 =
0.0025752034889400762 cps`.

Evidence:

- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json#/delayed_transport/SE = 1000000`; `#/delayed_transport/ID = 1000000`; `#/delayed_transport/TE_s = 11649.564832`; `#/delayed_transport/geometry` ends with the fix5 `.geo.setup`.
- `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py:436-441`: Step05 reads delayed `TE_s` from the delayed transport summary.
- `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py:561-570`: delayed event rate is `1.0 / delayed_time_s()`.
- `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py:829-866`: W2 selected rate is the sum of `cat["rate_hz"]` over events passing TES window, active veto, and side-entry Compton/FoV.
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv`, row 16: W2 delayed side-Compton/FoV `events=30`, `rate_s-1=0.00257520348894`.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json#/checks/selected_events = 30`; `#/checks/selected_rate_hz = 0.0025752034889400762`; `#/checks/rate_matches_step05 = true`; `#/checks/w_or_collimator_selected_events = 0`.

Warning: `1e6 / fixed_total_activity_Bq = 11702.859363 s`, while the SIM has
`TE_s = 11649.564832 s`; `1e6/TE_s` is 1.0045748087 times the fixed source
activity. The same-inventory PI-02 runs show similar 0.5-0.7% offsets. This is
consistent with Cosima transport-time normalization being taken from the SIM
observation time, and it slightly raises, not suppresses, the Step05 delayed
cps. It is not an O(10-100) effect.

### 6. Suspected O(10-100) suppressor

Status: **NO_BUG**

I do not find a current-fix5 processing bug or mismatch that can suppress the
delayed selected rate by O(10-100). The large old/current gap should not be
assigned to current fix5 delayed handling unless the old-chain auditor finds a
different normalization or selection definition. Current fix5 has:

- audited per-family division, no missing x8-style multiplier;
- archived NUBASE ground-state correction with zero line/unit mismatches;
- exact-position source activity conservation at <<1%;
- transport provenance with fix5 geometry and `SE=ID=1,000,000`;
- Step05 delayed cps exactly matching selected events divided by `TE_s`;
- PI-02 convergence completed with four same-inventory exact-position samplings.

Non-O(10) issues:

- **WARN**: small `TE_s` vs source-flux sum offset of about 0.46-0.65%, in the
  direction of increasing current delayed cps.
- **BUG, tooling-only**: `code/tools/build_fix5_w_activation_selected_audit.py`
  sets `STEP05_SCRIPT = ROOT / "code" / "tools" / "build_v3p5_centerfinger_step05_l1_response.py"` at lines 28-34, but that file is absent in the current workspace; the existing audit artifact is present and internally matches Step05, but a rerun would need the script path corrected to `old/code/tools/...`. This does not suppress the recorded delayed rate.

### 7. Old-chain quantities the supervisor must compare

Status: **PASS**

The supervisor should compare old-chain values against these exact current-fix5
quantities and definitions:

1. Source activity and buildup normalization:
   current `old_total_activity_Bq=87.48329383240524`,
   `new_total_activity_Bq=fixed_total_activity_Bq=85.44920253876245`,
   per-family `files`, `division`, `tt_sum_s`, `tt_mean_s`, `rp_raw_total`,
   `rp_scaled_total`, and any division warnings.
2. Half-life source and corrections:
   NUBASE archive path/hash, NUBASE line/value/unit for dominant nuclides,
   correction rows for I-128, Al-28, Cu-64, Nb-94, Al-26, Ni-59, W-180,
   W-187, W-185, W-181, and total activity removed/rescaled.
3. Exact-position sampling:
   `M`, fixed total activity, flux per PointSource, source text flux sum,
   sampled-support missed activity fraction, RPIP rows/keys, and whether the
   source uses true RPIP PointSource blocks or an axisymmetric/RadialProfileBeam
   compression.
4. Delayed transport normalization:
   source triggers, SIM `SE`, `ID`, `TS`, `TE_s`, source-card geometry, SIM
   header geometry, and `generated_decays / TE_s` versus source activity.
5. Step05 selection:
   W2 line window `[510.58, 511.42) keV`, active-veto threshold 50 keV for the
   current fix5 run, side-entry Compton/FoV reject policy `keep`, selected event
   counts at raw/active/final stages, and whether old used the same direct
   selected-event cps or a common-time-axis/accidental-veto product.
6. Selected-rate decomposition:
   delayed selected cps, Poisson sigma, selected W/collimator-origin delayed
   events/rate, top selected delayed source volumes, and W/collimator source
   activity fraction.
7. PI-02 convergence:
   current combined four-run same-inventory result has 103 selected events,
   combined delayed selected rate `0.0022127821289687215 cps`, sigma
   `0.00021803190178715983 cps`, relative uncertainty `0.09853292781642932`,
   and provenance PASS for all runs. Old must be compared at the same selection,
   source-normalization, and support/convergence level before treating the rates
   as physically comparable.

## PI-02 Convergence

Status: **PASS**

The current delayed selected-rate estimate satisfies the PI-02 minimum
convergence screen. The combined value is lower than the single production
sample used in the promotion artifact, but statistically consistent at the
PI-02 level and not suggestive of a hidden activity loss.

Evidence:

- `code/tools/build_fix5_pi02_delayed_convergence.py:124-155`: each run parses
  delayed transport with rate `1/TE_s`, applies the same Step05 W2 selection,
  and computes `sigma = sqrt(selected_events) / TE_s`.
- `code/tools/build_fix5_pi02_delayed_convergence.py:231-238`: combined rate is
  `sum(selected_events) / sum(TE_s)`.
- `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.csv`, rows 2-5: all four runs have `provenance_status=PASS`, same `source_activity_Bq=85.44920253876245`, same fix5 geometry, `1,000,000` generated decays each, and selected events 30, 18, 20, 35.
- `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json#/combined/selected_events = 103`; `#/combined/selected_rate_cps = 0.0022127821289687215`; `#/combined/relative_uncertainty = 0.09853292781642932`; `#/verdict/pi_status = "DONE"`.

## Top 5 Findings

1. **NO_BUG**: No current-fix5 delayed processing bug was found that can
   suppress delayed selected cps by O(10-100).
2. **PASS**: `fixed_total_activity_Bq` is grounded in the corrected fixed source
   and equals `85.44920253876245 Bq`; exact-position source construction
   preserves it.
3. **PASS**: Per-family division is correct and audited: all family divisions
   equal file counts, with exact `rp_scaled_total = rp_raw_total / division`.
4. **PASS**: NUBASE2020 ground-state half-life handling is audited with zero
   line/unit mismatches; material changes are expected long-lived ground-state
   corrections, especially Nb-94, Al-26, Ni-59, and W-180.
5. **WARN**: Current Step05 delayed cps uses selected events divided by SIM
   `TE_s`; the SIM `TE_s` is about 0.46% shorter than `triggers / fixed source
   activity`, so this cannot explain a suppressed delayed rate and is far below
   the old/current discrepancy scale.
