# Exact-position delayed-source M sampling audit

## Conclusion

- Status: `PASS_M_SAMPLING_AUDIT`.
- Scope: validates source-card M sampling and existing transport-backed M/seed convergence; it does not run new Cosima transport.
- Exact-position table rows: 253,770; activity: 85.6366958653 Bq.
- M/seed transport-backed cases: 4; W2 background relative range: 0.011191; Z20d relative range: 0.005508.

## Source-card cases

| case | M | seed | flux rel. delta | match frac. | species TV | family TV | category TV | max coord mean sigma | max coord hist TV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M5000_seed260613 | 5000 | 260613 | 0.000e+00 | 1.000000 | 0.0173 | 0.0021 | 0.0043 | 0.501 | 0.0249 |
| M5000_seed260614 | 5000 | 260614 | 0.000e+00 | 1.000000 | 0.0151 | 0.0031 | 0.0044 | 1.176 | 0.0242 |
| M20000_seed260613 | 20000 | 260613 | 0.000e+00 | 1.000000 | 0.0096 | 0.0034 | 0.0033 | 0.931 | 0.0110 |
| M50000_seed260613 | 50000 | 260613 | 0.000e+00 | 1.000000 | 0.0054 | 0.0013 | 0.0009 | 1.343 | 0.0081 |

## Missed nuclides

| case | missed ZA count | missed activity (Bq) | activity fraction | expected missed draws | dominant missed family | dominant missed category |
|---|---:|---:|---:|---:|---|---|
| M5000_seed260613 | 147 | 0.391486 | 4.571e-03 | 22.857 | n | CsI active shield |
| M5000_seed260614 | 158 | 0.457679 | 5.344e-03 | 26.722 | n | CsI active shield |
| M20000_seed260613 | 107 | 0.126609 | 1.478e-03 | 29.569 | n | CsI active shield |
| M50000_seed260613 | 76 | 0.0574501 | 6.709e-04 | 33.543 | n | CsI active shield |

Detailed missed-nuclide rows are written to `outputs/reports/m_sampling_audit_20260616/m_sampling_audit_missed_nuclides.csv`.

## Transport convergence

- Delayed W2 rate range: 0.0033823415--0.0040855584 s^-1.
- Total W2 background range: 0.062465066--0.063168283 s^-1.
- Z20d range: 6.1214147--6.1552222.

## Interpretation

- M=5000 is not a full enumeration of all rare RPIP rows/species, and should not be used to claim convergence of every rare isotope or spatial subpopulation.
- For the current hard-window rate and 20-day sensitivity, the activity is exactly conserved in the manifest and the existing M/seed transport sweep keeps the total W2 background and Z20d within the acceptance criteria recorded in the convergence summary.
