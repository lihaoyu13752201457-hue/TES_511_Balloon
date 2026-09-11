# SE3 Plan-1 common response

Status: `PASS__SE3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE`

Only fresh SE3 transport is used. S3d-O8 appears only as the frozen corrected-M05 background small-table comparison; no S3d signal is required or opened.

| Quantity | Value |
|---|---:|
| SE3 prompt W2 (cps) | 0 |
| SE3 delayed W2 (cps) | 0.0601133621 |
| SE3 total W2 (cps) | 0.0601133621 |
| SE3 full-envelope W2 selected rays | 21657 / 37194 |
| SE3 full-envelope W2 Aeff (cm2) | 11.69478 |
| Delayed RUN_83334 catalogs opened | 7 |
| Delayed SKIP_ZERO_A15 structural zero cells | 1 |

A SKIP_ZERO_A15 family contributes an exact central zero through an in-memory structural catalog. No nonexistent stage03 pickle or SIM is opened; its finite activation upper and separate holdout provenance are retained in delayed_zero_A15_provenance.csv.

The signal diagnostic table retains every zero-based frozen ray ID, first recorded interaction evidence, BPE/plastic/BGO deposits, response decisions, and the final failure category. First-interaction volume is resolved by a same-time primary CC-hit when available; zero-deposit interactions remain explicitly unresolved rather than guessed.
