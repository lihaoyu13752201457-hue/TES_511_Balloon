# Mass_model_511 Geometry Gate

generated_at_utc: `2026-07-07T15:02:28.172269+00:00`
status: `GEOMETRY_PASS`

| Check | Status | Evidence |
| --- | --- | --- |
| Candidate setup exists/includes resolve | `PASS` | `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup` |
| Cosima overlap | `PASS` | `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/Mass_model_511_stage_diam_300_300_300_350_350_400_overlap_after_support_parent_fix.log` |
| Final geometry review | `PASS` | `outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701/MASS_MODEL_511_STAGE_DIAM_300_300_300_350_350_400_FINAL_REVIEW.md` |
| Source cards migrated locally | `PASS` | `engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511/source_migration_manifest.json` |

Notes:
- This gate replaces the old NF2 detector-nearfield candidate with the latest Mass_model_511 detector geometry.
- The passive side-wall W/Pb liner caveat from the latest final review is preserved; this migration does not silently resolve it.
- This file is not a transport-rate or no-effect claim.
