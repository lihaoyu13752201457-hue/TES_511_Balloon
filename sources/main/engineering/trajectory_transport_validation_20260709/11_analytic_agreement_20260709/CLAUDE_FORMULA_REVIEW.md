# Claude Formula Review - Trajectory Analytic Curve

Status: `CLAUDE_CORRECTED_FORMULA_RECOVERED_FROM_JSONL`

## Source

Claude/Fable5 session:
`/home/ubuntu/.claude/projects/-home-ubuntu-TES-511-Balloon/9e439f14-1dc4-40e6-b2a6-e1326e236cf6.jsonl`

The exact model text appears in the tool result for the historical file:
`engineering/ENGINEERING_20260627_CURVE_CHECK/outputs/01_model_spec/corrected_analytic_curve_model.md`

That original engineering tree is no longer present in this checkout; this
review records the formula recovered from the chat log.

## Corrected Five-Layer Formula

Claude's corrected model is not the old Step06 single scalar. It splits the
mission-time curve into five physically separate curves:

1. Signal:
   `signal_rate(t) = F_511 * A_eff * T_atm_511(t) * epsilon_det`

2. Prompt background:
   `R_prompt_j(t) = sum_b Phi_b(t) * K_prompt[j,b]`

3. Activation production:
   `P_k(t) = sum_b Phi_b(t) * Y[k,b]`

4. Delayed inventory:
   `N_k(t+dt) = N_k(t) exp(-lambda_k dt) + P_k(t)/lambda_k * (1-exp(-lambda_k dt))`
   and `A_k(t) = lambda_k * N_k(t)`.

5. Delayed selected response:
   `R_delayed_j(t) = sum_k A_k(t) * epsilon[j,k]`

The key point is that `T_atm_511(t)` belongs only to the celestial signal. Local
prompt background and activation production must follow the local particle
field `Phi_b(t)` folded through response coefficients, not a shared atmospheric
transmission or depth/cutoff scalar.

## Relation To This Audit

The old scalar tested in `analytic_agreement_rows.csv` is:

`prompt_scale = exp((depth-depth_ref)/30 g cm^-2) * (11/Rc)^0.2`

That is the historical single-scalar proxy, not Claude's corrected model.

The `live_parma_species_weighted` rows in this audit are the current targeted
equivalent of Claude's prompt formula at particle-family resolution:

`R_prompt_j(t) / R_prompt_j(REF) = sum_b R_ref[j,b] * (Phi_b(t)/Phi_b(REF)) / sum_b R_ref[j,b]`

where `b in {eplus, n, gamma}` and `R_ref[j,b]` is the REF detector response rate
for the selected metric. This is why the combined 480--550 keV band is
consistent with `live_parma_species_weighted` but not with `step06_prompt_scalar`.

The continuous green curve in
`figures/analytic_curves_with_claude_source_response.png` is the same expression
evaluated for all 81 frozen trajectory bins and cached in
`claude_source_response_curve_by_time.csv`.

## Boundary

- Current targeted data can test the prompt family-response form for
  `eplus/n/gamma` in the TES 480--550 keV band and any-TES proxy.
- It does not restore the historical full4 W2 energy-angle response matrix.
- It does not validate activation production or delayed selected-rate layers.
- For W2, Claude's recovered conclusion remains: family-only response was still
  insufficient; pooled/regularized family-energy-angle response with uncertainty
  brought L1/L2/H1 back to about 1 sigma in the old full4 evidence.
