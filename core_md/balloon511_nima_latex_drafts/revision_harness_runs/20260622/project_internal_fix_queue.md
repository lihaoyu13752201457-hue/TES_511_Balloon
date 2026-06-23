# Project-internal fix queue after Phase 1

Status date: 2026-06-23

Scope: this is the project-side backlog that cannot be closed by manuscript
wording alone. It is not manuscript text. It covers simulation reruns,
provenance repair, configuration authority, validation tooling, figure/data
pipeline work, and claim-boundary decisions needed before stronger NIM A claims.

Current paper scope after Phase 1: reference-exposure selected-rate estimate for
an unresolved 511 keV line in the current detector/cryostat proxy mass model.
Under that scope the paper can stay Phase-1 closed, but stronger claims require
the work below.

## How I judge value

| Judgment | Meaning | Use in this queue |
|---|---|---|
| DO NOW | Low ambiguity, high leverage, or likely reviewer-critical even for the current NIM A estimate. | Should be scheduled before the next serious manuscript pass. |
| WORTH DOING | Real scientific/engineering value, but not necessarily needed to keep the current scoped claim. | Do before expanding claims or before submission if time permits. |
| CONDITIONAL | Worth doing only if the paper claim changes. | Do only if moving from proxy selected-rate estimate to flight-performance forecast or design optimization. |
| NOT WORTH NOW | Valid concern, but cost/scope is disproportionate for this paper phase. | Keep as limitation/future work; do not spend current effort unless the project goal changes. |

## Executive priority list

| Order | ID | Short name | Judgment | Why this order |
|---:|---|---|---|---|
| 1 | PI-01 | Evidence/provenance promotion and stale-artifact quarantine | DO NOW | Prevents old wrong numbers and debug files from leaking back into the paper. |
| 2 | PI-02 | Delayed selected-rate convergence | DO NOW | Current delayed component is based on 30 selected events; this is the weakest quantitative result. |
| 3 | PI-03 | Source-normalization audit | DO NOW | Units/source-plane handling is central to every rate and effective-area claim. |
| 4 | PI-04 | Simulation configuration authority | DO NOW | NIM A reproducibility expectation; cheap if run metadata can be located. |
| 5 | PI-05 | Figure/data pipeline rebuild for final paper figures | DO NOW/WORTH DOING | Not a physics rerun, but final figures need cleaner evidence and uncertainty display. |
| 6 | PI-06 | Selected delayed decomposition | WORTH DOING | Strengthens the activation story and explains the residual delayed component. |
| 7 | PI-07 | Likelihood/nuisance treatment | WORTH DOING | Needed before publication-level sensitivity language; can be deferred if paper stays diagnostic. |
| 8 | PI-08 | Representative trajectory/slant-column/duty-cycle fold | WORTH DOING | Needed before interpreting the threshold as mission performance. |
| 9 | PI-09 | Full-payload/lens-support prompt background boundary | CONDITIONAL | Mandatory for flight-background claims; not mandatory for a clearly scoped proxy study. |
| 10 | PI-10 | Reconstruction validation | CONDITIONAL | Needed if multi-hit topology is claimed as final reconstruction, not just baseline selection. |
| 11 | PI-11 | Detector-response envelope | CONDITIONAL | A bounded envelope is useful; a full detector engine is too large for this paper phase. |
| 12 | PI-12 | Broad-line/centroid-offset cases | CONDITIONAL | Useful for astrophysical interpretation; optional if headline remains unresolved-line. |
| 13 | PI-13 | Prompt/delayed spectra and cut-flow diagnostics | WORTH DOING | Helps reviewers understand backgrounds and figures, but does not change the core rate. |
| 14 | PI-14 | Shield-material trade study | NOT WORTH NOW | Real design issue, but it opens a separate optimization paper. |
| 15 | PI-15 | Diffuse sky/foreground model | NOT WORTH NOW | Astrophysical forecast layer, not needed for instrumental-background estimate. |
| 16 | PI-16 | Full detector/cryostat CAD and engineering services model | NOT WORTH NOW/CONDITIONAL | Needed for flight CDR-level claims, not for the current proxy paper. |

