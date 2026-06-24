# BGO P2 Engineering Completion Summary

Date: 2026-06-24

Scope: BGO same-envelope engineering run under `engineering/background_validation_20260624/06_bgo_matched_runs/p2`.  This is a matched-material engineering check, not a manuscript-authority replacement without a separate completion audit.

## Completed Transports

- Prompt instant P2: 68/68 jobs PASS, BGO same-envelope geometry headers checked.
- Buildup P2: 68/68 jobs PASS, BGO same-envelope geometry headers checked.
- Delayed exact-position source: 50,000 PointSources, 1,000,000 triggers, fixed total activity `29.185189557290116 Bq`.
- Delayed transport: PASS, `SE=1000000`, `ID=1000000`, `TE=32318.644709 s`, gzip OK, SIM geometry points to BGO same-envelope.
- Focused signal replay: PASS, `SE=37194`, `ID=37194`, BGO same-envelope SIM geometry, source EventList inherited from current f10m A1 v3p5 Step09 bridge.
- Step05 engineering ingest: PASS with prompt + delayed + focused signal, active veto `<50 keV`, coincidence window `1 us`.

## Key Artifacts

- Step05 summary: `p2/step05_ingest_exactpos_with_focus/bgo_engineering_step05_ingest_summary.json`
- Step05 rates: `p2/step05_ingest_exactpos_with_focus/bgo_engineering_step05_ingest_rates.csv`
- Delayed transport summary: `p2/delay_fix/bgo_p2_exactpos_m50000_s260613_delayed_source_manifest.json`
- Delayed SIM: `p2/delayed_transport_exactpos/DelayedDecayBgoP2ExactposM50000S260613.inc1.id1.sim.gz`
- Focused signal summary: `p2/step09_focus/step09_focus_summary.json`
- Focused signal SIM: `p2/step09_focus/run/Opticsim_laue_f10m_a1_bgo_same_envelope_p2_focus.inc1.id1.sim.gz`

## W2 Final Rates

Window: `510.58-511.42 keV`, final `side_compton_fov_pass`, active veto `<50 keV`.

| Case | Prompt cps | Delayed cps | Background cps | Signal cps at 1e-4 ph cm^-2 s^-1 | Z20d direct | F3 20d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BGO P2 engineering | `0.0339335772` | `0.00355831753` | `0.0374918947` | `0.00118056701` | `8.01482079` | `3.74306560e-05` |
| fix5 current authority | `0.0366410230` | `0.00257520349` | `0.0392162265` | `0.00118587481` | `7.87186814` | `3.81103944e-05` |

Interpretation: this BGO same-envelope engineering run does not show a large total-background improvement over fix5.  Prompt is slightly lower, delayed is higher, total W2 background is slightly lower, and signal keep is essentially unchanged.  With final background event counts of 158 for BGO and 84 for fix5, the total-background difference is well inside simple Poisson counting uncertainty.

## Boundary

- These outputs are engineering artifacts under `engineering/`, not promoted manuscript authority.
- No manuscript files were changed.
- Large SIM/cache products are intentionally left as workspace artifacts and should not be committed without an explicit storage policy.
