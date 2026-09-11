# Mass_model_511 Smoke Closure Conclusion

generated_at_utc: `2026-07-01T16:20:10Z`
status: `PASS_SMOKE_MATRIX_CLOSURE`

## Conclusion

The Mass_model_511 package is closed at the smoke-matrix detector-response level: baseline and candidate prompt/buildup, delayed S1, and focused-signal smoke products were propagated through the Step05 detector-response selections.

This is not a full-stat or manuscript-release closure. The conclusion is restricted to the smoke matrix and a Step08-style sensitivity proxy; publication claims still require the full-stat campaign and downstream mission-axis regeneration.

## Key W2 Rows

| quantity | baseline | candidate | rel delta | 95% CI / note |
| --- | ---: | ---: | ---: | --- |
| prompt instant final W2 | 0.0203834 cps | 0.0271495 cps | 0.3319 | [-1.396, 2.059] |
| prompt buildup final W2 | 0.0203834 cps | 0.0271495 cps | 0.3319 | [-1.396, 2.059] |
| delayed S1 final W2 | 0.0010787 cps | 0.00366292 cps | 2.396 | [1.004, 3.787] |
| total instant+S1 final W2 | 0.0214621 cps | 0.0308124 cps | 0.4357 | [-1.207, 2.078] |
| total buildup+S1 final W2 | 0.0214621 cps | 0.0308124 cps | 0.4357 | [-1.207, 2.078] |
| signal final W2 acceptance | 0.80064 | 0.798166 | -0.003089 | [-0.01914, 0.01296] |
| sensitivity proxy instant+S1 | 5.46514 | 4.54706 | -0.168 | smoke proxy |

## Scope And Boundary

- Geometry/source authority was not edited during closure.
- Old `engineering/nearfield_mass_impact_20260625/` outputs were not overwritten.
- Active veto threshold: `50 keV`; side-entry Compton/FoV policy: `keep` rejects.
- Quantitative delayed row uses `S1` (`1,000,000` delayed triggers in the smoke matrix).
- Full-stat/background publication closure remains `NOT_RUN` in this package.

## Artifacts

- JSON: `engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/mass_model_511_smoke_closure.json`
- prompt comparison CSV: `engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/prompt_rate_comparison.csv`
- delayed comparison CSV: `engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/delayed_rate_comparison.csv`
- signal comparison CSV: `engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/signal_acceptance_comparison.csv`
- key metrics CSV: `engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/combined_key_metrics.csv`
