# Superseded derived snapshots

This directory holds recoverable, small analysis snapshots replaced during
same-day review. Raw SIM/DAT files and transport receipts are never moved here.

- `04_common_response_pre_statfix_20260813/`: signal multiplicity/occupancy
  error columns used Poisson rather than fixed-trial binomial statistics, and
  70/80-keV threshold-scan rows were mixed into the nominal common cutflow.
- `06_mission_pre_occupancyfix_20260813/`: delayed full-band occupancy followed
  the W2-selected parent mixture instead of total family activity.
- `06_mission_pre_fluxsurface_label_20260813/`: numerically corrected mission
  fold before explicitly labeling the reference flux as top-of-atmosphere and
  joining the two retained time axes.
- `06_mission_day15_anchored_pre_forward_20260813/`: used a relative activity
  shape forced back to the constant-environment day-15 inventory. It was
  replaced by the zero-inventory forward fold from corrected production rates.
- `parma_scales_pre_reference_label_20260813.csv`: the first dE-integrated
  driver table called its denominator the corrected source environment even
  though the date-driven executable returns W=114.6 while the source contract
  records W=118.3. The replacement names it only as the PARMA reference.
- `06_mission_forward_pre_linearforcing_20260813/`: used the interval-average
  production rate in a constant-source decay solution and linearly interpolated
  Z for threshold crossing. It was replaced by exact piecewise-linear forcing
  and an interval solution of S(t)^2 = threshold^2 B(t).

Current products always live under `outputs/`.
