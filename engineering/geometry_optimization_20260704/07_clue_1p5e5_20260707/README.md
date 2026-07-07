# 20-day 1.5e-5 Optimization Clue Package

Status: `NO_VERIFIED_20D_1P5E_MINUS5_SCHEME_FOUND`

This package is a compact handoff for external review. It uses the current
geo-opt S1/BPE/W5 branch plus the atmospheric-511 replay, without promoting the
geometry or modifying the original Mass/511 geometry.

## Bottom line

Current Harris-included W2 performance is `4.08478147108e-05 ph cm^-2 s^-1`
at 20 days. At fixed signal acceptance, the requested `1.5e-5` requires total
background to fall from `0.0437241336493 cps` to `0.00589611677469 cps`,
an `86.52%` reduction.

Current W2 components:

- residual prompt e+: `0.0237663402077 cps`
- residual prompt neutron: `0.0088208851419 cps`
- delayed activation: `0.00279339080718 cps`
- Harris atmospheric 511: `0.00834351749248 cps`

The algebraic package that barely reaches the target is approximately:
atmospheric 511 rejection >=90%, residual e+ rejection >=95%, and residual
neutron rejection >=90%, with delayed activation unchanged. Current evidence
does not validate any of those three high-efficiency rejections.

## Interpretation

1. The current plastic skin is real and useful, but not enough. It reduces W2
   prompt e+ from `0.0359890` to `0.02376634 cps`, leaving the dominant term.
2. The BPE/plastic/W stack reduces internal activation by about 25%, not by an
   order of magnitude. W2 neutron residual remains `0.008820885 cps`.
3. Atmospheric 511 is essentially neutral to the active skin: W2 candidates are
   108 raw -> 108 active-veto pass -> 95 final. The geo-opt transfer is only
   about 6% below Mass.
4. Perfectly removing e+ plus atmospheric 511 still leaves neutron+delayed at
   projected F3 ~`2.11e-05`,
   so all three non-delayed components need simultaneous suppression.

## Files

- `evidence_summary.json`: machine-readable summary and required reductions.
- `background_budget.csv`: component rates plus scenario algebra.
- `optimization_levers.csv`: candidate levers, evidence level, risks, validation.
- `event_clues.csv`: compact event/count clues for e+, neutron, atm511.
- `geoopt_added_geometry_manifest.json`: added-volume manifest subset.
- `geoopt_added_volumes.geo`: extracted GeoOpt material/volume lines.
- `geo_opt_s1_bottomw_b4c_2d_detail.png`: 2D geometry detail.
- `geo_opt_s1_bottomw_b4c.wrl`: WRL visual geometry.
- `neutron_energy_depth_hexbin.png`: neutron energy/depth diagnostic.

## Source evidence outside this package

- Step05 rates: `stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_rates.csv`
- Step08 summary: `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json`
- Neutron/plastic audit: `engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/geo_opt_neutron_plastic_audit_summary.json`
- Atmospheric 511 replay: `engineering/geometry_optimization_20260704/06_atm511_replay_20260707/p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json`
- Geometry manifest: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geo_opt_s1_bottomw_b4c_manifest.json`
