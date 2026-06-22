# First-layer TES 511 keV efficiency

- SIM: `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/science_511_onaxis_source/Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz`
- Log: `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/science_511_onaxis_source/cosima_science_100k.log`
- Geometry: `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo`
- Generated particles: 100000
- Stored SIM events: 100000
- First TES layer for this source direction: `TES_L5` / `TP_L5_*`.

## All generated photons

- L5 active TES any HTsim hit: 36655/100000 = 0.366550 +/- 0.001524
- L5 active TES full-energy 506-516 keV: 25791/100000 = 0.257910 +/- 0.001383
- First non-init interaction in L5 slab: 37606/100000 = 0.376060 +/- 0.001532

## Conditioned on L5 active-pixel footprint

- Initial ray intersects a TP_L5 pixel footprint: 82102/100000 = 0.821020 +/- 0.001212
- L5 active TES any HTsim hit within that footprint: 36599/82102 = 0.445775 +/- 0.001735
- L5 active TES full-energy 506-516 keV within that footprint: 25785/82102 = 0.314061 +/- 0.001620
- First non-init interaction in L5 slab within that footprint: 37603/82102 = 0.458003 +/- 0.001739
- Prior non-L5 interaction within that footprint: 44494/82102 = 0.541936 +/- 0.001739

## First L5 interaction depth

- First L5 IA count: 38532
- Depth range from L5 top face: 0.000000 to 0.300000
- Mean depth from L5 top face: 0.136455
- First L5 IA deeper than 0.3 cm from top face: 1/38532 = 0.000026

## Interpretation

This report is generated directly from the selected SIM and current
geometry file. For the cm-scaled geometry the L5 active thickness is
0.3 cm, so no first L5 interaction depth can exceed the physical slab
thickness except for parser/numerical error.
