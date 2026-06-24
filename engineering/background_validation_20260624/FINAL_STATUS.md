# FINAL_STATUS

git_head: 7cd86de5f2c7e641a149bd508848c8c8c209fb32
git_status: dirty
harness_version: HARNESS_20260624 v1.0
terminal_status: BLOCKED_RESOURCE_APPROVAL
completion_audit: PASS_COMPLETION_AUDIT

| Gate | Status | Evidence | Blocking? | Next action |
|---|---|---|---:|---|
| G0 Authority | PASS | 00_manifest/baseline_authority_manifest.json | false | Proceed. |
| G1 Prompt normalization | PASS | 01_prompt_source_audit/prompt_normalization_audit.json | false | Proceed. |
| G2 eplus provenance | PASS | 02_prompt_eplus_provenance/eplus_survivor_provenance.json | false | Proceed. |
| G3 delayed convergence | DELAYED_CONVERGED | 03_delayed_convergence/delayed_selected_rate_convergence.json | false | Proceed. |
| G4 BGO geometry | PASS | 04_bgo_variant/bgo_geometry_manifest.json | false | Proceed only with approved matched run staging. |
| G5/G6 matched runs | BLOCKED_RESOURCE_APPROVAL | 05_matched_runs_resource_guard/RESOURCE_APPROVAL_REQUIRED.md | true | User approval required before P0/P1/P2 matched CsI/BGO runs. |
| G7 comparison | BLOCKED_RESOURCE_APPROVAL | 05_matched_runs_resource_guard/summary.json | true | Requires matched CsI/BGO run evidence. |
| G8 paper support | PASS_LIMITED_SUPPORT_WITH_MATCHED_RUNS_BLOCKED | 07_manuscript_support/background_validation_necessity_and_paper_impact_final.md | false | Do not edit manuscript or claim CsI/BGO material preference without matched runs. |
| Completion audit | PASS_COMPLETION_AUDIT | 08_completion_audit/completion_audit.json | false | Current endpoint is verified. |

Key results:
- final W2 prompt eplus survivor provenance: PASS, 47/47 classified A-C, eplus rate 0.0318897456148 cps.
- delayed PI-02 convergence: DELAYED_CONVERGED, 103 pooled selected W2 events, rate 0.00221278212897 cps, relative uncertainty 0.0985329278164.
- BGO same-envelope geometry: PASS, 24 CsI active-shield material lines changed to BGO, 0 non-whitelisted geometry diffs, detector references PASS, cosima overlap PASS.
- matched production: not run. Full matched CsI/BGO production exceeds the HARNESS_20260624 resource guard.

Files created:
- engineering/background_validation_20260624/00_manifest/
- engineering/background_validation_20260624/01_prompt_source_audit/
- engineering/background_validation_20260624/02_prompt_eplus_provenance/
- engineering/background_validation_20260624/03_delayed_convergence/
- engineering/background_validation_20260624/04_bgo_variant/
- engineering/background_validation_20260624/05_matched_runs_resource_guard/
- engineering/background_validation_20260624/07_manuscript_support/
- engineering/background_validation_20260624/08_completion_audit/
- engineering/background_validation_20260624/work_packets/
- engineering/background_validation_20260624/scripts/

Files intentionally not modified:
- baseline geometry
- baseline source cards
- Step05 authority outputs
- manuscript source

Resource approvals requested:
- none for new simulation runs.
- generated `05_matched_runs_resource_guard/RESOURCE_APPROVAL_REQUIRED.md` for the next matched-run stage.
