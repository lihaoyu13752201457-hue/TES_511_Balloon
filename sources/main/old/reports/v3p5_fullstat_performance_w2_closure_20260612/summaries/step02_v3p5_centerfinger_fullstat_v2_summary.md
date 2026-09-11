# Step02 v3p5 Center-Finger fullstat_v2 Closure

Status: `PASS_FULLSTAT_V2_TRANSPORT_CLOSURE`.

Scope: this is an all-particle `fullstat_v2` closure for the tilted v3p5 simulation geometry.

Geometry/source policy:
- geometry setup: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- geometry validation: `PROXY_PASS`
- far-field radius: `60.0 cm`
- side-window look elevation: `45 deg`
- detector core pixels: `2256`

Transport results:
- instant: `68/68` jobs passed, `25210216` generated particles
- buildup: `68/68` jobs passed, `25210216` generated particles
- delayed source: `4666` blocks, `85.637162 Bq` raw activity
- ground-state fixed source: `4653` blocks, `85.636696 Bq` fixed activity
- delayed transport: `TS=1000000`, `SE=1000000`, `ID=1000000`, `TE=11531.6 s`

Particle counts:

| particle | instant generated | buildup generated |
| --- | ---: | ---: |
| alpha | 191464 | 191464 |
| eminus | 3316936 | 3316936 |
| eplus | 1949816 | 1949816 |
| gamma | 10000000 | 10000000 |
| muminus | 82824 | 82824 |
| muplus | 92840 | 92840 |
| n | 7704528 | 7704528 |
| p | 1871808 | 1871808 |

Artifacts:
- summary JSON: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_fullstat_v2/step02_v3p5_centerfinger_fullstat_v2_summary.json`
- particle counts CSV: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_fullstat_v2/step02_v3p5_centerfinger_fullstat_v2_particle_counts.csv`
- source blocks CSV: `stepwise_maintenance/step02_raw_background_simulation/outputs_v3p5_centerfinger_fullstat_v2/step02_v3p5_centerfinger_fullstat_v2_source_blocks.csv`
- lightweight source snapshots: `stepwise_maintenance/step02_raw_background_simulation/source_snapshots_v3p5_centerfinger_fullstat_v2`
- delayed transport SIM: `runs/step02_delayed_transport_v3p5_centerfinger_fullstat_v2/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- delayed transport log: `runs/step02_delayed_transport_v3p5_centerfinger_fullstat_v2/cosima_delayed_transport_1m.log`

Known limitation: delayed-source generation still uses the existing axisymmetric `RadialProfileBeam` profile builder. For the tilted geometry, an exact-position source upgrade remains the next confidence step before paper-facing numbers.

