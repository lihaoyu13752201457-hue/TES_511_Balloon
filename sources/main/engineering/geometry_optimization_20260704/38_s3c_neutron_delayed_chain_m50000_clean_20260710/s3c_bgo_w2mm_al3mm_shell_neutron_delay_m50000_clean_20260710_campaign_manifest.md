# S3C Neutron-Only Delayed Chain M50000

- generated_at_utc: `2026-07-09T20:27:09Z`
- status: `PASS_S3C_NEUTRON_DELAYED_CHAIN_M50000_TRANSPORT`
- geometry: `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- selected transport particle: `n`
- M point-source blocks: `50000`
- seed: `260613`

| Step | Status | Evidence |
| --- | --- | --- |
| source cards | `PASS_S3C_NEUTRON_DELAY_SOURCE_CARDS` | `engineering/geometry_optimization_20260704/38_s3c_neutron_delayed_chain_m50000_clean_20260710/source_cards/source_migration_manifest.json` |
| assembled instant audit | `PASS_S3C_NEUTRON_DELAY_ASSEMBLED_INSTANT` | `runs/geometry_optimization_20260704/step02_instant_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/assembled_instant_manifest.json` |
| neutron buildup | `PASS_TRANSPORT` | `runs/geometry_optimization_20260704/step02_buildup_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/run_summary.json` |
| raw source | `True` | `runs/geometry_optimization_20260704/step02_decay_source_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/activation_decay_day15.source` |
| ground-state fixed source | `PASS` | `runs/geometry_optimization_20260704/step02_delay_fix_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/normalization_audit_groundstate_fix.json` |
| exactpos M50000 source | `PASS_S3C_BGO_W2MM_AL3MM_SHELL_NEUTRON_DELAY_M50000_CLEAN_20260710_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT` | `engineering/geometry_optimization_20260704/38_s3c_neutron_delayed_chain_m50000_clean_20260710/delayed_source/delayed_source_exactpos_summary.json` |
| delayed transport | `PASS_S3C_BGO_W2MM_AL3MM_SHELL_NEUTRON_DELAY_M50000_CLEAN_20260710_EXACTPOS_M50000_S260613_EXACTPOS_DELAYED_TRANSPORT` | `runs/geometry_optimization_20260704/step02_delayed_transport_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/DelayedDecayS3cBgoW2mmAl3mmShellNeutronDelayM50000.inc1.id1.sim.gz` |

Boundary: this is not yet a detector-rate or full-chain delayed-background claim.
