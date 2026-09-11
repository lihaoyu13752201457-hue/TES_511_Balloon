# Delayed candidate necessity audit

No transport was run.  This audit asks only what an unrealistically favorable
100% removal ceiling would have to remove in order to reach
`B_target = 0.016581812 cps`.

Two bases are kept separate:

- **official observed central:** `0.0544797522273 cps`; required reduction
  `0.0378979402273 cps` (69.57%);
- **full-inventory source-mix screen:** `0.0542275227384 cps`; required
  reduction `0.0376457107384 cps` (69.42%).

The first is the official central realization, not a deterministic component
yield.  The second is `A_k(15 d) * selected_k / realized_triggers_k` and
zero-imputes unsupported keys.  Neither is a candidate prediction.

## Optimistic 100% removal ceilings

| removed scope | official removed / residual (cps) | official pass? | source-mix removed / residual (cps) | screen pass? |
|---|---:|:---:|---:|:---:|
| MXC only | 0.01677150 / 0.03770826 | no | 0.01878838 / 0.03543914 | no |
| named Nb inner + Mu outer | 0.01557406 / 0.03890569 | no | 0.01304446 / 0.04118306 | no |
| all Nb + Mu material | 0.01696695 / 0.03751281 | no | 0.01357848 / 0.04064904 | no |
| all Copper material | 0.03639115 / 0.01808860 | no, short by 0.00150679 | 0.03968062 / 0.01454690 | yes, margin 0.00203491 |
| all Copper + Ag proxy | 0.03751281 / 0.01696695 | no, short by 0.00038513 | 0.04064904 / 0.01357848 | yes |
| all Copper + all Nb | 0.04559264 / 0.00888711 | yes | 0.04777505 / 0.00645247 | yes |
| all Copper + all Mu-metal | 0.04415660 / 0.01032315 | yes | 0.04516467 / 0.00906285 | yes |
| MXC + Nb inner + Mu outer + L0 | 0.03819506 / 0.01628469 | yes by 0.00029712 | 0.03931329 / 0.01491423 | yes by 0.00166758 |

These are ceilings: every selected event assigned to a removed group is set to
zero, no activity relocates to replacement material, no photon host migrates,
and signal is unchanged.  Real geometry changes can only be promoted by their
own production and decay transport.

## What is mathematically necessary

### Component partition

MXC must be involved under both bases.  Removing every other component group
while keeping MXC leaves `0.01677150 cps` official and `0.01878838 cps` in the
screen, both above target.  The official excess is only `0.00018968 cps`, but
it is positive.

No one-, two-, or three-component 100% deletion can close the target.  The
largest three-component official ceiling (MXC + Nb inner + Mu outer) removes
only `0.03234555 cps`; the largest three-component source-mix ceiling
(MXC + Nb inner + L0) removes `0.03382924 cps`.

The minimum cardinality is therefore four.  Only two four-bucket sets pass on
both bases:

1. MXC + Nb inner + Mu outer + L0;
2. MXC + Nb inner + Mu outer + `Other`.

`Other` is a heterogeneous accounting bucket, not a geometry operation.  The
unique all-named common ceiling is therefore MXC + Nb inner + Mu outer + L0.
Even this requires 99.22% of its combined official central rate, or 95.76% of
its source-mix rate, to disappear if the four groups scale together.  Its
official selected-position `Neff` is only 15.68.

### Material partition

Copper is necessary under both bases: even deleting every non-Copper material
leaves the Copper contribution, `0.03639115 cps` official or `0.03968062 cps`
screened, far above target.

- On the official central basis, deleting all Copper is still insufficient.
  It must be joined by at least 16.38% of the central Nb rate or 19.40% of the
  central Mu-metal rate under an additive perfect-removal assumption.  Copper
  + Ag is still insufficient.  Thus the minimum material-class ceiling is
  Copper + Nb or Copper + Mu-metal.
- On the source-mix screen, Copper alone is formally sufficient, but it must
  lose 94.87% of the screened Copper rate.  This is not evidence that a Copper
  topology works.
- Even if all non-Copper contribution vanished, at least 54.43% (official) or
  58.21% (screen) of the Copper contribution would still have to vanish.

The official/screen disagreement for all-Copper removal changes the verdict
from fail to pass, while its margins are only 0.0015–0.0020 cps.  Copper has
event `Neff=22.48`, position `Neff=17.74`, and only 92.77% coupling-supported
Bq coverage.  Its official position-weight fluctuation scale
`rate/sqrt(Neff_position)` is about `0.00864 cps`, several times larger than
either margin.  Therefore the screen pass is a central ceiling, not a
statistical proof.

## Can the present geometry/BOM define one simple topology?

No.  The current geometry shows that the needed accounting class is not one
piece:

- MXC is a separate 6 mm-thick, 15 cm-radius Copper plate;
- CP and Still are two additional separate 6 mm Copper plates;
- the can bottom is a 2 mm, 15.3 cm-radius Copper cap, with separate sidewalls;
- L0 is a separate 3.5 mm Copper disk, while L2–L5 are multiple 3 mm panel
  supports at different axial stations;
- the inner Nb and outer Mu-metal are separate closed approximately 2 mm
  magnetic shells;
- the remaining Copper bucket includes CP/Still plates, L3/L4 panels, can
  sidewalls, and Cu/CuNi heat-exchanger structures.

These definitions are in the frozen S3d-O8 geometry, but the available BOM does
not provide allowable per-piece removable mass, required thermal conductance,
support loads, interface/boss keep-outs, or minimum closed-shell magnetic
attenuation/field-cooling performance.  A material-wide 94.87% Copper-rate
removal would span many unrelated thermal and structural functions; the
official basis additionally requires changing a magnetic class.  Calling that
one topology would hide multiple independent design operations.

## Verdict and single blocker

- **KILL as sufficient:** MXC-only, Nb+Mu-only, and Copper+Ag-only.
- **MODIFY, not promote:** all-Copper is a source-mix mathematical pass but an
  official-central fail and would require near-total class elimination.
- **No delayed-only simple candidate is defined by present evidence.**

The single engineering blocker is a function-constrained BOM/topology map that
states, for each Copper piece and the Nb/Mu shells, the maximum allowed mass or
thickness change while preserving thermal, structural, assembly, and magnetic
requirements.  Without that map, every budget-closing delayed ceiling either
deletes mandatory shells/components or combines at least four independent
topologies.  Once one feasible topology is supplied, its own paired
BUILDUP -> inventory -> decay coupling is the statistical falsifier.

The 20-row machine-readable calculation, including position Neff, Bq coverage,
and pass margins, is `delayed_candidate_necessity.csv`.
