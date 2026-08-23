# O8 PARMA-511 compact supercampaign merge

`code/merge_o8_parma511_line_campaigns.py` combines one or more complete
`o8-parma511-line-campaign-aggregate-v1` receipts into one
`o8-parma511-line-supercampaign-aggregate-v1` receipt.

The merger is offline-only. It opens only the input aggregate receipts and
their hash-listed compact JSON/CSV response products. It rejects raw/log/source
paths, has no Cosima entry point, and records both `cosima_launched=false` and
`raw_sim_files_read=false`.

Before merging it fail-closes on:

- the exact 510.99895-keV atmospheric mono-gamma scope;
- the retained O8 setup/geo/det hashes and frozen Step05/Step09 hashes;
- the same 420-eV FWHM, thresholds, 64 response seeds, and PARMA80 proposal;
- complete receipt/provenance/artifact hashes;
- duplicate campaign identities, campaign/batch keys, run names, aggregate
  fingerprints, or transport seeds.

It merges `TS`, `TE`, count fields, TES events, TES pixel hits, event lineage,
and the paired 20/40/80 angular counts. It then imports the unchanged line-only
harness and calls its own `response_analysis` function on the merged compact
catalog. The frozen passive-Kapton-by-name veto blocker remains explicit.

Example:

```bash
python3 engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/code/merge_o8_parma511_line_campaigns.py merge \
  --receipt /path/to/first/campaign_aggregate_receipt.json \
  --receipt /path/to/supplement/campaign_aggregate_receipt.json \
  --output-dir engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/transport/supercampaigns/final_line_supercampaign
```

The real 1k smoke identity/rejection test is:

```bash
python3 engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/code/merge_o8_parma511_line_campaigns.py self-test
```

This default command is rerunnable: it creates a unique directory under `/tmp`,
rebuilds the single-input supercampaign, performs all identity and rejection
checks, and automatically removes the temporary products after reporting their
hashes. It does not overwrite the retained evidence.

To intentionally create a new persistent audit receipt, both output paths must
be explicit and absent:

```bash
python3 engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/code/merge_o8_parma511_line_campaigns.py self-test \
  --output-dir engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/transport/supercampaigns/o8_parma511_line_smoke_1k_identity_v1 \
  --self-test-receipt engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/data/o8_parma511_line_supercampaign_selftest_receipt.json
```

The retained receipt is `data/o8_parma511_line_supercampaign_selftest_receipt.json`.
The smoke result is intentionally diagnostic because it contains zero selected
W2 events; it validates merger identity and safety, not detector statistics.
