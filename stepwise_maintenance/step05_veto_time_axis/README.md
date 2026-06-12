# Step05 Veto Time-Axis Audit

Status: `COMPLETE` for the current DEMO2 mainline.

This step places science, prompt, and delayed streams on one Poisson time axis, groups event instances with a `1.0e-6 s` coincidence window, applies the active-shield veto, and then applies the Compton/FoV veto to TES hits in the surviving candidate group.

## Current Inputs

- Prompt: `runs/step02_instant_equiv2602_aligned/*.sim.gz`.
- Delayed: `runs/step02_delayed_transport_equiv2602_aligned/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`.
- Science: `runs/science_511_onaxis_source/Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz`.
- Summary authority: `outputs/reports/day15_complete_report/complete_day15_summary.json`.

The `cmfix` token in the science filename is only the current cm-scaled source-card convention.

Science 511 run summary:

- triggers/stored events: `100000 / 100000`;
- event-summed `480-550 keV`: `86916`;
- event-summed `506-516 keV`: `86210`;
- Cosima observation time: `99869.3 s`.

## Veto Logic

- Candidate grouping: adjacent event instances within `COINCIDENCE_WINDOW_S = 1.0e-6`.
- Active shield: summed veto-channel energy in the candidate must be `< 50 keV`.
- Current active veto authority: `CsI_Active_Shield`.
- Compatibility names counted as veto volumes: `BGO`, `ACTIVE_SHIELD`, `CEBR3`.
- Compton/FoV veto: one TES hit is kept; two-hit events test both orders; three to six hits use CSR best sequence; ambiguous rejects are retained with `reject_policy = keep`.
- The Compton/FoV reference remains the Be-window disk for this baseline; do not tighten to a focused spot until the PSF/optics bridge is promoted into the science analysis.

## Current DEMO2 Timeline Result

Baseline settings:

- `prompt_time_s = 541.3815137522625`;
- `delayed_time_s = 1584.61`;
- `obs_time_s = 1584.61`;
- `science_flux_ph_cm2_s = 1.0e-4`;
- `science_injection_rate_s^-1 = 0.0037609867166169403`;
- `bgo_threshold_keV = 50.0`;
- `reject_policy = keep`;
- `rng_seed = 260511`.

Catalog:

- events kept: `2824095`;
- pixel hits kept: `342484`;
- prompt catalog events: `2296769`;
- delayed catalog events: `444640`;
- science catalog events: `82686`.

Poisson draw:

- prompt drawn: `1199827`;
- delayed drawn: `444277`;
- science drawn: `3`;
- total event instances: `1644107`;
- candidates with TES: `128636`;
- mixed-stream candidates: `695`.

Broad `480-550 keV` timeline result:

- no veto: `6115` counts, `3.8589936956 cps`;
- active-shield pass: `5304` counts, `3.3471958400 cps`;
- final active-shield + Compton/FoV: `3724` counts, `2.3501050732 cps`.

Direct expectation cross-check:

- no veto: `3.8646574586 cps`;
- active-shield pass: `3.3708450985 cps`;
- final: `2.3682068117 cps`.

Direct final stream decomposition:

- prompt: `0.0535666610 cps`;
- delayed activation: `2.3122408668 cps`;
- science at `1e-4`: `0.0023992839 cps`.

## Generated Outputs

- `outputs/reports/day15_complete_report/complete_day15_summary.json`
- `outputs/reports/day15_complete_report/cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf`
- `outputs/reports/day15_complete_report/audit.md`
- `outputs/reports/day15_complete_report/timeline_spectrum_480_550_rates.csv`
- `outputs/reports/day15_complete_report/work/event_catalog.pkl`

## v3p5 Center-Finger L1 Response

Current v3p5 output:

- report: `outputs_v3p5_centerfinger_l1/step05_v3p5_centerfinger_l1_response_summary.md`
- summary JSON: `outputs_v3p5_centerfinger_l1/step05_v3p5_centerfinger_l1_response_summary.json`
- rates CSV: `outputs_v3p5_centerfinger_l1/step05_v3p5_centerfinger_l1_rates.csv`

Status: `PASS_V3P5_STEP05_SIDE_ENTRY_COMPTON_TIME_AXIS_L1`.

Scope: v3p5 side-entry Compton/FoV migrated to the tilted Be disk, direct
expectation, and one common Poisson time-axis draw for the v3p5 1/10 prompt,
day-15 delayed, and full focused EventList transport. This remains a
1/10-statistics checkpoint, not final paper statistics. The direct expectation
now also carries a physical reference-flux scale from f10m A1
`A_eff(511)=20.08476 cm2` and inherited `T_atm=0.7390423888027`, giving a
reference injection-plane rate of `0.00148435 s^-1` at
`1e-4 ph cm^-2 s^-1`.

Key direct rates:

- broad `480-550 keV`: prompt side-Compton/FoV pass `0 cps`, delayed pass
  `0.0727785 cps`, focused-signal pass `0.797172` per unit EventList injection
  rate; physical reference signal `0.00118328 cps`, direct `Z20d=5.76578`.
- W2 `510.58-511.42 keV`: prompt side-Compton/FoV pass `0 cps`, delayed pass
  `0.0157833 cps`, focused-signal pass `0.795747` per unit EventList injection
  rate; physical reference signal `0.00118117 cps`, direct `Z20d=12.359`.

Common Poisson time-axis draw (`obs_time=1140.447373 s`, unit EventList
injection-rate signal normalization):

- broad `480-550 keV`: raw `1.32580 cps`, active-veto pass `0.896140 cps`,
  side-Compton/FoV pass `0.867204 cps`.
- W2 `510.58-511.42 keV`: raw `1.01451 cps`, active-veto pass `0.818977 cps`,
  side-Compton/FoV pass `0.800563 cps`.

Pending before paper-facing v3p5 statistics: increase statistics beyond this
1/10 checkpoint, replace the axisymmetric delayed-source compression with
exact-position sampling, and add selection-consistent spatial/profile
likelihood products.

## Rebuild

The full rebuild parses large SIM products.  For documentation/PDF refresh from current summary and figures:

```bash
python3 code/tools/make_complete_day15_report_ADR.py --refresh-from-summary
```

The v3p5 L1 response is rebuilt separately:

```bash
python3 code/tools/build_v3p5_centerfinger_step05_l1_response.py --workers 8
```
