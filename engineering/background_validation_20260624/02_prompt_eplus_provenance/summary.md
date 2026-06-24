# WP02 Prompt eplus Survivor Provenance

Status: `PASS_EPLUS_PROVENANCE`.

Selected final W2 prompt eplus survivors: `47`.
Selected eplus rate: `0.0318897456148` cps.
A-C classified fraction: `1.000`.

## Classification Counts

| class | events | rate cps |
|---|---:|---:|
| A | 47 | 0.0318897456148 |

## Evidence

- Selection is reconstructed from the fix5 Step05 event catalog using the same active veto and side-entry Compton/FoV functions.
- Event provenance is parsed from existing prompt eplus SIM `IA`, `CC HIT`, and `HTsim` blocks; no transport was rerun.

Outputs:
- event table: `engineering/background_validation_20260624/02_prompt_eplus_provenance/eplus_survivor_events.csv`
- process summary: `engineering/background_validation_20260624/02_prompt_eplus_provenance/eplus_survivor_process_summary.csv`
- volume summary: `engineering/background_validation_20260624/02_prompt_eplus_provenance/eplus_survivor_volume_summary.csv`
