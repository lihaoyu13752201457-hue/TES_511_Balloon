# WP09 Downstream No-Rate-Authority Manifests

Task: document downstream rebuild status after WP08 returned NO_RATE_AUTHORITY.

Input allowlist:
- `engineering/delayed_source_authority_v2_20260624/08_promotion/promotion_decision.json`

Forbidden actions:
- no Step05, Step06, Step07, or Step08 rebuild
- no BGO transport
- no `runs/`, `outputs/`, or `stepwise_maintenance/` writes
- no manuscript edits

Acceptance gate: downstream artifacts explicitly state not rebuilt and list minimum future rebuild requirements.
