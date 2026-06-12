# CC 4.8 Review Log — NEW_GEO_RE

- Reviewer: Claude Code (Opus 4.8)
- Date: 2026-05-29
- Scope: Read-only technical review per `CC48_REVIEW_PROMPT.md`. No code edited; no Cosima runs launched. Only lightweight inspection (`grep`, `python` JSON readers, `ls`, `find`, targeted `Read`).
- Target: `/home/ubuntu/codex_tes_511_sim/new_geo_re`

---

## 1. What I inspected (process log)

Read-first docs:
- `README.md`, `MEMORY.md`, `workflow.md`, `stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md`
- Step docs: `step01_geo/README.md`, `step02_raw_background_simulation/README.md`, `step03_delay_source/README.md`, `step04_opticsim/README.md`, `step05_veto_time_axis/README.md`

Key outputs (JSON):
- `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json`
- `stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json`
- `outputs/reports/science_511_ADR_100k/science_511_100k_summary.json`
- `outputs/reports/day15_complete_report/complete_day15_summary.json`
- `stepwise_maintenance/step04_opticsim/outputs/step04_opticsim_audit.json`

Key code (targeted ranges):
- `code/tools/make_complete_day15_report_ADR.py` — normalization, Poisson draw, timeline grouping, veto aggregation
- `code/tools/make_day15_report_ADR.py` — Compton/FoV implementation
- `code/geometry/GenerateGeo_ADR_v4c_mkflange.py`, `code/tools/build_cm_geometry.py` — mm→cm scaling
- Cross-checked against the actual `…_cm.geo` volume blocks

Supporting evidence pulled:
- `runs/step02_instant_equiv2602_aligned/normalization.json`
- `runs/step02_delayed_transport_equiv2602_aligned/cosima_delayed_transport_1m.log`
- `config/science_511_onaxis_source/metadata/science_rate_ledger.csv`
- `config/run_configs/Science_511_onaxis_ADR_cm_local.source`
- `runs/` directory listing + existence checks for stale paths

---

## 2. Executive summary

The project is **internally consistent** across docs, JSON outputs, and code. Geometry, production paths, delayed-source numbers, prompt far-field normalization, veto settings, candidate-group BGO summing, aggregated Compton/FoV, and the Poisson↔expectation cross-check all line up. The accidental-merge count confirms the Poisson time axis is built correctly.

Largest *physics* risk: the **inherited Compton/FoV cone back-projection direction convention** (analytic concern; not executed). Remaining items are **hygiene**: an orphaned stale-path script, a 30-vs-50 keV doc mismatch, and `cmfix` filename tokens that resemble the "stale" pattern but are actually the live science file.

---

## 3. Findings

### Medium — Compton/FoV cone hemisphere convention (Confidence: Low–Medium)
- File: `code/tools/make_day15_report_ADR.py:224-293` (`sample_cone_plane`, `classify_hit2`); consumed at `make_complete_day15_report_ADR.py:595`.
- Evidence: cone is built around `axis_hat = hit2 − hit1` (scattered direction `a→b`, line 233) with half-angle θ, keeping only `t>0` window crossings (lines 258-259). For Compton source back-projection the cone axis should be `b→a` (−scattered direction). `{cosθ·âb + sinθ·⊥}` is the *incident*-direction cone; its `t>0` (upward) window crossings map to the *downward* (away-from-window) physical source rays. Testing both hit orders (line 287) swaps apex/energies but does not fix the forward/backward hemisphere for a given ordering.
- Why it matters: an inverted hemisphere selects the complementary arc of the cone–window conic, biasing the final 480-550 keV rate (FoV step alone: 0.472 → 0.399 cps).
- Suggested fix: add a synthetic-pair unit test (true source = Be-window center should return `keep`); if it fails, negate `axis_hat`. Note this is inherited "2602-workflow" code (docstring line 7) — verify before changing.

### Low — orphaned stale-path closure script (Confidence: High)
- File: `code/tools/make_new_geo_closure_report.py:121-127`.
- Evidence: points to MISSING dirs `runs/{instant,buildup}_equiv2602_ADR_cmfix`, `runs/{delay_fix,decay}_from_buildup_equiv2602_ADR_cmfix` and stale log `cosima_full1m.log`. Current layout is `runs/step02_*_equiv2602_aligned` + `cosima_delayed_transport_1m.log`. Not referenced by any doc/script.
- Why it matters: exactly the stale `*_ADR_cmfix` / `cosima_full1m` pattern the review flags; running it yields an empty/old closure.
- Suggested fix: delete, repoint to aligned paths, or mark `LEGACY` in the header.