## Detailed project-side repair list

### PI-01: Evidence/provenance promotion and stale-artifact quarantine

Judgment: DO NOW.

What to fix:
- Create a current paper-evidence manifest outside `old/` for all numbers still
  used by the paper.
- Promote the upstream Ge-proxy delayed evidence into a current read-only
  evidence summary, or add a manifest that points to the archived file and marks
  the stale derived upper limit as stale.
- Mark deprecated manuscript-support tables and old workflow tables so they
  cannot be accidentally re-input into the paper.
- Separate current English paper artifacts, Chinese/internal drafts, generated
  PDFs, figure source tables, and obsolete support resources.

Why it matters:
- The N2 upstream Ge-proxy result is now corrected in the manuscript, but the
  underlying authority currently lives under an archived path and that archived
  JSON also contains the old wrong zero-count upper rate.
- This is exactly the kind of project hygiene failure that causes a correct
  manuscript to regress later.

Expected closure artifact:
- `paper_evidence_manifest_20260623.{md,json}` with:
  - source path for each manuscript number;
  - value used in the paper;
  - whether the source is current, archived, or stale;
  - explicit note that the old Cosima-time zero-count upper limit is stale;
  - checksum or git hash where possible.
- `deprecated_manifest.md` for old manuscript-support tables.

My consideration:
- This is the cheapest high-confidence fix. It does not require rerunning
  simulation and directly lowers future audit risk. I would do it before any new
  physics run.

### PI-02: Delayed selected-rate convergence

Judgment: DO NOW.

What to fix:
- Rerun delayed replay with higher delayed-decay statistics.
- Use multiple production-position samplings and, if applicable, multiple random
  seeds.
- Report selected counts, selected rates, weighted variance, between-sampling
  variance, and convergence against the current selected-rate value.
- Keep the source-normalization audit separate from selected-rate convergence.

Why it matters:
- The current delayed component is `2.6(5)e-3 cps`, with the statistical scale
  inferred from 30 selected delayed events.
- That is acceptable as a clearly limited diagnostic value, but not enough for a
  final activation-background claim.

Expected closure artifact:
- `outputs/reports/.../delayed_selected_rate_convergence.md`
- `outputs/reports/.../delayed_selected_rate_convergence.json`
- Optional `delayed_selected_rate_convergence.csv` with one row per run.

Minimum content:
- source activity used;
- number of generated decays;
- number of selected events;
- selected rate and statistical uncertainty;
- weighted `sum_w`, `sum_w2` if weighted;
- production-position sampling ID;
- seed or deterministic sampling tag;
- pass/fail convergence statement.

My consideration:
- This is the most important physics fix. It is worth doing even if the paper
  remains a scoped selected-rate estimate, because delayed activation is a main
  novelty of the current work.

### PI-03: Source-normalization audit

Judgment: DO NOW.

What to fix:
- Write a units-complete derivation for prompt atmospheric source weights,
  delayed source activity normalization, and focused point-source photon
  normalization.
- Define the source-plane area convention and projected-area handling.
- Archive or summarize EXPACS/PARMA inputs and the conversion to MEGAlib source
  cards.
- Add analytic checks showing that per-particle-family exposure and weights close.

Why it matters:
- The manuscript has fixed photon units and selected effective area, but the
  project should still have a single authority explaining how every source card
  becomes a selected rate.
- Without this, reviewers can challenge the rate normalization even if the prose
  is clean.

Expected closure artifact:
- `source_normalization_audit.md`
- `source_normalization_audit.json`
- optional compact source-card manifest with paths, hashes, source-plane area,
  flux/integrated rate, generated primaries, and exposure.

My consideration:
- Very worth doing. It is mostly documentation plus validation around existing
  inputs. It protects all headline rates.

### PI-04: Simulation configuration authority

Judgment: DO NOW.

