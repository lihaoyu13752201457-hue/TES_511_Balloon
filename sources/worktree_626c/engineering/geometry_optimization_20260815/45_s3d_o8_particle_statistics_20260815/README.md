# S3d-O8 current all-particle statistics record

Status: **PASS**. This package freezes the current 2026-08-13 corrected-keV M05 all-eight-family authority for later S3d-O8 versus SE3 comparisons. It starts no new transport.

## Headline W2 statistics

W2 is 510.58--511.42 keV with 0.42-keV FWHM measured response, 0.3-keV pixel threshold, 50-keV active veto, and retained Step05 side-Compton/FoV selection.

| particle family | instant jobs / histories | buildup files / histories | day-15 ground Bq | prompt final events / cps +/- 1 sigma | delayed final events / cps +/- 1 sigma |
|---|---:|---:|---:|---:|---:|
| p (proton) | 19 / 25,448 | 19 / 25,448 | 762.5385368 | 0 / 0; UL95=0.1840873807 | 7 / 0.02135107903 +/- 0.008069949334 |
| n (neutron) | 38 / 232,991 | 50 / 232,991 | 348.2221636 | 0 / 0; UL95=0.08255608375 | 17 / 0.02367910713 +/- 0.005743027048 |
| alpha | 21 / 5,958 | 14 / 4,343 | 280.4144637 | 0 / 0; UL95=0.08113178412 | 4 / 0.00448663142 +/- 0.00224331571 |
| gamma | 132 / 3,207,738 | 78 / 2,356,499 | 8.170116379 | 2 / 0.03384292813 +/- 0.02393056398 | 24 / 0.0007843311724 +/- 0.0001601009301 |
| e- | 17 / 295,341 | 17 / 295,341 | 0.7807642479 | 0 / 0; UL95=0.02810137092 | 111 / 0.0003466593261 +/- 3.29034471e-05 |
| e+ | 21 / 60,184 | 24 / 60,184 | 3.754845926 | 0 / 0; UL95=0.08100740807 | 255 / 0.003829942845 +/- 0.0002398403243 |
| mu- | 8 / 10,443 | 12 / 67,690 | 0.2501632053 | 0 / 0; UL95=0.01989103411 | 2 / 2.00130564e-06 +/- 1.41513679e-06 |
| mu+ | 9 / 3,972 | 9 / 3,972 | 1.47783129e-05 | 0 / 0; UL95=0.05994108587 | 0 / 0; UL95=2.18061660e-10 |

Totals: prompt **2 events / 0.0338429281309 +/- 0.0239305639766 cps**; delayed **420 events / 0.0544797522273 +/- 0.0101598793116 cps**; constant-environment day-15 total **0.0883226803582 cps**.

Prompt is low support: only two gamma events survive. Every zero-survivor prompt family retains a positive Garwood 95% upper limit in the CSV/JSON; zero is not interpreted as a physical zero. Delayed p, alpha, and muminus are also low support; delayed muplus is a zero-survivor upper-limit branch.

## Input and activation statistics

- Instant prompt: 265 jobs, 3,842,075 histories.
- Buildup activation: 223 files, 3,046,468 histories, 72,054 RP records.
- Delayed transport: 250,000 triggers per family, 2,000,000 total.
- Every family row records both the exact-position source-sampling seed and the delayed-transport seed.
- Transported ground-state activity: 1,404.131068726 Bq; known proton excited-state holdout: 0.099809269 Bq.
- Prompt normalization is per family: `rate=N_selected/sum(instant TT)` and `event weight=1/sum(instant TT)`; TT is never pooled across particle families.
- Activation normalization is per geometry x incident family: `production rate=sum(RP)/sum(buildup TT)`, including zero-RP files in the TT denominator.
- Delayed normalization is per family: `event weight=day-15 transported-ground Bq/250000 triggers`; the 50,000-position source is deterministically thinned to 10,000 positions with stride 5 and retained flux multiplied by 5.

## Official 20-day forward-analytic mission fold

