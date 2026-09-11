# Final Normalization And Sampling Verdict

Date: 2026-06-23

This file supersedes `04_revised_user_summary.md`, `05_deep_sampling_axis_collapse_audit.md`,
and `06_final_deep_sampling_verdict.md` as the current final interpretation of
the delayed-processing re-audit.

## Bottom Line

Status: **OLD_NEW_GEO_RE_DELAYED_NORMALIZATION_BUG_FOUND**

The user's concern was correct.  The old `new_geo_re` delayed activity is
inflated by an `x8` non-gamma activation normalization error.  The old delayed
inventory/source uses raw non-gamma RP yields, while the intended current
contract requires division by the eight non-gamma replicas.

After applying the missing divide-by-8, the old delayed source activity is no
longer `~624 Bq`; it is `~78 Bq`, close to the current fix5 delayed source
activity `85.449 Bq`.

## Direct Numeric Proof

Old I-128 from the old buildup `.dat` files:

- raw I-128 RP total: `288648`
- divide-by-8 scaled I-128 RP total: `36081`
- raw/scaled ratio: `8.0`

Old inventory/source output:

- `activation_inventory_day15.csv` reports I-128 `RP_yield = 288648`
- reported I-128 activity: `533.2757337939474 Bq`
- corrected I-128 activity should be `66.65946672424344 Bq`

Old total delayed activity:

- old inventory CSV total: `624.5591421308807 Bq`
- recomputed from raw `.dat` yields: `623.9633399015754 Bq`
- recomputed with non-gamma divide-by-8: `77.99541748769693 Bq`
- raw/scaled ratio: `8.0`
- fixed-source total after ground-state correction: `624.2710918319826 Bq`
- fixed-source total if divided by 8: `78.03388647899782 Bq`

Current fix5 delayed activity:

- fixed source total: `85.44920253876245 Bq`

So the old/current activity comparison is not `624.27 / 85.45 = 7.31x` in
physical terms.  With the missing old divide corrected, it is
`78.03 / 85.45 = 0.91x`.

## Evidence

Old output proves raw activity was used:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_decay_source_equiv2602_aligned/activation_inventory_day15.csv:2-23`
  reports I-128 CsI rows such as `RP_yield=26973` and
  `Activity_Bq=49.832546179576646`.
- The implied `RP_yield / Activity_Bq` for the first row is `541.27 s`, matching
  a single replica TT, not a divide-by-8 scaled production.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step03_delay_source/outputs/fixed_source_blocks.csv`
  sums to `624.2710918416278 Bq` and I-128 alone sums to `533.27573379 Bq`.

Direct recomputation from old `.dat` files:

- non-gamma file count is 8 per family.
- I-128 is almost entirely neutron-produced: raw neutron I-128 is `288363`;
  scaled neutron I-128 is `36045.375`.
- Across all tags, I-128 raw/scaled is exactly `8.0`.
- Across all inventory keys with finite half-life, total raw/scaled activity is
  exactly `8.0`.

This means the old output is not just missing an audit artifact; the authority
inventory/source itself is the raw, un-divided non-gamma activity.

## What Remains After Fixing The 8x

The missing divide-by-8 explains why old delayed activity looked much larger
than current fix5.  It also scales old delayed rates down by 8:

- old inspected W2 delayed: `0.15211317269106375 cps`
- divide-by-8 corrected W2 delayed: `0.01901414658638297 cps`
- current fix5 production W2 delayed: `0.0025752034889400762 cps`
- corrected old/current W2 rate ratio: `7.38x`

That remaining `~7x` rate gap is not a source-activity normalization issue.  The
best current clue for the residual is the old delayed source-placement method:

- Old `RadialProfileBeam` source entries are emitted at `x_cm=0.0`, `y_cm=0.0`
  for each z-bin.
- Old SIM samples show dominant I-128 `IA INIT` positions collapsed to `r=0`.
- Current fix5 `PointSource` samples start at true CsI RPIP coordinates.

Therefore there are two separate old-chain problems:

1. **Primary:** missing non-gamma divide-by-8 in old delayed inventory/source.
2. **Secondary:** old radial-profile source placement/axis collapse makes the
   remaining detector coupling unreliable.

## Corrected Interpretation

The old `new_geo_re` delayed value `0.151456825339 cps` / inspected
`0.15211317269106375 cps` is not a valid physical benchmark for fix5.

The current fix5 delayed activity being `~85 Bq` is no longer suspicious once
the old normalization is corrected; it is close to the corrected old value
`~78 Bq`.

Current fix5 delayed handling still passes the relevant checks:

- per-family division audit passes;
- NUBASE ground-state correction passes;
- exact-position M=50000 sampling preserves activity;
- selected cps is selected events divided by `TE_s`.

## Required Next Check

The old delayed authority should be rebuilt before any old/current delayed
comparison:

1. Recompute old delayed inventory with per-family raw/scaled RP totals and
   explicit `division=8` for non-gamma families.
2. Build old exact-position `PointSource` delayed source from the corrected fixed
   inventory/RPIP points.
3. Verify emitted SIM `IA INIT` positions match RPIP coordinates and do not
   collapse to `r=0`.
4. Rerun the same hard W2 Step05 selection and report `selected_cps/Bq`.

Until then, old `new_geo_re` delayed numbers must be treated as invalid for
fix5 delayed gating.