What to fix:
- Collect actual Geant4, MEGAlib/Cosima, ROOT, compiler, physics list, decay data,
  production cuts, radioactive-decay settings, custom patches/hooks, and seed
  policy from the real run environment.
- Do not invent missing values from memory. Unknowns should be marked `UNKNOWN`
  with a plan to recover them.

Why it matters:
- NIM A readers expect reproducible instrument simulations.
- The paper should not include guessed software versions or hidden custom hooks.

Expected closure artifact:
- `simulation_config_authority.json`
- generated `simulation_config_table.tex` or `simulation_config_table.md`
- short note explaining missing metadata, if any.

My consideration:
- High value and likely cheap. This should be done before submission. It is a
  reproducibility requirement, not optional polish.

### PI-05: Figure/data pipeline rebuild for final paper figures

Judgment: DO NOW for hygiene and source traceability; WORTH DOING for full visual
redraw.

What to fix:
- Rebuild figure-generation scripts so every figure has traceable source data.
- Replace tiny raster labels with readable vector or high-resolution labels.
- Add uncertainty bars where Monte Carlo statistics matter.
- Add or improve:
  - effective-area or selected-area response figure;
  - focal spot / encircled-energy diagnostic;
  - selected prompt/delayed spectra;
  - separated cut-flow figure rather than overloaded multi-panel diagnostics;
  - mission-time fold figure with clear distinction between day-15 rate and
    time-folded counts.

Why it matters:
- Phase 1 removed the worst toy/debug figure and fixed float placement, but the
  current figures are still closer to engineering diagnostics than final NIM A
  figures.

Expected closure artifact:
- regenerated figure scripts under a clear figure pipeline directory;
- `figures_audit.md` with source data paths, script command, output hashes, and
  visual QA notes;
- updated figure PNG/PDF/SVG outputs.

My consideration:
- Worth doing before submission. It does not need to block physics closure, but
  it will strongly affect reviewer trust and readability.

### PI-06: Selected delayed-background decomposition

Judgment: WORTH DOING.

What to fix:
- Decompose selected delayed background by isotope, material/volume, production
  particle family, decay mode, and selected rate contribution.
- Report both source activity contribution and selected-rate contribution; these
  are not the same.
- Identify dominant selected channels and whether they are physically plausible.

Why it matters:
- The current manuscript correctly says delayed activation is spatially and
  materially structured, but it does not yet show which channels drive the
  selected delayed rate.
- This is the natural companion to the production-position-sampled delayed source
  method.

Expected closure artifact:
- `delayed_selected_decomposition.csv`
- `delayed_selected_decomposition.json`
- compact figure/table for manuscript or supplement.

My consideration:
- Worth doing after PI-02. It is not as urgent as convergence, but it converts
  the delayed result from a number into a physical explanation.

### PI-07: Likelihood and nuisance-parameter sensitivity treatment

Judgment: WORTH DOING before final sensitivity claims; not mandatory for the
current diagnostic selected-rate estimate.

What to fix:
- Replace headline reliance on `S/sqrt(B)` with a spatial-spectral or at least
  energy-window likelihood.
- Include nuisance parameters for prompt normalization, delayed normalization,
  energy-scale/resolution, atmospheric transmission, and selected effective area
  where possible.
- Report median expected `3 sigma`/`5 sigma` thresholds and upper limits under
  specified nuisance assumptions.
- Include coverage or toy-MC checks if claiming discovery/upper-limit
  performance.

Why it matters:
- The current `S/sqrt(B)` metric is explicitly diagnostic. A 1% background
  normalization uncertainty can materially reduce the apparent significance.

Expected closure artifact:
- likelihood implementation;
- `likelihood_sensitivity_report.md/json`;
- plots comparing diagnostic counting threshold and nuisance-profile threshold.

My consideration:
- Scientifically important, but I would not start here. It depends on stable
  background components and systematics definitions. Do PI-02, PI-03, and PI-04
  first.

### PI-08: Representative trajectory, visibility, duty cycle, and slant-column transmission

