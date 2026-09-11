# IO Contract Validation

Overall status: PASS

## phase_space
- Path: `runs/channel_wallbywall_rebuild/phase_space.csv`
- Rows: `5804`
- Status: `PASS`
- Extra columns: `particle_name, pdg_encoding, track_id, parent_id`

## optics_history
- Path: `runs/channel_wallbywall_rebuild/optics_history.csv`
- Rows: `209969`
- Status: `PASS`

## hits
- Path: `runs/geant4_detector_wallbywall_1k/hits.csv`
- Rows: `7102`
- Status: `PASS`

## event_summary
- Path: `runs/geant4_detector_wallbywall_1k/event_summary.csv`
- Rows: `1000`
- Status: `PASS`

## detector_crosslinks
- Path: `runs/geant4_detector_wallbywall_1k/hits.csv + runs/geant4_detector_wallbywall_1k/event_summary.csv`
- Rows: `1000`
- Status: `PASS`

## source_detector_event_ids
- Path: `runs/channel_wallbywall_rebuild/phase_space.csv + runs/geant4_detector_wallbywall_1k/event_summary.csv`
- Rows: `1000`
- Status: `PASS`
- Warnings:
  - event_summary has 1000 rows for 5804 phase-space photons; treating as an allowed subset run
