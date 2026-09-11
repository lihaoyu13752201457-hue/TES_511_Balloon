# Stats gap vs Fable5 ARGUE — what more events can and cannot fix

## Short answer

| Question | Answer |
|----------|--------|
| Is the difference from Fable5 **only** low statistics? | **No.** Partly stats (W2/activation), but **e+ band residual is already systematic**. |
| Can we top up events to become **the same** as Fable5? | **Not with events alone.** Need Step05 W2 + activation/delayed + ~full4 primaries. |
| What is running now? | Targeted: e+ **1e6**, n **2e5**, γ **5e5** per point (×4). |

## Why e+ band is already not a stats problem

Current smoke (50k e+/pt): ~2700 events in 480–550 keV TES proxy per point  
→ Poisson relative error ≈ **1.9%**.

Observed residual vs analytic \(S\): **~6–11%**.  
→ residual ≫ Poisson ⇒ **env-layer systematic** (analytic scalar vs live PARMA), not counting noise.

More e+ will tighten error bars but **will not erase** the L1-high / H1-low offset if the cause is \(S_{\rm analytic} \ne S_{\rm PARMA}\).

## Why Fable5 numbers need more than “bigger N”

| Fable5 observable | Reported residual (old scalar) | What it needs |
|-------------------|-------------------------------:|---------------|
| Prompt all-TES selected | 19.5% | Step05 selection, multi-species, high stats |
| Prompt **W2** selected | **60.7%** | Step05 W2 + ~1e7–1e8 primaries/pt |
| Activation production | 16.6% | Activation / isotope production campaign |

W2 rate scale (from recovered full4): ~37 REF W2 finals from ~1e8 primaries ≈ \(3.7\times10^{-7}\) per primary.

| e+ events / point | Expected W2-like counts (if same efficiency) |
|------------------:|---------------------------------------------:|
| 5e4 (current smoke) | ~0.02 |
| 1e6 (this targeted run) | ~0.4 |
| 1e7 | ~4 |
| 2.5e7 | ~9 (harness W2 min threshold ~10) |

So **1e6 still cannot claim W2 residual**. Matching Fable5 W2 argue needs **order full4** + **Step05**, not only Cosima gen-rate.

## This targeted campaign (in progress)

- Path: `05_targeted_stats/`
- Events: e+ 1e6, n 2e5, γ 5e5 × {REF,L1,L2,H1}
- Geometry / spectra: same Mass_model_511 + live PARMA as smoke
- Extract: still coarse TES det 1–6 + 480–550 (not W2)
- Expected claim after success: `TARGETED_STATS_NOT_FULL4` — tighter Q errors, confirm systematic stable

## Path to “same as Fable5 ARGUE”

1. Finish targeted → freeze e+ TES/band Q with small CI.  
2. Step05 W2 selection on sims (or re-run with StoreSimulationInfo compatible with ancestry).  
3. Scale to ≥1e7–full4 primaries if W2 expected counts <10.  
4. Separate activation production residual campaign.  
5. Delayed history-aware (still open in Fable5 too).

Only then can residual tables be compared apples-to-apples with recovered 16.6% / 19.5% / 60.7%.
