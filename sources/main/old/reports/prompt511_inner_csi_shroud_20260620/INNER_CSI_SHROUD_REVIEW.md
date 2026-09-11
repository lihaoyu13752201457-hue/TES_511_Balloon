# Prompt-511 Inner Active-CsI Shroud Review 2026-06-20

Status: `NO_PROMOTION__EPLUS_GATE_FAIL`

Candidate:

`outputs/reports/prompt511_inner_csi_shroud_20260620`

## Geometry

The candidate adds a native active-CsI shroud in the gap between the 60 K shield
and the vacuum jacket:

- `r=11.6..12.8 cm`
- `z=-13..13.35 cm`
- open signal port: `phi=171..189 deg`, `z=-7.2..-3.2 cm`
- estimated added CsI mass: `10.8485 kg`

New CsI volumes have low-threshold `.det` scintillator entries and names
beginning with `CsI_`, so the Step05-like proxy treats them as active veto
volumes.

## Checks

- Geometry/source builder: `python3 -m py_compile ...` passed.
- Source cards: 8 fullsphere cards, 20 `FarFieldAreaSource` beams each,
  `farfield_radius_cm=60`, no ROI/spot/focal/PointSource restriction.
- Fresh overlap command completed with exit code 0 and no visible
  `GeomVol`/`G4Exception` overlap warning.
- Prompt-only e+ transport completed `4/4` jobs.

## Prompt Gate

Step05-like L1 proxy:

| case | e+ L1-like events | e+ L1-like cps |
|---|---:|---:|
| current baseline | 80 | 0.0543377485 |
| inner active-CsI shroud | 30 | 0.0407121124 |

This fails the e+ decision gate:

- continue threshold: `<=0.020 cps`
- hard stop threshold: `>0.0276 cps`
- observed: `0.0407121124 cps`

Projected prompt total with only e+ replaced is `0.0454571 cps`, or `1.406x`
old `new_geo_re` prompt total. Therefore this candidate should not spend
additional n/mu/isotope budget.

## Interpretation

Active CsI in the inner vacuum gap alone does not restore the old-like prompt
level. It provides some active veto and material, but it does not remove enough
of the side-wall/upper-z 511 coupling. The next candidate should include a
thin inner W shadow to directly attenuate inward 511 rays, while using CsI only
as an active/old-like upper shroud rather than as the sole attenuator.