Judgment: WORTH DOING if the paper wants mission-performance language.

What to fix:
- Replace or supplement the synthetic 20 d reference trajectory with a
  representative balloon trajectory and a target-specific visibility model.
- Compute source zenith angle, line-of-sight atmospheric column, transmission,
  occultation/visibility, and on-source duty cycle.
- Keep the current synthetic trajectory as a controlled reference if useful, but
  do not call it a flight forecast.

Why it matters:
- The current threshold assumes continuous on-source exposure and a reference
  atmospheric transmission treatment. That is acceptable only as a reference
  calculation.

Expected closure artifact:
- `trajectory_visibility_slant_column_report.md`
- `trajectory_visibility_slant_column_report.json`
- optional time-series table with altitude, latitude, longitude, target zenith
  angle, transmission, live exposure, and source rate scale.

My consideration:
- Worth doing if you want to persuade NIM A reviewers that the number maps to a
  real observation. If the article stays a detector-coupled reference estimate,
  this can be a follow-up.

### PI-09: Full-payload/lens-support prompt background and optics self-background boundary

Judgment: CONDITIONAL. Mandatory for flight-background claims; not required for a
clearly scoped detector/cryostat proxy paper.

What to fix:
- Add lens support structures, optical bench, gondola-adjacent mass, electronics,
  pressure vessels, services, and any major line-of-sight or side-entry mass that
  can affect prompt background.
- Separate upstream hardware prompt self-background from ordinary
  detector/cryostat atmospheric prompt background.
- If not modeling it, create a formal scope-boundary document that says exactly
  which masses are excluded and why.

Why it matters:
- The present result is not a full-payload background closure.
- Upstream Ge-proxy delayed contribution is bounded, but prompt self-background
  from upstream hardware is not in the primary budget.

Expected closure artifact:
- full-payload or partial-payload geometry manifest;
- prompt self-background selected-rate budget;
- or `scope_boundary_full_payload_exclusions.md` if deferred.

My consideration:
- Do not start this unless the paper claim expands to flight performance. It can
  become a large geometry project. For current NIM A scope, a clean exclusion
  statement may be a better tradeoff.

### PI-10: Multi-hit reconstruction validation

Judgment: CONDITIONAL/WORTH DOING.

What to fix:
- Cross-check the current retained multi-hit classes with Revan/Mimrec or an
  independent reconstruction implementation.
- Report true/false acceptance, ARM or source-direction residuals, confusion
  matrix by multiplicity, and selected-rate impact.
- Distinguish single-site, valid reconstructed multi-site, and unreconstructed
  retained events.

Why it matters:
- The current manuscript correctly avoids calling unreconstructed retained events
  field-of-view passing, but the topology logic is still not a final
  reconstruction validation.

Expected closure artifact:
- `reconstruction_validation_report.md/json`;
- confusion-matrix table;
- selected-rate comparison with/without stricter multi-hit rejection.

My consideration:
- Worth doing before claiming a finalized reconstruction method. Not essential if
  the paper keeps topology selection as a baseline detector-level cut.

### PI-11: Detector-response envelope

Judgment: CONDITIONAL. A bounded envelope is useful; a full detector-effects
engine is NOT WORTH NOW.

What to fix:
- Instead of building a complete TES/CsI detector simulator, run a bounded
  sensitivity envelope for key response parameters:
  - TES Gaussian width;
  - non-Gaussian tail proxy;
  - energy-scale shift;
  - pile-up/dead-time proxy;
  - CsI veto threshold;
  - veto coincidence window;
  - shield energy resolution or threshold efficiency if available.

Why it matters:
- The current detector response is idealized. Reviewers will ask how fragile the
  threshold is to reasonable response changes.

Expected closure artifact:
- `detector_response_envelope_scan.md/json`;
- table of parameter ranges and impact on selected signal/background/threshold.

My consideration:
- Do the envelope, not the full engine. A full detector-effects engine is a
  separate TES/instrument paper and likely too expensive for the current NIM A
  simulation estimate.

