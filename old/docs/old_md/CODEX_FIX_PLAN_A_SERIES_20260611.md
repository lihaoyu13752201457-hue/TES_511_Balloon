# Codex Fix Plan — A-Series (current-data fixes, no new transport)

Date: 2026-06-11. Repo: `/home/ubuntu/codex_tes_511_sim/new_geo_re`, branch
`balloon511_0601_CsI`. Authored by the 2026-06-10/11 review session (Claude);
to be executed by Codex. 中文摘要：本计划完成 A1–A5 五项"仅用现有数据即可完成"
的修复；不跑任何 cosima 输运，不碰 `../new_geo_re_2`，不做 git commit。

Execution order: **A1 → A3 → A4 → A2 → A5 → Final phase.**
(A2 must run after A3/A4 so the regenerated report reflects final outputs.
A5 is independent and may be done any time.)

---

## 0. Global guardrails (read first)

1. **No git commits, no pushes.** Leave everything in the working tree.
2. **No cosima / no Geant4 runs.** Nothing in this plan needs transport.
3. **Do not touch** `../new_geo_re_2` (BGO branch), `tests/realpos_delayed_smoke/`,
   `runs/` (read-only inputs), or `stepwise_maintenance/step08_significance/code/time_fold_common.py`
   (new shared module; the two step08 sidecars import it — do not "clean it up").
4. **Archive before overwrite.** Before regenerating any output directory,
   archive it: `rsync -a --exclude work/ <dir>/ <dir>_pre_a_series_20260611/`
   (the `--exclude work/` matters only for `day15_complete_report`, whose
   `work/event_catalog.pkl` is 151 MB and is an input cache, not an output).
5. **Validator must stay PASS.** After each phase run
   `python3 code/tools/validate_new_geo_re.py` and confirm the report says
   `Status: **PASS**` (20 checks). It is already PASS on the current tree.
6. **STOP conditions** — stop, write your findings/questions into
   `CODEX_A_SERIES_EXECUTION_REPORT_20260611.md`, and do not improvise, if:
   - the validator goes FAIL at any point;
   - any headline key drifts more than **1e-3 relative** in step A3 (see §A3.5);
   - A4 cannot reproduce the published background rates within **1%** (§A4.4);
   - anything requires running cosima, or rerunning Step06 (PARMA external
     driver) — neither is in scope.
7. Python env: `python3` with numpy/matplotlib already works for all repo
   scripts. Scripts set `MPLCONFIGDIR` themselves. Use `--workers 6` where
   offered.
8. Write a completion report at repo root:
   `CODEX_A_SERIES_EXECUTION_REPORT_20260611.md` — per item: what changed,
   commands run, acceptance results (numbers before/after), deviations.

### Pre-verified facts (trust these; do not re-derive)

- Step04 optics authority: `stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`
  has `aeff_511_cm2 = 15.299280000000001`.
- Science ledger `config/science_511_onaxis_source/metadata/science_rate_ledger.csv`
  currently uses `A_opt_cm2 = 50.890000` (a pre-B-FULL placeholder). Its
  `T_atm` string is exactly `7.390423888027e-01`.
- `build_step06_mission_time_variation.py` reads the ledger **only** to assert
  `T_atm == 7.390423888027e-01` within 1e-12 (hard RuntimeError otherwise). It
  never reads `A_opt_cm2`. So the ledger fix is safe for Step06 **iff the
  T_atm string is preserved byte-identically**.
- The headline W1/W2/spot numbers do NOT come from the ledger. Current values
  (time-dependent headline convention, with constant-rate variants):
  | Selection | background cps | Z20d (time-dep) | Z20d (const) | T3 day (time-dep) | 3σ 20d flux (time-dep) |
  |---|---|---|---|---|---|
  | W2 line_pm_3sigma | 0.18434717748640367 | 2.735425315169172 | 2.75023 | 24.06 | (see line summary) |
  | spot_r90 | 0.055100483553150656 | 4.507789163321426 | 4.527484229695351 | 8.1793477059377 | 6.655147104949208e-05 |
  | W1 A-reference | (step08 summary) | 0.7669158563686436 | — | 306.0392090474061 (extrapolated) | — |
