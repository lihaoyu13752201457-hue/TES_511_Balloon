# Mass_model_511_candidate_Mass_model_511_fullstat_v1 Exact-Position Delayed Source

Status: `PASS_MASS_MODEL_511_CANDIDATE_MASS_MODEL_511_FULLSTAT_V1_EXACTPOS_DELAYED_TRANSPORT`.

- source: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1/activation_decay_day15_groundstate_fixed_exactpos.source`
- manifest: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1/candidate_Mass_model_511_fullstat_v1_exactpos_delayed_source_manifest.json`
- weighted table: `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1/exactpos_weighted_rpip_table.csv`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- instant generated: `25210216` / `25210216`
- buildup generated: `25210216` / `25210216`
- fixed day-15 activity: `141.83344 Bq`
- fixed source blocks: `14797`
- RPIP lines/keys: `389344` / `2668`
- eligible RPIP rows: `380872`
- PointSource blocks: `50000`
- seed: `260613`
- flux per PointSource: `0.0028366688 Bq`
- flux conservation abs delta: `0 Bq`
- source text flux abs delta: `6.30881e-08 Bq`
- W element activity: `1.1056933 Bq`
- W/collimator-volume activity: `2.6246995 Bq`
- sampling audit: `PASS`
- delayed sim: `runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_candidate_Mass_model_511_fullstat_v1/DelayedDecayMassModel511CandidateFullstatV1.inc1.id1.sim.gz`
- SE/ID/TS: `1000000/1000000/1`
- TE: `7027.052893` s

Boundary:
- Mass_model_511_candidate_Mass_model_511_fullstat_v1 exact-position delayed source/transport uses matched fix5 buildup production.
- Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.
