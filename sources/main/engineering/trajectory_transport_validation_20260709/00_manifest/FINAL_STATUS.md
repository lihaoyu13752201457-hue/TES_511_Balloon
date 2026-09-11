# FINAL_STATUS — trajectory_transport_validation_20260709

**Status:** `TARGETED_STATS_NOT_FULL4`  
**Date:** 2026-07-09  
**Claim level:** `TARGETED_STATS_NOT_FULL4` — **not** Fable5 full4, **not** Step05 W2, **not** activation/delayed, **not** manuscript-promotable end-to-end curve validation.

## Gates

| Gate | Result |
|------|--------|
| G0 authority lock | PASS — Mass_model geometry + Step06 trajectory + harness |
| G1 validation points | PASS — REF / L1 / L2 / H1 frozen |
| G2 sources | PASS — live PARMA (`cwd=parma_cpp`) multi-species spectra |
| G3 prompt smoke | PASS — 4 pts × {e+,n,γ} at 50k/30k/60k (`04_prompt_smoke/`) |
| G3b targeted stats | **PASS transport** — 4 pts × {e+ **1e6**, n **2e5**, γ **5e5**}, **12/12** gzip OK |
| Curve claim | **NOT** full4-validated; env-layer systematic confirmed at high e+ band stats |

## Targeted campaign (primary result)

| Item | Value |
|------|-------|
| Path | `05_targeted_stats/` |
| Events / point | e+ 1 000 000, n 200 000, γ 500 000 |
| Primaries total | 6.8e6 (instant, 3 species × 4 points) |
| Wall (parallel 3) | ~21 min Cosima matrix |
| TES proxy | HTsim energy **field[4]**; det IDs 1–6; band 480–550 keV |
| Tables | `05_targeted_stats/targeted_prompt_results.csv`, `combined_species_Q.csv` |

### Live PARMA environment vs analytic \(S_{\rm prompt}\)

| Point | analytic \(S\) | scale e+ | \(Q_{\rm env}(e+)\) | \(Q_{\rm env}(n)\) | \(Q_{\rm env}(\gamma)\) |
|-------|---------------:|---------:|--------------------:|-------------------:|-------------------------:|
| REF | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| L1 | 1.053 | 1.125 | **1.069** | **1.159** | **1.141** |
| H1 | 0.965 | 0.897 | **0.930** | **0.860** | **0.880** |
| L2 | 1.052 | 1.115 | **1.059** | **1.143** | **1.134** |

### e+ band / TES at targeted stats (~5.3e4 band counts / point)

| Point | n_band | band/REF | \(Q_{\rm band}\) vs analytic | \(Q_{\rm band}\) vs PARMA | \(Q_{\rm TES}\) vs analytic | \(Q_{\rm TES}\) vs PARMA |
|-------|-------:|---------:|-----------------------------:|--------------------------:|----------------------------:|-------------------------:|
| REF | 53532 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| L1 | 52900 | 1.125 | **1.069** | **1.000** | 1.082 | 1.013 |
| H1 | 54218 | 0.900 | **0.933** | **1.003** | 0.921 | 0.990 |
| L2 | 52647 | 1.108 | **1.053** | **0.994** | 1.068 | 1.008 |

**Verdict (targeted e+):** band and TES rates track **live PARMA** to ~1%. Residual vs analytic \(S\) is the **env-layer scalar mismatch** (~−7% H1 to +7% L1), **not** Poisson noise (band Poisson ≈ 0.4% at 5e4 counts).

### Combined multi-species band \(Q\) (e+-dominated)

| Point | \(Q_{\rm band}\) vs analytic | \(Q_{\rm band}\) vs PARMA e+ |
|-------|-----------------------------:|-----------------------------:|
| L1 | 1.069 | 1.000 |
| H1 | 0.927 | 0.997 |
| L2 | 1.062 | 1.002 |

n/γ 480–550 band counts remain O(70–90) even at targeted stats — **do not** use species-specific n/γ band \(Q\) as physics evidence.

## Explicit non-claims (vs Fable5 ARGUE)

| Fable5 recovered claim | This package |
|------------------------|--------------|
| Prompt all-TES residual 19.5% (old scalar) | **Not re-measured** with Step05 selection |
| Prompt W2 residual 60.7% | **Not run** — expected W2 counts ≪1 at 1e6 e+/pt |
| Activation production 16.6% | **Not run** |
| Family-response / LOO fine residual | **Not run** |
| Decision `FULL4_…_DEVIATES_…` | **Not authorized** — claim stays `TARGETED_STATS_NOT_FULL4` |

Directional agreement only: single-scalar analytic \(S_{\rm prompt}\) is coarse relative to multi-point live environment; MC follows the environment, not the frozen scalar.

## Smoke baseline (still retained)

Lower-stats campaign under `04_prompt_smoke/` (e+ 50k / n 30k / γ 60k) remains as pipeline proof. Targeted results supersede smoke for residual numbers.

## Figures

Regenerated from **targeted** e+ rates:

- `10_curve_validation/figures/analytic_curve_overlay_paperstyle.{png,pdf}`
- `10_curve_validation/figures/analytic_curve_vs_mc_points.{png,pdf}`
- `10_curve_validation/figures/analytic_curve_mc_diagnostics.{png,pdf}`
- copies under `05_targeted_stats/figures/`

Regenerate:

```bash
python3 engineering/trajectory_transport_validation_20260709/scripts/plot_analytic_curve_vs_mc.py
```

## Artifact index

| Product | Path |
|---------|------|
| Targeted sims | `05_targeted_stats/per_point/{pt}/{particle}/` |
| Targeted Q table | `05_targeted_stats/targeted_prompt_results.csv` |
| Combined Q | `05_targeted_stats/combined_species_Q.csv` |
| Decision JSON | `05_targeted_stats/targeted_decision.json` |
| Stats-gap note | `05_targeted_stats/README_STATS_GAP.md` |
| Runner | `scripts/run_targeted_stats_escalation.py` |
| Extract | `scripts/extract_targeted_stats.py` |
| Unit tests | `scripts/test_extract_targeted_stats.py` |
| Plot | `scripts/plot_analytic_curve_vs_mc.py` |
| Logs | `logs/targeted/` |

## Next (if pursuing Fable5-equivalent)

1. Step05 W2 selection on high-stat sims (need ≫1e7 primaries/pt for usable W2).  
2. Activation production residual campaign.  
3. Delayed history-aware transport.  
4. Only then compare residual tables to recovered 16.6% / 19.5% / 60.7%.

## Link to chat recovery

`engineering/trajectory_curve_validation_RECOVERED_20260709/`
