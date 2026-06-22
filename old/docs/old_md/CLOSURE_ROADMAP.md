# NEW_GEO_RE Closure Roadmap — toward BALLOONSIM parity

Author: review pass (Claude Opus 4.8), 2026-05-29.
Purpose: a step-by-step, self-consistent plan to bring `new_geo_re` from its
current Step01–05 state up to the analysis depth of the reference workflow
`/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM` (referred to below as
**BALLOONSIM**), while keeping the cleaner `new_geo_re` ADR mass model and unit
discipline.

---

## 0. How to use this document (for CODEX)

- This is an execution guide, not a finished record. Do the steps in the order
  of Section 8 unless a dependency says otherwise.
- Every new step must produce: (a) code under `code/tools/` or
  `stepwise_maintenance/stepNN_*/code/`, (b) a `README.md` in its step dir, (c)
  machine-readable JSON/CSV outputs, (d) an entry in
  `stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md`, and (e) a memory line.
- **Port logic, not artifacts.** Read the BALLOONSIM reference script, understand
  it, then re-implement against `new_geo_re` paths and the 35 cm far-field /
  ADR cm geometry. Do **not** copy BALLOONSIM source cards or configs verbatim —
  several still carry the legacy 10× unit bug (Section 3, R1).
- Label claim levels honestly (`L1_*`, `scaffold`, `template_analysis`,
  `not_full_profile_likelihood`). The reference workflow does this and it is the
  reason its conclusions survive scrutiny.
- After each step, run the validator (Step 10 once it exists) and keep its exit
  code at 0.

---

## 1. Current state (what `new_geo_re` already has)

| Step | Status | Substance |
| --- | --- | --- |
| 01 geometry | done | ADR v4c cm geometry, Be window 1.898/0.015 cm, CeBr3 active shield, A4K omitted. `outputs/geometry/.../bounds.json` is authority. |
| 02 raw sim | done | Prompt `instant` + activation `buildup` + delayed transport; event-count-aligned production (25,210,216 primaries; delayed TE 9003.74 s). 35 cm far-field. |
| 03 delayed source | done | RPIP spatial source, ground-state fix (4728→4674, 110.088 Bq), no-RPIP/unknown caveats explicit. |
| 04 opticsim | scaffold only | Reused `fix` Laue evidence. **No fresh detector-coupled EventList bridge.** Not a mechanical design. |
| 05 veto timeline | done | One Poisson time axis (science+prompt+delayed), 1 µs coincidence, active-shield/BGO veto (50 keV), Compton/FoV veto (Be-window disk reference). Static `science_sensitivity` (flux_3σ at fixed exposures). |
| 06 mission time variation | done as `L0_PROXY_COMPLETE` | Synthetic small-offset trajectory (`±0.25°` lat/lon, `±2.5 km` altitude), calibrated 511 keV atmospheric transmission, per-nuclide delayed ODE ledger, and time-dependent prompt/delayed/science rates. |
| 07 source cases | done as `L1_SOURCE_CASE_RATE_FOLDING` | A/B/C compact-GC, diffuse bulge/disk, and V404 benchmark cases; cm source cards; spectra/sky models; folded rates; point-vs-diffuse diagnostics. A on-axis mono source closes exactly to Step05. |
| 08 significance | done as `L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL` | Step07 cases folded over Step06 time axis; analytic `exp(-R*1us)` accidental live factor; counting T3/T5 tables; no profile-likelihood gain claimed. |
| 09 optics bridge | done as `L1_OPTICS_EVENTLIST_BRIDGE` | Step04 Laue phase-space converted to new_geo_re cm EventList; 1225 rows; max radius 0.3515 cm inside Be; 1000-trigger Cosima smoke transport succeeded. |
| 10 validator | done | `code/tools/validate_new_geo_re.py`; current `VALIDATION.md` status is `PASS`. |

