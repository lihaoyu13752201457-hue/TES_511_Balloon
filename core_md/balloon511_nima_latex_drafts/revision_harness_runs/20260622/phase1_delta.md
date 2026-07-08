# Phase 1 delta: manuscript revision pass 1

Run directory: `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/`

Scope decision used: default **(b)** from the harness, i.e. reframe the paper as a reference-exposure statistical sensitivity estimate for an unresolved 511 keV line. The simulation/experiment skeleton was not expanded beyond Phase 1 unless needed to remove an incorrect or over-strong claim.

Primary manuscript: `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`

Derived review artifact: `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md`

Pass diff: `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/pass_1.diff`

## Verification run

- `latexmk -g -xelatex -interaction=nonstopmode -halt-on-error balloon511_nima_draft_en.tex`: PASS. The build produced `balloon511_nima_draft_en.pdf`; only underfull boxes and one small overfull box remain.
- `python3 tools/export_balloon511_tex_to_md.py --input balloon511_nima_draft_en.tex --output balloon511_nima_draft_en.md`: PASS.
- Debug-language grep over the `.tex` was run after the manuscript pass. The strict case-sensitive internal-token grep should return no manuscript debug tokens. A case-insensitive broad grep can match legitimate words such as `field-of-view` and `active-veto-pass`; those are not the harness `FoV-pass` or uppercase `PASS` artifacts.

## Phase 1 item status

| ID | Status | Evidence in current manuscript/artifacts |
|---|---|---|
| N1 | APPLIED | The 20 d folded count is corrected to about `6.8e4` background counts and `2.0e3` signal counts at lines 533-535. The source project evidence is `t3_t5_summary.csv`: `total_background_counts=67953.7748377242`, `total_source_counts=2033.1694381571392`. |
| N2 | APPLIED | The upstream Ge-proxy zero-event 95% upper rate is corrected to `6.38e-5 cps`, and the derived fraction is corrected to about `0.16%`, at lines 625-631. Provenance for the inputs is in the archived Step11 upstream Ge-proxy evidence: `old/stepwise_maintenance/step11_upstream_optics_background/status.json` and `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json` record `total_activity_Bq=0.4256743799573773`, `generated_events_seen=20000`, and zero selected events. The archived derived zero-count limit in that Step11 file is the old Cosima-time value and is not reused; the manuscript recomputes the physical effective exposure as `20000/activity`. |
| N3 | APPLIED | `S/F0` is now stated as selected effective area, `A_sel=11.9 cm^2`, at line 232. |
| N4 | APPLIED | Photon fluxes now use `\phcms` defined at line 23. Uses include the abstract line 40, reference flux lines 78, 198, 232, and result lines 550, 560, 573, 578, 642, 663. Particle source-plane fluxes were not blanket-rewritten as photon fluxes. |
| N5 | APPLIED | Main rates and thresholds are rounded to 2-3 significant figures where they are interpretive claims: lines 40, 232, 253, 550-560, 572-578, 625-631, 642, 663. More precise source-inventory values remain only where they identify a source-construction audit quantity rather than a final sensitivity claim. |
| N6 | APPLIED WITH TRACEABLE STATISTICAL SCALE | The delayed component is rounded to `2.6(5)e-3 cps` at line 575. Lines 585-589 state that this is a Monte Carlo statistical scale from the selected delayed event count and excludes source-sampling/model systematics. Lines 601-606 and 646 state that only 30 selected delayed events set the present precision. Project evidence: `fix5_w_activation_selected_w2_audit.json` gives `selected_events=30`, `selected_rate_hz=0.0025752034889400762`; `fix5_final_closure_report.json` gives `sigma=0.0004701656803528284`. |
| N7 | APPLIED | A pinned Markdown exporter was added at `tools/export_balloon511_tex_to_md.py`, and the harness pins the command. The `.tex` still uses the manuscript macro `\wii`; the Markdown artifact is generated from the source rather than hand edited. The exporter now normalizes generated `\in W_{511}` spacing so the read-copy no longer exposes `\inW_{511}`. |
| D1 | APPLIED | Visible manuscript language now uses `production-position-sampled delayed source` or equivalent wording; the old exact-position wording is removed from visible manuscript text and LaTeX labels. The two figure file names were also renamed to publication-neutral names and the `includegraphics` paths updated. |
| D2 | APPLIED | Debug/process phrasing such as `current sampled-position chain`, `full-statistics`, `manuscript-facing`, `headline hard-window`, `smoke test`, and loose closure wording was removed or replaced by publication wording. |
| D3 | APPLIED | Seed/source-card/PASS inventory language was removed from main text. Source-normalization checks are kept as physics bookkeeping at lines 611-620 and explicitly not presented as convergence. |
| D4 | APPLIED | The cleanup was checked with a strict internal-token grep. Any remaining broad-grep matches are legitimate publication terms, not the harness debug tokens. |
| W1 | APPLIED | The paper is reframed as `reference-exposure statistical sensitivity` in the abstract line 40, traceability table lines 84-99, methods lines 101 and 232, result table lines 576-578, discussion lines 642 and 652, and conclusion line 663. `detection time` is replaced by net on-source exposure. |
| W2 | APPLIED | The headline is explicitly an unresolved-line sensitivity at title line 34, abstract line 40, methods line 101, results lines 547-560 and 578, discussion line 642, and conclusion line 663. The Gaussian smearing convention is stated as a single event-energy proxy, not per-pixel smearing, at lines 160 and 187. |
| W3 | APPLIED | The proxy-model scope is strengthened at lines 156 and 650-654: no final flight CAD, full payload, lens supports, gondola, optical bench, or diffuse celestial fields are included in the primary budget. |
| W4 | APPLIED | Baseline event classes are defined as single-site, valid reconstructed multi-site, and unreconstructed retained events at lines 357-386. The multi-hit residual index is explicitly `i=1` to `n-2` at line 374. The text no longer calls unreconstructed events `FoV-pass`. |
| W5 | APPLIED | `S/sqrt(B)` is diagnostic only at lines 526-532. The 1% background-normalization caveat reducing approximate `Z` from about 7.8 to about 2.8 is included at lines 529-532. Nuisance/profile-likelihood language appears at lines 652 and 656-658. |
| W6 | APPLIED/SOFTENED | The detector response is stated as an idealized single Gaussian event-energy proxy with no per-pixel smearing and no gain drift, tails, pile-up, saturation, or response scans at lines 160 and 187. |
| W7 | APPLIED/SOFTENED | The title was revised to `Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity...` at line 34. |
| F1 | APPLIED | `placeins` is loaded and `\FloatBarrier` is placed before the references at line 678. The rebuilt PDF has no references-after-floats failure known from the previous pass. |
| F2 | PARTIAL PHASE-1 APPLIED | Captions were shortened/restyled where feasible without redrawing physics figures; hyperlink boxes are hidden through `\hypersetup{hidelinks}`. Full vector redraws, axis relabeling in image pixels, MC error bars, and optics-response plots remain in the Phase 2 figure backlog. |
| F3 | APPLIED | Main-text workflow detail was compressed into one traceability table at lines 82-99; detailed workflow tables are stated to be outside the main text. The source-inventory/PASS table was removed from main text and replaced by normalization-check prose at lines 611-620. |
| F4 | APPLIED | The toy Compton/FoV event diagram was removed from the main manuscript. The detector-selection figure now stops at the selected-rate/mission fold figure at lines 404-420. |
| F5 | APPLIED/SOFTENED | The selected-rate result and background composition are merged into one primary results table at lines 562-591. |
| C1cite | APPLIED WITH KNOWN METADATA CAVEAT | New bibliography entries include Jean 2006, Siegert 2019, De Cesare 2011, Roques 2015, Sato 2016 PARMA4.0, Allison 2016, Gallego/COSI balloon context, Beechert 2022, Sleator 2019, Ciabattoni 2025, and Cowan 2011 at lines 684-777. Final published metadata for arXiv-only/new COSI references should be checked by the author before submission. |

