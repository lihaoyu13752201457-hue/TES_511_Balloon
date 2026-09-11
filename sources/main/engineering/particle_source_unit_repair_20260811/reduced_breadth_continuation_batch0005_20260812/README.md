# Batch0005 reduced-breadth continuation

This non-overwriting corrected-keV batch is an add-on to the canonical
batch0004 partial prefix through global ordinal 97. It does not modify
batch0004 and is not a batch0004 final, seven-family total, 1M-equivalent, or
historical full-stat authority.

The fixed schedule has seven family/mode checkpoints, eight operationally
paired shards, 16 transport jobs, and 27,340 primaries across both geometries:
alpha instant `[250,149]`, alpha buildup `250`, electron instant/buildup
`5,000` each, positive-muon instant/buildup `1,043` each, and negative-muon
buildup `935`, all per geometry. Batch0005 checkpoints credit only these new
histories; downstream composite accounting must bind the pinned batch0004
partial ledger separately.

Safety gates are inherited unchanged from the original batch0003 execution:
hard deadline `2026-08-12T02:31:43.664883Z`, no new launch after
`02:01:43.664883Z`, at least 20 GiB free-space reserve, no raw deletion,
maximum two workers, same-seed retry only, write-once receipts, and dynamic
shard/checkpoint/final validation. All 127 seeds registered by the frozen
batch0004 contract are excluded, including its unexecuted ordinals 98--127.

Read-only plan:

```bash
python3 engineering/particle_source_unit_repair_20260811/reduced_breadth_continuation_batch0005_20260812/code/run_reduced_breadth_continuation_batch0005.py --print-plan --workers 2
```

Transport command (only after independent GO):

```bash
python3 engineering/particle_source_unit_repair_20260811/reduced_breadth_continuation_batch0005_20260812/code/run_reduced_breadth_continuation_batch0005.py --workers 2
```