- `make_complete_day15_report_ADR.py` CLI: `--outdir` (default
  `outputs/reports/day15_complete_report`), `--workers` (default 6), `--seed`
  (default 260511), `--science-flux` (default 1e-4), `--reject-policy keep`,
  `--rebuild-cache` (do NOT pass it; reuse the 151 MB event cache),
  `--refresh-from-summary`. Original delayed transport: 1M triggers, 1577 s.
- The validator does not pin any Route B numbers, and its step08 checks prefer
  `*_time_dependent` keys with loose inequalities (e.g. `spot_r90_Z20d > 3.0`).

---

## A1. Route B mainline disk: treat Siegert 60/10.5 as sigma (not FWHM)

**Problem.** `code/tools/build_route_b_diffuse_supplement_20260602.py` defines
the thick-disk component with `"fwhm_l_deg": 60.0, "fwhm_b_deg": 10.5`, then
divides by 2.3548 — i.e. it narrows the disk (sigma 25.48/4.46). The BGO branch
already fixed this; port exactly that fix. Conclusion direction is unchanged
(Route B stays a null/foreground comparison).

**A1.1 Patch** (two hunks; verified against the BGO-branch diff — do NOT port
anything else from that file; in particular its `BOUNDS` path is BGO-specific):

In the `SKY_COMPONENTS` disk entry (`"model_id": "disk_thick_gaussian"`), replace

```python
        "fwhm_l_deg": 60.0,
        "fwhm_b_deg": 10.5,
```

with

```python
        "sigma_l_deg": 60.0,
        "sigma_b_deg": 10.5,
        "fwhm_l_deg": 60.0 * FWHM_TO_SIGMA,
        "fwhm_b_deg": 10.5 * FWHM_TO_SIGMA,
```

In the metric function (currently around lines 203–204), replace

```python
    sigma_l = float(component["fwhm_l_deg"]) / FWHM_TO_SIGMA
    sigma_b = float(component["fwhm_b_deg"]) / FWHM_TO_SIGMA
```

with

```python
    sigma_l = float(component.get("sigma_l_deg", float(component["fwhm_l_deg"]) / FWHM_TO_SIGMA))
    sigma_b = float(component.get("sigma_b_deg", float(component["fwhm_b_deg"]) / FWHM_TO_SIGMA))
```

**A1.2 Run.** Archive `outputs/reports/route_b_diffuse_supplement_20260602/`
per guardrail 4, then `python3 code/tools/build_route_b_diffuse_supplement_20260602.py`.
It rewrites the output dir and the tracked `ROUTE_B_DIFFUSE_SUPPLEMENT_20260602.md`.

**A1.3 Acceptance.**
- In the regenerated `route_b_diffuse_metrics.csv`: disk row has
  `sigma_l_deg=60.0`, `sigma_b_deg=10.5`, `fwhm_l_deg≈141.2892`,
  `fwhm_b_deg≈24.7256`. Bulge rows (3/8/12 deg) unchanged vs archive.
- Disk-row *sky-model* fields (sigma, central intensity, fov_fraction) now
  match the BGO branch file
  `../new_geo_re_2/outputs/reports/route_b_diffuse_supplement_20260602/route_b_diffuse_metrics.csv`
  (read-only comparison; detector-response-side fields may differ).
- The MD's conclusion stays "Route B diffuse foreground is far below the
  Route-A point-source case" (ratios will move somewhat; that is expected —
  record old vs new disk-row numbers in the execution report).
- Validator PASS.

---

## A3. Science ledger 50.89 → 15.29928, then Step05 rerun + step08 refresh

