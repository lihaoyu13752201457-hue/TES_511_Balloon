# Stepwise Maintenance

This directory records incremental maintenance for `new_geo_re`.

Layout:

- `outputs/geometry/`: consolidated WRL and 2D schematic outputs for the
  current detector/cryostat geometry.
- `step01_geo/`: geometry cleanup and Be-window-matched aperture checkpoint.
- `step02_raw_background_simulation/`: prompt/buildup/delayed raw COSIMA simulation checkpoint.
- `CURRENT_PROGRESS_STEP_BREAKDOWN.md`: current step status.
- `REFERENCE_PAPERS_INDEX_20260602.md`: paper and technical-reference index collected from step-maintenance docs.

Current v3p5 low-stat closure:

- Geometry/Step00: `step00_geometry/outputs/v3p5_centerfinger/`.
- Step02 1/10 transport: `step02_raw_background_simulation/outputs_v3p5_centerfinger_1of10/`.
- Step05 L1 response: `step05_veto_time_axis/outputs_v3p5_centerfinger_l1/`.
- Step06 mission-axis fold: `step06_mission_time_variation/outputs_v3p5_centerfinger_1of10/`.
- Step07 source cases: `step07_source_cases/outputs_v3p5_centerfinger_1of10/`.
- Step08 time-dependent significance: `step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_time_dependent.md`.
- Unified closure: `../outputs/reports/v3p5_centerfinger_1of10_closure/v3p5_centerfinger_1of10_closure_report.md`.

Policy:

- Keep reproducible commands in each step README.
- Keep source snapshots lightweight.
- Do not store `.sim.gz` or `.dat` products in maintenance snapshots.
