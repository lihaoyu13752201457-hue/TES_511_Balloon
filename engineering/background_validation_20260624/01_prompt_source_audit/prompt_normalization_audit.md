# Prompt Normalization Audit

- status: `PASS`
- source cards: `8`
- flux bins: `160`
- max flux relative diff vs manifest: `3.248179668082206e-13`
- farfield radius unique: `True`
- unique seeds: `True`
- prompt W2 final reconstructed cps: `0.036641023029691404`
- prompt W2 final official cps: `0.036641023029691425`
- selected-rate relative diff: `5.681250137271889e-16`
- prompt W2 final sum_w2: `2.486230720388958e-05`

## Problems
- none

## Evidence

- `source_card_inventory.csv` records geometry lines, source-card flux sums, and radius comments.
- `source_flux_bin_audit.csv` records the 20 equal-mu angular bins for each particle family.
- `farfield_geometry_audit.json` records radius/area and local MEGAlib/runner code evidence.
- `prompt_weight_closure.csv` reconstructs W2 prompt selected rates from event weights and Step05 selection code.