### Low — active-veto threshold doc mismatch (Confidence: High)
- File: `bounds.json` `ACTIVE_SHIELD.recommended_veto_threshold_keV = 30.0` vs `make_complete_day15_report_ADR.py:79` `BGO_THR_KEV = 50.0`.
- Evidence: geometry authority recommends 30 keV; analysis uses 50 keV (intentional "fix baseline", documented in MEMORY/Step05). The review's required value is 50 keV, so the analysis is correct, but the geometry recommendation is not reconciled in-text.
- Suggested fix: add one line in Step05/geometry notes reconciling the 30 keV geometry recommendation with the 50 keV analysis baseline.

### Low — `cmfix` tokens resemble the stale pattern but are the live science file (Confidence: High)
- File: `Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz` referenced at `make_complete_day15_report_ADR.py:57`, `workflow.md:3,12`, Step05/breakdown docs.
- Evidence: this is the CURRENT production science SIM (used by Step05), not stale; but its name carries the `cmfix` token the review wants flagged. The old `MEMORY.new_geo_legacy.md` file was a legacy note and has since been cleaned.
- Why it matters: reviewer/tooling confusion only.
- Suggested fix: optional rename to a non-`cmfix` token, or add a note that `cmfix` in the science filename is the current convention, not legacy.

---

## 4. Non-issues / confirmed correct

1. **Geometry — Be window**: `…_cm.geo` `Win_Be_Cryostat.Shape PCON … -0.0075 0 1.898 0.0075 0 1.898` → r 1.898 cm, thickness 0.015 cm, z 12.8425; matches `bounds.json`, docs, and `BE_WINDOW_Z_CM/R_CM` constants.
2. **Geometry — windows/omissions**: 5 windows (SampleBox_Al, Nb can, 4K Al, 50K Al, Be). A4K/Cryoperm ABSENT; vacuum jacket has Be-only aperture (`hole=1.898`, no `Win_Vacuum`). Active shield = `CeBr3_Active_Shield`.
3. **Units**: `build_cm_geometry.py SCALE=0.1` (mm→cm); generator `entrance_r=18.98 mm`/`th_win_be=0.15 mm` → 1.898/0.015 cm. No cm/mm or 10x mismatch. Science beam `HomogeneousBeam 0 0 16.051 0 0 -1 1.8` (cm), 1 µm above collimator top.
4. **Production paths**: prompt/delayed/science and Step03 audit all resolve to `step02_*_equiv2602_aligned`.
5. **Delayed source**: 4728 raw → 4674 fixed, 54 removed, 110.0883→110.0882 Bq; profiles 4674/4674; `DecayMode ActivationDelayedDecay`; RPIP/profile spatial support (not uniform prior); no-RPIP (294) and unknown-isotope (6) caveats explicit; fixed source contains no W183/W180.
6. **Active-shield/BGO veto**: `is_active_veto_volume` matches `BGO`/`ACTIVE_SHIELD`/`CEBR3`; timeline sums `bgo_total_keV` over the whole 1 µs candidate group (`analyze_timeline:575`), threshold 50 keV. Coincidence window `1.0e-6 s`.
7. **Compton/FoV grouping**: runs on `aggregate_candidate_hits` over the same candidate group; Be-window disk (12.8425 cm / 1.898 cm) is the reference, not a Laue spot.
8. **Prompt normalization**: 35 cm far-field, area πR²=3848.45 cm², gamma time = 10⁷/(4.79966·3848.45)=541.38 s; non-gamma weight 1/8 consistent with base×8 counts. Detector max extent ≈25.75 cm < 35 cm, so the start sphere encloses the geometry → detection rate is far-field-radius-independent (the 150→35 cm change is sound).
9. **Poisson timeline math**: total rate 843.1 Hz = 7,590,678/9003.74; accidental merges 7,590,678−7,584,199 = 6,479 ≈ N·R·Δt (≈6,400). Candidate-multiplicity histogram sums to 154,970 = `n_candidates_with_tes`.
10. **Direct vs Poisson cross-check**: raw 0.832/0.834, BGO 0.472/0.465, final 0.399/0.390 cps — close, as expected for finite sampling.
11. **Step04 honesty**: `channel_optics_used=false`, `geant4_bottom_code_modified=false`, `uses_external_efficiency_table_for_physics=false`, `bridge_tool.exists=false`, `laue_eventlist_payload.exists=false`. Correctly scoped as reused temporary Laue scaffold, not a fresh detector-coupled bridge.
12. **Step02/Step05 boundary**: Step02 explicitly excludes veto/timeline; Step05 applies them — no conflict.

