# S3 CsI Barrel Delayed Chain M50000

- generated_at_utc: `2026-07-09T09:27:02Z`
- status: `PASS_S3_DELAYED_CHAIN_M50000_TRANSPORT`
- geometry: `engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- statistics_reference: `Mass_model_511 fullstat_v1 delayed chain`
- M point-source blocks: `50000`
- seed: `260613`

| Step | Status | Evidence |
| --- | --- | --- |
| source cards | `PASS_S3_SOURCE_COPY_PREPARED` | `engineering/geometry_optimization_20260704/23_s3_delayed_chain_m50000_20260709/source_cards/source_migration_manifest.json` |
| assembled instant audit | `PASS_S3_ASSEMBLED_INSTANT_AUDIT` | `runs/geometry_optimization_20260704/step02_instant_s3_csi_barrel_fullstat_v1_20260709/assembled_instant_manifest.json` |
| buildup | `PASS_TRANSPORT` | `runs/geometry_optimization_20260704/step02_buildup_s3_csi_barrel_fullstat_v1_20260709/run_summary.json` |
| raw source | `True` | `runs/geometry_optimization_20260704/step02_decay_source_s3_csi_barrel_fullstat_v1_20260709/activation_decay_day15.source` |
| ground-state fixed source | `PASS` | `runs/geometry_optimization_20260704/step02_delay_fix_s3_csi_barrel_fullstat_v1_20260709/normalization_audit_groundstate_fix.json` |
| exactpos M50000 source | `PASS_S3_CSI_BARREL_FULLSTAT_V1_20260709_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT` | `engineering/geometry_optimization_20260704/23_s3_delayed_chain_m50000_20260709/delayed_source/delayed_source_exactpos_summary.json` |
| delayed transport | `PASS_S3_CSI_BARREL_FULLSTAT_V1_20260709_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT` | `runs/geometry_optimization_20260704/step02_delayed_transport_s3_csi_barrel_fullstat_v1_20260709/DelayedDecayS3CsiBarrelFullstatV1M50000.inc1.id1.sim.gz` |

Boundary: this is not yet a detector delayed-rate claim.