## Project-evidence links used for numerical corrections

- `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/t3_t5_summary.csv`: mission-fold count and `Z` evidence (`total_background_counts=67953.7748377242`, `total_source_counts=2033.1694381571392`, `final_counting_Z=7.79950030715189`, `F3=3.8464002588077305e-05`).
- `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/summary.json`: mean selected rate evidence (`w2_dt_weighted_background_final_cps=0.03935462874339332`, `w2_dt_weighted_science_final_cps_at_ref_flux=0.001177483126730607`).
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json`: delayed selected event count and rate evidence (`selected_events=30`, `selected_rate_hz=0.0025752034889400762`, zero W/collimator selected events in the project audit source).
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_final_closure_report.json`: selected-rate comparison table, delayed uncertainty, and headline statistical threshold evidence.
- `old/stepwise_maintenance/step11_upstream_optics_background/status.json` and `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json`: archived upstream Ge-proxy delayed component provenance for the N2 zero-count correction (`0.4256743799573773 Bq`, `20000` generated decays, zero selected events). These files also preserve the old derived Cosima-time upper-limit value; the manuscript deliberately recomputes the corrected physical-live-time upper limit required by the review/harness.

## Deliberate Phase 1 non-actions

- No new simulation was run for trajectory/slant-column, broad-line cases, full-payload/lens-support prompt background, delayed selected-rate convergence, Revan/Mimrec validation, or spatial-spectral likelihood.
- Those items remain Phase 2/backlog work under B1, B2, B3, B4, B6, B6d, B7, B8, B9, and Bfig.
- The manuscript now states the corresponding limitations rather than claiming those validations are complete.