**Problem.** `config/science_511_onaxis_source/metadata/science_rate_ledger.csv`
still normalizes the Step05 broad-window science decomposition to the legacy
on-axis `A_opt=50.89 cm2`. The B-FULL lens authority is `15.29928 cm2`.
Contained: headline numbers unaffected; only the Step05 science decomposition,
timeline `science_containing` rows, and the legacy flux-limit block carry it.

**A3.1 Regenerate the ledger** with a small python snippet (do not hand-edit):
- Keep the same 5 data rows / column order / header.
- `A_opt_cm2`: `15.299280` (6 decimal places, matching the old `50.890000` style).
- `T_atm`: keep the exact string `7.390423888027e-01` (guardrail: Step06 asserts it).
- `rate_to_injection_plane_s^-1 = flux * 15.29928 * 0.7390423888027`, formatted
  like the existing values (`{:.12e}` style). Cross-check: at `flux=1e-4` the
  new value must be ≈ `1.130682e-03` (old: `3.760986716617e-03`; ratio
  `15.29928/50.89 = 0.3006342…`).
- Last two columns are formula strings — copy them through unchanged.
- `source_id` stays `science_511_onaxis_v0`.

**A3.2 Archive** `outputs/reports/day15_complete_report/` per guardrail 4
(exclude `work/`).

**A3.3 Rerun Step05** (uses the cached event catalog; expect ≲ tens of minutes):

```bash
python3 code/tools/make_complete_day15_report_ADR.py --workers 6 \
  > /tmp/step05_rerun_a3_20260611.log 2>&1
```

Defaults give the same outdir, seed 260511, science-flux 1e-4, keep policy.
Do NOT pass `--rebuild-cache`.

**A3.4 Step05 acceptance** (compare new `complete_day15_summary.json` vs the
archived copy):
- Background expectation rates unchanged: all background-component rows (and
  `expectation_rates_cps` stages as far as they exclude science) identical to
  archive; any field that *includes* the science stream may shift only by the
  science-rate delta.
- Science rows scaled by `×0.300634` (e.g. the broad-window science
  decomposition `0.002399 cps → ≈0.000721 cps` at 1e-4).
- `timeline_rates_cps` may wiggle within MC noise (the science stream changes
  the RNG consumption); the validator's `timeline_expectation_closure` check
  (5% tolerance) must still PASS.
- `science_reference_sensitivity.csv` / flux-limit block rescaled consistently
  (limits scale by `×1/0.300634` where they are ∝ 1/A_opt).

**A3.5 Refresh step08** (cheap, seconds each; archive
`stepwise_maintenance/step08_significance/outputs/` first):

```bash
python3 stepwise_maintenance/step08_significance/code/build_step08_significance.py
python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py
python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py
```

Acceptance: every headline key in §0's table equal to its archived value
within **1e-3 relative** (expected: identical, or ≤1e-4 drift if the
accidental-live factor reads a day15 total that includes the science stream).
Record the exact deltas. Larger drift = STOP condition.

**Do NOT rerun Step06** (its only ledger dependence is the preserved T_atm
assertion; its day15 inputs are the unchanged prompt/delayed rates; rerunning
it would require the external PARMA driver — out of scope). **Do NOT rerun
Step09** (its background table derives from the day15 event cache, which is
unchanged; science rows do not enter it).

- Final: validator PASS.

---

## A4. Headline statistical uncertainties (NIMA submission-blocker #1, analysis half)

**Goal.** Quote Poisson/MC uncertainties on the three headline backgrounds and
propagate them to Z20d, T3, and the 3σ flux. Sidecar only — no existing output
file is modified.

