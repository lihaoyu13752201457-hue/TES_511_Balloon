# 07 Pre-Fix Verdict

ROLE = Pre-Fix Gatekeeper
INDEPENDENCE = SUBAGENT

## Final Gate

NO_FIX_YET: ENTER_FIX = false. The harness rule requires a conjunction of five predicates: at least two independent roles must identify the same PROBABLE_BUG, with exact evidence, material impact, controlled non-geometry scope, and a new-output-only path; the default is NO_FIX_YET unless all predicates hold. Evidence: `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_background_composition_audit/PROMPT_NEW_SESSION_BACKGROUND_COMPOSITION_AUDIT_HARNESS_ZH.md:237`, `:239`, `:240`, `:241`, `:242`, `:243`, `:244`, `:245`, `:246`.

## Predicate Evaluation

| ENTER_FIX predicate | Gatekeeper status | Evidence |
|---|---|---|
| At least two independent roles identify the same PROBABLE_BUG | NOT_SATISFIED | The Local Data Auditor's PROBABLE_BUG section gives NO_BUG for wrong fix5 geometry, delayed activity/source mismatch, per-family delayed over-normalization, and delayed cps dimension error; it also ranks PROBABLE_BUG as not supported. Evidence: `05_discrepancy_hypotheses.md:39`, `:41`, `:43`, `:45`, `:47`, `:55`. The Literature Auditor states that literature identifies neither a project BUG nor NO_BUG. Evidence: `06_literature_background_matrix.md:67`, `:69`; `06_literature_background_matrix.json` `/overall_verdict/statement = Public literature ... identifies neither a project BUG nor NO_BUG and rules out direct absolute-rate transfer from X/XL-Calibur, SPI, or COSI.` |
| Exact file/field/code/formula evidence for the same PROBABLE_BUG | NOT_SATISFIED | No same PROBABLE_BUG exists to attach evidence to. Local evidence instead supports NO_BUG on the audited current delayed cps dimension check: `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` `/runs/0 = selected_events=30, TE_s=11649.564832, selected_rate_cps=0.0025752034889400762` and `/combined = selected_events=103, total_TE_s=46547.736739, selected_rate_cps=0.0022127821289687215`; mirrored in `04_delay_normalization_audit.md:15` and `05_discrepancy_hypotheses.md:47`. |
| Material impact on current delayed or prompt/delayed composition | NOT_SATISFIED | The artifacts identify material composition differences and statistical limits, but not a current project bug with material impact. Evidence: `05_discrepancy_hypotheses.md:21`, `:23`, `:25`, `:29`, `:51`, `:54`, `:55`. |
| Controlled scope without geometry redesign | NOT_REACHED | Because the same-PROBABLE_BUG predicate is not satisfied, no fix scope is authorized. The harness allows fix execution only after ENTER_FIX is true and then requires exact allowed files/dirs and frozen paths. Evidence: `PROMPT_NEW_SESSION_BACKGROUND_COMPOSITION_AUDIT_HARNESS_ZH.md:253`, `:255`, `:256`. |
| New-output-only path without overwriting authority | NOT_REACHED | Because ENTER_FIX is false, no new repair output path is authorized. The harness requires new output directories only if a clear bug is fixed, and forbids overwriting authority outputs. Evidence: `PROMPT_NEW_SESSION_BACKGROUND_COMPOSITION_AUDIT_HARNESS_ZH.md:153`, `:155`, `:156`, `:253`, `:255`, `:266`, `:267`. |

## Source Role Read

- PASS: allowed source artifacts are marked independent subagent products. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:3`, `04_delay_normalization_audit.md:3`, `05_discrepancy_hypotheses.md:3`, `06_literature_background_matrix.md:4`; JSON mirrors include `03_current_vs_new_geo_re_rate_matrix.json` `/independence = SUBAGENT`, `04_delay_normalization_audit.json` `/independence = SUBAGENT`, and `06_literature_background_matrix.json` `/INDEPENDENCE = SUBAGENT`.
- WARN: `03` shows the old `new_geo_re` values are report-only for current fix5 pass/fail decisions, not a repair trigger. Evidence: `03_current_vs_new_geo_re_rate_matrix.md:9`; `03_current_vs_new_geo_re_rate_matrix.json` `/judgments/0/status = WARN`, `/judgments/0/evidence/0/value = NOT_ALIGNED`, `/judgments/0/evidence/1/value = Old new_geo_re prompt_total_cps and delayed_total_cps may be reported as historical context only, not used as pass/fail gates.`
- PASS: `04` reports clean current fix5 provenance and delayed-normalization audit checks. Evidence: `04_delay_normalization_audit.md:9`, `:10`, `:11`, `:12`, `:13`, `:14`; `04_delay_normalization_audit.json` `/judgments/0/status = PASS`, `/judgments/1/status = PASS`, `/judgments/2/status = PASS`, `/judgments/3/status = PASS`, `/judgments/4/status = PASS`, `/judgments/5/status = PASS`.
- NO_BUG: `04` and `05` find no current evidence for the named delayed normalization/dimension/provenance failure modes. Evidence: `04_delay_normalization_audit.md:15`; `04_delay_normalization_audit.json` `/judgments/6/status = NO_BUG`; `05_discrepancy_hypotheses.md:9`, `:41`, `:43`, `:45`, `:47`.
- WARN: `05` retains stale/provenance risk for old `new_geo_re`, but this is not a current fix5 bug trigger. Evidence: `05_discrepancy_hypotheses.md:11`, `:35`, `:37`.
- PASS_WITH_CAVEATS: `06` says literature supports both delayed-dominant and low-final-delayed outcomes under different instruments/selections, and does not by itself identify a project bug. Evidence: `06_literature_background_matrix.md:47`, `:48`, `:49`, `:50`, `:51`, `:52`, `:69`; `06_literature_background_matrix.json` `/overall_verdict/verdict = PASS_WITH_CAVEATS`, `/overall_verdict/statement = Public literature supports that delayed/activation dominance is expected for some Ge wide-field line instruments and material-rich configurations, while a pointed shielded TES-Laue narrow-window selection could plausibly have a much smaller final delayed component if local normalization and selection audits pass. Literature alone identifies neither a project BUG nor NO_BUG and rules out direct absolute-rate transfer from X/XL-Calibur, SPI, or COSI.`

## Authorized Action

NO_FIX_YET: no code, geometry, current authority output, old `new_geo_re` output, or repair-output generation is authorized by this pre-fix gate. Evidence: ENTER_FIX remains false under the prompt's required conjunction in `PROMPT_NEW_SESSION_BACKGROUND_COMPOSITION_AUDIT_HARNESS_ZH.md:239`, `:240`, `:241`, `:242`, `:243`, `:244`, `:245`, `:246`; source artifacts provide NO_BUG rather than a shared PROBABLE_BUG at `05_discrepancy_hypotheses.md:39`, `:41`, `:43`, `:45`, `:47`, `:55` and `06_literature_background_matrix.md:67`, `:69`.

