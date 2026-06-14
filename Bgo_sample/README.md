# Bgo_sample

Status: `PASS`.

This package is a current-v3p5 BGO equal-attenuation geometry sample for TES_511_Balloon. The Step01 geometry/control closure is complete, a small all-particle Step02 prompt/buildup smoke transport has been run, an activation-probe delayed-source/transport smoke has been run, and a low-statistics `1of10` exact-position day-15 delayed-source/transport closure has passed. These runs prove BGO geometry, source-card connectivity, and low-stat exact-position delayed-transport connectivity; they are still not a BGO background-rate or sensitivity result.

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
| Activation-probe RPIP PointSource blocks | 30 |
| Delayed-source/transport smoke | PASS_BGO_SAMPLE_DELAYED_TRANSPORT_SMOKE |
| Delayed smoke SE/ID/TE | 200/200/5.664515 s |
| Step02 `1of10` instant/buildup production | 11/11 + 11/11 jobs, 1,190,129 generated per mode |
| `1of10` fixed day-15 activity | 24.791139 Bq |
| `1of10` exact-position PointSource blocks | 568 |
| `1of10` exact-position delayed transport | PASS_BGO_SAMPLE_1OF10_EXACTPOS_DELAYED_TRANSPORT |
| `1of10` delayed SE/ID/TE | 100000/100000/3730.929734 s |

## Files

- `Bgo_sample.geo`
- `Bgo_sample.det`
- `Bgo_sample.geo.setup`
- `bounds.json`
- `mass_budget.json` / `mass_budget.csv`
- `attenuation_verification.json` / `attenuation_verification.csv`
- `cosima_overlap.log`
- `step02_smoke_summary.json` / `STEP02_SMOKE.md`
- `delayed_smoke_summary.json` / `DELAYED_SMOKE.md`
- `step02_1of10_exactpos_summary.json` / `STEP02_1OF10_EXACTPOS.md`

## Boundary

- Inner detector-head geometry and side-entry pointing are inherited from the current v3p5 center-finger bounds.
- BGO thicknesses are recomputed against the current v3p5 CsI side/bottom/top thicknesses, not copied from the older `new_geo_re_2` branch.
- The active package and outer Al shell follow the new BGO active-envelope by preserving the original radial and z offsets.
- Step02 smoke has run all eight source-card particle classes (`alpha, eminus, eplus, gamma, muminus, muplus, n, p`) in both prompt and activation-build-up modes at 596 generated particles per mode.
- The delayed-source smoke is built from the p,n activation probe at 50k gamma-equivalent statistics. It uses 30 true RPIP positions, 22 volume-isotope keys, 30 exact-position `PointSource` blocks, and 200 delayed-transport triggers. Its fluxes are DAT-count/probe-time smoke proxies, not day-15 BGO activities.
- The `1of10` exact-position closure uses low-stat prompt and buildup production, a day-15 ground-state-fixed inventory, 568 true-RPIP `PointSource` blocks, and 100000 delayed-transport triggers. Its fixed activity is conserved to `4.32448e-09 Bq`.
- Full production-statistics Step02, full-stat production day-15 delayed-source/rate transport, Step05 veto/time-axis response, Step06--Step08 significance propagation, and detector-coupled Step09 response remain `NOT_RUN` for this sample.
