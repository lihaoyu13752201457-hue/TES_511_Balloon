# RESOURCE_APPROVAL_REQUIRED

Status: `BLOCKED_RESOURCE_APPROVAL`.

The BGO same-envelope geometry and BGO source cards are ready, but matched production must not start without approval.

- fullstat gamma events per variant: `10000000`
- prompt+buildup events per variant: `50420432`
- prompt+buildup events for CsI+BGO: `100840864`
- event guard per launch batch: `5000000`

## Failure Contract

- affected claim: No CsI/BGO material-comparison rate, ratio, uncertainty, or design preference can be claimed until matched CsI/BGO transport and identical Step05 selection are run.
- minimal next action: Approve and run the staged P0 syntax/geometry smoke batch, then review P0 before any P1/P2 escalation.
- requires user decision: `True`
- unexecuted phases:
  - WP05 P0/P1/P2 matched prompt instant transport
  - WP05 matched activation buildup transport
  - WP05 matched delayed source and delayed decay transport
  - WP05 matched focused science replay
  - WP06 CsI/BGO comparison

Evidence:
- `engineering/background_validation_20260624/05_matched_runs_resource_guard/bgo_source_card_manifest.csv`
- `engineering/background_validation_20260624/05_matched_runs_resource_guard/matched_run_resource_plan.json`
- `engineering/background_validation_20260624/05_matched_runs_resource_guard/RESOURCE_APPROVAL_REQUIRED.md`
- `engineering/background_validation_20260624/01_prompt_source_audit/prompt_normalization_audit.json`
- `engineering/background_validation_20260624/04_bgo_variant/bgo_geometry_manifest.json`

Recommended next approved batch:
- P0 syntax/geometry smoke only
- gamma_events=1000, gamma_splits=1, non_gamma_replicas=1
- delayed_decays=1000
- no rate/material conclusion from P0

Full P2 production requires a separate explicit approval after P0/P1 evidence.
