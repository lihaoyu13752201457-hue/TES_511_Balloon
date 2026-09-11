# S3d-O8 LG1 local-guard screening package

Status: `PASS_LG1_FIRST_PASS_SMOKE__NO_RATE_OR_PROMOTION_AUTHORITY`

This isolated package implements the preregistered LG1 geometry hypothesis as
a strict additive delta from the retained S3d-O8 authority in
`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/`.
It never modifies that authority.

## Candidate A

LG1 adds an open negative-X optical-axis BGO well inside the retained Nb
magnetic cylinder:

- 5 mm radial side sleeve: `x=-3.55..3.10 cm`, `r=3.10..3.60 cm`;
- 3 mm back annulus: `x=3.70..4.00 cm`, `r=1.85..3.60 cm`;
- both are centered on `(y,z)=(0,-5.2 cm)` and rotate the PCON axis onto X;
- no front cap is added, so the focused-signal entrance remains open.

The analytic BGO mass is approximately `0.5631 kg`. This excludes optical
wrapping, support, readout, cabling, and any relief machining.

## Build and static validation

```bash
python3 engineering/particle_source_unit_repair_20260811/s3d_o8_lg1_screening_20260813/code/build_lg1_geometry.py
python3 engineering/particle_source_unit_repair_20260811/s3d_o8_lg1_screening_20260813/code/validate_lg1_geometry.py
```

The builder copies the retained O8 GEO, DET, Intro, and Materials bytes into
this package, appends exactly two BGO volume blocks and two scorer blocks, and
generates a uniquely named setup using absolute includes. It also creates one
overlap-check source for a later explicit Cosima gate; the builder does not run
that source.

The validator independently requires:

- exact retained GEO/DET bytes after removing the LG1 suffix patches;
- exact copied Intro and Materials bytes;
- no duplicate declarations and exactly two new volumes/scorers;
- analytic mass and declared geometric clearance gates;
- one unique setup with absolute GEO/DET paths;
- active-veto contract equal to the retained six exact volumes plus LG1 two;
- no source file in the static `geometry/` directory other than its
  overlap-check source (the separately frozen smoke cards live under
  `smoke_inputs/sources/`).

Static validation authority:
`data/lg1_geometry_validation.json`. Its PASS status does not imply a Cosima
overlap/load or transport PASS.

## Static-package claim boundary

The builder and static validator alone establish geometry screening only; their
PASS does not establish overlap cleanliness, focused-signal throughput, prompt
rejection, activation/delayed background reduction, detector threshold
performance, accidental-veto rate, thermal feasibility, magnetic
compatibility, mass qualification, or the `3E-5` mission target.  The later
first-pass smoke below was launched under its own frozen plan and remains a
mechanism diagnostic, not rate or promotion authority.  No BUILDUP, inventory,
delayed, common-response, or mission simulation was run in this package.

Required later gates, if separately authorized, are Cosima overlap/load,
matched focused signal, corrected-keV prompt, all-family activation lineage,
delayed response, accidental veto, and mission-time closure.

## 2026-08-14 first-pass result

The separately frozen 16-job A/B smoke was launched after static validation.
All 8192 events passed gzip/header/geometry/seed/ID/trailer validation; the
aggregate SIM size is 18,068,437 bytes.  The physical diagnostic is
`LG1_SMOKE_DIAGNOSTIC.md` with machine-readable detail in
`data/lg1_smoke_diagnostic.json`.

LG1 intercepts all 5 candidate raw-W2/original-six-pass events appearing in
the three 4148 keV Nb/MuMetal directional replicas at 80 keV, but intercepts
0/2 in the 5769 keV mixing-chamber-Cu replicas.  At 50 keV, its broader
conditional hit fraction among original-six-pass events is 94/301 for the
4148-keV cassette but only 6/118 for the 5769-keV cassette.  Focused
first-1000 raw-W2 is
826 for the baseline and 817 for LG1, and none of the 817 candidate raw-W2
events coincides with LG1 at 1--80 keV.  These are finite-tape diagnostics,
not sky rates or a promotion result.

The source diagnosis, target budget, literature comparison, and ranked next
directions are in `REPORT.md` and `data/optimization_summary.json`.
