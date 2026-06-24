# Background Validation Necessity and Paper Impact - Final

Status: `PASS_SUPPORT_UPDATED_WITH_BGO_P2_UNRESOLVED_DIFFERENCE`.

## 1. Current Paper Claim Boundary

This engineering pass supports the fix5 source/response validation and a same-envelope BGO material-control run.  It does **not** support a paper claim that BGO is better or worse than the current fix5/CsI active-shield configuration, because the BGO-vs-fix5 W2 total-background difference is not statistically resolved in the present simulation.

Allowed claims:
- fix5 prompt source normalization and selected-rate reconstruction are audited against existing Step05 authority;
- final W2 prompt `eplus` survivors are traced to annihilation-photon lineage in existing SIM records;
- delayed selected-rate PI-02 pooled uncertainty meets the 10% minimum convergence screen;
- a material-only BGO same-envelope geometry was built and overlap-checked;
- a staged BGO engineering run P0/P1/P2 was completed after explicit user approval, with source cards and SIM headers pointing to the BGO same-envelope geometry;
- BGO P2 W2 selected total background is statistically consistent with the fix5 authority under a simple independent-sample Poisson check.

Disallowed claims:
- BGO improves or worsens the detector background in a statistically resolved way;
- BGO should replace the current fix5/CsI authority;
- W/collimator selected W2 delayed contribution is zero in BGO, because no BGO selected-W2 event-origin decomposition was generated.

## 2. Veto Authority

The fixed Step05 active-veto authority for this harness is `shield_total_keV < 50 keV` with a `1 us` coincidence window.  The BGO engineering ingest used the same Step05 parser/selection logic and records:

- active veto threshold: `50.0 keV`;
- coincidence window: `1.0e-6 s`;
- prompt files: `68`;
- delayed stream: BGO exact-position M=50000 delayed transport;
- science stream: BGO focused EventList replay included.

No `.det` trigger/noise threshold or 40/60/90 keV threshold test was used as rate authority.

## 3. Prompt Normalization Audit

Prompt normalization status is `PASS`.  The reconstructed fix5 final W2 prompt rate is `0.0366410230297 cps` with `sum_w2=2.48623072039e-05`.  The G1 audit verifies 60 cm source radius consistency, `pi R^2` area handling, source-card flux closure, unique seeds, split/replica completeness, and independent selected-rate reconstruction against Step05.

The BGO P2 prompt run reused the fix5 source physics table and full-stat matrix:

- `gamma_events=10000000`;
- `gamma_splits=12`;
- `non_gamma_replicas=8`;
- `farfield_radius_cm=60.0`;
- `farfield_area_cm2=11309.733552923255`.

The BGO source-card manifest reports physics-source hash equality excluding geometry and identical flux sums for all 8 particle families.

## 4. eplus Survivor Physical Source

The final W2 prompt `eplus` contribution in fix5 is `0.0318897456148 cps`.  Existing SIM `IA`, `CC HIT`, and `HTsim` records classify `1.000` of selected eplus survivors into A-C.  In this run all 47 survivors classify as class A, aperture-coupled annihilation-photon lineage.

| class | process summary | events | rate cps |
|---|---|---:|---:|
| A | gamma/phot/annihil/e+ | 25 | `0.0169626306462` |
| A | gamma/compt/annihil/e+ | 20 | `0.0135701045169` |
| A | e-/eIoni/compt/gamma | 2 | `0.00135701045169` |

## 5. Delayed Convergence and BGO Delayed Normalization

Fix5 delayed convergence status is `DELAYED_CONVERGED`.  Four independent exact-position production-position samplings give 103 pooled selected W2 events, selected rate `0.00221278212897 cps`, sigma `0.000218031901787 cps`, and relative uncertainty `0.0985329`.

BGO P2 delayed source/transport checks:

- ground-state/division audit: `PASS`;
- gamma division: `12`;
- non-gamma division: `8`;
- exact-position PointSources: `50000`;
- fixed total activity: `29.1851895573 Bq`;
- delayed transport: `SE=1000000`, `ID=1000000`, `TE=32318.644709 s`;
- delayed SIM geometry: BGO same-envelope setup;
- source-level W/collimator activity: `2.18753223485 Bq`.

Boundary: no BGO selected-W2 event-origin decomposition was generated, so source-level W/collimator activity must not be translated into a selected W/collimator rate claim.

