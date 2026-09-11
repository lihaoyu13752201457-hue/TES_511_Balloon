# Laue all-diffract detector-handoff regression

- phase_space: `runs/laue_fake_table_no_double_absorption_regression/all_diffract/phase_space.csv`
- detector_demo: `/tmp/opticsim-build-g4-11.4.0/detector_only_demo`
- run_dir: `runs/laue_all_diffract_detector_handoff`
- n_phase_rows: 60
- n_requested: 60
- summary_json: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_all_diffract_detector_handoff_regression.json`
- overall_status: **PASS**

## Checks

| check | status |
|---|---|
| phase_rows_equal_fake_all_diffract_n | PASS |
| detector_n_input_matches_phase_rows | PASS |
| detector_n_simulated_matches_requested | PASS |
| detector_events_written_matches_requested | PASS |
| event_summary_rows_match_requested | PASS |
| source_detector_contract_passes | PASS |

## Detector summary

| metric | value |
|---|---:|
| n_input_photons | 60 |
| n_simulated | 60 |
| n_events_written | 60 |
| event_summary_rows | 60 |
| n_hits | 398 |

## Interpretation

- The fake Laue table forces all optics decisions into `DIFFRACT`, so every input primary should produce one focused phase-space photon.
- The detector-only handoff consumes the standard phase-space columns and writes one event summary per requested photon.
- This guards against dropping Laue diffracted photons through parent-ID assumptions or schema filters at the optics-detector boundary.
- It does not validate detector material response fidelity; it validates handoff completeness and IO contract compatibility.
