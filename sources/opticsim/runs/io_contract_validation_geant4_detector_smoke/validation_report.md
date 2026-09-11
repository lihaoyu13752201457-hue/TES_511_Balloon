# IO Contract Validation

Overall status: PASS

## phase_space
- Path: `runs/channel_4ring_calibrated_v2/phase_space.csv`
- Rows: `79942`
- Status: `PASS`

## optics_history
- Path: `runs/channel_4ring_calibrated_v2/optics_history.csv`
- Rows: `100000`
- Status: `PASS`

## hits
- Path: `runs/geant4_detector_only_smoke/hits.csv`
- Rows: `479`
- Status: `PASS`

## event_summary
- Path: `runs/geant4_detector_only_smoke/event_summary.csv`
- Rows: `50`
- Status: `PASS`

## detector_crosslinks
- Path: `runs/geant4_detector_only_smoke/hits.csv + runs/geant4_detector_only_smoke/event_summary.csv`
- Rows: `50`
- Status: `PASS`

## source_detector_event_ids
- Path: `runs/channel_4ring_calibrated_v2/phase_space.csv + runs/geant4_detector_only_smoke/event_summary.csv`
- Rows: `50`
- Status: `PASS`
- Warnings:
  - event_summary has 50 rows for 79942 phase-space photons; treating as an allowed subset run
