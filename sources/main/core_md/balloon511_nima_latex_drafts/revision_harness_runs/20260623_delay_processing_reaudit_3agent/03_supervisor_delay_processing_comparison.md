# Supervisor Delayed-Processing Comparison

Date: 2026-06-23

Scope: supervisor comparison of `01_current_fix5_delay_chain_audit.*` and
`02_old_new_geo_re_delay_chain_audit.*`, with spot checks of existing artifacts.
No code, source card, geometry, authority output, or old `new_geo_re` output was
modified.

## Verdict

**Classification: UNRESOLVED_COMPARABILITY, most likely methodological/source-inventory mismatch.**

The old/current delayed discrepancy is not explained by fixed activity alone,
and neither subaudit proves an O(10-100) delayed-processing bug. The strongest
quantitative split is:

- Current fix5 fixed activity: `85.44920253876245 Bq`.
- Old `new_geo_re` fixed activity: `624.2710918319826 Bq`.
- Activity ratio old/current: `7.30575679215723`.
- Current fix5 W2 delayed production sample: `30 / 11649.564832 s = 0.0025752034889400762 cps`.
- Current fix5 PI-02 combined delayed estimate: `0.0022127821289687215 cps`.
- Old inspected W2 both-veto delayed: `0.15211317269106375 cps`; benchmark restatement: `0.151456825339 cps`.
- Selected-cps ratio old/current production: `59.06840890219195`.
- Selected-cps ratio old/current PI-02: `68.74295065007456`.
- Selected cps per Bq: current production `3.01372442624246e-05`, current PI-02 `2.589587805649718e-05`, old `2.4366525165320926e-04`.
- Residual selected-cps-per-Bq ratio old/current: `8.085186871482254` versus current production, or `9.409422268733405` versus PI-02.

Therefore fixed activity explains only about `7.31 / 59.07 = 0.1237` of the
production-sample gap. The remaining factor is in selection, source spatial
sampling/compression, source-surface/geometry/inventory distribution, or some
combination of those.

## Required Conclusions

1. **Is an O(10-100) difference explained by fixed activity alone?** No. Fixed
   activity differs by only `7.3058x`, while selected W2 delayed differs by
   `59.07x` against the current production sample and `68.74x` against the
   PI-02 combined current estimate.
2. **Is current delayed processing suppressing by O(10-100)?** Not supported by
   the evidence. Current fix5 has a PASS per-family division audit, PASS
   NUBASE/ground-state audit, PASS exact-position M=50000 activity conservation,
   fix5 geometry provenance, and Step05 delayed cps exactly equal to selected
   events divided by `TE_s`. The small `TE_s` vs source-flux offset raises the
   TE-based current rate by about `0.46%`; it does not suppress it.
3. **Is old delayed processing proven inflated by O(10-100)?** No. The old code
   contains the intended non-gamma divide-by-8, uses NUBASE ground-state
   correction with a PASS half-life audit, and computes delayed event rate as
   `1 / TE`. The old chain has audit gaps and a radial-profile compression
   method that can bias detector acceptance, but this re-audit does not prove an
   O(10-100) inflation bug.
4. **Most likely mismatch and discriminator:** the most likely mismatch is a
   combined source-inventory/source-position/selection-definition mismatch:
   old `new_geo_re` has much higher fixed activity, uses z-bin/radial-profile
   `RadialProfileBeam` compression, and reports a detector-coupled Gaussian W2
   probability table; current fix5 uses exact-position M=50000 `PointSource`
   sampling and a hard W2 selected-event count through current Step05. The exact
   next validation is a cross-over replay without new buildup: replay the old
   fixed inventory/RPIP through exact-position PointSource sampling and the
   current hard W2 Step05 selection; optionally pair it with the inverse replay
   of the current inventory through old radial compression and old Gaussian W2
   table construction. Identical Step05 selection on the old inventory is the
   single most discriminating next check.

## Evidence And Comparison

### Fixed activity

Current fix5 `source_fix_summary.json` records the normalization audit file and
per-family divisions, including non-gamma `division=8` and gamma `division=12`
in auto mode (`runs/step02_delay_fix_fix5_fullstat_v2/source_fix_summary.json:7`,
`:10-13`, `:64-68`). Its ground-state normalization audit is `status: PASS` with
`problems: []` and shows representative closures such as `alpha 145/8=18.125`,
`eplus 4/8=0.5`, `muminus 4422/8=552.75`, and
`n 251062/8=31382.75`
(`runs/step02_delay_fix_fix5_fullstat_v2/normalization_audit_groundstate_fix.json:1-3`,
`:5-20`, `:41-56`, `:77-92`, `:113-128`).

Current exact-position source summary records the fix5 geometry, exact-position
source mode, and delayed transport `SE=ID=1000000`, `TE_s=11649.564832`
(`outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json:2-8`,
`:523-532`). Its sampling audit passes with `parsed_pointsource_blocks=50000`,
`manifest_flux_relative_delta=0.0`,
`source_text_flux_relative_delta=4.53631512934923e-10`,
`matched_back_to_exact_table_fraction=1.0`, and
`missed_nuclides_total_activity_fraction=0.0001463401094264377`
(`.../fix5_delayed_source_exactpos_summary.json:361-377`).

Old `new_geo_re` fixed source activity is `624.2710918319826 Bq`, after
ground-state correction from raw `624.5591421396799 Bq`, with `6008` input
source blocks and `40` removed blocks
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/source_fix_summary.json:7-12`).
The old delay-source audit records `fixed_total_activity_Bq=624.2710918416279`,
`fixed_source_blocks=5968`, `samples_positions_from_rpip_profiles=true`, and
`uses_rpip_radial_profile_beam=true`
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json:1-10`,
`:27-34`).

