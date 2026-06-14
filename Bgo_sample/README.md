# Bgo_sample

Status: `PASS`.

This package is a current-v3p5 BGO equal-attenuation geometry sample for TES_511_Balloon. The Step01 geometry/control closure is complete, and a small all-particle Step02 prompt/buildup smoke transport has been run. It is still not a BGO background-rate or sensitivity result.

| quantity | value |
| --- | --- |
| Source CsI thickness side/bottom/top | {'side': 4.0, 'bottom': 5.999999999999998, 'top': 3.0} |
| BGO thickness side/bottom/top | {'side': 2.137, 'bottom': 3.287, 'top': 1.582} |
| BGO veto threshold | 70.0 keV |
| Attenuation max abs relative diff | 0.0731183 |
| BGO active mass | 45.0259 kg |
| Source CsI active mass | 62.8337 kg |
| Active mass ratio BGO/CsI | 0.716589 |
| Logical active segments | 20 |
| BGO proxy detectors at 70 keV | 24 |
| BGO proxy energy-resolution low anchors at 70 keV | 24 |
| Cosima overlap | PASS |
| Step02 prompt/buildup smoke | PASS_BGO_SAMPLE_STEP02_ALLPARTICLE_SMOKE_TRANSPORT |

## Files

- `Bgo_sample.geo`
- `Bgo_sample.det`
- `Bgo_sample.geo.setup`
- `bounds.json`
- `mass_budget.json` / `mass_budget.csv`
- `attenuation_verification.json` / `attenuation_verification.csv`
- `cosima_overlap.log`
- `step02_smoke_summary.json` / `STEP02_SMOKE.md`

## Boundary

- Inner detector-head geometry and side-entry pointing are inherited from the current v3p5 center-finger bounds.
- BGO thicknesses are recomputed against the current v3p5 CsI side/bottom/top thicknesses, not copied from the older `new_geo_re_2` branch.
- The active package and outer Al shell follow the new BGO active-envelope by preserving the original radial and z offsets.
- Step02 smoke has run all eight source-card particle classes (`alpha, eminus, eplus, gamma, muminus, muplus, n, p`) in both prompt and activation-build-up modes at 596 generated particles per mode.
- Full production-statistics Step02, delayed-source construction, delayed transport, Step05 veto/time-axis response, Step08 significance, and detector-coupled Step09 response remain `NOT_RUN` for this sample.