Remaining major work is now upgrade-level, not closure-level: add optics hardware mass to prompt/delayed simulations and replace L1 counting/template proxies with higher-fidelity likelihood/systematics if needed.
The current optics policy remains modular: use the present Step04/Step05
temporary Laue/on-axis beam scaffold until a new optics bridge is supplied.
2026-05-29 Claude follow-up accepted one closure fix: Step06 prompt/delayed-production
L0 scaling now uses the secondary-dominated float-regime sign, increasing with
residual atmospheric depth and decreasing with altitude. Validator pins this
trend while keeping 511 keV atmospheric transmission with the opposite
Beer-Lambert altitude trend.

---

## 2. Gap analysis vs BALLOONSIM

| Capability | BALLOONSIM reference | `new_geo_re` | Gap → closure step |
| --- | --- | --- | --- |
| Mission trajectory + environment (alt/lat/lon/cutoff/depth) | `tools/build_environment_grid.py`, `phase2_parma_grid_driver.cpp`, `reports_260516/source_time_update/trajectory_profile.csv` | Step06 `L0_proxy` small-offset profile done; no PARMA grid yet | Step06 upgrade later if real environment grid is needed |
| Prompt reweight by time/environment | `tools/reweight_prompt_by_environment.py` | Step06 rate-level L0 proxy done; secondary-dominated depth sign fixed and validator-guarded | Step08 uses it; later replace with EXPACS/PARMA |
| Time-variable delayed (half-life ODE, A_j(t)) | `tools/build_time_variable_delayed_sources.py`, `Records/03_mission_time_variation` | Step06 per-nuclide ODE ledger done, anchored to day-15; rate folding still uses total-activity proxy | Later add per-nuclide detector-response matrix before line-window claims |
| Atmospheric transmission T_atm_511(t) | `environment_grid_real/science_atmospheric_transmission.csv` | Step06 calibrated Beer-Lambert proxy done | Later replace with real atmosphere grid if supplied |
| Astrophysical source cases (point/diffuse/V404/GC, sky models) | `build_511_sky_models.py`, `build_astro_511_spectra.py`, `fold_511_source_cases.py`, `make_511_phase10_point_diffuse_report.py` | Step07 L1 source-case folding done; no full optics focal map | Step09 can replace optics response; Step08 consumes rates |
| Time-dependent cumulative significance / T3-day crossing | `make_260516_source_time_update.py`, `make_phase2_cam511_paper_flux_significance_vs_time.py` | Step08 L1 counting T3/T5 done | Later replace with profile likelihood if templates are available |
| Accidental / pile-up veto model | `tools/estimate_science_accidental_veto.py`, `tools/scan_timing_windows.py` | Step08 analytic live factor done; fast catalog energy/BGO sanity anchor only | Later add full per-rate MC timing anchors if needed |
| Spatial-spectral / profile likelihood | `tools/fit_511_spatial_spectral_likelihood.py`, ERL metric (`metric_closure_final.json`) | Step08 intentionally sets template proxy gain to 1.0 | Optional profile-likelihood upgrade; no current headline claim |
| Detector-coupled optics EventList bridge | `tools/opticsim_phase_space_bridge.py`, `analyze_opticsim_laue_detector_replay.py`, `estimate_optics_focused_gamma_background.py` | Step09 EventList bridge and smoke transport done | Future upgrade: optics hardware prompt/delayed mass transport |
| Workspace closure validator (hard checks) | `tools/validate_workspace.py`, `validate_phase*.py` | Step10 validator extended through Step09; `VALIDATION.md` PASS | Continue extending for future upgrades |

---

## 3. Guiding principles / invariants (must hold across all steps)

- **R1 — Unit discipline.** All geometry numbers are cm; `bounds.json` is the
  only length authority. Any source-card beam-z **must** lie inside the geometry
  bounding box. BALLOONSIM still has stale 10× cards (`z=127.66`, `r=18.0`); do
  not port them. Add the unit guard test in Step 10.
- **R2 — Normalization is geometry-local.** `new_geo_re` uses a 35 cm far-field
  radius (area 3848.45 cm², prompt time 541.38 s). The detection rate is
  invariant to far-field radius only while the start sphere encloses the
  detector (max extent ≈ 25.75 cm < 35 cm — OK). Never reuse BALLOONSIM's 150 cm
  prompt time; always recompute from `runs/step02_instant_*/normalization.json`.
