# S3d lightweight geometry — O9 Pareto-knee candidate

Status: `S3D_O9_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS`

Performance-screening status: `FAIL_S3D_SCREENING_PROMOTION_GATES`

The geometry itself is valid, but O9 is not eligible for promotion.  Its
matched e+/n/atmospheric-511 subset is `0.00621054222 cps`, above the frozen
`0.0052 cps` limit.  Full-chain O9 production is therefore stopped; the
pending neutron-only delayed diagnostic cannot reverse this mandatory-gate
failure.  The retained fallback work proceeds in the separate `43_` package.

This package is a strict, auditable delta from the retained S3c-C0 geometry.
The selected profile uses uniform 30 mm active BGO, removes the three 2 mm W
mechanical-shell volumes, and retains the original Al3 and Kapton package.

## Decision

The 41_ audit arithmetic is internally consistent, but it does not prove that
the lightest O10 point preserves performance: e+/n/residual were frozen and the
method calibration differs from the historical LW1 screen by a factor of 7.98.
O9 is used here because it is the Pareto knee: `139.266 kg`
(`35.60%`) pre-relief mass saving with
the screening proxy at +6.57% F3.  O10 saves only 8.88 kg more while thinning
the top active shield from 30 to 10 mm; it is kept as a later stress test.

## Authorized geometry delta

- BGO side: `r=21.2..25.2 -> 21.2..24.2 cm`; `z=-19.4..40.9 cm` unchanged.
- BGO bottom: `z=-23.4..-19.4 -> -22.4..-19.4 cm`; radius unchanged.
- BGO top annulus: `z=40.9..44.9 -> 40.9..43.9 cm`; radii unchanged.
- Remove the three S3c W2 side/bottom/top placements and detector scorers.
- Preserve Al3, Kapton, aperture, service opening, reliefs, TES/cryostat,
  BPE/plastic, materials, thresholds, and response definitions.

The reported mass is pre-relief analytic bookkeeping for the BGO/Kapton/outer
shell package only; it is neither whole-instrument mass nor a structural mass
qualification.  `outer_w2_shell_kg = 0` does not imply that unrelated retained
tungsten parts elsewhere in the instrument were removed.  Source:
`engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_mass_ledger.json`.

Keeping the external Kapton/Al envelope byte-identical leaves a deliberate
`1.17 cm` BGO-to-Kapton and `0.30 cm` Kapton-to-Al service/vacuum clearance on
the side, bottom, and top.  This is the frozen minimal-delta transport model;
it requires a separate support/manufacturing design before hardware use.

## Gehrels 1985 design check

The design follows the classic recommendations to minimize passive material
near the detector, prefer low-Z structural material, retain active shielding,
and avoid trading aperture/background control for passive high-Z mass.  The
paper also recommends a shield threshold well below 50 keV.  This geometry
retains the S3c native 80 keV BGO detector definition while the analysis uses a
matched 50 keV post-processing veto; that mismatch is an explicit systematic
boundary, not a claimed hardware achievement.

Reference: N. Gehrels, *Instrumental background in balloon-borne gamma-ray
spectrometers and techniques for its reduction*, NIM A 239 (1985) 324-349,
doi:10.1016/0168-9002(85)90732-6.

## Generated evidence

- Geometry: `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Manifest: `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_geometry_manifest.json`
- Mass ledger: `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3d_mass_ledger.json`
- S3c-to-S3d static diff audit: `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/s3c_to_s3d_static_diff_summary.json`
- Cosima overlap source: `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/geometry/overlap_check_s3d.source`
- Cosima overlap summary: `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/data/cosima_overlap_s3d_summary.json` (`PASS` for the current geometry hashes)

## Required promotion gates

1. Static diff PASS, Cosima overlap/load PASS, and every source/SIM header must
   resolve to this geometry.
2. Matched e+/n/atm511 dominant W2 subset <= 0.0052 cps.
3. f10m A1 final W2 signal acceptance loss <= 2% versus S3c-C0.
4. Clean neutron-only delayed activity <= 57.8243 Bq with NUBASE, TT division,
   exact-position sampling, and provenance gates all PASS.
5. After all prompt families and delayed response are closed, central F3 <=
   1.05 times C0 and its 95% upper ratio <= 1.10; otherwise fall back to O8.

## Non-claims

- No transport or performance result is created by this geometry builder.
- The pre-relief mass is not a structural qualification.
- The 41_ screening proxy is not a validated F3 or promotion decision.
- Optics-hardware background remains outside this detector geometry branch.
