# WP08 Promotion Decision

Status: `NO_RATE_AUTHORITY`.

G4 source-v2 and G6 timing are closed, and G5 native difference is explained, but G7 has only 1000-trigger v2/native pilot diagnostics and the legacy L0 comparator timed out. No full-stat v2 selected-rate convergence, seed variance, or sum_w2 ledger exists.

Promoted numbers: none.

Retained numbers:
- `legacy fix5 delayed W2 selected cps` = `0.0025752034889400762` (RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED)

Unresolved limitations:
- No v2 full-stat selected-rate authority.
- No v2 selected-rate seed variance or sum_w2 ledger.
- Legacy L0 pilot comparator did not produce a SIM output within the bounded 300 s cap.
- Native volume-based pilot is diagnostic and not an exact-position selected-rate replacement.

Next minimum step: Generate an explicit resource/approval plan for v2 full-stat selected-rate convergence, or accept NO_RATE_AUTHORITY as the legal endpoint for this harness run.
