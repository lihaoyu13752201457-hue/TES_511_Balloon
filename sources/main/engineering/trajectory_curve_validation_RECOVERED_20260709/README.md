# Trajectory Curve Validation — Recovered Package (2026-07-09)

**Status:** `RECOVERED_FROM_CHAT_AND_LOGS_NOT_ORIGINAL_TREE`  
**Claim level:** Evidence reconstruction only. Does **not** restore full transport products, sim files, or authorize Step06 promotion.

## Why this package exists

The cleaned `TES_511_Balloon` checkout no longer contains:

- `engineering/trajectory_transport_validation_20260626/`
- `engineering/ENGINEERING_20260627_CURVE_CHECK/`
- `engineering/report_html_20260702_curve_atm511_revan/`

Recovery-log git snapshots show these paths as **untracked (`??`)** before disappearance — they were almost certainly never committed and were lost in a workspace cleanup, not “never done.”

This directory reconstructs the **scientific argument, numbers, point table, decisions, and path map** from:

1. Local Claude / **Fable 5** session  
   `~/.claude/projects/-home-ubuntu-TES-511-Balloon/9e439f14-1dc4-40e6-b2a6-e1326e236cf6.jsonl`
2. Tool-result fragments and HTML body recovered from that session
3. Cross-checks against still-present formula smokes under `old/docs/manuscript_legacy/`

**It cannot restore** the ~544-job Cosima corpus or binary sim outputs unless those files are found on another disk/backup.

---

## Core scientific argument (as of 2026-07-02 Fable5 report)

### Question

Can the Step06 **analytic mission-time curve** replace full transport at every flight state for 20-day \(Z\) / \(F_{3\sigma}\)?

### Old model (falsified on prompt + activation production)

- Signal: \(T_{\mathrm{atm},511}(t)=\mathrm{e}^{-\mu_{\mathrm{eff}} x(t)}\) (day-15 anchored).
- Prompt **and** activation production shared one scalar  
  \[
  s(t)=\exp\!\left[\frac{x(t)-x_{\mathrm{ref}}}{30\,\mathrm{g\,cm^{-2}}}\right]
  \left(\frac{11\,\mathrm{GV}}{R_c(t)}\right)^{0.2}.
  \]

**Root cause:** one scalar cannot jointly scale celestial 511 transmission, local prompt flux by particle family, and activation yields by family.

### Validation design (direct transport on the curve)

| ID | day | alt km | lat deg | lon deg | \(R_c\) GV | role |
|----|----:|-------:|--------:|--------:|-----------:|------|
| **REF** | 15.00 | 38.75 | 34.000 | 100.000 | 11.00 | anchor |
| **L1** | 3.75 | 36.25 | 34.156 | 99.750 | 10.98 | low early |
| **L2** | 18.75 | 36.25 | 33.944 | 100.125 | 11.01 | low late |
| **H1** | 6.25 | 41.25 | 33.750 | 100.043 | 11.02 | high |
| M1 (smoke only) | 10.00 | 38.75 | 34.244 | 100.086 | 10.98 | mid smoke |

Normalization used:

\[
Q(t)=\frac{R_{\mathrm{MC}}(t)/R_{\mathrm{MC}}(\mathrm{REF})}{S_{\mathrm{analytic}}(t)}.
\]

- **Smoke:** five points REF/L1/L2/H1/M1; gate verdict low-stat / deviate.  
- **Full4:** weighted prompt + activation at REF/L1/L2/H1 — **544 jobs, ~\(1.0\times10^8\) primaries**.

### Full4 decision (old scalar)

| Observable | max residual vs old scalar | note |
|------------|---------------------------:|------|
| Activation production total | **16.6%** | \(p\approx 0\) |
| Prompt all-TES selected | **19.5%** | \(p\sim 4\times10^{-14}\) |
| Prompt W2 selected | **60.7%** | \(p\sim 0.025\) |

Decision string:

```text
FULL4_PROMPT_ACTIVATION_DEVIATES_ANALYTIC_CURVE_PENDING_DELAYED_FULL
```

Boundary flags recovered from decision JSON fragment:

- `marks_curve_validated_full: false`
- `marks_model_correction_complete: false`
- `authorizes_delayed_full_replay: false`
- `authorizes_step06_07_08_rewrite: false`
- `edits_manuscript_source: false`

### Corrected five-layer model

1. **Signal:** \(F_{511}\,A_{\mathrm{eff}}\,T_{511}(t)\,\varepsilon\)  
2. **Prompt:** \(\sum_b \Phi_b(t)\,K_b\) (window needs \(K_{b,E,\theta}\))  
3. **Activation production:** \(\sum_b \Phi_b(t)\,Y_{k,b}\)  
4. **Delayed inventory:** production–decay ODE  
5. **Delayed selected counting:** \(\sum_k A_k(t)\,\varepsilon_k\) — **not directly validated**

### Residuals after correction (recovered table)

