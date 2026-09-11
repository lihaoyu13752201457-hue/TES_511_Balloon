# Corrected-keV 81-bin forward analytic mission scenario

Status: `PASS__M05_CORRECTED_81BIN_FORWARD_ANALYTIC_SCENARIO__PROMOTION_DEFERRED`

Stage-02 production rates are advanced under the scenario assumption of zero inventory at mission day 0 using an exact piecewise-linear-source decay convolution. Pre-flight/ground activation is not included, and no day-15 activity is forced to match the constant-environment inventory.

| Geometry | Z20 central | Z20 conditional proxy | T3 d | T5 d | F3(20d) | F3 proxy |
|---|---:|---:|---:|---:|---:|---:|
| Mass_model_511 | 2.70939 | 1.33431 | >20 (sqrt-time extrap. 24.52) | >20 (sqrt-time extrap. 68.11) | 0.000110726 | 0.000224835 |
| S3d_O8 | 4.33291 | 1.46337 | 9.36768 | >20 (sqrt-time extrap. 26.63) | 6.92375e-05 | 0.000205006 |

## Day-15 node versus constant-environment reference

| Geometry | Static reference B (cps) | Trajectory-node B (cps) | Ratio |
|---|---:|---:|---:|
| Mass_model_511 | 0.231273 | 0.225151 | 0.97353 |
| S3d_O8 | 0.0883227 | 0.0862124 | 0.976107 |

The corrected broadband gamma already includes the annihilation bump; no atmospheric mono-511 background is added. The conditional endpoint is a componentwise mixture proxy, not a joint 95% interval.

The PARMA executable returns W=114.6 for the retained date while the corrected source contract records W=118.3. Only ratios to the driver's 34N,100E,38 km reference are used; the within-family energy spectrum, angular distribution, detector response, and activation yield remain fixed scenario assumptions.