- **R3 — Response-matrix discipline.** Treat each Geant4/Cosima run as a sample
  of a per-particle response `K_j(E, cuts)`. Time/flux variation enters only
  through rates `r(t)` and activities `A_j(t)`, **not** through re-running
  transport per time bin. Veto efficiency is a property of `K_j`, not of time
  (see Step 08 / Section 6).
- **R4 — Two layers of randomness stay separated.** Geant4 = response sampling;
  Poisson overlay = counting + timing + accidentals. Re-sampling the timeline is
  only needed to anchor the accidental correction `Δ(R)`, at a few rate points —
  never per mission bin.
- **R5 — Claim control.** Every significance/limit carries a `claim_level` and
  states whether it is counting, template, or profile-likelihood, and whether it
  includes time-variation and accidental veto.
- **R6 — Reproducibility.** Each step regenerates its outputs from a single
  documented command; no manual numbers.

---

## 4. Closure steps

### Step 06 — Mission time-variation layer

**Goal.** Replace the single day-15 snapshot with a trajectory-driven time axis:
prompt, delayed, and science streams each become time-dependent rates over the
flight, on a synthetic/reference balloon profile.

**Why.** This is the single biggest analysis gap and the prerequisite for any
"day-N to 3σ" statement. BALLOONSIM's `Records/03_mission_time_variation` is the
template and is internally closed (per-nuclide ODE total reproduces the grid
total activity to 1.2e-15).

**Inputs already present.** `runs/step02_*` catalogs, `config/.../science_rate_ledger.csv`
(already exposes `A_opt_cm2=50.89`, `T_atm=0.739`), `stepwise_maintenance/step03_*`
activation inventory with per-nuclide `hl_s`.

**Reference.** `build_environment_grid.py`, `reweight_prompt_by_environment.py`,
`build_time_variable_delayed_sources.py`, `make_260516_source_time_update.py`.

**Tasks.**
1. Define a reference trajectory CSV (`time_mid_s, day_mid, altitude_km,
   latitude_deg, longitude_deg, Rc_GV, depth_g_cm2`). Synthetic is acceptable;
   label it not-telemetry.
2. Build/borrow an EXPACS/PARMA environment grid to get per-bin particle flux
   scale vs day-0. If the PARMA driver is unavailable, start with a documented
   analytic altitude/cutoff scaling and mark it `L0_proxy`.
3. Prompt: `prompt_final_cps(t) = prompt_final_cps(day0) × atm/flux scale(t)`.
   Reweight at rate level first (cheap); event-level reweight is a later upgrade.
4. Delayed: integrate the per-nuclide half-life ODE
   `dN_j/dt = P_j,ref·driver(t) − λ_j N_j`, `A_j(t)=λ_j N_j`. **Feed the
   per-nuclide template, not just total activity** (see Section 5, F3).
5. Science: `T_atm_511(t)` and source zenith from the trajectory; `atm_scale(t)
   = T_atm_511(t)/T_ref`.
6. Emit `outputs/.../time_dependent_driver_grid.csv` and
   `background_time_variation.csv` analogous to BALLOONSIM.

**Deliverables.** `stepwise_maintenance/step06_mission_time_variation/` with code,
README, driver grid, background-time-variation ledger, and figures.

**Acceptance.** Per-nuclide ODE total vs grid total activity closes to <1e-10;
all rates reduce to the Step05 day-15 numbers when evaluated at the day-15 bin.

**Pitfalls.** Backward-difference dt makes the first bin width 0 (BALLOONSIM bug,
Section 5 F4) — define `dt` as bin-centered widths so no exposure is dropped.

---

### Step 07 — Astrophysical source cases (point / diffuse / V404 / GC)

**Goal.** Generalize the science stream from a single on-axis 511 beam to a set
of physical source cases, each folded as `R = F_511 · A_opt · T_atm` into the
existing post-processing injection.

**Why.** A single beam cannot answer point-vs-diffuse discrimination or
benchmark V404 / Galactic-center cases, which are the actual science targets.

**Inputs already present.** `Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz`,
`config/run_configs/`, `science_rate_ledger.csv`.