**A4.1 New script:**
`stepwise_maintenance/step08_significance/code/build_headline_statistical_uncertainty.py`.
Import the shared fold like the sidecars do:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from time_fold_common import time_dependent_fold
```

**A4.2 Data source.** `outputs/reports/day15_complete_report/work/event_catalog.pkl`
(151 MB pickle; the Step05 per-event cache behind the veto chain and the
step09 background table). **Introspect its schema first** (top-level type,
keys, one record per stream) and document what you find in the execution
report. Expected content: per-stream event records carrying per-event rate
weights, summed TES energy after the veto chain, shield/veto energies,
classification flags, and TES hit positions.

**A4.3 Selections to reproduce** (must match the published chain):
- `W1`: summed-TES energy in `[500.994, 521.006]` keV after the full veto chain.
- `W2`: `511 ± 0.42` keV (i.e. `[510.58, 511.42]`).
- `spot_r90`: W2 **and** focal-plane radius ≤ `signal_radius_r90_cm` (read the
  value from `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy_summary.json`
  `checks.signal_radius_r90_cm`) around the focal centroid (centroid from
  `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json`
  or the spatial-cuts CSV next to it — use whichever field
  `build_spatial_line_proxy.py` itself uses; read that script to copy its
  exact selection logic rather than re-inventing it).
- Reject policy `keep`, consistent with the published chain.

**A4.4 Cross-check before computing errors** (STOP if violated): the
reconstructed weighted background rates must reproduce
- W2: `0.18434717748640367 cps` within 1%,
- spot_r90: `0.055100483553150656 cps` within 1%,
- W1: the value in
  `stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv`
  within 1%.

**A4.5 Statistics.** Per selection, over the passing events with weights `w_i`:
`B = Σw_i` (cps), `N_eff = (Σw_i)^2 / Σw_i^2`, `δB = B / sqrt(N_eff)`.
Also report the per-stream decomposition (each prompt species; delayed) with
its own `N_eff`, and combine as
`δB_total^2 = Σ_streams (B_s^2 / N_eff,s)` — streams are independent MC samples.
Sanity expectation: `N_eff(W2) = O(300)`, `N_eff(spot_r90) = O(90)` (rough
review estimates — if you get a very different order, STOP and report rather
than "fixing" anything).

**A4.6 Propagation.** The day-15 background normalization error is fully
correlated across mission time bins, so:
- `δZ/Z = δB/(2B)` — verify numerically by calling `time_dependent_fold` with
  the background inputs scaled by `(1 ± δB/B)` and re-reading
  `Z20d_time_dependent_at_reference_flux`;
- `δT3`: numeric, from the same two scaled refolds (`T3_day_time_dependent`);
- `δ(3σ flux)/flux = δB/(2B)` (flux limit ∝ sqrt(B)).
Use the same Step06 CSV / day15 summary paths the sidecars pass to the fold.

**A4.7 Outputs.**
- `stepwise_maintenance/step08_significance/outputs/headline_statistical_uncertainty.csv`
  — one row per selection: B, δB, N_eff, Z20d_td ± δZ, T3_td ± δT3,
  flux3σ_td ± δflux, plus per-stream N_eff columns or a companion long-format CSV.
- `...//headline_statistical_uncertainty.md` — short human summary including
  the headline sentence to be quoted in the paper, e.g.
  `spot_r90: B = 0.0551 ± 0.006 cps (N_eff≈90), Z20d = 4.51 ± 0.25` (fill real
  numbers).
- Do not modify existing summaries or `which_number_is_headline.md` beyond
  appending a single pointer line to the MD (allowed).
- Validator PASS afterwards (the validator does not read the new files; this
  is just the routine end-of-phase check).

---

## A2. Experiment report: switch quotes to time-dependent keys, regenerate

**Problem.** `outputs/reports/experiment_report_20260601/experiment_report.md`
(generator: `code/tools/build_experiment_report_20260601.py`, no CLI args)
still quotes constant-rate Z/T3/flux. Headline convention moved to Step06
time-dependent folds on 2026-06-04.

**A2.1 Key mapping** (generator currently reads `line_chk` =
`line_window_sensitivity_summary.json[checks]`, `spatial_chk` =
`spatial_line_proxy_summary.json[checks]`, `step08_chk` =
`step08_significance_summary.json[checks]`). Replace quoted keys, preferring
the time-dependent key with the constant-rate one as a labeled variant in
parentheses. Use `.get(td_key, .get(const_key))` fallback style so the
generator stays robust:

