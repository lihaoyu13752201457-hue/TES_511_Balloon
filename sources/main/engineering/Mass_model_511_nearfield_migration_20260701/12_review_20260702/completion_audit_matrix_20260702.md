# Mass_model_511 Completion Audit Matrix - 2026-07-02

review_role: `review_subagent`
status: `OPEN_ITEMS_NOT_CLOSED`
scope: `engineering/Mass_model_511_nearfield_migration_20260701`
write_scope: `12_review_20260702`

## Review Conclusion

The current package is closed only at `PASS_SMOKE_MATRIX_CLOSURE`. None of the
six unfinished Mass_model_511 TODO items in
`11_manuscript_support/TODO_AND_RECENT_UPDATES_20260702.md` are presently closed
as manuscript-ready physics results.

The current detector-only boundary is internally consistent: `G5 =
OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY` is acceptable for the detector branch,
but it is not an optics-background/full-chain closure. The `05_optics_migration/`
record is a parallel optics geometry migration and smoke verification only.

P1/P2/P3 outputs are correctly described as fix5-derived manuscript-revision
inputs. They must not be promoted as Mass_model_511 line-width, atmospheric-line,
or science-case performance results until replayed against Mass_model_511
full-stat Step05/Step08 authority.

## Evidence Baseline Read

- `00_manifest/FINAL_STATUS.md`: G0/G1/G2/G5/G3/G4/G6 pass at smoke level, but
  full-stat background publication closure, no-material-effect release, and
  regenerated Step06--Step08 mission-axis products remain `NOT_RUN` / not
  claimed.
- `06_smoke_closure/CONCLUSION.md`: explicitly says the conclusion is not
  full-stat or manuscript-release closure; full-stat campaign and downstream
  mission-axis regeneration are still required.
- `11_manuscript_support/TODO_AND_RECENT_UPDATES_20260702.md`: explicitly marks
  the six Mass_model_511 work items as unfinished and states P1/P2/P3 are from
  `fix5_fullstat_v2_exactpos_m50000_s260613`, not completed Mass_model_511.
- `core_md/README.md`: cleaned workspace index; the historical fix5 gate bundle is no longer retained here. Step06--Step08 must still depend on Step05
  that has passed provenance and normalization; delayed claims require
  ground-state correction, per-family TT division guard, and M-sampling
  inventory audit.

## Completion Matrix

