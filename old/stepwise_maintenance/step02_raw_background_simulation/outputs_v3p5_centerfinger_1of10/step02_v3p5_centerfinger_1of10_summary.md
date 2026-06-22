# Step02 v3p5 Center-Finger 1/10-Statistics Closure

Status: `PASS_1OF10_TRANSPORT_CLOSURE`.

Scope: this is an all-particle 1/10-statistics closure for the tilted v3p5 simulation geometry. It is not the full-statistics physics result.

Geometry/source policy:
- geometry setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- geometry validation: `PROXY_PASS`
- far-field radius: `60.0 cm`
- side-window look elevation: `45 deg`
- detector core pixels: `2256`

Transport results:
- instant: `19/19` jobs passed, `1190129` generated particles
- buildup: `19/19` jobs passed, `1190129` generated particles
- delayed source: `787` blocks, `86.437919 Bq` raw activity
- ground-state fixed source: `786` blocks, `86.382997 Bq` fixed activity
- delayed transport: `TS=100000`, `SE=100000`, `ID=100000`, `TE=1140.45 s`

Particle counts:

| particle | instant generated | buildup generated |
| --- | ---: | ---: |
| alpha | 2393 | 2393 |
| eminus | 41462 | 41462 |
| eplus | 24373 | 24373 |
| gamma | 1000000 | 1000000 |
| muminus | 1035 | 1035 |
| muplus | 1161 | 1161 |
| n | 96307 | 96307 |
| p | 23398 | 23398 |

Artifacts:
- summary JSON: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_summary.json`
- particle counts CSV: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_particle_counts.csv`
- source blocks CSV: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_source_blocks.csv`
- lightweight source snapshots: `stepwise_maintenance/step02_raw_background_simulation/source_snapshots_v3p5_centerfinger_1of10`
- delayed transport SIM: `runs/step02_delayed_transport_v3p5_centerfinger_1of10/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- delayed transport log: `runs/step02_delayed_transport_v3p5_centerfinger_1of10/cosima_delayed_transport_1of10.log`

Known limitation: delayed-source generation still uses the existing axisymmetric `RadialProfileBeam` profile builder. For the tilted geometry, an exact-position source upgrade remains the next confidence step before paper-facing numbers.