### PI-12: Broad-line and centroid-offset response cases

Judgment: CONDITIONAL.

What to fix:
- Run representative source cases with broader intrinsic line widths and/or
  centroid shifts.
- At minimum, test a narrow unresolved case versus one or two astrophysically
  motivated broader cases.
- Recompute the analysis window or show loss if the current unresolved-line
  window is retained.

Why it matters:
- The current result is explicitly for an unresolved line. Astrophysical 511 keV
  sources can have line broadening or centroid shifts.

Expected closure artifact:
- `source_line_profile_case_scan.md/json`;
- table with line width, centroid offset, selected signal rate, background window
  rate, and threshold.

My consideration:
- Useful, but not mandatory unless the paper discusses broad-line science. Do not
  run a large grid until the core unresolved-line result is stable.

### PI-13: Prompt/delayed spectra and cut-flow diagnostics

Judgment: WORTH DOING.

What to fix:
- Produce selected and pre-selected spectra around the 511 keV region for prompt,
  delayed, and signal streams.
- Split cut-flow into clear stages: pre-veto, active-shield pass, topology pass,
  energy-window pass, and final selected rate.
- Add Monte Carlo uncertainties to rates and fractions.

Why it matters:
- Reviewers need to see whether the selected 511 keV window is driven by a line,
  continuum leakage, activation lines, or topology/veto behavior.

Expected closure artifact:
- `selected_spectra_and_cutflow_report.md/json`;
- figure source tables;
- final plot scripts.

My consideration:
- Worth doing because it is explanatory and helps figure quality. It may use
  existing event outputs, so it should be cheaper than new full simulations.

### PI-14: CsI alternative-shield trade study

Judgment: NOT WORTH NOW.

What to fix if reopened:
- Compare CsI with one or more alternative active-shield materials using matched
  geometry, veto assumptions, activation production, and selected background.

Why it matters:
- Iodine activation is a real engineering signal.

Expected closure artifact if reopened:
- `shield_material_trade_study.md/json`.

My consideration:
- Do not do this for the current paper. It changes the design question and can
  easily become a separate optimization study. Keep one sentence in future work.

### PI-15: Diffuse celestial sky and astrophysical foregrounds

Judgment: NOT WORTH NOW.

What to fix if reopened:
- Add diffuse Galactic 511 keV emission, continuum foregrounds, cosmic diffuse
  gamma background, and off-axis source leakage to the observation likelihood.

Why it matters:
- Needed for a real observation forecast or target-specific analysis.

Expected closure artifact if reopened:
- `diffuse_foreground_model_report.md/json`.

My consideration:
- Not worth doing inside this instrumental-background paper phase. It should
  remain scoped out unless the paper becomes an astrophysical observation
  forecast.

### PI-16: Full detector/cryostat CAD and engineering services model

Judgment: NOT WORTH NOW for current scope; CONDITIONAL for flight design claims.

What to fix if reopened:
- Replace proxy masses with a final CAD-derived mass model, including supports,
  harnesses, readout boxes, thermal straps, service penetrations, and detailed
  material inventories.

Why it matters:
- Proxy geometry limits the meaning of absolute flight-background claims.

Expected closure artifact if reopened:
- CAD-to-Geant4 geometry manifest;
- material/mass table;
- comparison of proxy versus CAD selected rates.

My consideration:
- Too large for this paper phase. It is worth doing only when the engineering
  design is stable enough that the added detail is meaningful.

### PI-17: Parameter scans for threshold, veto, shielding, and analysis window

Judgment: WORTH DOING if resources allow; otherwise lower priority than PI-02 to
PI-06.

What to fix:
- Scan CsI threshold, veto window, line-window width, TES resolution proxy, and
  possibly W sleeve/aperture parameters within the current geometry.
- Report selected signal, prompt background, delayed background, and threshold for
  each case.

Why it matters:
- Gives reviewers a sense of robustness and identifies whether the result is
  tuned to one analysis point.