| Current quote | Switch to (headline) | Keep as variant |
|---|---|---|
| `line_pm_3sigma_Z20d` | `line_pm_3sigma_Z20d_time_dependent` | constant-rate value |
| `line_pm_3sigma_T3_day_constant_rate` (if quoted) | `line_pm_3sigma_T3_day_time_dependent` | constant-rate value |
| `line_pm_3sigma_flux_3sigma_20d_ph_cm2_s` (if quoted) | `line_pm_3sigma_flux_3sigma_20d_time_dependent_ph_cm2_s` | constant-rate value |
| `spot_r90_Z20d` | `spot_r90_Z20d_time_dependent` | constant-rate value |
| `spot_r90_T3_day` | `spot_r90_T3_day_time_dependent` | constant-rate value |
| `spot_r90_flux_3sigma_20d_ph_cm2_s` | `spot_r90_flux_3sigma_20d_time_dependent_ph_cm2_s` | constant-rate value |
| `best_cut_id` / `best_cut_Z20d` | `best_time_dependent_cut_id` / `best_time_dependent_Z20d` | constant-rate pair (note: the best cut id may differ between conventions — print both ids) |
| `broad_Z20d` (if quoted) | `broad_Z20d_time_dependent` | constant-rate value |

Known quote sites: generator lines ≈151, 179–180, 206–209, 235–237. The W1
quote `A_reference_final_Z_20d` (0.766916) and
`A_reference_T3_day_extrapolated_constant_profile` (306.04) are **already**
the time-dependent step08 chain — leave them, but make the labeling say so.
Lines 235–237 quote `w1`/`w2` dicts for background/signal cps — keep those cps
values (they are rates, not folds), but the Z20d quoted alongside should come
from the step08 time-dependent keys per the table above.

Where the report text says "Z20d", make the headline sentence read
"time-dependent fold (headline)" with "constant-rate variant" in parentheses —
mirroring Project_Memory's convention.

**A2.2 Optional (nice-to-have, small):** add one line quoting A4's
`headline_statistical_uncertainty.csv` numbers (`B ± δB`, `Z ± δZ`) for W2 and
spot_r90 if A4 completed successfully.

**A2.3 Run.** Archive `outputs/reports/experiment_report_20260601/` per
guardrail 4, then `python3 code/tools/build_experiment_report_20260601.py`.

**A2.4 Acceptance.**
- New report quotes: W2 `Z20d=2.7354…` (const `2.7502…` as variant),
  spot_r90 `Z20d=4.5078…`, `T3=8.179…`, `flux=6.6551…e-05` (constants as
  variants), W1 `0.766916` / `306.04` labeled as already-time-dependent.
- No remaining bare constant-rate headline (grep the new MD for `2.75023`,
  `4.52748`, `6.62620e-05`/`6.626196e-05` — they may appear only as labeled
  variants).
- Validator PASS.

---

## A5. CsI activation anchor (referee item #5): analytic I-128 cross-check

**Goal.** The activation chain currently has no external benchmark. Build a
self-contained analytic anchor for the dominant CsI activation product
(I-128, t½ = 24.99 min, from I-127(n,γ)) and compare with the chain's day-15
inventory. Documentation deliverable — changes no science authority.

**A5.1 Chain side.** Sum the day-15 I-128 activity (ZA = 53128) over all CsI
volumes from `runs/step02_decay_source_equiv2602_aligned/activation_inventory_day15.csv`
(cross-check against
`outputs/reports/day15_complete_report/activation_inventory_day15_after_groundstate_fix.csv`).
Get the total CsI active-shield mass from the geometry mass budget (locate via
`grep -ril "mass" outputs/geometry stepwise_maintenance/outputs/geometry` —
there is a mass-budget CSV; each CsI shield piece is ~1.5 kg per the inventory
mass column). Compute the specific activity `Bq/kg`.