**Reference.** `build_511_sky_models.py`, `build_astro_511_spectra.py`,
`build_science_511_line_sources.py`, `fold_511_source_cases.py`,
`make_511_phase10_point_diffuse_report.py`, `build_cosima_sources_from_plane_cases.py`.

**Tasks.**
1. Define a source-case YAML (point/diffuse/V404/GC) with literature flux
   anchors, mirroring `particle_sources/configs/astro_source_cases/`.
2. Generate Cosima science sources at the **cm** Be-window plane convention
   (`z` from `bounds.json`, `r ≤ 1.8`). **Reject any 127.66/18.0 value.**
3. Diffuse: implement sky-intensity-over-solid-angle → aperture projection;
   point: on-axis or off-axis beam; do not conflate "far-field start sphere"
   with "source angular extent" (the Step04 explainer already states this).
4. Fold each case through the existing veto/timeline post-processing.

**Deliverables.** `stepwise_maintenance/step07_source_cases/` with source YAML,
generated cards, per-case folded rates, point-vs-diffuse discrimination report.

**Acceptance.** Each case's injected rate equals `F·A_opt·T_atm` at reference;
on-axis case reproduces Step05 science numbers.

**Pitfalls.** Do not inherit `astro_cases/*.source` from BALLOONSIM (stale 10×).
Regenerate fresh.

**Current closure record.** Done as `L1_SOURCE_CASE_RATE_FOLDING` under
`stepwise_maintenance/step07_source_cases/`. The implementation writes local
source-case and literature-anchor YAML, spectra, diffuse sky-model aperture
tables, four cm-valid point-source Cosima source-card candidates, folded-rate
CSV/JSON outputs, and point-vs-diffuse diagnostics. The A on-axis mono
`1e-4 ph cm^-2 s^-1` case closes exactly to the Step05 final rate
`0.0023056729066227868 cps` and plane rate `0.0037609867166169403 cps`.
B diffuse is intentionally aperture-integrated and skipped as a focal-spot
source card until Step09 supplies a real optics focal map.

---

### Step 08 — Time-dependent significance + accidental-veto folding

**Goal.** Compute "day-N to 3σ/5σ" per source case, integrated over the mission
profile, with VETO and time-variation both folded in, and the accidental
(rate-dependent) veto correction handled analytically.

**Why.** This is the headline science number. BALLOONSIM's version is correct in
that it folds time-variation and post-veto rates, but it emits **two estimates
(counting vs ERL-template) that differ ~4×** and mixes selections (Section 5,
F1/F2). Do it cleaner here.

**Inputs.** Step06 driver grid, Step07 case rates, Step05 catalog/efficiencies.

**Reference.** `make_260516_source_time_update.py`,
`make_phase2_cam511_paper_flux_significance_vs_time.py`,
`estimate_science_accidental_veto.py`, `fit_511_spatial_spectral_likelihood.py`.

**Tasks.**
1. Extract **rate-independent post-veto per-stream efficiencies** `ε_stream` from
   the Step05 `direct_expectation` (zero-pile-up limit). These are constants in
   time. `R_final(t) = Σ r_stream(t)·ε_stream`.
2. **Accidental-veto correction (answers the open question).** Model the
   accidental veto loss analytically:
   `factor_acc(t) = exp(−R_veto(t)·Δt) ≈ 1 − R_veto(t)·Δt`, where `R_veto(t)` is
   the time-varying rate of veto-active events (shield ≥50 keV or extra TES hit).
   Anchor/validate it against the full Poisson timeline run at 2–3 representative
   total rates (min/mean/max over the mission) — **not** per bin. Cross-check
   that `Δ(R) = timeline − expectation` matches the analytic factor.
3. Significance: report **both** a counting `S/√B` and a template/likelihood
   estimate, but make them **selection-consistent** (same energy/radius/layer cut
   for signal response and background). Prefer porting
   `fit_511_spatial_spectral_likelihood.py` to replace the f3-anchored scalar.
4. T3 crossing via interpolation; extrapolate with `Z ∝ √T`.

**Deliverables.** `stepwise_maintenance/step08_significance/` with per-case
cumulative significance CSV, T3 table, accidental-veto ledger, and a one-page
"which number is the headline and why" note.

