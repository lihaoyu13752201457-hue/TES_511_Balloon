# Trajectory transport validation — 20260709 re-run

Harness-based **re-instantiation** of the multi-point trajectory validation after the original 20260626/20260627 packages were lost.

## Quick status

- **Points frozen:** REF / L1 / L2 / H1  
- **Live PARMA:** **fixed** (`cwd=parma_cpp`); multi-species spectra rebuilt  
- **Cosima smoke:** 4 pts × {eplus 50k, n 30k, gamma 60k} — 12/12 OK (`04_prompt_smoke/`)  
- **Cosima targeted:** 4 pts × {eplus **1e6**, n **2e5**, gamma **5e5**} — **12/12 OK** (`05_targeted_stats/`)  
- **Claim level:** `TARGETED_STATS_NOT_FULL4` — not Fable5 full4 / W2 / activation / delayed  
- **Full4 / delayed / Step05 W2:** **not** yet  

See `00_manifest/FINAL_STATUS.md` for residual tables and honest bounds.

## Headline residuals (targeted e+ 1e6 — primary)

| Layer | Finding |
|-------|---------|
| Env (live PARMA vs analytic \(S\)) | \(Q_{\rm env}(e+)\) ≈ 0.93–1.07; n/γ up to ~±16% |
| e+ band vs live PARMA | \(Q_{\rm band}\) ≈ **0.994–1.003** (~5e4 band counts/pt) |
| e+ band vs analytic | \(Q_{\rm band}\) ≈ **0.933–1.069** (env-layer systematic) |
| Combined band vs PARMA e+ | \(Q\) ≈ **0.997–1.002** |

Smoke (50k e+) remains under `04_prompt_smoke/` as pipeline baseline; **use targeted numbers for residuals**.

## Layout

| Path | Content |
|------|---------|
| `00_manifest/` | harness + FINAL_STATUS |
| `01_points/` | frozen validation points + analytic predictions |
| `02_sources/parma_live/` | live PARMA scales/meta |
| `02_sources/spectra_live/{pt}/` | 20-bin PDFs per species |
| `04_prompt_smoke/` | medium-smoke Cosima + Q |
| `05_targeted_stats/` | **targeted** Cosima + Q + figures + decision |
| `10_curve_validation/figures/` | analytic curve + MC overlay (from targeted) |
| `scripts/run_targeted_stats_escalation.py` | targeted Cosima runner |
| `scripts/extract_targeted_stats.py` | TES/band Q extract |
| `scripts/test_extract_targeted_stats.py` | unit tests for extract |
| `scripts/plot_analytic_curve_vs_mc.py` | curve-overlay figures (prefers targeted CSV) |

## Figures (analytic curve + MC points)

```bash
python3 engineering/trajectory_transport_validation_20260709/scripts/plot_analytic_curve_vs_mc.py
```

| File | Content |
|------|---------|
| `figures/analytic_curves_with_validation_points.png` | **Fable5-style** 3 curves + NEW targeted Cosima e+ band points |
| `figures/tes_w2_cumulative_significance.png` | **Fable5-style** 20d cumulative Z + validation-day markers + \(Q\) diagnostic |
| `figures/*_reference_fable5_style.png` | user-supplied originals (backup) |
| `figures/analytic_curve_overlay_paperstyle.png` | clean single-panel: \(S(t)\) + e+ band MC + live PARMA |
| `figures/analytic_curve_vs_mc_points.png` | main 2-panel: scale overlay + \(Q\) residual |
| `figures/analytic_curve_mc_diagnostics.png` | 4-panel multi-species / env / Q bars |

```bash
# Regenerate the two Fable5-style figures with targeted MC points
python3 engineering/trajectory_transport_validation_20260709/scripts/plot_fable5_style_two_figures.py
```

## How to re-run

```bash
# Targeted matrix (long) then extract + plot
python3 engineering/trajectory_transport_validation_20260709/scripts/run_targeted_stats_escalation.py
python3 engineering/trajectory_transport_validation_20260709/scripts/extract_targeted_stats.py
python3 engineering/trajectory_transport_validation_20260709/scripts/plot_analytic_curve_vs_mc.py
python3 engineering/trajectory_transport_validation_20260709/scripts/test_extract_targeted_stats.py
```

Requires: `phase2_parma_grid_driver` with cwd `parma_cpp`, Cosima + `geant4.sh` env, Mass_model geometry path in script.

## Relation to recovered chat package

`../trajectory_curve_validation_RECOVERED_20260709/` holds historical full4 numbers from Fable5 (16.6% / 19.5% / 60.7%).  
This 20260709 tree **does not** claim numerical identity with those residuals; it confirms the env-layer single-scalar coarseness at targeted e+ TES/band stats.
