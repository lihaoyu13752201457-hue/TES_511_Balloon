# Reconstructed residual summary

Source: Fable5 session narrative + recovered HTML slides + handoff/FINAL_STATUS fragments.  
Not a substitute for original `full4_*_residuals.csv` / `residual_summary.json`.

## Smoke stage (five points)

From recovered `FINAL_STATUS` fragment:

- G3/G4 transport: 680 jobs; 25,210,220 generated primaries (smoke)
- Activation smoke: `prod_residual ≈ 0.1577`, `cu_residual ≈ 0.2317`
- Verdict: `LOWSTAT_SMOKE_DEVIATES_RUN_FULLSTAT`

## Full4 vs old single-scalar curve

| Observable | max residual | p-value (reported) | Verdict |
|---|---:|---:|---|
| Activation production total | 16.6% | ≈0 | deviate |
| Prompt all-TES selected | 19.5% | 4e-14 | deviate |
| Prompt W2 selected | 60.7% | 0.025 | deviate |

Decision: `FULL4_PROMPT_ACTIVATION_DEVIATES_ANALYTIC_CURVE_PENDING_DELAYED_FULL`  
Full4 scale (reported): **544 jobs**, **~1.008e8** generated primaries scanned for W2 ancestry.

## After five-layer / family source-response correction

| Observable | old scalar | family response | finer model |
|---|---:|---:|---|
| Activation production | 16.6% | **1.1%** | χ² still nonzero — percent-level follow-up |
| Prompt all-TES | 19.5% | **4.4%** (p=0.42 consistent) | — |
| Prompt W2 | 60.7% | 48.9% | LOO pooled fine: max residual **17.9%**, p=0.71 |

### W2 LOO pooled fine response (recovered row numbers)

| point | direct_cps | REF_fine_pred | LOO_pooled_pred | LOO_combined_z |
|---|---:|---:|---:|---:|
| REF | 0.025106 | 0.025106 | 0.034823 | -1.949 |
| L1 | 0.042481 | 0.029767 | 0.036021 | 0.992 |
| L2 | 0.039478 | 0.029547 | 0.036632 | 0.448 |
| H1 | 0.029799 | 0.021579 | 0.027771 | 0.417 |

Note: REF LOO is leave-one-out prediction for REF using other points — expected tension; L1/L2/H1 are the out-of-sample checks (~1σ).

## W2 ancestry stats (reported)

- W2 raw events with ancestry: 524  
- Final side-selected: 192  
- REF W2 final side-selected: only **37** (why REF-only fine matrix is sparse)  
- Generated denominator scanned: 1.008e8 primaries; unassigned 0  

## TES-end fold overlay (reported)

With full4 points overlaid on existing Step06/Step08 W2 fold:

- \(Z_{20d}=7.8\), \(F_{3\sigma}=3.846\times10^{-5}\) **reproduced**  
- Delayed TES direct at four points: **not re-run** in that campaign  
