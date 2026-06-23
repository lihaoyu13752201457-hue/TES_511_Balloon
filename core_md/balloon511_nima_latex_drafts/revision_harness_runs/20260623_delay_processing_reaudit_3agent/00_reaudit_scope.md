# Delayed Processing Re-Audit Scope

Date: 2026-06-23

This re-audit supersedes the previous high-level conclusion for the specific
question of why old `new_geo_re` delayed was dominant while current fix5 delayed
is small. The prior no-bug conclusion is treated as unproven until this focused
delayed-chain comparison is complete.

User concern: the two mass models may not differ enough to explain the delayed
activity/rate gap by geometry or inventory alone. Therefore the primary focus is
delayed simulation handling:

- activation RPIP extraction and source-block construction;
- ground-state/NUBASE half-life handling;
- per-family TT/live-time division;
- source activity normalization;
- decay sampling method, source-position sampling/compression, and M sampling;
- Cosima delayed transport `SE`/`ID`/`TE` interpretation;
- selected-event to cps conversion;
- whether old and current selected delayed rates are physically comparable.

Required role split:

1. Current-fix5 delayed-chain auditor: inspect only current `/home/ubuntu/TES_511_Balloon` fix5 artifacts and scripts.
2. Old-new_geo_re delayed-chain auditor: inspect only `/home/ubuntu/codex_tes_511_sim/new_geo_re` artifacts and scripts.
3. Supervisor/comparison auditor: read the two reports and compare both chains.

No code, geometry, source cards, current authority outputs, or old `new_geo_re`
outputs may be modified by this re-audit.
