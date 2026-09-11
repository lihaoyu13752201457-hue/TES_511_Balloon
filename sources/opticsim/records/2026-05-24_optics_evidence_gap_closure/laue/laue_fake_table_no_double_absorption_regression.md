# Laue fake-table no-double-absorption regression

- demo: `/tmp/opticsim-build-g4-11.4.0/laue_multiring_table_demo`
- ring_config: `data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- run_dir: `runs/laue_fake_table_no_double_absorption_regression`
- n_per_case: 60
- summary_json: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_fake_table_no_double_absorption_regression.json`
- overall_status: **PASS**

## Checks

| check | status |
|---|---|
| all_absorb_exact | PASS |
| all_transmit_exact | PASS |
| all_diffract_exact | PASS |
| one_boundary_decision_per_event | PASS |

## Cases

| case | p_diff | p_abs | p_trans | stages | phase_rows | transmitted_rows | one_row_per_event |
|---|---:|---:|---:|---|---:|---:|---|
| all_absorb | 0.0 | 1.0 | 0.0 | `{'ABSORB': 60}` | 0 | 0 | PASS |
| all_transmit | 0.0 | 0.0 | 1.0 | `{'TRANSMIT': 60}` | 0 | 60 | PASS |
| all_diffract | 1.0 | 0.0 | 0.0 | `{'DIFFRACT': 60}` | 60 | 0 | PASS |

## Interpretation

- The fake table forces each branch to probability one and verifies that the Laue process emits exactly one boundary decision per primary.
- The all-absorb case does not create downstream phase-space photons; the all-transmit case writes only `transmitted_space.csv`; the all-diffract case writes only focused `phase_space.csv`.
- This guards against accidental double counting of table absorption/transmission inside the app-level Laue boundary process. It is not a detector-material EM absorption validation.
