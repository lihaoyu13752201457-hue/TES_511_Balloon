# WP05 Matched CsI/BGO Resource Guard

Status: `BLOCKED_RESOURCE_APPROVAL`.

BGO source cards: `8`.
Physics source hash equal excluding geometry: `True`.
Flux sums equal: `True`.
Full matched production exceeds event guard: `True`.

Failure contract:
- affected claim: No CsI/BGO material-comparison rate, ratio, uncertainty, or design preference can be claimed until matched CsI/BGO transport and identical Step05 selection are run.
- minimal next action: Approve and run the staged P0 syntax/geometry smoke batch, then review P0 before any P1/P2 escalation.
- requires user decision: `True`

Outputs:
- BGO source manifest: `engineering/background_validation_20260624/05_matched_runs_resource_guard/bgo_source_card_manifest.csv`
- approval request: `engineering/background_validation_20260624/05_matched_runs_resource_guard/RESOURCE_APPROVAL_REQUIRED.md`
