# Final Deep-Sampling Verdict

Date: 2026-06-23

**Superseded by `07_final_normalization_and_sampling_verdict.md`.**

The axis-collapse clue in this file remains useful as a second processing
problem, but it is not the first-order explanation.  A later direct recomputation
from old `.dat` files shows that the old `new_geo_re` delayed inventory/source
used raw non-gamma activation rather than the required divide-by-8 scaled
activation.  That is the primary 8x normalization issue.

This verdict supersedes `04_revised_user_summary.md` where the state was still
`UNRESOLVED_COMPARABILITY`.

## Bottom Line

Status: **PROBABLE_OLD_NEW_GEO_RE_DELAYED_SOURCE_PLACEMENT_BUG**

The clue is now concrete: old `new_geo_re` delayed source sampling appears to
collapse dominant CsI/I-128 activity onto the z-axis through the
`RadialProfileBeam` source construction.

This explains why the old delayed rate is far too strongly coupled to TES
without needing a half-life or total-activity bug.

## Why This Explains The Gap

Activity alone is too small:

- total fixed delayed activity old/current: `7.31x`
- I-128 activity old/current: `8.14x`

But old/current detector coupling is huge:

- delayed TES-event fraction old/current: `102.0x`
- broad 480-550 raw selected per delayed catalog event old/current: `125.1x`
- sampled I-128 any-TES fraction old/current: `~450x`

The source decay rate per Bq is not the culprit; current actually has the higher
delayed catalog rate per Bq.  The large discrepancy appears when old source
events are transported through the detector.

## Direct Evidence

Old source builder:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:1014-1020`
  writes every z/r source entry with `x_cm=0.0`, `y_cm=0.0`.

Old source card:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source:5986-5988`
  shows a CsI/I-128 source as
  `RadialProfileBeam 0.000000 0.000000 -21.549924 ...`.

Old SIM sample:

- first `20000` delayed events sampled
- I-128 events: `16856`
- I-128 `IA INIT` mean radius: `0.0 cm`
- I-128 fraction with `r < 0.001 cm`: `1.0`
- top first-hit volume: `Passive_Bottom_W_Shield`, not CsI
- I-128 any-TES fraction: `0.17619838633127669`

Current fix5 exact-position sample:

- first `20000` delayed events sampled
- I-128 events: `15322`
- I-128 `IA INIT` mean radius: `14.78431518348516 cm`
- I-128 fraction with `r < 0.001 cm`: `0.0`
- top first-hit volumes are actual CsI segment/quadrant volumes
- I-128 any-TES fraction: `0.0003915937867119175`

## Corrected Interpretation

The old `new_geo_re` delayed dominance should **not** be treated as a physical
benchmark against fix5.  The old delayed rate is very likely contaminated by the
production delayed-source placement method.

Current fix5 delayed handling still looks internally consistent:

- audited per-family division
- NUBASE ground-state correction
- exact-position M=50000 `PointSource` source
- selected cps equal to selected events divided by `TE_s`

The issue is not that current fix5 is mysteriously suppressing delayed by
`O(10-100)`.  The issue is that old `new_geo_re` delayed transport was likely
inflated by source-position collapse in the radial-profile delayed source.

## Next Action

Do not use old `0.151456825339 cps` / inspected `0.15211317269106375 cps` as a
delayed comparison gate.

The correct discriminator is to rebuild old `new_geo_re` delayed source from old
fixed inventory/RPIP using exact-position `PointSource` sampling, verify that
I-128 `IA INIT` coordinates no longer collapse to `r=0`, then rerun the same W2
selection and compare `selected_cps/Bq`.
