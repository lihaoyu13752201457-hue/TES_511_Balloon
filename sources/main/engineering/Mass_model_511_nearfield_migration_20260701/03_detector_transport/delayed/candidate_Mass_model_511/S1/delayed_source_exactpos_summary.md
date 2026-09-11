# Mass_model_511_candidate_Mass_model_511_S1_smoke Exact-Position Delayed Source

Status: `PASS_MASS_MODEL_511_CANDIDATE_MASS_MODEL_511_S1_SMOKE_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_S1_smoke/activation_decay_day15_groundstate_fixed_exactpos_S1.source`
- manifest: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_S1_smoke/candidate_Mass_model_511_S1_exactpos_delayed_source_manifest.json`
- weighted table: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_S1_smoke/exactpos_weighted_rpip_table_S1.csv`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `2521022` / `2521022`
- buildup generated: `2521022` / `2521022`
- fixed day-15 activity: `135.3105 Bq`
- fixed source blocks: `5332`
- RPIP lines/keys: `38773` / `872`
- eligible RPIP rows: `36835`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.00270621 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `5.86112e-08 Bq`
- W element activity: `1.0077418 Bq`
- W/collimator-volume activity: `2.4994462 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_candidate_Mass_model_511_S1_smoke/DelayedDecayMassModel511CandidateS1.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `7371.163696` s

Boundary:
- Mass_model_511_candidate_Mass_model_511_S1_smoke exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
