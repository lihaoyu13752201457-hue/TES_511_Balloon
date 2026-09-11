# S3c BGO Thinning and Shield-Volume Audit
Status: `FAIL_S3C_THINNING_AUDIT_G5` — WARN: METHOD_LOW_CONFIDENCE

## Answers

1. **Can BGO be thinner?** C0 has 18,781/717,428 straight-ray cavity passthroughs. The mild isolated cuts are O4 bottom30: +974 leaks, T/T0=1.0519, F3=1.367883e-05; O6 top10: +2,324, T/T0=1.1237, F3=1.379062e-05; and O2 side30: +3,217, T/T0=1.1713, F3=1.386408e-05. The combined worst listed case is O10 at T/T0=1.7481. These are only proposals for the 40_ screening matrix, not transport closure. Sources: `data/thinning_leak_table.csv`, `data/pareto_options.csv`, `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_mainline_analysis_summary.json`.
2. **Which volume is cheapest to remove?** The counted-interceptions/kg ranking is al_shell 9960.6 > w_shell 8891.2 > bgo_bottom 1676.6 > bgo_top 1525.3 > bgo_side 1229.5; the lightest Pareto-listed option is O10. Use the ranking only as a screening proxy because prompt counts include primary and descendant IA records deduplicated to one interception per event-volume. Sources: `data/panel_importance.csv`, `data/pareto_options.csv`.

The 6-event W2 atm511 anchor carries +/-41% (1 sigma) counting error, which dominates every predicted_atm511_w2_cps. Source: `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_w2_background_distribution.csv`.

## Option table

All numbers below are sourced from `data/pareto_options.csv`; Delta-m is option minus C0 (negative means saved mass). All options retain Al3 and unchanged Kapton; `LW4/LW5` identify BGO profiles, not the historical Al5 shell.

| Option | change | mass kg | Delta-m kg | atm511 T/T0 (95% CI) | atm511 W2 cps | B total cps | F3 scale | F3 20d | Pareto | delayed note |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|---|
| O1 | remove W only | 337.322 | -53.877 | 1.1284 [1.1135, 1.1434] | 0.001316678 | 0.005199798 | 1.01472 | 1.379780e-05 | yes | W-removal family evidence: 57.824->31.308 Bq; O1 itself is not a delayed transport result |
| O2 | side 40->30 mm | 324.475 | -66.724 | 1.1713 [1.1561, 1.1866] | 0.001366755 | 0.005249875 | 1.01960 | 1.386408e-05 | yes | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O3 | side 40->20 mm | 260.452 | -130.747 | 1.6687 [1.6507, 1.6869] | 0.001947182 | 0.005830302 | 1.07448 | 1.461040e-05 | no | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O4 | bottom 40->30 mm | 376.974 | -14.225 | 1.0519 [1.0375, 1.0664] | 0.001227395 | 0.005110515 | 1.00597 | 1.367883e-05 | yes | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O5 | bottom 40->20 mm | 362.750 | -28.449 | 1.2110 [1.1956, 1.2265] | 0.001413043 | 0.005296163 | 1.02408 | 1.392506e-05 | no | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O6 | top annulus 40->10 mm | 377.878 | -13.321 | 1.1237 [1.1089, 1.1388] | 0.001311272 | 0.005194392 | 1.01420 | 1.379062e-05 | no | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O7 | top annulus removed | 373.438 | -17.761 | 1.1898 [1.1745, 1.2052] | 0.001388314 | 0.005271434 | 1.02169 | 1.389252e-05 | no | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O8 | side40/bottom30/top10, no W (LW4 profile) | 309.777 | -81.422 | 1.4511 [1.4343, 1.4681] | 0.001693253 | 0.005576373 | 1.05082 | 1.428869e-05 | yes | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O9 | side30/bottom30/top30, no W (LW5 profile) | 251.933 | -139.266 | 1.5877 [1.5702, 1.6055] | 0.001852681 | 0.005735801 | 1.06574 | 1.449151e-05 | yes | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |
| O10 | side30/bottom30/top10, no W | 243.053 | -148.146 | 1.7481 [1.7297, 1.7667] | 0.002039819 | 0.005922939 | 1.08299 | 1.472601e-05 | yes | BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here |

