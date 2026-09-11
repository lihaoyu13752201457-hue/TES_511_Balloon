# Corrected-keV 81-bin forward analytic mission scenario

Status: `PASS__M05_CORRECTED_81BIN_FORWARD_ANALYTIC_SCENARIO__PROMOTION_DEFERRED`

Stage-02 production rates are advanced from zero inventory using the energy-integrated PARMA family ratios. No day-15 activity is forced to match the constant-environment inventory.

| Geometry | Z20 central | Z20 conditional proxy | T3 d | T5 d | F3(20d) | F3 proxy |
|---|---:|---:|---:|---:|---:|---:|
| Mass_model_511 | 2.70941 | 1.33431 | >20 (sqrt-time extrap. 24.52) | >20 (sqrt-time extrap. 68.11) | 0.000110725 | 0.000224835 |
| S3d_O8 | 4.33297 | 1.46338 | 9.35578 | >20 (sqrt-time extrap. 26.63) | 6.92366e-05 | 0.000205005 |

## Day-15 node versus constant-environment reference

| Geometry | Static reference B (cps) | Trajectory-node B (cps) | Ratio |
|---|---:|---:|---:|
| Mass_model_511 | 0.231273 | 0.225651 | 0.975693 |
| S3d_O8 | 0.0883227 | 0.0865359 | 0.97977 |

The corrected broadband gamma already includes the annihilation bump; no atmospheric mono-511 background is added. The conditional endpoint is a componentwise mixture proxy, not a joint 95% interval.

The PARMA executable returns W=114.6 for the retained date while the corrected source contract records W=118.3. Only ratios to the driver's 34N,100E,38 km reference are used; this and the unchanged within-family spectral response remain scenario systematics.