### TE/source flux and selected cps

Current Step05 hard W2 delayed selection has `events=30` and
`rate_s-1=0.00257520348894` after side Compton/FoV pass
(`stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv:11-16`).
The current Step05 implementation reads delayed `TE_s` from the delayed
transport summary and assigns delayed event rate `1.0 / delayed_time_s()`
(`old/code/tools/build_v3p5_centerfinger_step05_l1_response.py:436-441`,
`:561-570`). The same script forms the hard window by requiring
`tes_total_keV >= emin` and `< emax`, then sums `cat["rate_hz"]` for kept events
(`old/code/tools/build_v3p5_centerfinger_step05_l1_response.py:829-866`).

Old delayed transport generated `1000000` particles and logged observation time
`1584.61 sec`
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delayed_transport_equiv2602_aligned/cosima_delayed_transport_1m.log:4126876-4126878`,
`:4132849-4132852`). Old Step05 records `delayed_time_s=1584.61`,
delayed catalog `events=444640`, and delayed catalog rate
`280.59901174421475 cps`
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json:7-10`,
`:33-36`). Its broad 480-550 keV final delayed direct expectation is
`2.31224086683797 cps`
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json:123-133`).

Old Step09 W2 is not the same hard-count operation as the current quoted W2
rate. It computes a Gaussian window probability
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/code/build_detector_coupled_focus_response.py:117-119`),
defines W2 as `510.58` to `511.42 keV`
(`.../build_detector_coupled_focus_response.py:147-151`), and adds
`rate * prob` into window/stage rows
(`.../build_detector_coupled_focus_response.py:364-409`). The old W2 both-veto
CSV row gives delayed `0.15211317269106375 cps`
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv:6-9`), with
uncertainty `0.009671642969996412 cps`, `N_eff=247.36208744053428`, and
weighted event count `344`
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty_by_stream.csv:1-5`).

### Sampling and inventory

Current fix5 uses exact RPIP point weights:
`weight = total_activity * wfile / denom`, then emits equal-flux PointSource
blocks with total activity from `new_total_activity_Bq`
(`code/tools/build_fix5_1of10_exactpos_delayed_source.py:413-438`). The exact
weighted RPIP table sums to `85.44920253544149 Bq`; top current components are
CsI/I-128 bottom quadrants and side segments, then `ColdPlate_4K/Cu-64` and
side-port Al/Al-28, e.g. `CsI_Bottom_Quadrant_03/53128 = 7.822245023628611 Bq`
and `ColdPlate_4K/29064 = 1.8401688967800034 Bq`
(`runs/step02_delay_fix_fix5_fullstat_v2/exactpos_weighted_rpip_table_m50000_s260613.csv:1-8`;
derived aggregation of the `sample_weight` column).

Old `new_geo_re` source construction divides non-gamma RP by `non_gamma_div`
and sets RPIP point weights to `1/non_gamma_div`
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:140-181`,
`:203-205`). It then compresses RPIP points into z-bin and radial profiles
(`.../makedecaysourcewithplot_rpip.py:269-330`) and writes
`Beam RadialProfileBeam` source blocks (`.../makedecaysourcewithplot_rpip.py:745-756`).
The old fixed source block CSV is activity-dominated by CsI/I-128 shields,
e.g. `CsI_Active_Shield_Bottom03/53128 = 49.83254619 Bq` and many side CsI
segments near `36.6-37.4 Bq` each
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step03_delay_source/outputs/fixed_source_blocks.csv:1-8`;
derived aggregation of the `flux_Bq` column).

The old project itself documents the radial-profile limitation: production
Step03 compresses exact RPIP positions into an axisymmetric z-bin plus radial
profile grid, which is too coarse for thin-wall structures, and exact
PointSource sampling was introduced to preserve the exact 3D distribution
(`/home/ubuntu/codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/README.md:5-19`,
`:63-78`).

### Benchmark identity

`fix5_benchmarks.json` explicitly says the old `new_geo_re` benchmark selection
definition is `UNVERIFIED` and must be aligned before gate use
(`core_md/fix5_benchmarks.json:84-96`). It restates old delayed as
`0.151456825339 cps` (`core_md/fix5_benchmarks.json:89-92`), while the inspected
old Step09 artifact gives `0.15211317269106375 cps`. The `0.43%` difference is
negligible for this re-audit, but it should not be hidden when comparing
benchmark labels.

## Bug Status

**Current fix5:** `NO_BUG_FOUND_FOR_O10_TO_O100_SUPPRESSION`. Remaining warnings
are percent-level TE/source-flux offset and a stale rerun path in a W-origin
audit helper, neither of which changes the recorded Step05 rate.

**Old new_geo_re:** `NO_PROVEN_O10_TO_O100_INFLATION_BUG`, but with audit
weaknesses. The missing current-style per-family TT/division artifact is a
reproducibility gap; the inspected implementation contains the divide-by-8. The
radial-profile compression and Gaussian W2 table are real methodological
differences and are the main comparability blockers.

## Recommended Next Checks

1. Build an old-inventory exact-position delayed source from old fixed inventory
   and old RPIP points, then run the same current hard W2 Step05 selection.
   This directly tests whether old high delayed is inventory/geometry or old
   radial compression/selection.
2. Build the inverse current-inventory radial-compressed source and score it
   through the old Gaussian W2 Step09 table. This isolates the radial
   compression and Gaussian probability contribution.
3. For both cross-over checks, publish per-family raw/scaled RP totals, TT,
   division, fixed activity, source flux sum, `TE_s`, selected events, and
   `selected_cps / fixed_activity_Bq`.
4. Treat old `0.151456825339 cps` and current `0.0026-0.0039 cps` as
   report-only until the same inventory sampling and the same W2 selection are
   applied.