---

## 5. Open questions (blockers)

1. Compton/FoV: is the cone built around the scattered (`a→b`) or back-projected (`b→a`) axis by design? (Confirms or clears the Medium finding.)
2. Is `make_new_geo_closure_report.py` intended to be live, or legacy to remove?
3. Should the 30 keV geometry recommendation or the 50 keV analysis baseline be the documented standard?

---

## 6. Minimal next actions (priority ordered)

1. Add a synthetic-source unit test for `classify_hit2`/`sample_cone_plane` to settle the cone-direction convention.
2. Delete or `LEGACY`-mark `make_new_geo_closure_report.py` (stale `*_ADR_cmfix` / `cosima_full1m`).
3. Add one reconciling line for the 30 keV (geometry) vs 50 keV (analysis) threshold.
4. Optionally retire the `cmfix` token in the live science filename or annotate it as current.

---

*Log generated from a read-only inspection. Items labeled Low–Medium confidence were not executed and are analytic concerns; verify by unit test before acting.*

---

# Addendum — follow-up discussions (2026-05-29)

Records the conceptual Q&A after the initial review. The old standalone
`NEW_GEO_RE_math_report.html` was later cleaned; the active closure plan is in
`CLOSURE_ROADMAP.md`.

## A. Compton/FoV fix verified correct
The user changed `make_day15_report_ADR.py:236` from `axis_vec = p2 - p1` to
`axis_vec = p1 - p2`. This is correct: the source back-projection cone axis must
be `b→a` (= −scattered direction), apex at the first hit `a`, half-angle θ from
`compton_cos_theta`. With the `t>0` (toward-window) filter, the code now selects
the physically source-pointing half-cone. Both hit orders still tested. Fix
applies to the 3+-hit path too (same `sample_cone_plane`). Recommend locking with
a unit test (synthetic on-axis pair → `keep`; off-FoV → `veto`).

## B. Two-layer Monte Carlo — why Geant4 cannot be replaced by direct Poisson
Two independent randomness sources: (1) microscopic per-particle response
(non-analytic, correlated `(E_TES, pixels, E_shield, topology)`) sampled by
Geant4 → response template `K_j`; (2) counting+timing (analytic Poisson) sampled
by hand. `R(E,t)=Σ_j A_j(t) K_j`. A "direct Poisson MC without Geant4" still
needs a per-event response, which can only come from the Geant4 library or a
matrix built from Geant4 — no third path. Veto needs full correlated events, so
the catalog cannot be collapsed to a 1-D spectrum.

## C. Poisson superposition & accidental coincidences — confirmed sound
Sum of independent Poisson streams is Poisson with summed rate; uniform arrival
times; accidental merges `≈ N·R·Δt`. Numerically verified: N=7,590,678,
R≈843.1 Hz, Δt=1e-6 → predicted 6,398 vs observed 6,479 merges. The Poisson time
axis is correct.

## D. Resampling: with-replacement is required AND correct
- The code (`draw_timeline:528`) draws **with replacement** and **must**: n drawn
  (6.98M) > catalog size M (2.36M), so without-replacement is impossible.
- Statistically correct regardless: the catalog is an empirical sample of the
  response PDF; i.i.d. draws from it = bootstrap = with replacement. Without
  replacement imposes a spurious finite-population anti-correlation and
  underestimates variance.
- For the **mean** (which the 3σ uses), no resampling is needed at all — analytic
  coefficients on `R(E,t)=Σ A_j(t) K_j` suffice (`direct_expectation`). Resampling
  is only for (i) validating the accidental correction Δ(R) and (ii) variance
  bands, done at 2–3 representative rates, not per time bin.
- Practical caveat: the relevant library size is the **per-bin distinct-event
  count in 480–550-final**, not the total — check tail faithfulness there.

## E. day-15 as basis + per-stream analytic extrapolation
Each stream has ONE fixed simulation basis; time-variation is analytic
reweighting on top, NOT per-bin re-transport:
- delayed: basis = day-15 activation library; coefficient = `A_j(t)/A_j(t15)`
  (half-life ODE). Per-nuclide reweight needs a nuclide-tagged library.
- prompt: basis = reference EXPACS spectrum (day-0), NOT day-15; coefficient =
  `r(t)`. Valid only while the spectral/angular SHAPE is time-invariant.
- science: basis = 511 keV beam SIM; coefficient = `T_atm(t)` (exact).
Validity boundary: analytic extrapolation holds only while the response
template SHAPE `K_j` is constant (geometry/materials/veto/spatial+spectral
shape). It breaks → re-transport needed when: RPIP spatial map shifts, prompt
spectral shape changes materially, full parent-fed decay chains, or
geometry/threshold change.

