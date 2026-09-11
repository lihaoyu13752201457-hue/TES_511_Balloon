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
- Path: `runs/detector_only_4ring_calibrated_v2/hits.csv`
- Rows: `66886`
- Status: `PASS`

## event_summary
- Path: `runs/detector_only_4ring_calibrated_v2/event_summary.csv`
- Rows: `79942`
- Status: `PASS`
- Extra columns: `status, x_det_mm, y_det_mm, in_line_window, selected_signal`

## detector_crosslinks
- Path: `runs/detector_only_4ring_calibrated_v2/hits.csv + runs/detector_only_4ring_calibrated_v2/event_summary.csv`
- Rows: `79942`
- Status: `PASS`

## source_detector_event_ids
- Path: `runs/channel_4ring_calibrated_v2/phase_space.csv + runs/detector_only_4ring_calibrated_v2/event_summary.csv`
- Rows: `79942`
- Status: `PASS`