## 6. BGO Same-Envelope Geometry and P2 Simulation

The BGO same-envelope geometry status is `PASS_BGO_SAME_ENVELOPE_GEOMETRY`.  It changes `24` active-shield material lines from CsI to BGO while preserving geometry shape, position, mother, detector references, source radius, and Step05 selection plumbing.  The BGO material authority is MEGAlib `BGO`, density `7.1 g/cm3`, composition `Bi 4, Ge 3, O 12`.

Staged BGO run status:

| Stage | Instant | Buildup | Step05 |
|---|---|---|---|
| P0 smoke | PASS | PASS | PASS |
| P1 pilot | PASS | PASS | PASS |
| P2 production | PASS | PASS | PASS |

Focused signal replay also passed through BGO geometry: `37194/37194` events.

## 7. W2 BGO-vs-fix5 Result

Window: `510.58-511.42 keV`, final `side_compton_fov_pass`, active veto `<50 keV`.

| Case | Prompt cps | Delayed cps | Total background cps | Signal cps at 1e-4 ph cm^-2 s^-1 | Final bkg events |
|---|---:|---:|---:|---:|---:|
| BGO P2 engineering | `0.0339335772` | `0.00355831753` | `0.0374918947` | `0.00118056701` | 158 |
| fix5 current authority | `0.0366410230` | `0.00257520349` | `0.0392162265` | `0.00118587481` | 84 |

Simple independent-sample Poisson approximation:

- BGO sigma: `0.00518544925 cps`;
- fix5 sigma: `0.00500832932 cps`;
- BGO - fix5: `-0.00172433179 cps`;
- z-score: `-0.239`.

Interpretation: the BGO P2 engineering run is provenance-clean, but the W2 total-background difference is far below 2 sigma.  The correct paper-facing statement is that no statistically resolved material preference is supported by this control run.

## 8. Methods/Results/Discussion Help

Methods can cite the validated source normalization, fixed 50 keV/1 us veto authority, delayed normalization closure, exact-position source sampling, and material-only BGO derivation procedure.

Results can cite the BGO material-control run as an engineering cross-check showing no resolved W2 total-background difference relative to the current fix5 authority under matched source/statistics/selection.

Discussion should frame BGO as a material-control branch that did not reveal a hidden large material-driven background effect.  It should not be used to claim a design improvement.

## 9. Candidate English Insertion

The background model was subjected to an engineering validation pass.  The prompt source normalization was audited from the far-field source cards through selected-event rate reconstruction, and the dominant prompt positron survivors in the 511 keV window were traced to annihilation-photon lineages in the simulation records.  A same-envelope BGO material-control geometry was then generated by replacing only the active-shield material assignments while preserving the detector segmentation, geometry envelope, source model, and Step05 selection.  In the full BGO engineering run, the final W2 background rate was `0.03749 cps`, compared with `0.03922 cps` for the current fix5 authority, while the reference-flux signal rate was unchanged within 1%.  The difference is not statistically resolved in the present Monte Carlo sample, so no material-preference claim is made from this control run.

## 10. Claims Not Supported

- Do not claim BGO improves sensitivity or total background.
- Do not change headline sensitivity numbers from this document alone.
- Do not claim selected W/collimator-origin delayed events are absent in BGO.
- Do not describe the non-significant material-control difference as a design conclusion.

## 11. Provenance Table

| item | path |
|---|---|
| G1 prompt normalization | `01_prompt_source_audit/prompt_normalization_audit.json` |
| G2 eplus provenance | `02_prompt_eplus_provenance/eplus_survivor_provenance.json` |
| G3 delayed convergence | `03_delayed_convergence/delayed_selected_rate_convergence.json` |
| G4 BGO geometry | `04_bgo_variant/bgo_geometry_manifest.json` |
| BGO user approval | `05_matched_runs_resource_guard/USER_APPROVAL_20260624.md` |
| BGO P2 audit | `09_bgo_p2_completion_audit/bgo_p2_completion_audit.json` |
| BGO P2 Step05 | `06_bgo_matched_runs/p2/step05_ingest_exactpos_with_focus/bgo_engineering_step05_ingest_summary.json` |
| BGO P2 rates | `06_bgo_matched_runs/p2/step05_ingest_exactpos_with_focus/bgo_engineering_step05_ingest_rates.csv` |
| BGO P2 focused signal | `06_bgo_matched_runs/p2/step09_focus/step09_focus_summary.json` |
