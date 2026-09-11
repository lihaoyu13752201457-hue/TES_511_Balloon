# Time-Axis Formula Smoke Audit

Status: `PASS_TIME_AXIS_FORMULA_SMOKE_AUDIT`.

This audit recomputes the Step06 analytic trajectory formula at the day-15 center point and at the two altitude extrema, then checks that the W511 time-dependent rates and Step08 cumulative result are reproduced from the CSV products.

## Probe Points

| day | altitude km | T_atm | prompt scale | delayed activity scale | max formula delta |
|---:|---:|---:|---:|---:|---:|
| 15.00 | 38.75 | 0.739042388803 | 1 | 1 | 0.000e+00 |
| 1.25 | 41.25 | 0.811094979198 | 0.965181809612 | 0.913070839359 | 0.000e+00 |
| 3.75 | 36.25 | 0.646122572391 | 1.05298763053 | 1.02178977033 | 0.000e+00 |

## Rate And Significance Closure

- Maximum relative delta when reconstructing W511 prompt, delayed, background, and signal rates from day-15 rates and time-dependent scales: `0.000e+00`.
- Step08 final Z20d delta between cumulative CSV and summary JSON: `0.000e+00`.
- Step08 final source/background count deltas: `0.000e+00` / `0.000e+00`.

## Delayed-Distribution Assumption

The current rate fold reuses the reference activation-production nuclide/volume/position distribution and lets the trajectory change only a scalar production driver before isotope-by-isotope half-life integration. This audit proves formula and bookkeeping closure for that model; it does not prove that activation-product distributions are physically invariant under a different altitude/latitude/longitude transport. If future center/extreme activation transports contradict the scalar-driver assumption, the manuscript fallback is to interpolate production vectors over the trajectory grid before solving the same ODE.
