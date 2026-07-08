# Revised Delayed-Processing Verdict

Date: 2026-06-23

This parent summary supersedes the earlier broad statement that the old
`new_geo_re` versus current fix5 delayed-rate difference is mainly physical
model/inventory.  The focused three-agent delayed-chain re-audit gives a more
constrained result.

## Verdict

Status: **UNRESOLVED_COMPARABILITY**

The old/current delayed discrepancy is **not explained by fixed delayed
activity alone**.  Old fixed activity is `624.2710918319826 Bq`; current fix5
fixed activity is `85.44920253876245 Bq`, so the activity ratio is only
`7.30575679215723x`.

The selected delayed W2 rate ratio is much larger:

- current fix5 production sample: `30 / 11649.564832 s =
  0.0025752034889400762 cps`
- current fix5 PI-02 combined estimate: `0.0022127821289687215 cps`
- old inspected `new_geo_re` W2 both-veto delayed:
  `0.15211317269106375 cps`
- old/current selected-rate ratio: `59.06840890219195x` versus the production
  sample, or `68.74295065007456x` versus PI-02
- residual selected-cps-per-Bq ratio after activity: `8.085186871482254x`
  versus the production sample, or `9.409422268733405x` versus PI-02

Therefore activity/inventory accounts for only part of the discrepancy.  The
remaining factor is in selection, source spatial sampling/compression,
source-distribution geometry, or a combination of those.

## Bug Status

Current fix5 delayed processing: **NO O(10-100) suppression bug found**.

The current chain has audited per-family division, NUBASE ground-state
half-life correction, exact-position M=50000 activity preservation, fix5
geometry provenance, and selected cps equal to selected events divided by
`TE_s`.  The `TE_s` versus source-flux mismatch is about `0.46%` and raises the
current TE-based rate slightly; it cannot suppress delayed by O(10-100).

Old `new_geo_re` delayed processing: **NO proven O(10-100) inflation bug, but
with audit gaps**.

The old implementation contains the non-gamma divide-by-8 and has a PASS
NUBASE ground-state half-life audit.  However, it lacks the current-style
per-family TT/division audit artifact.  More importantly, it uses compressed
z/r `RadialProfileBeam` delayed sources and a detector-coupled Gaussian W2
probability table, while current fix5 uses exact-position `PointSource`
sampling and hard W2 selected-event counting in Step05.

## Corrected Interpretation

Do not claim that old `new_geo_re` delayed dominance versus current fix5 is
settled as a physical mass-model/inventory effect.  The clean statement is:

1. Fixed activity differs by `7.31x`, not enough for the `59-69x` selected-rate
   gap.
2. Current fix5 delayed handling is not shown to be suppressing the rate by
   O(10-100).
3. Old `new_geo_re` delayed handling is not proven inflated by O(10-100).
4. The old and current delayed W2 numbers are not gate-comparable until source
   sampling and W2 selection are aligned.

## Required Next Check

The decisive check is a cross-over replay without new buildup:

1. Build an old-inventory exact-position delayed source from old fixed
   inventory/RPIP points.
2. Score it with the current hard W2 Step05 selection.
3. Report fixed activity, per-family raw/scaled RP totals, TT/division, source
   flux conservation, `TE_s`, selected events, cps, and `selected_cps/Bq`.

The optional inverse check is to run current fix5 inventory through the old
radial-profile compression and old Gaussian W2 table.  Until at least the first
cross-over exists, the old `0.151456825339 cps`/`0.15211317269106375 cps` delayed
number must remain report-only for fix5 delayed gating.

## Audit Artifacts

- `00_reaudit_scope.md`
- `01_current_fix5_delay_chain_audit.md`
- `01_current_fix5_delay_chain_audit.json`
- `02_old_new_geo_re_delay_chain_audit.md`
- `02_old_new_geo_re_delay_chain_audit.json`
- `03_supervisor_delay_processing_comparison.md`
- `03_supervisor_delay_processing_comparison.json`
- `04_revised_user_summary.md`
