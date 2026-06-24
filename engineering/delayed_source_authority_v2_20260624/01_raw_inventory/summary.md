# WP01 Raw Inventory Ledger

status: `PASS`
dat files: `68`
raw RP rows: `5401`
aggregated full keys: `2073`
direct day-15 activity: `86.99984206699579647254965889` Bq

## Formula
`production_rate = sum(raw RP counts for tag/key) / sum(TT for production_tag)`

## Classification Counts
- `EMITTED_CANDIDATE`: `2036`
- `STABLE`: `37`

## Findings
- Parsed 68 .dat files and 5401 raw RP rows.
- Direct day-15 activity sum: 86.99984206699579647254965889 Bq.
- Classification counts: {'EMITTED_CANDIDATE': 2036, 'STABLE': 37}.
- 5 duplicate NUBASE excitation-state rows exist globally but none match raw .dat keys.