**Acceptance.** counting and template estimates are reconciled (documented ratio
or unified selection); accidental factor agrees with MC anchors within MC noise;
at Δt=1 µs and R≈843 Hz the accidental fraction ≈ 8e-4 (sanity bound).

**Pitfalls.** Do not quote the optimistic template T3 as "the" sensitivity
without stating it is template/likelihood, not counting.

**Current closure record.** Done as
`L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL` under
`stepwise_maintenance/step08_significance/`. The current headline number is
counting significance in the final 480-550 keV BGO+Compton/FoV selection.
`template_proxy_Z` is intentionally equal to counting `Z`
(`template_proxy_gain=1.0`), so no profile-likelihood improvement is claimed.
The accidental factor is `exp(-R_coincidence*1e-6 s)` with mission loss range
`8.05e-4` to `8.86e-4` and day-15 scale loss `8.43e-4`. The A compact-GC
anchor `8e-5 ph cm^-2 s^-1` reaches 20-day counting `Z=3.9085`; the A reference
`1e-4 ph cm^-2 s^-1` reaches `Z=4.8857` and crosses 3 sigma at `6.784 day`.
The catalog bootstrap anchor is a fast energy/BGO sanity check only; Compton is
not recomputed there.

---

### Step 09 — Opticsim detector-coupled EventList bridge

**Goal.** Turn Step04 from a scaffold into a real bridge: export the Laue focal-
plane phase space and convert it to a MEGAlib EventList source that is then
transported through the `new_geo_re` detector.

**Why.** Step04 explicitly admits `bridge_tool=False`, `eventlist=False`. Until
this exists, the science source is a generic on-axis beam, not an optics-coupled
response, and the "Laue" claim is unbacked for production.

**Inputs.** Latest opticsim `phase_space.csv` (from the opticsim repo commit
recorded in step04 audit), `bounds.json`.

**Reference.** `opticsim_phase_space_bridge.py`,
`analyze_opticsim_laue_detector_replay.py`,
`estimate_optics_focused_gamma_background.py`.

**Tasks.**
1. Implement a phase-space → EventList converter (position/direction/energy at
   focal plane → Cosima `EventList`/beam list at the cm Be-window convention).
2. Transport through the detector; produce an optics-coupled science SIM.
3. Replace (or add alongside) the on-axis beam as a science case in Step07.
4. Keep "Laue lens mass in the prompt/delayed transport" as a separate,
   explicitly-flagged upgrade (the lens material itself activates and scatters).

**Deliverables.** `stepwise_maintenance/step09_optics_bridge/` with bridge tool,
optics-coupled SIM manifest, replay analysis, and honest status flags.

**Acceptance.** Bridge round-trips a known focal-plane test set; optics-coupled
response is within expected order of the geometric A_opt=50.89 cm² ledger.

**Pitfalls.** Channel optics is out of scope (Laue only). Do not silently swap a
channel model in.

**Current closure record.** Done as `L1_OPTICS_EVENTLIST_BRIDGE` under
`stepwise_maintenance/step09_optics_bridge/`. The current Step04 Laue
`phase_space.csv` is converted to a new_geo_re cm EventList at `z=16.051 cm`
with x/y scaled by `0.1 cm per opticsim mm`; `1225/1225` rows are written,
energy range is `480-550 keV`, max radius is `0.3515013832 cm` inside the
`1.898 cm` Be window, and all directions point toward the detector. A
1000-trigger Cosima smoke transport succeeded, producing
`runs/step09_optics_bridge/Opticsim_laue_new_geo_re_smoke1000.inc1.id1.sim.gz`
with `1000` stored events. Remaining caveat: optics hardware mass itself is
not yet added to prompt/delayed activation transport.

---

### Step 10 — Workspace validator / closure gate

**Goal.** A single `tools/validate_new_geo_re.py` with hard checks that fail the
build if any invariant breaks.

**Why.** Without it, regressions (units, stale paths, broken closure) go
unnoticed. BALLOONSIM's `validate_workspace.py` is the template.

**Reference.** `validate_workspace.py`, `validate_phase*.py`.