| particle family | prompt counts | delayed counts | total background counts |
|---|---:|---:|---:|
| p (proton) | 0 | 34906.51797 | 34906.51797 |
| n (neutron) | 0 | 38280.45044 | 38280.45044 |
| alpha | 0 | 7574.68144 | 7574.68144 |
| gamma | 55398.97943 | 1258.011485 | 56656.99092 |
| e- | 0 | 563.6350304 | 563.6350304 |
| e+ | 0 | 6218.419276 | 6218.419276 |
| mu- | 0 | 3.14701591 | 3.14701591 |
| mu+ | 0 | 0 | 0 |

Totals: prompt **55398.979434025**, delayed **88804.862651876**, background **144203.842085901**, and signal **1645.387753066** counts.

These per-family mission counts reuse the same transported samples in a 20-day, 81-node family-scalar analytic fold. The focused source is fixed at 45-degree elevation; the signal uses post-Be-window effective area times 45-degree slant transmission at a top-of-atmosphere reference flux of 1e-4 ph cm-2 s-1. Inventory is zero at mission day 0, so pre-flight and ground activation are excluded. Background gamma is the corrected `unit_only_total_gamma` component; there is no additive atmospheric mono-511 stream. No reliable family-level cumulative MC variance was propagated, so this record does not manufacture family error bars.

Exact mission-authority exclusions retained in the machine record:

- PARMA driver gives W=114.6 while the corrected source contract records W=118.3; only driver-internal relative ratios are used
- family scalar transport holds the within-family energy spectrum, angular distribution, detector response, and activation yield fixed across trajectory bins; no corrected multipoint transport validates that approximation
- zero inventory at mission day 0 excludes pre-flight and ground activation
- non-day15 delayed occupancy uses a family-total-activity proxy because active-only parent lineage is unavailable
- 10k exact-position source-mixture uncertainty (parent-ZA TV up to 6.19%)
- 0.0998092689784 Bq S3d excited-state holdout and unresolved NUBASE rows
- optics effective-area systematic and source visibility/duty-cycle history
- full-envelope BPE/plastic optical transmission outside the post-Be EventList scope
- the 81-bin altitude/position profile is synthetic rather than flight telemetry
- T3/T5 values beyond 20 d are labeled sqrt-time extrapolations, not trajectory crossings

## Focused 511-keV signal (separate from background gamma)

The post-Be-window focused EventList has **37,194 trials -> 27,855 selected**, acceptance **0.748911114696** with 95% interval **[0.744471369437, 0.753311966105]**. The selected effective area is **15.041700 cm2** with 95% interval **[14.952528782, 15.130090044] cm2**. At the top-of-atmosphere reference flux of **1.0e-04 ph cm-2 s-1**, the 20-day mission signal is **1645.387753066** counts (lower95 **1635.633454683**).

This is a focused signal gamma component, not a ninth atmospheric background family and not an additive mono-511 background source.

## Files

- `data/s3d_o8_particle_family_statistics.csv`: one complete row per particle family.
- `data/s3d_o8_w2_cutflow_by_family.csv`: raw pre-veto and canonical measured pre-veto/veto50/Step05 cutflows.
- `data/s3d_o8_mission20_counts_by_family.csv`: integrated 20-day family counts.
- `data/s3d_o8_focused_511_signal_statistics.csv`: separate focused-signal trials, acceptance, effective area, and mission counts.
- `data/s3d_o8_particle_statistics_summary.json`: full machine-readable record, totals, contracts, sources, and caveats.
- `data/s3d_o8_authority_sources.csv`: absolute path, SHA256, and size for every pinned authority.
- `audit/s3d_o8_particle_statistics_validation.json`: deterministic self-validation gates and output hashes.
- `code/build_s3d_o8_particle_statistics.py`: deterministic rebuild/validation entry point.

## Authority and exclusions

Primary authority is `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813`. The 601e integrated arbitration is an audit/index layer, not an independent simulation reproduction.

Do not mix this corrected M05 record with either (1) the older package-43 Step05 prompt result of 5 events / 0.003393031514 cps, or (2) the separate frozen pixel/L3 diagnostic mission counts. Large SIM files were not re-hashed here; the authority relies on terminal-ledger/receipt hash declarations. The mission is a forward-analytic family-scalar scenario, not 81 independent environment-point transports and not a final geometry-promotion authority.
