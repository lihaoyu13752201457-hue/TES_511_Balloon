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
- Path: `runs/geant4_detector_only_1k/hits.csv`
- Rows: `6256`
- Status: `PASS`

## event_summary
- Path: `runs/geant4_detector_only_1k/event_summary.csv`
- Rows: `1000`
- Status: `PASS`

## detector_crosslinks
- Path: `runs/geant4_detector_only_1k/hits.csv + runs/geant4_detector_only_1k/event_summary.csv`
- Rows: `1000`
- Status: `PASS`

## source_detector_event_ids
- Path: `runs/channel_4ring_calibrated_v2/phase_space.csv + runs/geant4_detector_only_1k/event_summary.csv`
- Rows: `1000`
- Status: `PASS`
- Warnings:
  - event_summary has 1000 rows for 79942 phase-space photons; treating as an allowed subset run