**Tasks (hard checks).**
1. **Unit guard:** every active source card's beam-z ∈ geometry z-range and
   r ≤ Be-window r. (Catches 127.66/18.0 automatically.)
2. Geometry: `bounds.json length_unit=cm`, TES thickness 0.3 cm, Be 1.898/0.015.
3. Production paths resolve to `step02_*_equiv2602_aligned`; delayed obs time from
   `cosima_delayed_transport_1m.log`.
4. Fixed delayed source has no `ParticleType 74183/74180` (W-183/W-180).
5. Timeline vs expectation agree within a tolerance band.
6. Step06 ODE↔grid activity closure < 1e-10.
7. No orphaned stale-path scripts run in the pipeline (flag
   `make_new_geo_closure_report.py`, Section 5 H1).

**Deliverables.** Validator + a `VALIDATION.md` report; exit code 0 required.

---

## 5. Cross-cutting fixes (carry-over bugs & hygiene — do alongside)

- **F1 (Step08) — dual-metric 3σ.** counting vs ERL-template differ ~4× in
  BALLOONSIM because `f3` encodes a multi-bin template significance (at reference
  the counting S/√B is only ~1.08, not 3). Pick one headline; make selections
  consistent.
- **F2 (Step08) — selection mismatch.** Signal response uses
  `energy_radius_layer`; the time-grid background uses `broad_480_550 final`.
  Unify or document.
- **F3 (Step06) — delayed scaling.** Current closure has the per-nuclide ODE
  ledger, but rate folding still uses a total-activity per-Bq proxy because no
  per-nuclide detector-response matrix exists yet. This is an upgrade item; do
  not fake per-nuclide line response without `K_j`.
- **F4 (Step06) — first-bin dt=0.** Fixed: centered bin widths are used.
- **F5 (Step08) — accidental veto.** Fixed at L1: analytic
  `exp(-R_coincidence(t)*1e-6 s)` live factor is folded and bootstrap-anchored.
- **F6 (Step06) — prompt altitude sign.** Fixed after Claude follow-up:
  secondary-dominated prompt and activation-production proxy increases with
  residual atmospheric depth; validator checks prompt decreases with altitude
  while 511 keV transmission increases with altitude.
- **H1 — orphaned script.** `code/tools/make_new_geo_closure_report.py` points at
  non-existent `*_ADR_cmfix` dirs and `cosima_full1m.log`. Delete or repoint;
  exclude from any pipeline.
- **H2 — threshold doc.** `bounds.json` recommends 30 keV active-veto; analysis
  uses 50 keV. Reconcile in one line, or run a threshold scan (Section 7).
- **H3 — Compton fix.** The `axis_vec = p1 - p2` back-projection fix is correct;
  lock it with a unit test (synthetic on-axis pair → `keep`; off-FoV → `veto`).
  `tests/compton_fov_geometry.py` is the place.
- **H4 — catalog resampling.** Poisson draw is with-replacement; prompt 2.36M
  distinct events drawn 6.98M times (~3× reuse). Fine for the body, tail-limited
  for rare high-multiplicity coincidences — note it where tails matter.
- **H5 — naming.** The live science SIM keeps the `cmfix` token; it is current,
  not legacy — annotate so it is not mistaken for the stale `*_ADR_cmfix` pattern.

---

## 6. Trade-offs to weigh

- **Per-bin transport vs response-template reweighting.** Re-running Cosima per
  time bin is unnecessary while geometry/spectra/veto are time-invariant
  (`R(E,t)=Σ A_j(t) K_j`). Only re-run when EXPACS spectral/angular change is
  believed to move RPIP production positions, or for full parent-fed decay
  chains. Default to reweighting; budget a few transport cross-checks.
- **Counting vs template/profile-likelihood.** Counting is robust and
  conservative; template/likelihood is more sensitive but needs careful
  systematics. For a defensible first claim, lead with counting and report
  template as an upside.
- **Total-activity vs per-nuclide delayed.** Total-activity scaling is cheap and
  fine near day-15 / dominant-nuclide regimes; per-nuclide is needed when the
  composition shifts (late mission, line window). Implement per-nuclide; keep
  total as a sanity cross-check.
