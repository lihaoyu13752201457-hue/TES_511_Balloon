# Batch0004 partial checkpoint publisher

Status: `PASS__BATCH0004_PARTIAL_CHECKPOINT_THROUGH_GLOBAL_ORDINAL0097_MERGE_ELIGIBLE`.
Initial strict publication and an independent read-only reconstruction both
passed on 2026-08-12.  The canonical 12-stage batch0004 final report and
ledger remain absent.

This package salvages only the contiguous, completed corrected-keV batch0004
prefix after the frozen T+8 stop-launch gate.  It does not resume transport,
invoke Cosima, alter the frozen runner/validator, or publish the canonical
12-stage batch0004 final authority.

The frozen scope is:

- five complete canonical checkpoints: gamma buildup, neutron instant and
  buildup, and positron instant and buildup;
- alpha instant global ordinals 91--97, corresponding to stage shards 1--7
  of 9;
- one contiguous global pair prefix, ordinals 1--97, with exactly two
  geometry jobs per ordinal.

If both immutable geometry receipts for alpha shard 7 revalidate exactly, the
publisher may create the missing write-once paired receipt.  It then publishes
an explicitly partial alpha authority and an explicitly partial umbrella
ledger.  The umbrella includes a campaign manifest suitable for
geometry+mode+family-specific TES, veto, prompt, or activation diagnostics.
It explicitly forbids treating absent campaigns as zero, forming a complete
seven-family total, or claiming delayed closure, sensitivity, or geometry
promotion.

Run tests:

```bash
python3 -m unittest discover \
  -s engineering/particle_source_unit_repair_20260811/batch0004_partial_checkpoint_20260812/tests \
  -p 'test_*.py'
```

Publish once after transport is stopped:

```bash
python3 engineering/particle_source_unit_repair_20260811/batch0004_partial_checkpoint_20260812/code/publish_batch0004_partial_checkpoint.py \
  --publish
```

Exact read-only revalidation:

```bash
python3 engineering/particle_source_unit_repair_20260811/batch0004_partial_checkpoint_20260812/code/publish_batch0004_partial_checkpoint.py \
  --check
```

The publisher obtains the same controller lock as the batch0004 runner, so it
fails rather than racing a resume.  Every canonical checkpoint artifact is
hash-checked; every alpha-prefix SIM is re-read with the frozen validator; all
authority files are write-once.

## Published result

- complete pair ordinals: 1--97;
- validated geometry jobs: 194;
- validated new primaries: 2,235,468;
- complete checkpoint stages: 5/12;
- alpha instant: 7/9 shards, 1,750 new primaries per geometry, 1,991
  cumulative primaries per geometry after 241 credited prior histories;
- missing scope: ordinals 98--127, represented explicitly in the umbrella
  authority rather than interpreted as zero.

Canonical partial authority hashes are recorded in
`IMPLEMENTATION_MANIFEST.json`.  The umbrella ledger is a downstream campaign
manifest, but its `seven_family_total_eligible` and
`canonical_batch0004_final_eligible` gates are both `false`.