Expected closure artifact:
- `analysis_parameter_scan_report.md/json`;
- compact robustness table.

My consideration:
- Worth doing after the main provenance/statistics fixes. Avoid using this as a
  new geometry optimization unless the design is explicitly reopened.

### PI-18: Activation-history validation and nuclear-data checks

Judgment: WORTH DOING for activation credibility, but after PI-02.

What to fix:
- Check dominant activation channels against decay data, half-lives, and expected
  decay signatures.
- Record which nuclear data library and radioactive-decay settings were used.
- Compare source inventory, transported delayed spectra, and selected delayed
  channels for consistency.

Why it matters:
- The project already uses NUBASE ground-state corrections. A stronger activation
  claim needs a short validation chain from produced isotope inventory to selected
  detector events.

Expected closure artifact:
- `activation_history_validation.md/json`;
- table of dominant isotopes/materials/decay modes and selected contribution.

My consideration:
- Worth doing, but it should be coupled to PI-02 and PI-06 rather than run as an
  isolated documentation exercise.

### PI-19: Reproducible archive packaging

Judgment: WORTH DOING before submission.

What to fix:
- Create an archive manifest for code, geometry, source definitions, run
  manifests, seeds, derived data, figure scripts, and manuscript source.
- Decide which raw Cosima/event outputs are too large for the paper archive and
  represent them by commands, checksums, and summaries.
- Separate public-shareable data from machine-local scratch outputs.

Why it matters:
- The paper already promises data/software availability. The project needs a
  concrete package plan before submission.

Expected closure artifact:
- `paper_reproducibility_archive_manifest.md/json`;
- checksum list;
- generated README for the public archive.

My consideration:
- Worth doing. It is not a physics improvement, but it is necessary for a clean
  NIM A submission and future review response.

## Items I would not spend current effort on

| Item | Reason not worth doing now | What to do instead |
|---|---|---|
| Full TES/CsI detector electronics simulation | Too broad; would become a detector-characterization project. | Run bounded response envelope PI-11 and state limitations. |
| Full CsI-vs-alternative shield optimization | Reopens instrument design and geometry optimization. | Keep iodine activation as future-work motivation. |
| Diffuse sky and foreground modeling | Belongs to an observation forecast, not this detector-background estimate. | Keep scoped out; add later only for target-specific likelihood. |
| Full CAD replacement of proxy geometry | Only useful when engineering design is stable; high effort. | Keep proxy boundary clear or add selected missing masses only if claim expands. |
| Large broad-line/off-axis grid | Not needed for unresolved-line headline. | Run one or two representative cases only if the science discussion needs them. |
| New geometry optimization | User has not reopened geometry design; risks derailing closure. | Preserve current geometry and validate it. |

## Suggested engineering sequence

1. Close no-simulation hygiene first: PI-01, PI-03, PI-04, PI-19.
2. Run the key physics-statistics closure: PI-02, then PI-06 and PI-18.
3. Improve paper evidence presentation: PI-05 and PI-13.
4. Add robustness methods only after rates are stable: PI-07, PI-11, PI-17.
5. Expand claim scope only by explicit decision: PI-08, PI-09, PI-10, PI-12.
6. Leave PI-14, PI-15, and PI-16 as future work unless the project goal changes.

## Minimal acceptance checks for future project-side fixes

- Every new number used by the manuscript has a machine-readable provenance file
  and a short human-readable audit note.
- Any old/stale output retained for provenance is explicitly marked stale where
  appropriate and is not used directly as manuscript-facing authority.
- Current paper-facing `.tex/.md` files remain clean of internal/debug wording.
- New simulation outputs do not overwrite existing authority outputs; they use a
  new run directory and a manifest.
- Any run used for a rate claim records source card path, geometry path, generated
  events, physical exposure/activity, selected events, selected rate, uncertainty
  method, and code/config metadata.
- If a claim changes from "reference selected-rate estimate" to "flight
  performance", the queue must require PI-07, PI-08, and PI-09 before the claim is
  accepted.
