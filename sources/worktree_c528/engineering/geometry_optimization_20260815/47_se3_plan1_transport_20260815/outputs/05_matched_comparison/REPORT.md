# S3d-O8 versus SE3 matched day-15 comparison

Status: `PASS__SE3_PLAN1_DAY15_BACKGROUND_COMPARISON_AND_SE3_ONLY_FULL_ENVELOPE_SIGNAL`

| W2 measured after explicit veto + Step05 | S3d-O8 | SE3 | SE3/S3d |
|---|---:|---:|---:|
| prompt (cps) | 0.033842928 | 0 | 0.0 |
| delayed day15 (cps) | 0.054479752 | 0.060113362 | 1.1034074055201029 |
| total background (cps) | 0.08832268 | 0.060113362 | 0.6806107085371749 |
| full-envelope selected Aeff (cm²) | unavailable by user scope | 11.69478 | UNAVAILABLE_BY_USER_SCOPE |

S3d-O8 background and activation use only strictly filtered 104d frozen small tables. Fresh signal transport is SE3-only. No fresh S3d receipt is required. The historical post-Be S3d signal is not substituted for the missing fair full-envelope denominator.

Zero survivors retain two-sided Garwood bounds and a one-sided upper-limit flag. Central ratios are never treated as promotion authority when either side has zero or low Monte Carlo support. Mission folding and F3 remain stage06 work.
A fresh SKIP_ZERO_A15 family retains an exact central zero without an invented isotope row. Its finite activation upper and holdout-separation provenance remain machine-readable in family_comparison.csv and summary.json for the conservative stage06 proxy.
