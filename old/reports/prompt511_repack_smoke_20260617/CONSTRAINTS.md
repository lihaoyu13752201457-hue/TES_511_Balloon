# Prompt-511 Repack Smoke Constraints (2026-06-17)

Purpose: fast, non-authority smoke test for a local side-entry geometry repack
that reserves a high-Z prompt-511 shadow liner.

Always re-read this file before continuing work in this directory.

## Authority Boundaries

- Current paper-facing rate authority remains
  `fullstat_v2_exactpos_m50000_s260613`.
- This directory is a design smoke branch only. Do not replace or edit the
  authority geometry under `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/`.
- Do not quote smoke rates as manuscript sensitivity. Use them only to decide
  whether the CAD direction is worth a full Step02/Step05/activation rerun.
- `1of10` and lower statistics are closure checks, not rate authority.

## Required Scope

- Work only under `outputs/reports/prompt511_repack_smoke_20260617/` and run
  products under its `runs/` subdirectory.
- Start from the current v3p5 geometry copy, then make only local changes needed
  to reserve a W shadow-liner volume.
- Keep the signal sector open: `phi=[160,200] deg`.
- Compare prompt and delayed backgrounds directly in the line window
  `510.58 <= TES_total_keV < 511.42`.
- Do not apply active-veto, Compton/FoV, spatial, Step06, Step07, or Step08
  corrections in this smoke.
- Reuse existing source and SIM parsing conventions where practical.

## Geometry Design Under Test

- Add segmented W liner around the local z axis:
  - material `W`
  - `r=[4.25,5.95] cm`
  - `z=[-8.75,-0.65] cm` and `z=[0.65,4.65] cm`
  - open signal sector `phi=[160,200] deg`
- Repack local can/support interference just enough to clear this annulus:
  compact the local Nb/Cryoperm/Al side-entry can panels inward, shorten local
  Cu off-axis cold fingers, and move the local CuNi continuous heat exchanger
  radially outside the W liner.
- This is an engineering smoke. It intentionally tests whether a real reserved
  high-Z volume would suppress prompt; it is not a mechanically final CAD.

## Comparison Plan

1. Build copied/repacked geometry and migrated source cards.
2. Run Cosima overlap check. No `GeomVol1002` overlap warnings are acceptable
   for the candidate geometry.
3. Run small prompt transport. Prefer all-particle low-stat if runtime allows;
   prompt-eplus-only is acceptable as a first discriminator because prompt W2 is
   eplus dominated.
4. Build and run a small delayed source from matching buildup products if
   feasible. A delayed replay using the old inventory through the repacked
   geometry is only a transport smoke and must be labeled as missing new-W
   activation add-back.
5. Parse SIMs directly and report raw line-window TES rates and event counts.

## Known Risks

- W liner prompt suppression from the analytic 80-event screen is an upper
  bound until MC includes W self-emission, scattering refill, and activation.
- Any delayed comparison that does not rebuild activation from the new geometry
  misses new W activation.
- Low-stat zero or few-event outcomes must be reported with Poisson limits or
  explicit low-stat caveats.