O1's delayed family figures come from `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_lightweight_candidates.csv` and `engineering/geometry_optimization_20260704/38_s3c_neutron_delayed_chain_m50000_clean_20260710/delayed_source/delayed_source_exactpos_summary.json`; no Bq value is extrapolated to a BGO-thinning row.

The ratio interval is a 95% Wilson binomial interval for option leaks among counted cavity-directed photons, divided by the observed C0 leak fraction. The absolute normalization assumes the per-cavity-reaching-photon W2 conversion probability is option-independent. Sources: `data/thinning_leak_table.csv`, `data/pareto_options.csv`.

## Geometry and mass arithmetic

Analytic gross BGO masses reproduce the retained side/bottom/top values within 1%; the retained relief factors are then held fixed for thinner panels. The W side/bottom/top extents are r=25.50--25.70 cm, z=-23.70--45.20 cm / r=0--26.00 cm, z=-23.90---23.70 cm / r=20.90--26.00 cm, z=45.20--45.40 cm; Al is r=25.70--26.00 cm, z=-23.70--45.20 cm / r=0--26.00 cm, z=-24.20---23.90 cm / r=20.90--26.00 cm, z=45.40--45.70 cm. Sources: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup` and its included `.geo`, `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/README.md`, `data/summary.json`.

The right-censored straight-chord fit gives mu_eff=0.89871 cm^-1. Source: `data/depth_profile.csv`.

## Method calibration

O1 implies an F3 shift of 1.472% versus C0, while the historical LW1 screen is +11.75% and also changes Al 3->8 mm; the larger/smaller shift ratio is 7.981. Sources: `data/pareto_options.csv`, `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_lightweight_candidates.csv`.

## Method limits

(a) coupling drops secondary particles that interactions in the removed slab would have produced (biases leak LOW);

(b) some newly leaked photons would scatter in remaining material and miss W2 anyway (biases leak HIGH);

(c) e+/n/residual components are held flat at the frozen budget — thinning effects on them are NOT modeled here and require the 40_ run-matrix screening transport.

## Data-quality and gate notes

- G1: PASS; analytic BGO mass errors and parsed W/Al extents are in `data/summary.json`.
- G2: PASS; exact per-option identities are in `data/thinning_leak_table.csv`.
- G3: PASS; mu_eff=0.89871 cm^-1 from `data/depth_profile.csv`.
- G4: WARN; O1/LW1 shift comparison is in `data/summary.json`.
- G5: FAIL; literal `git status --porcelain` evidence is in `data/summary.json`.
- G6: PASS; checked again by `code/validate_audit.py`.
- RAYL-first cavity-directed events: 24,828; source: `data/summary.json`.

## Gaps

- G5 literal gate is `MISSING_CLEAN_WORKTREE`: pre-existing modified/untracked paths outside `41_` were already present and were preserved. This audit created no intended output outside `41_`; see `data/summary.json` for the status snapshot.
- Prompt-panel importance used uniformly selected whole-file subsamples because the projected full scan exceeded 15 minutes; fractions are in `data/summary.json`.

## Non-claims

- Screening arithmetic on frozen budgets; NOT a full S3c prompt-family or Step05–08 closure; NOT structural qualification; no promotion decision.
- atm511 absolute normalization inherits the unresolved Harris-vs-4π-sidecar calibration; ratios reported here are internal to the 4π sidecar and do not resolve it.
- The 6-event W2 atm511 anchor carries ±41% (1σ) counting error which dominates every predicted_atm511_w2_cps; print this next to the table.