| Observable | old scalar | family response | family×E×θ / LOO |
|------------|----------:|----------------:|-----------------:|
| Activation production | 16.6% | **1.1%** | — |
| Prompt all-TES | 19.5% | **4.4%** (consistent, \(p=0.42\)) | — |
| Prompt W2 | 60.7% | 48.9% (still weak) | **17.9%** LOO pool, \(p=0.71\) |

W2 LOO combined \(z\) (pooled fine response): L1 **0.99**, L2 **0.45**, H1 **0.42**.

### Still open (must not over-claim)

1. **Delayed selected-rate layer** — no full time-specific delayed replay at the four points.  
2. **Step06 mainline patch** — only a plan (`07_step06_patch_plan/`); not promoted.  
   Current tree still carries the old single-scalar style constants in  
   `stepwise_maintenance/step06_mission_time_variation/code/build_step06_mission_time_variation.py`  
   (`PROMPT_ATTEN_DEPTH_G_CM2 = 30.0`, analytic depth–cutoff form).  
3. TES-end fold still **reproduced** headline \(Z_{20d}=7.8\), \(F_{3\sigma}=3.846\times10^{-5}\) when full4 points were overlaid on the legacy Step06/08 ledger — that is **consistency of the rate fold bookkeeping**, not promotion of a new time model.

---

## Two-package chain (historical layout)

```text
trajectory_transport_validation_20260626/
  00_manifest/ … 01_points/ … 02_sources/ …
  04_prompt_smoke/ 05_activation_smoke/ 06_history_model/
  07_delayed_sources/ 08_delayed_smoke/
  09_full_if_required/
    full_4point_prompt_activation_weighted/   # 544-job transport
    full_4point_curve_validation/             # decision + residuals
  10_curve_validation/
  scripts/

ENGINEERING_20260627_CURVE_CHECK/
  ENGINEERING.md, HANDOFF_20260627_CURVE_CHECK.md
  outputs/
    01_model_spec/corrected_analytic_curve_model.md
    02_source_flux_matrix/ 03_ref_response_matrix/
    04_corrected_curve_predictions/ 05_direct_comparison/
    06_statistics_vs_bias/ 07_step06_patch_plan/
    08_manuscript_support/ 09_report/ (html + assets)
    10_tes_rate_sensitivity/ 11_source_ancestry/
  scripts/build_curve_check_outputs.py

report_html_20260702_curve_atm511_revan/
  report.html, figs/, README.md, claims_metrics.json
```

See `recovered_path_inventory.txt` for every path string scraped from the Fable5 session.

---

## What is in *this* recovery directory

| Path | Content |
|------|---------|
| `README.md` | This file — full scientific recovery |
| `RECONSTRUCTED_full4_validation_decision.json` | Decision object rebuilt from chat fragments |
| `RECONSTRUCTED_validation_points.csv` | REF/L1/L2/H1/(M1) table |
| `RECONSTRUCTED_residual_summary.md` | Old vs corrected residual numbers |
| `recovered_partial_report.html` | Partial 14-slide HTML body (section ① complete in text; images missing) |
| `extracted_fragments/` | Raw chat tool dumps |
| `extracted_json/` | Any parseable JSON blobs |
| `SOURCE_PROVENANCE.md` | Session IDs, dates, recovery method |

## What is *not* here

- Cosima `.sim.gz` / job trees for 544 runs  
- Original residual CSVs with full per-point rows  
- Original PNG assets under `09_report/assets/`  
- Promoted Step06 code patch  

---

## Relation to still-present “formula smokes”

Do **not** confuse with:

- `old/docs/manuscript_legacy/time_axis_smoke_audit_20260617.*`  
  → recomputes analytic formula at 3 probes; **no** multi-point detector transport.  
- `old/docs/manuscript_legacy/delayed_distribution_invariance_smoke_20260617.*`  
  → PARMA family reweight \(D_{TV}<6\times10^{-3}\); **no** full4.

Those smokes support bookkeeping / distribution-shape necessity; **full4 is the direct-transport falsification**.

---

## Recommended next actions

1. **Search backups** for directory names above; restore under `engineering/` and add to git.  
2. Until restore: paper § mission-time must either  
   - cite this recovery + state “full4 products offline,” or  
   - keep the old scalar with an honest limitation that it was falsified for prompt/activation.  
3. **Do not** silently treat current Step06 as “validated multi-point transport.”  
4. Optional: re-run a reduced full4 (4 points × prompt/buildup only) from the harness if sources still exist in `runs/` under old names.

---

## Honest one-liner for the manuscript

> Multi-point direct transport at four trajectory states (REF/L1/L2/H1) falsified the single-scalar mission-time model for prompt and activation production; a five-layer source-response model restores agreement at those layers. Delayed selected-rate validation and mainline Step06 promotion were not closed. The original evidence tree is missing from this checkout and is reconstructed here from session logs.
