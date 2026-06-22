# New Memory: Exactpos Closure Continuation

Last updated: 2026-06-14

## Current Objective

Close the remaining `fullstat_v2_exactpos` work end to end. The support-size
and seed convergence item is now closed by transport-backed evidence; the
remaining work is documentation/validator consistency and final verification.

## Current Evidence

- `fullstat_v2` authority:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_20260612/`
  with W2 background `0.0729576 cps`, `Z20d=5.70221`, and
  `F_3sigma(1Ms)=6.82301e-5`.
- Exact-position closure:
  `outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/`
  with W2 background `0.0624651 cps`, `Z20d=6.15522`, and
  `F_3sigma(1Ms)=6.32564e-5`.
- Current exactpos transport uses 5000 sampled `PointSource` support blocks,
  `seed=260613`, `SE=ID=1,000,000`, and `TE=11530.473845 s`.
- `python3 code/tools/validate_v3p5_exactpos_closure.py --label fullstat_v2_exactpos`
  passed after the provisional-authority and sampling-audit repairs.
- Convergence report:
  `outputs/reports/v3p5_exactpos_convergence_20260614/` has
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE` and recommends
  `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`.
- The convergence set has four transport-backed cases:
  `fullstat_v2_exactpos`, `fullstat_v2_exactpos_m05000_s260614`,
  `fullstat_v2_exactpos_m20000_s260613`, and
  `fullstat_v2_exactpos_m50000_s260613`.
- Convergence ranges: W2 delayed cps `0.187413`, W2 background cps
  `0.0111915`, `Z20d` `0.00550844`.

## Required Next Work

1. Rebuild and verify the exactpos boundary/performance reports so
   `authority_role` is `CURRENT_EXACT_POSITION_RATE_AUTHORITY`.
2. Rebuild and verify the fullstat_v2 reports so they are labeled
   `CONSERVATIVE_RADIALPROFILE_BASELINE_CROSSCHECK`.
3. Run final validators and stage the new convergence report, code, and docs.

## Guardrails

- Do not overwrite the existing `runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos`
  or `runs/step02_delayed_transport_v3p5_centerfinger_fullstat_v2_exactpos`
  products while running convergence cases.
- Do not promote exactpos authority from source-level sampling diagnostics
  alone; the decisive quantity is downstream delayed W2 rate / Step08
  sensitivity stability.
- The convergence report now proves exactpos stability with transport-backed
  evidence, so `fullstat_v2_exactpos` is current authority and `fullstat_v2` is
  the conservative radial-profile baseline cross-check.
