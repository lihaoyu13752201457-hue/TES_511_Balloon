# Ingress / Veto / Barrel-Shield Hypothesis Plan

Status: `PLANNING_ACTIVE_WITH_XHGIH_SUBAGENTS`

This branch is a new geometry-optimization/hypothesis test. It must not modify
the original `511_Mass`, `Mass_model_511`, fix5 authority geometry, or existing
paper-facing outputs.

## Roles

- Parent Codex: planning, gates, integration, final interpretation.
- `XHGIH-EXEC`: implementation and runs in this directory plus
  `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/`.
- `XHGIH-REVIEW`: independent review in
  `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_review/`.

## Required Evidence Products

1. `ingress_summary.{csv,json,md}`
   - Particles: prompt `e+`, prompt `n`, atmospheric `511`.
   - At minimum, report W2 final-candidate ingress proxies.
   - Preferred fields: source file, event id, source initial position/direction
     if available, first interaction or first RP/IP proxy, inferred surface
     bucket (`side`, `bottom`, `top`, `window/negative-x`, `unknown`), and the
     selection stage where the event appears.
   - If source INIT direction is unavailable or ambiguous in `.sim.gz`, state
     the fallback explicitly.

2. `veto_efficiency_summary.{csv,json,md}`
   - Stage chain must be explicit:
     `raw TES-window` -> `active_veto_pass` -> `side_compton_fov_pass`.
   - Active anticoincidence rejection:
     `1 - active_veto_pass / raw`.
   - Compton/FoV rejection conditional on active pass:
     `1 - side_compton_fov_pass / active_veto_pass`.
   - Total rejection:
     `1 - side_compton_fov_pass / raw`.
   - For `e+` and `n`, use current geo-opt Step05 / audit tables.
   - For atmospheric `511`, use the P2 replay:
     `engineering/geometry_optimization_20260704/06_atm511_replay_20260707/`.

3. Barrel-shield hypothesis geometry
   - New geometry only.
   - Preserve TES array geometry.
   - Preserve CsI scintillator position and shape as active veto.
   - Preserve external support structures requested by the user.
   - Remove or omit unrelated internal passive mass where feasible for this
     hypothesis test.
   - Add a cylindrical/barrel passive shield outside the retained detector.
     Primary candidate: W barrel. Secondary candidate if time permits:
     stainless-steel barrel.
   - Add a side window using thin aluminium aligned with the existing side
     window/opening.
   - Must include `.geo.setup`, `.geo`, `.det`, material file, manifest, and
     2D/WRL or equivalent geometry visualization.

4. Positron-only transport and response
   - Source card must point to the new barrel hypothesis geometry.
   - Run only `e+`.
   - If full-stat is too long, run smoke first and mark it as smoke. The source
     card and scripts must be full-stat extensible.
   - Report raw W2 TES-window rate/count, active-veto pass, Compton/FoV pass,
     and survival/rejection ratios.
   - Compare against current geo-opt e+ W2 reference:
     raw `0.0421003740822 cps`, active pass `0.0271615316659 cps`,
     final `0.0237663402077 cps`.

## Current Reference Numbers

Current geo-opt S1/BPE/W5 W2, without atmospheric 511:

| component | raw cps | active pass cps | final cps |
|---|---:|---:|---:|
| prompt all | 0.0950096805511 | 0.0359824168078 | 0.0325872253496 |
| prompt e+ | 0.0421003740822 | 0.0271615316659 | 0.0237663402077 |
| prompt n | 0.0407117775780 | 0.0088208851419 | 0.0088208851419 |
| delayed | 0.00451240053468 | 0.00322314323906 | 0.00279339080718 |

Atmospheric 511 current geo-opt W2 replay at planning time
(superseded on 2026-07-08 by the 4pi sidecar replay in
`engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/`):

| stage | events | transfer cps/(ph cm^-2 s^-1) |
|---|---:|---:|
| raw TES-window | 108 | 0.407064836383 |
| active pass | 108 | 0.407064836383 |
| final side/FoV pass | 95 | 0.358066291262 |

The superseding 2026-07-08 sidecar W2 cutflow is `114/114/107`, with final
nominal atmospheric-511 rate `0.0207913135058 cps` and sidecar-included
`F3(20d) = 4.62986036016e-05 ph cm^-2 s^-1`.

## Interpretation Gates

- Do not claim a barrel geometry win from transport attenuation alone unless the
  source card, geometry path, and event selection are all verified.
- Do not mix "plastic material present" with "plastic counted as active veto".
- Do not use active-veto efficiency with `final` as denominator. The denominator
  is raw TES-window candidates.
- Do not use Compton/FoV efficiency with `raw` as denominator unless it is
  explicitly named total rejection; the conditional denominator is active-pass.
- A positron-only smoke run can show a qualitative direction, but it cannot
  replace full-stat e+ production or all-particle background closure.
- A simplified geometry that removes internal passive materials is a hypothesis
  test, not a replacement geometry. Any reduction may come from removing
  annihilation/passive scattering sites rather than from the external barrel
  alone.

## Success Criteria For This Branch

- `XHGIH-EXEC` produces the required statistics and a new geometry/run package.
- `XHGIH-REVIEW` independently signs off or flags specific blockers.
- Parent Codex reports what is proven, what is smoke-only, and what should be
  simulated next.
