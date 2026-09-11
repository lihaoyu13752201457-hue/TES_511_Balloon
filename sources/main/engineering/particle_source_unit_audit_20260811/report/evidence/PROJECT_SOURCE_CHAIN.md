# TES-511 project particle-source evidence chain

All paths are repository-relative. Hashes for every raw spectrum, both DP
trees, all 24 audited source cards, relevant code, and retained corroborating
artifacts are in `../../data/evidence_hashes.csv`.

## Raw input and correct conversion

- `expacs_fullsphere_20bin_sources/raw_expacs/spectrum_gamma_bin00_theta18.19_BHNo.dat:8-11`
  declares MeV and cm^-2 s^-1 MeV^-1 sr^-1.
- `expacs_fullsphere_20bin_sources/raw_expacs/spectrum_alpha_bin00_theta18.19_BHNo.dat:8-11`
  declares MeV per nucleon and cm^-2 s^-1 (MeV/n)^-1 sr^-1.
- For each raw spectrum, let `I` be its trapezoidal integral over the raw
  energy coordinate and let `B=1000` for all non-alpha families or `B=4000`
  for alpha. The correct transformation is
  `x_keV_total = B × E_raw` and `p_per_keV = f_raw / (I × B)`.
- The audit reconstructs all 160 files in `cosima_spectra_dp/` point by point.
  The worst energy residual is `3.638e-12 keV`; the worst relative PDF
  residual is `8.543e-11`. All eight families pass. This establishes the
  correct directory from raw data rather than from its name.

## Legacy transformation and active source-card references

- `expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units/gamma_bin00_theta18.19_pdf.dat:1-6`
  explicitly says the archived keV values were divided by 1000.
- Across all eight families, every legacy DP x value equals its correct x
  value times 0.001 within floating-point representation; every y value is
  identical. The legacy DP integrals are approximately 0.001, while the
  correct DP integrals are approximately 1. This changes sampled energy, not
  explicit Flux.
- Representative active card:
  `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8/source_cards/Background_gamma_fullsphere20.source:47-55`
  shows degree bounds, a `_2602units` Spectrum File, and an independent Flux.
- Exhaustive counts: Mass_model_511 160/160 legacy references; S3c package 32
  160/160; S3d/O8 package 43 160/160. This is 480/480 references across 24
  cards, not a gamma-only defect.
- `engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/code/run_s3d_o8_all8_activation.py:180-203`
  deliberately pins the same legacy directory and tree hash. That check proves
  reproducibility of the selected input; it does not validate the input unit.

## Transport-level corroboration

- `engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/o8_prompt_gamma_line_dedup_audit.json`
  records a scan of 10,000,000 retained gamma `IA INIT` primaries: 7,639,501
  were below 1 keV. Correct line-adjacent DP nodes 449.65, 566.08, and 712.64
  keV were transported as 0.44965, 0.56608, and 0.71264 keV.
- The same audit states that the original raw-to-DP generator was not found in
  the repository. A full-repository search also did not find a generator for
  `_2602units`; this is a provenance gap, although the point-by-point
  reconstruction closes the numerical transformation.

## Unit chains that do pass, with scope limits

- The explicit Flux sum in each audited card family matches
  `expacs_fullsphere_20bin_sources/manifest.csv` to at most `3.1e-16` relative.
  The 20 equal-mu bins sum to 4*pi. `code/tools/run_equiv2602_pipeline_NEW_GEO.py:354-380,433-447`
  uses `A=pi R²` with `R=60 cm`; its retained arithmetic is internally closed.
- `engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/parma_line_closure.json`
  converts 0.51099895 MeV to 510.99895 keV and closes 20/40/80-bin flux sums.
  This is a source-level pass for the standalone atmospheric 511-keV line.
- `stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py:190-264`
  converts optics x/y from mm to cm, writes 511 in the EventList energy column,
  and writes seconds. All 37,194 retained rows have 15 tokens. The artificial
  1 ns ordering clock is not a balloon exposure time, and the bridge starts at
  the Be-window injection plane.
- Delayed-source code checks NUBASE ground-state half-lives, per-family TT
  normalization, total Bq conservation, PointSource coordinates in cm, and MC
  trigger counts. Those are local bookkeeping passes. The isotope inventory
  was nevertheless produced by the factor-1000-low primary spectra, so the
  existing delayed rates are not physically authoritative.

## Superseded statement

`engineering/m04_validation_geometry_handoff_20260810/00_review/FROZEN_PREFIX_CORRECTION_PROPOSAL.md:164-180`
states that seven non-photon families were unaffected. The exhaustive current
audit contradicts that claim: all eight families reference the same legacy DP
tree and all eight have the same x-axis factor.