## F. VETO into time-variation — two channels, both veto types
`B_final(t) = [Σ r_stream(t)·ε_stream] · exp(−R_shield(t)Δt) · (1 − c·R_TES(t)Δt)`.
- Channel ① intrinsic efficiency `ε` (time-INdependent): both BGO and Compton are
  baked into `ε`; time-variation enters only via `r(t)`. This is the dominant
  effect and is already what the post-veto time-grid rate represents.
- Channel ② accidentals (time-DEpendent): scintillator anti-coincidence ∝
  `R_shield(t)Δt`; Compton/FoV ∝ `R_TES(t)Δt`. Both folded analytically with the
  time-varying rates; magnitude ~R·Δt ≈ 8e-4 (sub-permille time-variation).
Answer to "can both Compton and scintillator veto be made time-varying": yes,
identically — constant ε plus each its own rate-driven accidental term.

## G. 3σ chain audit (`make_260516_source_time_update.py`, reference dir)
The 3σ DOES fold time-variation and VETO: signal uses post-selection response
(24.86 cps/flux) × atm_scale(t); background uses post-veto prompt(t)+delayed(t).
BUT it emits two estimates differing ~4×: counting `S/√B` vs ERL-template
(f3-anchored). At reference, counting Z≈1.08 not 3 → f3 encodes a multi-bin
template/likelihood significance, not a single-window count. Must (a) pick the
headline metric explicitly, (b) make signal-response and background use the same
selection, (c) fix first-bin `dt=0` (~1.25% exposure dropped).

## H. Trajectory-perturbation assumption (alt ±2.5 km, lat/lon ±0.25°) — verdict
Question: can the activation nuclide spatial distribution / composition be taken
as trajectory-invariant under these perturbations?
- **SHAPE (K_j^delayed: RPIP spatial map + nuclide composition + veto efficiency):
  reasonable L1 assumption to hold fixed.** Governed by geometry + cross-sections
  + the relatively stable spectral/angular SHAPE; over ±2.5 km / ±0.25° the shape
  change is second-order. The buildup time-integral further smooths it.
- **MAGNITUDE: do NOT hold fixed.** ±2.5 km altitude ≈ ±40% atmospheric depth
  (scale height ~6.5 km), so prompt rate `r(t)` and `activation_driver(t)` change
  ~±40% — but that is exactly the analytic coefficient; you only fix the shape.
- **lat/lon ±0.25°: negligible** (sub-percent Rc; <3% of the reference profile's
  lat/lon span) for both shape and magnitude.
- **Recommended validation:** run transport ONCE at float ±2.5 km and check the
  480–550-final spectrum shape and the RPIP spatial map are stable (target few-%);
  if stable, the L1 assumption is confirmed; if not, use altitude-binned templates.
Conclusion: the rough assumption is defensible at L1 **provided** you keep the
rate/driver time-varying and only fix the response SHAPE, and confirm with the
two altitude-extreme transport cross-checks.

## I. Claude follow-up review: Step06 prompt altitude sign (2026-05-29)

Accepted:
- Step06 prompt/activation-production altitude scaling had the wrong sign for
  the current secondary-dominated float-regime proxy. It used to make prompt
  background rise with altitude. Fixed to make prompt/delayed-production scale
  increase with residual atmospheric depth and decrease with altitude.
- Added a validator-guarded trend audit: prompt scale at min/max altitude is
  `1.05298763053` / `0.965181809612`; altitude-vs-prompt correlation is
  `-0.9946100642388752`; altitude-vs-511-keV-transmission correlation is
  `0.997952343357823`.
- Rebuilt Step06 and Step08. Updated Step08 checks: accidental loss range
  `0.0008046129834964333` to `0.0008860077736297933`; A reference 20-day
  counting `Z=4.88566984831696`; A reference T3 `6.784446087481758 day`.

Deferred / kept as explicit limitations:
- F3 per-nuclide delayed detector-response weighting remains upgrade-level until
  a per-nuclide response matrix `K_j` exists. Current rate folding honestly stays
  a total-activity per-Bq proxy.
- Accidental occupancy still uses the total prompt+delayed event rate; this is
  conservative at the sub-permille level and is already documented as an
  analytic upper-bound style live factor.

Validation:
- `python3 code/tools/validate_new_geo_re.py` exits 0 and `VALIDATION.md` is
  `PASS` after the sign fix and Step08 rebuild.