**A5.2 Analytic side.** Saturation activity per kg CsI:
`A_sat = N_I127_per_kg × ∫ φ(E) σ(E) dE`, with
- `N_I127_per_kg(CsI) = (126.904/259.81) × (1000/126.904) × 6.022e23 ≈ 2.32e24`,
- σ(I-127(n,γ)): thermal `6.2 b` at 0.0253 eV with 1/v shape below ~1 keV,
  plus resonance integral `RI ≈ 150 b` applied to the epithermal
  per-lethargy flux,
- φ(E): the EXPACS/PARMA atmospheric neutron spectrum at float altitude
  already used by the chain — take it from the Step02/Step06 EXPACS inputs
  (see `code/tools/run_equiv2602_pipeline_NEW_GEO.py` for where the EXPACS
  tables/parameters live; if only integral fluxes are convenient, a
  thermal+epithermal two-group estimate is acceptable — state the grouping).
Since t½ = 25 min ≪ 15 days, day-15 I-128 is at saturation with the local
production rate: `A_chain ≈ R_production`.

**A5.3 Compare and write up** in
`stepwise_maintenance/step03_delay_source/outputs/csi_activation_anchor_20260611.md`
(+ a small CSV next to it with the numbers):
- table: chain Bq/kg vs analytic Bq/kg, ratio;
- expected agreement: order of magnitude (factor ≲3–5 is a pass — geometry
  self-shielding, local moderation, and the two-group approximation account
  for that). If the ratio exceeds ~10, flag it prominently as a **finding**
  (do not "fix" anything) and put it in the execution report.
- include a short "literature slots" section: named placeholders for published
  CsI instrument activation comparisons (e.g. INTEGRAL/PICsIT CsI experience,
  proton-irradiation CsI activation measurements) with TODO marks for the
  user to fill citations — do not invent citation details. If you have
  verified web access, you may fill them with properly checked references.

---

## Final phase: documentation sync + validator

1. Run `python3 code/tools/validate_new_geo_re.py` — must be PASS.
2. **`Project_Memory.md` updates** (surgical edits, keep its structure):
   - `Pending Fix Reference` #7: mark the three sub-items **DONE 2026-06-11**
     (Route B disk sigma fix — A1; ledger regenerated + Step05 rerun +
     step08 refresh — A3; experiment report regenerated on time-dependent
     keys — A2), each with one line saying what changed and the output path.
   - `What Not To Misquote`: rewrite the two related bullets — the Step05
     science-decomposition bullet now says the ledger was fixed 2026-06-11
     (old reports normalized to 50.89 remain wrong to quote); the
     experiment-report bullet now says the report was regenerated 2026-06-11
     and old copies/archives must not be quoted.
   - `Current State`: one line each — Route B disk now sigma-correct
     (numbers updated); Step05 science decomposition now on 15.29928;
     headline uncertainties available (quote the A4 numbers:
     `W2 B=… ± …`, `spot_r90 B=… ± …`, `Z=… ± …`).
   - `Route B` section: remove/replace the narrowed-proxy caveat with the fix
     note (keep one line of history: "was FWHM-narrowed until 2026-06-11").
   - `Fast Authority Map`: un-STALE the final Route-A report row; add rows for
     `headline_statistical_uncertainty.csv` and the CsI activation anchor MD.
   - `Review Verdict → Publication readiness`: annotate item 1 (statistical
     uncertainties) as "quantified 2026-06-11 (A4); remaining option is to
     extend MC statistics"; item 5 as "analytic anchor added 2026-06-11 (A5);
     literature citations still to fill".
3. **`Project_List.md`**: update the REVIEW-ADD ledger warning to say the
   mainline CSV was regenerated at 15.29928 on 2026-06-11 — migration should
   copy the fixed CSV, and the warning now reduces to "regenerate whenever
   optics authority or geometry changes".
4. Finish `CODEX_A_SERIES_EXECUTION_REPORT_20260611.md` (per guardrail 8):
   before/after numbers for A1 disk row, A3 science rows + step08 deltas,
   A4 table, A2 quote diff summary, A5 ratio. List any deviations from this
   plan explicitly.
