# Step02 v3p5 Center-Finger Low-Stat Closure

Status: `PASS_LOWSTAT10K_TRANSPORT_CLOSURE`.

Scope: this is an all-particle low-stat smoke closure for the tilted v3p5 simulation geometry. It is not the final 1/10-statistics or full-statistics physics result.

Geometry/source policy:
- geometry setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- geometry validation: `PROXY_PASS`
- far-field radius: `60.0 cm`
- side-window look elevation: `45 deg`
- detector core pixels: `2256`

Transport results:
- instant: `9/9` jobs passed, `11902` generated particles
- buildup: `9/9` jobs passed, `11902` generated particles
- delayed source: `24` blocks, `79.582637 Bq` raw activity
- ground-state fixed source: `24` blocks, `79.582556 Bq` fixed activity
- delayed transport: `TS=1000`, `SE=1000`, `ID=1000`, `TE=11.68 s`

Particle counts:

| particle | instant generated | buildup generated |
| --- | ---: | ---: |
| alpha | 24 | 24 |
| eminus | 415 | 415 |
| eplus | 244 | 244 |
| gamma | 10000 | 10000 |
| muminus | 10 | 10 |
| muplus | 12 | 12 |
| n | 963 | 963 |
| p | 234 | 234 |

Artifacts:
- summary JSON: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_lowstat10k/step02_v3p5_centerfinger_lowstat10k_summary.json`
- particle counts CSV: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_lowstat10k/step02_v3p5_centerfinger_lowstat10k_particle_counts.csv`
- source blocks CSV: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_lowstat10k/step02_v3p5_centerfinger_lowstat10k_source_blocks.csv`
- lightweight source snapshots: `stepwise_maintenance/step02_raw_background_simulation/source_snapshots_v3p5_centerfinger_lowstat10k`
- delayed transport SIM: `runs/step02_delayed_transport_v3p5_centerfinger_lowstat10k/DelayedDecayRPIPGroundStateFixed.inc2.id1.sim.gz`
- delayed transport log: `runs/step02_delayed_transport_v3p5_centerfinger_lowstat10k/cosima_delayed_transport_lowstat10k.log`

Known limitation: delayed-source generation still uses the existing axisymmetric `RadialProfileBeam` profile builder. For the tilted geometry, an exact-position source upgrade remains the next confidence step before paper-facing numbers.