| TODO | Required Evidence To Prove Completion | Current Evidence | Status | Gaps / Review Tests |
| --- | --- | --- | --- | --- |
| 1. Full-stat detector background campaign | Full-stat candidate Mass_model_511 prompt `instant`, `buildup`, and delayed transports at publication statistics; run manifests with event counts, seeds, return codes, log-error scans, and SIM headers proving the active geometry is `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`; no reuse of smoke-only transport as full-stat. | `03_detector_transport/transport_gate.json` reports `PASS_G3_G4_DETECTOR_TRANSPORT_SMOKE`; candidate prompt/buildup each have about 2.52M requested/generated smoke events; delayed S0/S1 uses 100k/1M triggers. `06_smoke_closure/mass_model_511_smoke_closure.json` has `fullstat_status: NOT_RUN`. | `OPEN` | Need full-stat run directories/manifests outside smoke labels, expected geometry in every SIM header, publication-stat delayed transport, and log scans. Reject closure if artifacts are only `*_smoke`, only baseline/fix5, or lack geometry-header proof. |
| 2. Full-stat Step05 detector-response release | Regenerated Step05 selected W2 prompt/delayed/background rates from the full-stat Mass_model_511 transports using unchanged Step05 normalization/cuts; rate uncertainties; selected event counts / effective counts; prompt family decomposition; delayed isotope/volume decomposition; prompt `1/sum(TT)` audit; delayed ground-state correction, per-family TT division guard, exact-position M-sampling inventory audit, and W/collimator delayed-origin checks. | `06_smoke_closure/CONCLUSION.md` and CSVs provide smoke Step05 rows only. Method file requires Step05 provenance and normalization before downstream gates. | `OPEN` | Need publication-stat Step05 release manifest and audit bundle. Reject closure if it lacks uncertainties/decomposition, uses smoke event catalogs, changes cuts/thresholds without authority update, or omits delayed normalization/M-sampling evidence. |
| 3. No-material-effect / replacement release | Formal Mass_model_511-vs-current-paper-authority pass/fail decision with decision JSON/MD; comparison against current paper authority, not old new_geo_re or smoke baseline only; thresholds for total background, delayed/W activation red flags, signal keep, Z20d/F3 held or improved, and uncertainty treatment. | Current smoke comparison gives W2 candidate/baseline deltas but explicitly says it is not a no-effect or replacement claim. `FINAL_STATUS.md` says no-effect release remains not claimed. | `OPEN` | Need full-stat Step05 plus Step08 inputs first. Reject closure if decision uses smoke proxy, old NF2/new_geo_re target only, or P1/P2/P3 fix5 numbers as Mass_model_511 decision evidence. |
| 4. Step06--Step08 mission-axis regeneration | Mass_model_511 Step06 mission-time fold from validated full-stat Step05 day-15 rates; 81-bin day 0--20 trajectory products; source-case rates; Step07/Step08 products with `Z20d`, `T3`, `F3(20d)`, live-time factor, and provenance tying back to Mass_model_511 full-stat Step05. | No Mass_model_511 Step06--Step08 products found in this package. `06_smoke_closure/CONCLUSION.md` says downstream mission-axis regeneration is still required. | `OPEN` | Need regenerated mission-axis outputs after TODO 2. Reject closure if Step06--Step08 point to fix5 full-stat authority, smoke Step05, or unlabeled baseline products. |
| 5. Optics integration decision | Explicit decision record saying either: (a) manuscript claims stay detector-only and optics migration is not coupled, or (b) a defined optics-to-detector/full-chain coupling path exists with coupled transport/response evidence and background-rate/no-effect decision. If (b), include geometry coupling provenance, transfer/coupling method, rates, uncertainties, and boundary update. | `04_bridge_resolution/bridge_resolution.json` says detector-only bridge not required and does not promote OF1 optics-local background. `05_optics_migration/optics_migration.md` says optics geometry is migrated/smoke verified but not coupled into detector background chain and makes no background-rate, bridge, or no-effect claim. | `OPEN_FOR_MANUSCRIPT_SCOPE_DECISION` | Detector-only G5 is not a blocker for detector branch, but manuscript optics claims need a separate coupling closure. Reject closure if `OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY` is cited as optics-background closure. |
| 6. P1/P2/P3 replay on Mass_model_511 | After full-stat Mass_model_511 Step05/Step08 exist: P1 line-width/window table regenerated from Mass_model_511 background and signal; P2 atmospheric 511-keV transfer rerun or validly reweighted on Mass_model_511 candidate geometry and included in background table; P3 science-case geometry framing re-evaluated with Mass_model_511 Step06--Step08 products and manuscript-facing numbers. | P1 input JSON points to `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`; P2 input JSON also points to that fix5 promotion decision; P3 summary declares current authority as that fix5 promotion decision. TODO file explicitly says these are fix5-derived inputs, not Mass_model_511 claims. | `OPEN_BLOCKED_BY_TODO_2_AND_TODO_4` | Need Mass_model_511-specific replay products with source manifests and geometry/provenance. Reject closure if P1/P2/P3 numbers remain fix5-derived while text implies Mass_model_511 replacement. |

## Detector-Only vs Optics Boundary Check

Current boundary status: `PASS_AS_DETECTOR_ONLY_BOUNDARY`.

Allowed now:

- Cite `PASS_SMOKE_MATRIX_CLOSURE` for detector smoke matrix.
- Cite `OPTICS_GEOMETRY_MIGRATED_AND_MC_SMOKE_VERIFIED_IN_REPO` as a parallel
  optics geometry migration / load / overlap / MC smoke record.
- Cite P1/P2/P3 fix5-derived files as manuscript-revision inputs.

Not allowed now:

- Mass_model_511 full-stat background rate.
- Mass_model_511 `Z20d`, `T3`, or `F3(20d)`.
- Mass_model_511 no-material-effect or replacement claim.
- Any claim that migrated multiband optics is coupled into detector
  background/full-chain rates.

## P1/P2/P3 Misattribution Check

Current status: `NO_CURRENT_FALSE_CLOSURE_FOUND_IN_REVIEWED_FILES`, with
`HIGH_RISK_IF_CARRIED_FORWARD_WITHOUT_RELABELING`.

Evidence:

- P1 summary uses fix5 promotion decision as input and reports current fix5
  `F3_20d_ph_cm2_s`.
- P2 summary uses fix5 promotion decision as input and reports an atmospheric
  511-keV correction to the fix5 unresolved-line threshold.
- P3 sufficiency summary declares the primary authority as
  `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`.
- The Mass_model_511 TODO file correctly labels all three as fix5-derived
  carry-forward updates.

Review rule for future products: if a file claims Mass_model_511 P1/P2/P3
closure, it must not depend on `fix5_fullstat_v2_exactpos_m50000_s260613` as the
physics authority except as the comparator baseline.

## Follow-Up Review Trigger

When execution-agent products appear, re-run this matrix against the new
manifests. A TODO can move to `CLOSED` only when all required evidence is present
and the false-closure tests in the `Gaps / Review Tests` column pass.