- **35 cm far-field cost vs realism.** Smaller sphere = fewer wasted primaries,
  but must always enclose the detector and any added optics mass (Step09 may grow
  the envelope — re-check R2).
- **Accidental veto: analytic vs MC.** Analytic `exp(−R_veto·Δt)` is cheap and
  time-foldable; MC is exact but per-rate. Use analytic folding anchored by 2–3
  MC points.

---

## 7. Innovation / brainstorm backlog (my ideas, optional)

- **Response-matrix-as-code.** Persist `K_j(E, cuts)` (per stream/nuclide, with
  veto folded) as versioned tables so the whole time/flux/significance analysis
  becomes linear algebra over rates — decouples expensive Geant4 from cheap
  re-analysis and makes Step06/08 trivially re-runnable.
- **Auto unit-guard CI.** A test that bounds-checks every source card against
  `bounds.json` would have caught the 127.66/18.0 landmine class automatically;
  generalize to a provenance manifest (far-field radius, geometry hash, unit
  scale) attached to every run, so cross-run normalization mismatches fail loudly.
- **Threshold-band systematic.** Instead of a single 50 keV active-veto, fold the
  `bounds.json` `threshold_scan_keV = [10,20,30,50,70,100]` into a systematic
  band on the final rate and the sensitivity — turns H2 from a doc nit into a
  quantified uncertainty.
- **Accidental-veto as a measured dead-time.** Express the rate-dependent veto
  loss as an effective live-time fraction `e^{−R_veto(t)Δt}`; this plugs directly
  into the exposure term of the significance and is intuitive for reviewers.
- **Parent-fed decay chains.** BALLOONSIM itself has not done full branch-ratio
  parent→daughter chains. With an audited branching table, `new_geo_re` could go
  beyond the reference for the delayed 511 line (e.g., β+ emitters fed by
  parents) — a genuine improvement, not just parity.
- **Point-vs-diffuse discriminator from the FoV cut.** The Compton/FoV
  back-projection already reconstructs source-cone–window intersection; turn it
  into a quantitative point-vs-diffuse test statistic (cone-density on the
  window) rather than a binary keep/veto.
- **Far-field invariance unit test.** Add a test asserting the detection rate is
  invariant under far-field radius (35 vs 150 cm) for a fixed flux — this both
  validates R2 and gives a cross-check against the BALLOONSIM normalization.
- **Single timeline, many realizations.** Cache the event catalog once, then run
  N Poisson realizations to report not just the mean but the variance of the
  final rate and of T3 — gives an honest statistical band on "day-N to 3σ".

---

## 8. Suggested execution order & dependencies

```
Step 10 (validator skeleton)  ──► run continuously from here on
        │
Step 06 (mission time-variation)        [depends on: 02,03,05]
        │
        ├─► Step 07 (source cases)       [done, depends on: 05,06]
        │
        └─► Step 08 (time-dep significance + accidental veto)  [done, depends on: 05,06,07]
                │
Step 09 (optics bridge)  ──► done at EventList smoke-transport level
```

1. **Step 10 first (skeleton).** Stand up the validator with the unit guard and
   current invariants so every later change is gated.
2. **Step 06.** The backbone; everything time-dependent hangs off it.
3. **Step 07.** Source cases (needs the time axis for folding). Done at L1.
4. **Step 08.** Significance + accidental veto (needs 06+07). Done at L1.
5. **Step 09.** Optics bridge in parallel; fold its coupled case into 07/08 when
   ready. Done at EventList smoke-transport level.
6. Fold the Section 5 fixes into whichever step owns them; keep the validator green.

---

### One-line summary

`new_geo_re` now has a clean, unit-correct detector + veto + day-15 snapshot,
a first L0 mission time axis (06), an L1 source-case layer (07), an L1
time-dependent counting-significance layer with analytic accidental veto (08),
an L1 Laue EventList bridge smoke-transported through the detector (09), and a
validator (10). Remaining work is upgrade-level: optics hardware mass in
prompt/delayed transport, higher-statistics optics-coupled production, and an
optional selection-consistent profile likelihood.
