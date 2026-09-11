# Corrected-keV M05 activation inventory

Status: `PASS__M05_CORRECTED_ACTIVATION_INVENTORY_READY__DELAYED_TRANSPORT_INCOMPLETE`

The retained corrected BUILDUP catalog contributes 446 jobs and
6,092,936 primary histories.  Its 97,247 production records
are normalized as `sum(RP)/sum(TT)` inside each geometry x incident-family
cell; all zero-RP DAT live times remain in the denominator.

| Geometry | Known day-15 activity | Transported ground-state activity | Known holdout | Unknown states |
|---|---:|---:|---:|---:|
| Mass_model_511 | 482.117936 Bq | 482.117936 Bq | 0 Bq | 3 |
| S3d-O8 | 1404.23088 Bq | 1404.13107 Bq | 0.099809269 Bq | 2 |

All 97,247 retained `CC IP RP` records match a
geometry/family/volume/ZA/state key.  Fifteen geometry-family cells already
have 50,000-point exact-position source cards; Mass_model_511/muplus has no
transportable positive ground-state activity and is retained as a zero source
cell.

This stage reports inventory Bq and source readiness only.  It does not turn
inventory Bq into a TES delayed-background rate, and it does not support a
geometry ranking, mission sensitivity, or paper conclusion before delayed
transport and the common detector response are complete.
